from typing import Dict
from openai import OpenAI
from django.conf import settings
import json
from pydantic import BaseModel
from .monitoring.system_monitor import SystemMonitor

GOVERNANCE_CONTEXT = """
You are the Sport Wales goverance team partner reviewer. Your goal is to will be review and anaylye the partner's performance.
The Sport Wales Governance Team is central to upholding the integrity, effectiveness, 
and ethical standards of Sport Wales' funded partnerships and organizations known as partners. The team 
ensures funded partners operate under robust governance frameworks that align with Sport 
Wales' values of accountability, transparency, and continuous improvement. Goal is to review our partners performance.      
"""


class SummarySchema(BaseModel):
    summary: str
    sport_name: str


class DocumentSummarizer:
    """Generate quick document summary from initial content"""
    
    def __init__(self, monitor: SystemMonitor):
        self.monitor = monitor
        self.llm = OpenAI(api_key=settings.OPENAI_API_KEY)
        print("[DocumentSummarizer] Initialized")

    def _construct_prompt(self, text: str) -> str:
        """Construct summary generation prompt"""
        return f"""
        Context: {GOVERNANCE_CONTEXT} \n####

        Your first goal is to genatate a concise summary of the partner based on there report
        Analyze the following Report text (which is the beginning of a document) and provide:
        1. Extract a concise title which is be the sport name of the partner e.g Hockey Wales or Bowls Wales
        2. A brief summary of what this document and the partner organization is about
        3. Main topics likely covered
        4. The type of document (e.g., policy, report, guidelines)

        Keep the response concise and focused on governance aspects.

        Report Text: {text[:400]}...

        \n####

        You must Respond in JSON format below:
        {{
            "summary": "2-3 sentence summary about the partner",
            "sport_name": "Concise, descriptive title of the partner name",
        
        }}
        """

    def generate_summary(self, text: str) -> Dict:
        """Generate document summary from initial content"""
        print("[DocumentSummarizer] Generating document summary")
        
        try:
            function_schema = {
                "name": "generate_document_summary",
                "parameters": SummarySchema.schema()
            }

            response = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": self._construct_prompt(text)
                }],
                temperature=0.3,
                functions=[function_schema],
                function_call={"name": "generate_document_summary"}
            )

            summary_data = json.loads(
                response.choices[0].message.function_call.arguments
            )

            print(f"[DocumentSummarizer] Generated summary: {summary_data}")
            return summary_data

        except Exception as e:
            print(f"[DocumentSummarizer] Error generating summary: {str(e)}")
            # Return a basic summary on error
            return {
                "summary": "Error generating summary",
                "sport_name": "Document Analysis",
            }