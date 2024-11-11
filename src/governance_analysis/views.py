# src/governance_analysis/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from functools import partial
from django.db import transaction
from asgiref.sync import sync_to_async
import asyncio

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
        """Synchronous wrapper for async document analysis"""
        print("\n[analyze_documents] Starting document analysis")
        
        async def _async_analyze():
            files_data = request.data if isinstance(request.data, list) else [request.data]
            results = []
            all_shared_themes = set()
            all_shared_keywords = set()

            try:
                for file_data in files_data:
                    # Extract data from request
                    file_name = file_data.get('file_name')
                    file_url = file_data.get('file_url')
                    file_id = file_data.get('file_id')
                    file_type = file_data.get('file_type')
                    
                    if not all([file_url, file_id, file_type]):
                        return Response(
                            {
                                'status': 'error',
                                'message': f'Missing required fields for file {file_name}'
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    file_size = len(file_url.encode('utf-8'))

                    # Create document record
                    document = await sync_to_async(GovernanceDocument.objects.create)(
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
                    process_result = await sync_to_async(processor.process_document)(document)
                    chunks = process_result['chunks']

                    if chunks:
                        summary = await sync_to_async(summariser.generate_summary)(chunks[0].text)
                        print(f"[analyze_documents] Generated summary for {file_name}")
                      

                    best_practices_data = []
                    document_themes = set()
                    document_keywords = set()

                    for chunk in chunks:
                        practices = await sync_to_async(extractor.process_chunk)(chunk, summary)
                        if practices:
                            for practice in practices:
                                # Process each practice
                                practice = await analyzer.analyze_practice(practice, summary, all_shared_themes, all_shared_keywords)
                                await sync_to_async(vector_store.store_practice)(practice)
                                print(f"[analyze_documents] Stored practice {practice.id}")
                                
                                # Track themes
                                if practice.themes:
                                    document_themes.update(practice.themes)
                                    all_shared_themes.update(practice.themes)

                                    document_keywords.update(practice.themes)
                                    all_shared_keywords.update(practice.themes)

                                print(f"[analyze_documents] Themes: {practice.themes}")
                                
                                best_practices_data.append({
                                    'text': practice.text,
                                    'context': practice.context,
                                    'impact': practice.impact,
                                    'page_number': practice.page_number,
                                    'keywords': practice.keywords,
                                    'themes': practice.themes,
                                    'confidence_score': practice.confidence_score,
                                    'is_best_practice': practice.is_best_practice  # Add this line only
                                })

                    # Update document
                    document.processed_status = 'COMPLETED'
                    print(f"[analyze_documents] Updated document {document.id}")
                    await sync_to_async(document.save)()

                    results.append({
                        'document': {
                            'id': str(document.id),
                            'filename': document.filename,
                            'file_size': document.file_size,
                            'upload_date': document.upload_date.isoformat(),
                            'total_pages': document.total_pages,
                        },
                        'best_practices': best_practices_data,
                        'document_themes': list(document_themes)
                    })
                print(f"[analyze_documents] Finished processing {len(results)} documents")
                return Response({
                    'status': 'success',
                    'documents': results,
                    'shared_themes_analysis': {
                        'total_shared_themes': len(all_shared_themes),
                        'shared_themes': list(all_shared_themes),
                        'documents_processed': len(results)
                    }
                })

            except Exception as e:
                print(f"[analyze_documents] Error: {str(e)}")
                return Response(
                    {
                        'status': 'error',
                        'message': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Run the async function in the sync world
        return asyncio.run(_async_analyze())