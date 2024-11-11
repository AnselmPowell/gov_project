# src/goverment_analysis/model.py
from django.db import models
import uuid
from django.contrib.postgres.fields import ArrayField
from pgvector.django import VectorField

class ProcessingLog(models.Model):
    """Track document processing history"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    stage = models.CharField(max_length=100)  # Increased length
    status = models.CharField(max_length=50)  # Increased length
    message = models.TextField(null=True)     # Already unlimited
    duration = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    document_id = models.UUIDField(null=True)
    
    class Meta:
        db_table = 'processing_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['document_id', 'timestamp']),
            models.Index(fields=['stage', 'status'])
        ]

class GovernanceDocument(models.Model):
    """Store governance document metadata and status"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    pinata_id = models.CharField(max_length=500)   # Increased length
    filename = models.CharField(max_length=500)    # Increased length
    url = models.TextField()  # Changed to TextField for long URLs
    upload_date = models.DateTimeField(auto_now_add=True)
    total_pages = models.IntegerField(default=0)
    processed_status = models.CharField(
        max_length=50,  # Increased length
        choices=[
            ('PENDING', 'Pending'),
            ('PROCESSING', 'Processing'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed')
        ],
        default='PENDING',
        db_index=True  # Add index for status queries
    )
    processing_duration = models.FloatField(null=True)
    error_message = models.TextField(null=True)
    file_size = models.BigIntegerField(null=True)  # Added for large files
    mime_type = models.CharField(max_length=100, null=True)  # Added for file type tracking

    class Meta:
        db_table = 'governance_documents'
        indexes = [
            models.Index(fields=['upload_date']),
            models.Index(fields=['processed_status'])
        ]

    def log_processing(self, stage: str, status: str, duration: float, message: str = None):
        """Log processing stage with error handling"""
        try:
            ProcessingLog.objects.create(
                stage=stage,
                status=status,
                message=message,
                duration=duration,
                document_id=self.id
            )
        except Exception as e:
            # Fallback logging if creation fails
            print(f"Error logging process: {str(e)}")
            ProcessingLog.objects.create(
                stage=stage,
                status='ERROR',
                message=f"Log creation failed: {str(e)}",
                duration=duration,
                document_id=self.id
            )

class DocumentChunk(models.Model):
    """Store document chunks with efficient indexing"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    document = models.ForeignKey(
        GovernanceDocument, 
        on_delete=models.CASCADE,
        related_name='chunks'  # Added for easier querying
    )
    text = models.TextField()  # Already unlimited
    page_number = models.IntegerField(db_index=True)  # Added index
    position = models.IntegerField()
    chunk_size = models.IntegerField()
    processing_time = models.FloatField(null=True)
    word_count = models.IntegerField(null=True)  # Added for chunk analysis
    
    class Meta:
        db_table = 'document_chunks'
        ordering = ['page_number', 'position']
        indexes = [
            models.Index(fields=['document', 'page_number', 'position']),
            models.Index(fields=['chunk_size'])  # For size analysis
        ]

class BestPractice(models.Model):
    """Store best practices with vector search capabilities"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    document = models.ForeignKey(
        GovernanceDocument, 
        on_delete=models.CASCADE,
        related_name='practices'
    )
    text = models.TextField()
    page_number = models.IntegerField(db_index=True)
    context = models.TextField()
    impact = models.TextField()
    keywords = ArrayField(
        models.CharField(max_length=200),
        default=list,
        null=True
    )
    themes = ArrayField(
        models.CharField(max_length=200),
        default=list,
        null=True
    )
    embedding = VectorField(dimensions=1536, null=True)
    extraction_time = models.FloatField(null=True)
    analysis_time = models.FloatField(null=True)
    confidence_score = models.FloatField(null=True)
    is_best_practice = models.BooleanField(default=True)  # Added field
    
    class Meta:
        db_table = 'best_practices'
        indexes = [
            models.Index(fields=['document', 'page_number']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['is_best_practice'])  # Added index
        ]



####

class SharedTheme(models.Model):
    """Track globally shared themes across documents"""
    name = models.CharField(max_length=200, unique=True)
    frequency = models.IntegerField(default=1)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shared_themes'
        ordering = ['-frequency']
        indexes = [
            models.Index(fields=['frequency']),
            models.Index(fields=['name'])
        ]

class DocumentRelationship(models.Model):
    """Track relationships between documents"""
    source_document = models.ForeignKey(
        GovernanceDocument,
        on_delete=models.CASCADE,
        related_name='source_relationships'
    )
    target_document = models.ForeignKey(
        GovernanceDocument,
        on_delete=models.CASCADE,
        related_name='target_relationships'
    )
    shared_themes = models.ManyToManyField(SharedTheme)
    relationship_strength = models.FloatField(
        default=0.0,
        help_text="Calculated based on number of shared themes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_relationships'
        unique_together = ['source_document', 'target_document']
        indexes = [
            models.Index(fields=['relationship_strength'])
        ]

class ThemeOccurrence(models.Model):
    """Track where themes appear in documents"""
    theme = models.ForeignKey(SharedTheme, on_delete=models.CASCADE)
    document = models.ForeignKey(GovernanceDocument, on_delete=models.CASCADE)
    chunk = models.ForeignKey(DocumentChunk, on_delete=models.CASCADE)
    text_excerpt = models.TextField(
        help_text="Relevant text excerpt where theme appears"
    )
    confidence_score = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'theme_occurrences'
        indexes = [
            models.Index(fields=['theme', 'document']),
            models.Index(fields=['confidence_score'])
        ]