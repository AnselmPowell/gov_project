# src/document_analysis/services.py
import PyPDF2
import docx
import requests
import nltk
from io import BytesIO
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords

# nltk.download('punkt')
# nltk.download('stopwords')

class DocumentAnalyser:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))

    def analyse_pdf(self, file_content):
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return self._analyse_text(text)

    def analyse_docx(self, file_content):
        try:
            doc = docx.Document(BytesIO(file_content))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return self._analyse_text(text)
        except Exception as e:
            print(f"DOCX processing error: {str(e)}")
            return {
                "error": f"Failed to process DOCX file: {str(e)}",
                "status": "failed"
            }

    def _analyse_text(self, text):
        if not text.strip():
            return {
                "word_count": 0,
                "sentence_count": 0,
                "error": "No readable text found"
            }

        # Basic metrics
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        words_no_stop = [word for word in words if word.lower() not in self.stop_words]
        # Analysis
        return {
            "status": "success",
            "word_count": len(words),
            "sentence_count": len(sentences),
            "unique_words": len(set(words_no_stop)),
            "average_sentence_length": round(len(words) / len(sentences), 2),
            "estimated_read_time": f"{round(len(words) / 200, 2)} minutes"
        }

    def analyse_odt(self, file_content):
        try:
            doc = load(BytesIO(file_content))
            all_text = []
            
            # Extract text from all paragraph nodes
            for paragraph in doc.getElementsByType(text.P):
                all_text.append(teletype.extractText(paragraph))
            
            text_content = "\n".join(all_text)
            return self._analyse_text(text_content)
        except Exception as e:
            print(f"ODT processing error: {str(e)}")
            return {
                "error": f"Failed to process ODT file: {str(e)}",
                "status": "failed"
            }

    def analyse_file(self, file_url, file_type):
        try:
            response = requests.get(file_url)
            response.raise_for_status()
            content = response.content
            
            if file_type == 'application/pdf':
                result = self.analyse_pdf(content)
            elif file_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'document']:
                result = self.analyse_docx(content)
            elif file_type == 'application/vnd.oasis.opendocument.text':
                result = self.analyse_odt(content)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
         
            if result['status']:
                if result['status'] == 'failed':
                    raise Exception(result['error'])
                    return result
            
            return {
                "result": result,
                "status": "success"
            }
        except Exception as e:
            print(f"File processing error: {str(e)}")
            return {
                "error": str(e),
                "status": "failed"
            }