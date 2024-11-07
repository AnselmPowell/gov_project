# src/document_analysis/models.py
from django.db import models
import json

class DocumentAnalysis(models.Model):
    file_id = models.CharField(max_length=255, unique=True)
    file_url = models.URLField()
    file_type = models.CharField(max_length=50)
    analysis_result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'document_analysis'

    def __str__(self):
        return f"Analysis for {self.file_id}"

    def get_analysis_summary(self):
        return json.loads(self.analysis_result)