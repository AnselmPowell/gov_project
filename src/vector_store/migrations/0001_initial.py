# src/vector_store/migrations/0001_initial.py
from django.db import migrations
import django.contrib.postgres.fields.jsonb
import pgvector.django
import uuid
from django.db import models

class Migration(migrations.Migration):
    initial = True
    
    dependencies = []
    
    operations = [
        # Enable vector extension
        migrations.RunSQL(
            'CREATE EXTENSION IF NOT EXISTS vector;',
            'DROP EXTENSION IF EXISTS vector;'
        ),
        # Create model
        migrations.CreateModel(
            name='VectorDocument',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('metadata', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('contents', models.TextField()),
                ('embedding', pgvector.django.VectorField(dimensions=1536)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'vector_documents',
                'ordering': ['-created_at'],
            },
        ),
        # Create indexes
        migrations.AddIndex(
            model_name='vectordocument',
            index=models.Index(fields=['created_at'], name='vector_doc_created_idx'),
        ),
        migrations.RunSQL(
            sql=[
                "CREATE INDEX vector_embedding_idx ON vector_documents USING ivfflat (embedding vector_cosine_ops)",
            ],
            reverse_sql=["DROP INDEX IF EXISTS vector_embedding_idx"]
        ),
    ]