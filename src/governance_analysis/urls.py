from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GovernanceAnalysisViewSet

router = DefaultRouter()
router.register(r'analysis', GovernanceAnalysisViewSet, basename='governance-analysis')

urlpatterns = [
    path('', include(router.urls)),
]