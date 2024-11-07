# src/vector_store/services.py
import time
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from django.conf import settings
from django.db import transaction
from asgiref.sync import sync_to_async
from openai import OpenAI
from pgvector.django import CosineDistance

from .models import VectorDocument
from .exceptions import VectorServiceError

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.VECTOR_STORE.get(
            'EMBEDDING_MODEL', 'text-embedding-3-small'
        )
        self.dimensions = settings.VECTOR_STORE.get('DIMENSIONS', 1536)

    def get_embedding(self, text: str) -> List[float]:
        text = text.replace("\n", " ").strip()
        start_time = time.time()
        
        try:
            response = self.openai_client.embeddings.create(
                input=[text],
                model=self.embedding_model,
            )
            embedding = response.data[0].embedding
            
            elapsed_time = time.time() - start_time
            logger.info(f"Generated embedding in {elapsed_time:.2f}s")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise VectorServiceError(f"Failed to generate embedding: {str(e)}")

    @sync_to_async
    def _create_document(self, content: str, metadata: Dict, embedding: List[float]) -> VectorDocument:
        """Synchronous document creation"""
        with transaction.atomic():
            return VectorDocument.objects.create(
                contents=content,
                metadata=metadata or {},
                embedding=embedding
            )

    async def create_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VectorDocument:
        """Create new document with embedding"""
        try:
            embedding = self.get_embedding(content)
            document = await self._create_document(content, metadata, embedding)
            logger.info(f"Created document {document.id}")
            return document
            
        except Exception as e:
            logger.error(f"Document creation failed: {str(e)}")
            raise VectorServiceError(f"Failed to create document: {str(e)}")

    @sync_to_async
    def _perform_search(
        self,
        query_embedding: List[float],
        limit: int,
        metadata_filters: Optional[Dict] = None,
        time_range: Optional[tuple] = None,
        threshold: float = 0.9
    ) -> List[VectorDocument]:
        """Synchronous similarity search"""
        try:
            # Start with base query
            queryset = VectorDocument.objects.all()
            
            # Add annotation for cosine similarity
            queryset = queryset.annotate(
                similarity=CosineDistance('embedding', query_embedding)
            )
            
            # Debug print
            print("\nDEBUG - Raw distances:")
            for doc in queryset:
                print(f"Document ID: {doc.id}")
                print(f"Distance: {doc.similarity}")
                print(f"Content: {doc.contents[:50]}...")
                print("---")

           # Convert to list and sort by similarity
            results = list(queryset)
            results.sort(key=lambda x: x.similarity)

            # Then apply any filters
            # metadata filter
            if metadata_filters:
                print("Filtering by metadata:", metadata_filters)
                if isinstance(metadata_filters, str):
                    # If string, assume it's the category
                    results = [r for r in results if r.metadata.get('category') == metadata_filters]
                elif isinstance(metadata_filters, dict):
                    # If dictionary, check all key-value pairs
                    results = [r for r in results if all(
                        r.metadata.get(k) == v for k, v in metadata_filters.items()
                    )]

            # time filter
            if time_range:
                start_date, end_date = time_range
                results = [r for r in results if start_date <= r.created_at <= end_date]

            # Finally take top results
            results = results[:limit]

            print("\nDEBUG - Final results:", results)
            for doc in results:
                print(f"Document ID: {doc.id}")
                print(f"Distance: {doc.similarity}")
                print(f"Category: {doc.metadata.get('category')}")
                print("---")

            return results

        except Exception as e:
            print(f"Search error: {str(e)}")
            raise

    async def similarity_search(
        self,
        query: str,
        limit: int = 5,
        metadata_filters: Optional[Dict] = None,
        time_range: Optional[tuple] = None,
        threshold: float = 0.8
    ) -> List[VectorDocument]:
        """Perform similarity search with filters"""
        try:
            query_embedding = self.get_embedding(query)
            
            results = await self._perform_search(
                query_embedding=query_embedding,
                limit=limit,
                metadata_filters=metadata_filters,
                time_range=time_range,
                threshold=threshold
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise VectorServiceError(f"Search failed: {str(e)}")