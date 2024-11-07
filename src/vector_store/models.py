# src/vector_store/models.py
import uuid
from django.db import models
from django.db.models import JSONField
from pgvector.django import VectorField

class VectorDocument(models.Model):
    """
    Vector document storage with metadata and embeddings
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metadata = JSONField(default=dict)
    contents = models.TextField()
    embedding = VectorField(dimensions=1536)  # OpenAI embedding dimension
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vector_documents'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Document {self.id}"