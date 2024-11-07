from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/api/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/document/', include('document_analysis.urls')),
    path('api/vector/', include('vector_store.urls')),
]
