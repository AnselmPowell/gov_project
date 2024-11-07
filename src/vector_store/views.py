# src/vector_store/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError

from .models import VectorDocument
from .serializers import VectorDocumentSerializer, SearchRequestSerializer
from .services import VectorService
from .exceptions import VectorServiceError

class VectorDocumentViewSet(viewsets.ModelViewSet):
    queryset = VectorDocument.objects.all()
    serializer_class = VectorDocumentSerializer
    permission_classes = [IsAuthenticated]
    vector_service = VectorService()

    @action(detail=False, methods=['post'])
    async def search(self, request):
        """
        Perform similarity search
        """
        serializer = SearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Extract search parameters
            query = serializer.validated_data['query']
            limit = serializer.validated_data.get('limit', 5)
            metadata_filters = serializer.validated_data.get('metadata_filters')
            threshold = serializer.validated_data.get('threshold', 0.8)
            
            # Handle time range
            start_date = serializer.validated_data.get('start_date')
            end_date = serializer.validated_data.get('end_date')
            time_range = (start_date, end_date) if start_date and end_date else None

            # Perform search
            results = await self.vector_service.similarity_search(
                query=query,
                limit=limit,
                metadata_filters=metadata_filters,
                time_range=time_range,
                threshold=threshold
            )

            # Serialize results
            response_serializer = self.get_serializer(results, many=True)
            return Response(response_serializer.data)

        except VectorServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )