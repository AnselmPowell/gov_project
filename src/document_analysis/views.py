# src/document_analysis/views.py
from rest_framework import views, status
from rest_framework.response import Response
from .services import DocumentAnalyser
from .models import DocumentAnalysis
from django.core.exceptions import ValidationError

class AnalyseDocumentView(views.APIView):
    def post(self, request):
        file_url = request.data.get('file_url')
        file_id = request.data.get('file_id')
        file_type = request.data.get('file_type')
        print("inside analyse document view", [file_url, file_id, file_type])
        if not all([file_url, file_id, file_type]):
            return Response(
                {"error": "Missing required fields"},
                status=status.HTTP_400_BAD_REQUEST
            )
         
        try:
            print("inside try")
            # Check if analysis already exists

            # existing_analysis = DocumentAnalysis.objects.filter(file_id=file_id).first()
            # if existing_analysis:
            #     return Response(existing_analysis.get_analysis_summary())

            # Perform new analysis

            analyser = DocumentAnalyser()
            analysis_result = analyser.analyse_file(file_url, file_type)
            print("analysis result", analysis_result)
            
            # Store analysis
            
            # DocumentAnalysis.objects.create(
            #     file_id=file_id,
            #     file_url=file_url,
            #     file_type=file_type,
            #     analysis_result=analysis_result
            # )

            return Response(analysis_result)
        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )