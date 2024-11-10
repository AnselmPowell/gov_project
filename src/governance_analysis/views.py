# src/governance_analysis/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction

from .models import GovernanceDocument, BestPractice, ProcessingLog
from .services.document_processor import GovernanceDocumentProcessor
from .services.document_summary import DocumentSummarizer
from .services.best_practice_extractor import BestPracticeExtractor
from .services.theme_analyzer import ThemeAnalyzer
from .services.vector_store import VectorStore
from .services.monitoring.system_monitor import SystemMonitor, ProcessStage



@method_decorator(csrf_exempt, name='dispatch')
class GovernanceAnalysisViewSet(viewsets.ViewSet):
    def __init__(self, **kwargs):
        print("\n[GovernanceAnalysisViewSet] Initializing viewset")
        super().__init__(**kwargs)
        self.monitor = SystemMonitor()
        print("[GovernanceAnalysisViewSet] Monitor initialized")

    @action(detail=False, methods=['POST'])
    def analyze_documents(self, request):
        print("\n[analyze_documents] Starting document analysis")
        print(f"[analyze_documents] Request data: {request.data}")

        # Extract data from request
        file_name = request.data.get('file_name')
        file_url = request.data.get('file_url')
        file_id = request.data.get('file_id')
        file_type = request.data.get('file_type')
        file_size = len(file_url.encode('utf-8')) 

        if not all([file_url, file_id, file_type]):
            print("[analyze_documents] ERROR: Missing required fields")
            return Response(
                {
                    'status': 'error',
                    'message': 'Missing required fields'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Create document record
            document = GovernanceDocument.objects.create(
                pinata_id=file_id,
                url=file_url,
                filename=file_name,
                mime_type=file_type,
                file_size=file_size
            )

            # Initialize services
            processor = GovernanceDocumentProcessor(self.monitor)
            extractor = BestPracticeExtractor(self.monitor)
            analyzer = ThemeAnalyzer(self.monitor)
            vector_store = VectorStore(self.monitor)
            summariser = DocumentSummarizer(self.monitor)

            
            # Process document
            with self.monitor.stage(ProcessStage.PARSE):
                process_result = processor.process_document(document)
                chunks = process_result['chunks']
                

                # Generate document summary from first chunk
                if chunks:
                    summary = summariser.generate_summary(chunks[0].text)
                    print(f"[analyze_documents] Document summary generated: {summary}")
                    print(f"[analyze_documents] Partner Name: {summary['sport_name']}")
    

            best_practices_data = []
        
            with self.monitor.stage(ProcessStage.EXTRACT):
                for chunk in chunks:
                    practices = extractor.process_chunk(chunk, summary)  # Now returns list
                    if practices:
                        for practice in practices:  # Handle multiple practices
                            practice = analyzer.analyze_practice(practice)
                            vector_store.store_practice(practice)
                            
                            # Updated practice details collection
                            best_practices_data.append({
                                'text': practice.text,
                                'context': practice.context,
                                'impact': practice.impact,
                                'page_number': practice.page_number,
                                'keywords': practice.keywords,
                                'themes': practice.themes,
                                'confidence_score': practice.confidence_score,
                                # 'practice_type': practice.practice_type,  # New field
                                # 'category': practice.category,  # New field
                                # 'evidence': practice.evidence,  # New field
                                # 'criteria_met': practice.criteria_met  # New field
                            })

            # Update document status
            document.processed_status = 'COMPLETED'
            document.save()

            # Prepare response with requested data
            result = {
                'status': 'success',
                'document': {
                    'id': str(document.id),
                    'filename': document.filename,
                    'file_size': document.file_size,
                    'upload_date': document.upload_date.isoformat(),
                    'total_pages': document.total_pages,
                },
                'best_practices': best_practices_data,
                'processing_details': {
                    'total_practices_found': len(best_practices_data),
                    'unique_themes': len(set().union(*[set(p['themes']) for p in best_practices_data])) if best_practices_data else 0,
                }
            }

            print(f"[analyze_documents] Returning result with {len(best_practices_data)} practices")
            print(f"\n \n [analyze_documents] Final Results Returned {result} \n  \n")
            return Response(result)

    @action(detail=False, methods=['GET'])
    def search_practices(self, request):
        print("\n[search_practices] Starting practice search")
        query = request.query_params.get('query', '')
        limit = int(request.query_params.get('limit', 5))

        vector_store = VectorStore(self.monitor)
        practices = vector_store.find_similar(query=query, limit=limit)

        response_data = {
            'status': 'success',
            'practices': [
                {
                    'text': p.text,
                    'context': p.context,
                    'impact': p.impact,
                    'page_number': p.page_number,
                    'keywords': p.keywords,
                    'themes': p.themes,
                    'confidence_score': p.confidence_score
                }
                for p in practices
            ]
        }

        return Response(response_data)

    @action(detail=False, methods=['GET'])
    def search_practices(self, request):
        print("\n[search_practices] Starting practice search")
        query = request.query_params.get('query', '')
        limit = int(request.query_params.get('limit', 5))
        print(f"[search_practices] Query: {query}, Limit: {limit}")

        vector_store = VectorStore(self.monitor)
        print("[search_practices] Vector store initialized")

        practices = vector_store.find_similar(
            query=query,
            limit=limit
        )
        print(f"[search_practices] Found {len(practices)} similar practices")

        response_data = {
            'status': 'success',
            'practices': [
                {
                    'id': str(p.id),
                    'text': p.text,
                    'context': p.context,
                    'impact': p.impact,
                    'themes': p.themes,
                    'keywords': p.keywords,
                    'document': p.document.filename,
                    'page': p.page_number
                }
                for p in practices
            ]
        }
        print(f"[search_practices] Response prepared with {len(response_data['practices'])} practices")
        return Response(response_data)