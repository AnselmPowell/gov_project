# src/document_analysis/urls.py
from django.urls import path
from .views import AnalyseDocumentView

urlpatterns = [
    path('analyse/', AnalyseDocumentView.as_view(), name='analyse-document'),
]