# src/governance_analysis/services/vector_store.py
from typing import Dict, List, Optional
from openai import OpenAI
from django.conf import settings
import numpy as np
import time
from datetime import datetime, timedelta
from ..models import BestPractice
from .monitoring.system_monitor import ProcessStage, SystemMonitor
from pgvector.django import L2Distance

class VectorStore:
    """Efficient vector storage and similarity search"""
    def __init__(self, monitor: SystemMonitor):
        print("\n[VectorStore] Initializing vector store")
        self.embedder = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.monitor = monitor
        self._embedding_cache = {}
        self._cache_ttl = timedelta(hours=24)
        print(f"[VectorStore] Initialization complete. Cache TTL: {self._cache_ttl}")

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        print(f"\n[_get_cache_key] Generating cache key for text length: {len(text)}")
        key = hash(text)
        print(f"[_get_cache_key] Generated key: {key}")
        return key

    def _clean_text(self, text: str) -> str:
        """Clean text for embedding"""
        print(f"\n[_clean_text] Cleaning text of length: {len(text)}")
        cleaned = ' '.join(text.split())
        print(f"[_clean_text] Cleaned text length: {len(cleaned)}")
        return cleaned

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with caching"""
        print(f"\n[generate_embedding] Starting embedding generation for text length: {len(text)}")
        start_time = time.time()
        cache_key = self._get_cache_key(text)

        # Check cache
        print("[generate_embedding] Checking cache")
        if cache_key in self._embedding_cache:
            cache_entry = self._embedding_cache[cache_key]
            if datetime.now() < cache_entry['expires']:
                print("[generate_embedding] Cache hit!")
                self.monitor.log_document_metric(
                    "embedding_cache",
                    "embedding_cache_hit",
                    True
                )
                print(f"[generate_embedding] Returning cached embedding of size: {len(cache_entry['embedding'])}")
                return cache_entry['embedding']
        
        print("[generate_embedding] Cache miss - generating new embedding")
        # Generate new embedding
        cleaned_text = self._clean_text(text)
        print("[generate_embedding] Sending request to OpenAI")
        response = self.embedder.embeddings.create(
            input=[cleaned_text],
            model="text-embedding-3-small"
        )
        print("[generate_embedding] Received response from OpenAI")

        embedding = response.data[0].embedding
        duration = time.time() - start_time
        print(f"[generate_embedding] Generation time: {duration:.2f} seconds")
        print(f"[generate_embedding] Embedding size: {len(embedding)}")

        # Update cache
        print("[generate_embedding] Updating cache")
        self._embedding_cache[cache_key] = {
            'embedding': embedding,
            'expires': datetime.now() + self._cache_ttl
        }
        print(f"[generate_embedding] Current cache size: {len(self._embedding_cache)}")

        # Maintain cache size
        if len(self._embedding_cache) > 1000:
            print("[generate_embedding] Cache size limit reached, cleaning cache")
            self._clean_cache()

        self.monitor.log_document_metric(
            "embedding_generation",
            "complete",
            {
                'duration': duration,
                'vector_size': len(embedding)
            }
        )

        return embedding

    def _clean_cache(self):
        """Remove expired and oldest cache entries"""
        print("\n[_clean_cache] Starting cache cleanup")
        initial_size = len(self._embedding_cache)
        now = datetime.now()
        
        print("[_clean_cache] Removing expired entries")
        self._embedding_cache = {
            k: v for k, v in self._embedding_cache.items()
            if v['expires'] > now
        }
        print(f"[_clean_cache] Removed {initial_size - len(self._embedding_cache)} expired entries")

        # If still too large, remove oldest entries
        while len(self._embedding_cache) > 1000:
            oldest_key = next(iter(self._embedding_cache))
            self._embedding_cache.pop(oldest_key)
            print(f"[_clean_cache] Removed oldest entry with key: {oldest_key}")

        print(f"[_clean_cache] Final cache size: {len(self._embedding_cache)}")

    def store_practice(self, practice: BestPractice) -> None:
        """Store practice with embedding"""
        print(f"\n[store_practice] Starting storage for practice ID: {practice.id}")
        start_time = time.time()

        with self.monitor.stage(ProcessStage.VECTORIZE):
            # Combine text for embedding
            text_to_embed = (
                f"{practice.text}\n{practice.context}\n{practice.impact}"
            )
            print(f"[store_practice] Combined text length: {len(text_to_embed)}")

            # Generate embedding
            print("[store_practice] Generating embedding")
            embedding = self.generate_embedding(text_to_embed)
            print(f"[store_practice] Embedding generated, size: {len(embedding)}")

            # Store embedding
            print("[store_practice] Storing embedding in practice record")
            practice.embedding = embedding
            practice.save()
            print("[store_practice] Practice record updated")

            duration = time.time() - start_time
            print(f"[store_practice] Total storage time: {duration:.2f} seconds")

            self.monitor.log_document_metric(
                practice.document.id,
                f"practice_{practice.id}_vectorization",
                {
                    'duration': duration,
                    'vector_size': len(embedding)
                }
            )

    def find_similar(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.8
    ) -> List[BestPractice]:
        """Find similar practices with distance threshold"""
        print(f"\n[find_similar] Starting similarity search")
        print(f"[find_similar] Query: {query}")
        print(f"[find_similar] Limit: {limit}, Threshold: {threshold}")
        start_time = time.time()

        # Generate query embedding
        print("[find_similar] Generating query embedding")
        query_embedding = self.generate_embedding(query)
        print(f"[find_similar] Query embedding generated, size: {len(query_embedding)}")

        # Get nearest neighbors
        print("[find_similar] Performing vector search")
        results = BestPractice.objects.alias(
            distance=L2Distance('embedding', query_embedding)
        ).filter(
            distance__lte=threshold
        ).order_by('distance')[:limit]

        results_list = list(results)
        duration = time.time() - start_time
        print(f"[find_similar] Search completed in {duration:.2f} seconds")
        print(f"[find_similar] Found {len(results_list)} results")

        self.monitor.log_document_metric(
            'Find Similar Practices',
            'similarity_search',
            {
                'query': query,
                'duration': duration,
                'results_count': len(results_list)
            }
        )

        # Print results details
        for i, result in enumerate(results_list):
            print(f"[find_similar] Result {i+1}:")
            print(f"  - Practice ID: {result.id}")
            print(f"  - Text: {result.text[:100]}...")

        return results_list