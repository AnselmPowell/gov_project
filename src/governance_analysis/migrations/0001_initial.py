# src/governance_analysis/migrations/0001_initial.py
from django.db import migrations
import django.contrib.postgres.fields
import pgvector.django
import uuid
from django.db import models

class Migration(migrations.Migration):
    initial = True
    
    dependencies = []
    
    operations = [
        # First, create the vector extension
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS vector;",
            "DROP EXTENSION IF EXISTS vector;"
        ),
        
        # Then create your models
        migrations.CreateModel(
            name='ProcessingLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('stage', models.CharField(max_length=50)),
                ('status', models.CharField(max_length=20)),
                ('message', models.TextField(null=True)),
                ('duration', models.FloatField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('document_id', models.UUIDField(null=True)),
            ],
            options={
                'db_table': 'processing_logs',
                'ordering': ['-timestamp'],
            },
        ),
        
        migrations.CreateModel(
            name='GovernanceDocument',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('pinata_id', models.CharField(max_length=255)),
                ('filename', models.CharField(max_length=255)),
                ('url', models.URLField()),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('total_pages', models.IntegerField(default=0)),
                ('processed_status', models.CharField(
                    max_length=20,
                    choices=[
                        ('PENDING', 'Pending'),
                        ('PROCESSING', 'Processing'),
                        ('COMPLETED', 'Completed'),
                        ('FAILED', 'Failed')
                    ],
                    default='PENDING'
                )),
                ('processing_duration', models.FloatField(null=True)),
                ('error_message', models.TextField(null=True)),
            ],
            options={
                'db_table': 'governance_documents',
            },
        ),
        
        migrations.CreateModel(
            name='DocumentChunk',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('document', models.ForeignKey('GovernanceDocument', on_delete=models.CASCADE)),
                ('text', models.TextField()),
                ('page_number', models.IntegerField()),
                ('position', models.IntegerField()),
                ('chunk_size', models.IntegerField()),
                ('processing_time', models.FloatField(null=True)),
            ],
            options={
                'db_table': 'document_chunks',
                'ordering': ['page_number', 'position'],
            },
        ),
        
        migrations.CreateModel(
            name='BestPractice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('document', models.ForeignKey('GovernanceDocument', on_delete=models.CASCADE)),
                ('text', models.TextField()),
                ('page_number', models.IntegerField()),
                ('context', models.TextField()),
                ('impact', models.TextField()),
                ('keywords', django.contrib.postgres.fields.ArrayField(
                    base_field=models.CharField(max_length=100),
                    default=list
                )),
                ('themes', django.contrib.postgres.fields.ArrayField(
                    base_field=models.CharField(max_length=100),
                    default=list
                )),
                ('embedding', pgvector.django.VectorField(dimensions=1536)),
                ('extraction_time', models.FloatField(null=True)),
                ('analysis_time', models.FloatField(null=True)),
            ],
            options={
                'db_table': 'best_practices',
            },
        ),
        
        # Create indexes
        migrations.AddIndex(
            model_name='ProcessingLog',
            index=models.Index(fields=['timestamp'], name='proc_log_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='GovernanceDocument',
            index=models.Index(fields=['processed_status'], name='gov_doc_status_idx'),
        ),
        migrations.AddIndex(
            model_name='DocumentChunk',
            index=models.Index(fields=['document', 'page_number'], name='doc_chunk_doc_page_idx'),
        ),
        
        # Create vector index
        migrations.RunSQL(
            sql=[
                "CREATE INDEX best_practices_embedding_idx ON best_practices USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS best_practices_embedding_idx;"
            ]
        ),
    ]