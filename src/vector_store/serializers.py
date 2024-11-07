# src/vector_store/serializers.py
from rest_framework import serializers
from .models import VectorDocument

class VectorDocumentSerializer(serializers.ModelSerializer):
    """Serializer for vector documents"""
    class Meta:
        model = VectorDocument
        fields = ['id', 'metadata', 'contents', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class SearchRequestSerializer(serializers.Serializer):
    """Serializer for search requests"""
    query = serializers.CharField(required=True, max_length=1000)
    limit = serializers.IntegerField(required=False, default=5, min_value=1, max_value=100)
    metadata_filters = serializers.DictField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    threshold = serializers.FloatField(required=False, default=0.8, min_value=0, max_value=1)