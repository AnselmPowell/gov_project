from typing import Dict, List, Tuple
import time
from datetime import datetime
from llama_parse import LlamaParse
from django.conf import settings
from ..models import GovernanceDocument, DocumentChunk
from .monitoring.system_monitor import SystemMonitor, ProcessStage
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import requests
import mimetypes
from docx import Document as DocxDocument
from io import BytesIO
from odf import text, teletype
from odf.opendocument import load

class TextChunker:
    """Efficient text chunking with minimal complexity"""
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        print(f"\n[TextChunker] Initializing with chunk_size={chunk_size}, overlap={overlap}")
        self.chunk_size = chunk_size
        self.overlap = min(overlap, chunk_size // 2)  # Ensure overlap isn't too large
        print(f"[TextChunker] Adjusted overlap size: {self.overlap}")

    def split_text(self, text: str) -> List[Dict[str, any]]:
        print(f"\n[TextChunker.split_text] Starting text chunking")
        print(f"[TextChunker.split_text] Input text length: {len(text)}")
        
        words = text.split()
        chunks = []
        current_position = 0
        
        while current_position < len(words):
            end_position = min(current_position + self.chunk_size, len(words))
            chunk_text = ' '.join(words[current_position:end_position])
            chunk_data = {
                'text': chunk_text,
                'size': end_position - current_position,
                'start_pos': current_position,
                'end_pos': end_position
            }
            chunks.append(chunk_data)
            current_position = end_position - self.overlap
            if current_position >= len(words) - self.overlap:
                break
            if current_position <= chunks[-1]['start_pos']:
                current_position = chunks[-1]['start_pos'] + 1
        
        print(f"[TextChunker.split_text] Finished chunking. Total chunks created: {len(chunks)}")
        return chunks

class DocumentPageExtractor:
    """Handles page extraction for different file types"""
    
    @staticmethod
    def extract_pdf_pages(file_path: str) -> List[Tuple[str, int]]:
        """Extract pages from PDF"""
        print(f"[extract_pdf_pages] Processing PDF: {file_path}")
        pages = []
        with fitz.open(file_path) as doc:
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                content = page.get_text("text")
                if content.strip():
                    pages.append((content, page_num + 1))
                    print(f"[extract_pdf_pages] Extracted page {page_num + 1}")
        return pages

    @staticmethod
    def extract_docx_pages(file_path: str) -> List[Tuple[str, int]]:
        """Extract pages from DOCX using section breaks"""
        print(f"[extract_docx_pages] Processing DOCX: {file_path}")
        doc = DocxDocument(file_path)
        pages = []
        current_page = []
        page_number = 1

        for paragraph in doc.paragraphs:
            if '\f' in paragraph.text or not current_page:  # Page break or start
                if current_page:
                    content = '\n'.join(current_page)
                    if content.strip():
                        pages.append((content, page_number))
                        print(f"[extract_docx_pages] Extracted page {page_number}")
                    page_number += 1
                    current_page = []
                current_page.append(paragraph.text)
            else:
                current_page.append(paragraph.text)

        # Add the last page
        if current_page:
            content = '\n'.join(current_page)
            if content.strip():
                pages.append((content, page_number))
                print(f"[extract_docx_pages] Extracted final page {page_number}")

        return pages

    @staticmethod
    def extract_odt_pages(file_path: str) -> List[Tuple[str, int]]:
        """Extract pages from ODT using paragraph breaks"""
        print(f"[extract_odt_pages] Processing ODT: {file_path}")
        doc = load(file_path)
        pages = []
        current_page = []
        page_number = 1
        
        for paragraph in doc.getElementsByType(text.P):
            content = teletype.extractText(paragraph)
            
            if not content.strip() and current_page:  # Use empty paragraphs as page breaks
                page_content = '\n'.join(current_page)
                if page_content.strip():
                    pages.append((page_content, page_number))
                    print(f"[extract_odt_pages] Extracted page {page_number}")
                page_number += 1
                current_page = []
            else:
                current_page.append(content)

        # Add the last page
        if current_page:
            page_content = '\n'.join(current_page)
            if page_content.strip():
                pages.append((page_content, page_number))
                print(f"[extract_odt_pages] Extracted final page {page_number}")

        return pages

class GovernanceDocumentProcessor:
    def __init__(self, monitor: SystemMonitor, batch_size: int = 3):
        print("\n[GovernanceDocumentProcessor] Initializing document processor")
        self.parser = LlamaParse(
            api_key=settings.LLAMA_PARSE_KEY,
            result_type="markdown",
            num_workers=4,
            verbose=True,
            language="en"
        )
        self.chunker = TextChunker()
        self.monitor = monitor
        self.batch_size = batch_size
        self.data_dir = Path("governance_analysis/services/data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        print(f"[GovernanceDocumentProcessor] Initialization complete with batch_size={batch_size}")

    def _download_file(self, url: str, filename: str) -> str:
        """Download file from URL and preserve original extension"""
        print(f"[_download_file] Downloading file from URL: {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Keep original extension
            extension = Path(filename).suffix
            if not extension:
                extension = '.pdf'  # Default to .pdf if no extension
            
            file_path = self.data_dir / f"downloaded{extension}"
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"[_download_file] File downloaded successfully to: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"[_download_file] Error downloading file: {str(e)}")
            raise

    def _get_file_path(self, document: GovernanceDocument) -> str:
        """Get file path based on environment"""
        if document.url.startswith('http'):
            print("[_get_file_path] Using remote URL")
            return self._download_file(document.url, document.filename)
        else:
            print("[_get_file_path] Using local file path")
            return str(self.data_dir / "file.pdf")

    def _process_document_pages(self, file_path: str, mime_type: str) -> List[Tuple[str, int]]:
        """Process document pages based on file type"""
        print(f"[_process_document_pages] Processing {mime_type} file: {file_path}")
        
        if mime_type == 'application/pdf':
            return DocumentPageExtractor.extract_pdf_pages(file_path)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return DocumentPageExtractor.extract_docx_pages(file_path)
        elif mime_type == 'application/vnd.oasis.opendocument.text':
            return DocumentPageExtractor.extract_odt_pages(file_path)
        else:
            raise ValueError(f"Unsupported file type: {mime_type}")

    def _process_page_batch(self, page_batch: List[Tuple[str, int, str]]) -> List[Dict]:
        """Process a batch of pages"""
        results = []
        for content, page_num, _ in page_batch:
            print(f"[_process_page_batch] Processing page {page_num} in batch")
            
            # Create temporary PDF for LlamaParse
            pdf_document = fitz.open()
            page = pdf_document.new_page()
            page.insert_text((72, 72), content, fontsize=12, fontname="helv")
            
            temp_path = self.data_dir / f"temp_page_{page_num}.pdf"
            pdf_document.save(str(temp_path))
            
            try:
                parsed_docs = self.parser.load_data(str(temp_path))
                results.append({
                    'content': content,
                    'page_num': page_num,
                    'parsed_docs': parsed_docs
                })
            finally:
                if temp_path.exists():
                    temp_path.unlink()
            
        return results

    def _process_text_chunks(self, text: str, document: GovernanceDocument, page_number: int) -> List[DocumentChunk]:
        """Process text into chunks"""
        print(f"\n[_process_text_chunks] Processing text for page {page_number}")
        chunks = []
        chunk_start = time.time()

        text_chunks = self.chunker.split_text(text)
        print(f"[_process_text_chunks] Split page {page_number} into {len(text_chunks)} chunks")

        for pos, chunk_data in enumerate(text_chunks):
            word_count = len(chunk_data['text'].split())
            print(f"[_process_text_chunks] Processing chunk {pos+1} with {word_count} words")
            
            chunk = DocumentChunk.objects.create(
                document=document,
                text=chunk_data['text'],
                page_number=page_number,
                position=pos,
                chunk_size=chunk_data['size'],
                processing_time=time.time() - chunk_start,
                word_count=word_count
            )
            chunks.append(chunk)
            print(f"[_process_text_chunks] Chunk {pos+1} stored in database")

        return chunks

    def _get_mime_type(self, filename: str) -> str:
        """Determine MIME type from filename"""
        print(f"[_get_mime_type] Getting MIME type for filename: {filename}")
        mime_type, _ = mimetypes.guess_type(filename)
        result = mime_type or 'application/octet-stream'
        print(f"[_get_mime_type] Determined MIME type: {result}")
        return result

    def process_document(self, document: GovernanceDocument) -> Dict:
        """Main document processing method"""
        print(f"\n[process_document] Starting document processing for document ID: {document.id}")
        start_time = time.time()
        chunks = []
        downloaded_file = None

        try:
            print("[process_document] Updating document status to PROCESSING")
            document.processed_status = 'PROCESSING'
            document.file_size = len(document.url.encode('utf-8'))
            document.mime_type = self._get_mime_type(document.filename)
            document.save()

            self.monitor.log_document_metric(
                document.id,
                'process_start',
                {
                    'timestamp': datetime.now().isoformat(),
                    'file_size': document.file_size,
                    'mime_type': document.mime_type
                }
            )

            with self.monitor.stage(ProcessStage.PARSE):
                file_path = self._get_file_path(document)
                downloaded_file = file_path if document.url.startswith('http') else None
                
                # Extract pages from document
                pages = self._process_document_pages(file_path, document.mime_type)
                document.total_pages = len(pages)
                print(f"[process_document] Extracted {len(pages)} pages")

                # Prepare pages in batches
                page_batches = []
                current_batch = []
                
                for content, page_num in pages:
                    if content.strip():
                        current_batch.append((content, page_num, document.filename))
                        
                        if len(current_batch) == self.batch_size:
                            page_batches.append(current_batch)
                            current_batch = []
                
                if current_batch:
                    page_batches.append(current_batch)

                # Process batches using ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(self._process_page_batch, batch) 
                             for batch in page_batches]
                    
                    for future in futures:
                        batch_results = future.result()
                        for result in batch_results:
                            page_chunks = self._process_text_chunks(
                                result['content'],
                                document,
                                result['page_num']
                            )
                            chunks.extend(page_chunks)

                print(f"[process_document] Processed {len(chunks)} chunks across {document.total_pages} pages")

            duration = time.time() - start_time
            document.processed_status = 'COMPLETED'
            document.processing_duration = duration
            document.save()

            return {
                'document_id': document.id,
                'chunks': chunks,
                'total_chunks': len(chunks),
                'total_pages': document.total_pages,
                'total_words': sum(c.word_count for c in chunks),
                'duration': duration,
                'status': 'success'
            }

        except Exception as e:
            print(f"[process_document] Error processing document: {str(e)}")
            document.processed_status = 'FAILED'
            document.error_message = str(e)
            document.save()
            raise

        finally:
            if downloaded_file and Path(downloaded_file).exists():
                try:
                    Path(downloaded_file).unlink()
                    print(f"[process_document] Cleaned up downloaded file: {downloaded_file}")
                except Exception as e:
                    print(f"[process_document] Error cleaning up file: {str(e)}")