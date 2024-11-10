import os
import sys
import django
import asyncio
from pathlib import Path
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Now import Django-specific modules
from django.core.files import File
from openai import OpenAI
from governance_analysis.models import GovernanceDocument, DocumentChunk, BestPractice

class GovernanceTestRunner:
    """
    Simple test runner for governance analysis functions
    """
    def __init__(self):
        self.test_file = Path(__file__).parent / 'data' / 'file.pdf'
        self.llm = OpenAI()
        self.test_results = []
        
    def log_result(self, stage: str, success: bool, message: str):
        """Log test result with timestamp"""
        self.test_results.append({
            'timestamp': datetime.now().isoformat(),
            'stage': stage,
            'success': success,
            'message': message
        })
        
        # Print immediate feedback
        status = "✓" if success else "✗"
        print(f"\n[{status}] {stage}: {message}")

    async def test_document_upload(self):
        """Test document upload to Pinata"""
        try:
            if not self.test_file.exists():
                raise FileNotFoundError(f"Test file not found at {self.test_file}")

            with open(self.test_file, 'rb') as f:
                file_content = f.read()

            # Create test document record
            document = await GovernanceDocument.objects.acreate(
                filename=self.test_file.name,
                pinata_id='test_id',
                url=f'file://{self.test_file}',
                total_pages=0
            )

            self.log_result(
                'Document Upload', 
                True,
                f"Successfully created document record: {document.id}"
            )
            return document

        except Exception as e:
            self.log_result(
                'Document Upload',
                False,
                f"Failed to upload document: {str(e)}"
            )
            return None

    async def test_document_processing(self, document):
        """Test document parsing and chunking"""
        try:
            # Simple text extraction for test
            with open(self.test_file, 'rb') as f:
                text = f.read().decode('utf-8', errors='ignore')

            # Create test chunks
            chunks = []
            chunk_size = 1000
            for i in range(0, len(text), chunk_size):
                chunk = await DocumentChunk.objects.acreate(
                    document=document,
                    text=text[i:i + chunk_size],
                    page_number=1,
                    position=len(chunks)
                )
                chunks.append(chunk)

            self.log_result(
                'Document Processing',
                True,
                f"Created {len(chunks)} chunks"
            )
            return chunks

        except Exception as e:
            self.log_result(
                'Document Processing',
                False,
                f"Failed to process document: {str(e)}"
            )
            return []

    async def test_best_practice_extraction(self, chunk):
        """Test best practice extraction from a chunk"""
        try:
            prompt = f"""
            Analyze this text for governance best practices:
            
            {chunk.text[:500]}...
            
            If no best practices are found, respond with "NO_BEST_PRACTICES".
            If found, format as: "PRACTICE: [description]"
            """

            response = await self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": prompt
                }]
            )

            content = response.choices[0].message.content
            if "NO_BEST_PRACTICES" not in content:
                practice = await BestPractice.objects.acreate(
                    document=chunk.document,
                    text=content.replace("PRACTICE: ", ""),
                    page_number=chunk.page_number
                )
                
                self.log_result(
                    'Best Practice Extraction',
                    True,
                    f"Extracted practice from chunk {chunk.id}"
                )
                return practice

            self.log_result(
                'Best Practice Extraction',
                True,
                "No best practices found in chunk"
            )
            return None

        except Exception as e:
            self.log_result(
                'Best Practice Extraction',
                False,
                f"Failed to extract best practices: {str(e)}"
            )
            return None

    async def test_theme_analysis(self, practice):
        """Test theme and keyword extraction"""
        try:
            prompt = f"""
            Analyze this governance best practice for themes and keywords:
            
            {practice.text}
            
            Format response as JSON:
            {{
                "themes": ["theme1", "theme2"],
                "keywords": ["keyword1", "keyword2", "keyword3"]
            }}
            """

            response = await self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": prompt
                }]
            )

            analysis = response.choices[0].message.content
            
            # Update practice
            practice.themes = analysis.get('themes', [])
            practice.keywords = analysis.get('keywords', [])
            await practice.asave()

            self.log_result(
                'Theme Analysis',
                True,
                f"Analyzed themes for practice {practice.id}"
            )
            return practice

        except Exception as e:
            self.log_result(
                'Theme Analysis',
                False,
                f"Failed to analyze themes: {str(e)}"
            )
            return None

    def print_summary(self):
        """Print test results summary"""
        print("\n=== Test Results Summary ===")
        
        total = len(self.test_results)
        successful = sum(1 for r in self.test_results if r['success'])
        
        print(f"\nTotal Tests: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status = "✓" if result['success'] else "✗"
            print(f"\n[{status}] {result['stage']}")
            print(f"    {result['message']}")

async def run_tests():
    """Run all tests"""
    runner = GovernanceTestRunner()
    
    print("\n=== Starting Governance Analysis Tests ===\n")
    
    # Test document upload
    document = await runner.test_document_upload()
    if not document:
        print("\nTest failed at document upload stage")
        return
    
    # Test document processing
    chunks = await runner.test_document_processing(document)
    if not chunks:
        print("\nTest failed at document processing stage")
        return
    
    # Test best practice extraction
    practices = []
    for chunk in chunks[:3]:  # Test first 3 chunks
        practice = await runner.test_best_practice_extraction(chunk)
        if practice:
            practices.append(practice)
    
    # Test theme analysis
    for practice in practices:
        await runner.test_theme_analysis(practice)
    
    # Print summary
    runner.print_summary()

if __name__ == "__main__":
    # Run tests
    asyncio.run(run_tests())