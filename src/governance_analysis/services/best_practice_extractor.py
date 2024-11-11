# src/governor/services/best_practice_extractor.py
from typing import Dict, Optional, List, Union
from openai import OpenAI
from django.conf import settings
import json
import time
from ..models import DocumentChunk, BestPractice
from .document_summary import DocumentSummarizer
from .monitoring.system_monitor import ProcessStage, SystemMonitor
from pydantic import BaseModel, Field
from typing import List as PyList

GOVERNANCE_CONTEXT = """
You are the Sport Wales goverance team partner reviewer. Your goal is to will be review and anaylye the partner's performance.
The Sport Wales Governance Team is central to upholding the integrity, effectiveness, 
and ethical standards of Sport Wales' funded partnerships and organizations known as partners. The team 
ensures funded partners operate under robust governance frameworks that align with Sport 
Wales' values of accountability, transparency, and continuous improvement. Goal is to review our partners performance.

best_practices'
                "Strong Financial Management",
                "Transparent Governance",
                "Risk Management & Compliance",
                "Strategic Objectives",
                "Continuous Improvement",
                "Effective Safeguarding",
                "Ethical Culture & Accountability",
                "Diversity, Equity, Inclusion"
\n#########
'concerns'
                "Financial Instability",
                "Weak Governance Structures",
                "Non-Compliance in Risk & Safeguarding",
                "Unclear Objectives",
                "Resistance to Feedback",
                "Insufficient Safeguarding",
                "Ethical Concerns",
                "Lack of Inclusivity"
            
"""

# Enhanced schema definitions
class PracticeSchema(BaseModel):
    practice: str = Field(..., description="The specific best practice or concern identified")
    category: str = Field(..., description="The category this practice falls under")
    context: str = Field(..., description="The surrounding context supporting this identification")
    impact: str = Field(..., description="The expected impact or implications")
    is_best_practice: bool = Field(..., description="Whether this is a best practice (True) or concern (False)")
    evidence: str = Field(..., description="Specific evidence from the text supporting this practice")

class ChunkAnalysisSchema(BaseModel):
    practices: PyList[PracticeSchema] = Field(default_factory=list)
    criteria_met: bool = Field(..., description="Whether the chunk meets governance criteria")
    dominant_categories: PyList[str] = Field(default_factory=list)

class BestPracticeExtractor:
    """Enhanced extractor with criteria-based analysis"""
    def __init__(self, monitor: SystemMonitor):
        print("\n[BestPracticeExtractor] Initializing extractor")
        self.monitor = monitor
        self.llm = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._cache = {}
        self.categories = {
            'best_practices': [
                "Strong Financial Management",
                "Transparent Governance",
                "Risk Management & Compliance",
                "Strategic Objectives",
                "Continuous Improvement",
                "Effective Safeguarding",
                "Ethical Culture & Accountability",
                "Diversity, Equity, Inclusion"
            ],
            'concerns': [
                "Financial Instability",
                "Weak Governance Structures",
                "Non-Compliance in Risk & Safeguarding",
                "Unclear Objectives",
                "Resistance to Feedback",
                "Insufficient Safeguarding",
                "Ethical Concerns",
                "Lack of Inclusivity"
            ]
        }
        print("[BestPracticeExtractor] Initialization complete")

    def _construct_prompt(self, text: str, summary: DocumentSummarizer) -> str:
        """Construct enhanced analysis prompt"""
        print("\n[_construct_prompt] Constructing analysis prompt")
        
        prompt = f"""
        # Context: {GOVERNANCE_CONTEXT} \n####
        
        # Partner Name: {summary['sport_name']}
        Partner {summary['sport_name']}  Background:
        {summary['summary']}


        Below is a chunck of the text document from the Partner Report for {summary['sport_name']} partner. 
        Document Text: {text}

        \n####
        Task: Analyze the text for governance bestpractices or/and concerns.

        First, determine if the Document Text contains significant governance content that is relevant to the governance team and meets the criteria for: Best Practices or a Concerns
        
        Must of the Document test wont contain any Best Practices or Concerns, its okay if it doesnt we will move on to the next document text 
        If the  Doucment Text doesn't contain significant governance content, respond with:
        {{"criteria_met": false, "practices": []}}


        If governance criteria for Best Practices or a Concerns found is met in the Document Text:
        1. Identify it as a best practices and concerns, best practice is "true", concern is "false"
        2. Categorize each finding into one of the predefined categories, 
        3. Provide specific evidence from the text
        4. Assess the impact

        For each practice or concern identified, provide:
        {{
            "practice": "The specific practice or concern",
            "category": "One of the predefined categories",
            "context": "Relevant surrounding context",
            "impact": "Expected impact or implications",
            "is_best_practice": true/false,
            "evidence": "Direct evidence from text"
        }}
        \n####

        Always Return your answer in the json format below: if criteria not met, return "criteria_met": False and practices/concerns as empty []
        {{
            "criteria_met": True/False,
            "practices": [list of practices/concerns],
            "dominant_categories": ["main categories found"]
        }}
        """
        
        print(f"[_construct_prompt] Prompt constructed with length: {len(prompt)}")
        return prompt

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key with metadata"""
        print(f"[_get_cache_key] Generating cache key for text of length: {len(text)}")
        key = hash(text)
        print(f"[_get_cache_key] Generated key: {key}")
        return key

    def process_chunk(self, chunk: DocumentChunk, summary: DocumentSummarizer) -> Optional[BestPractice]:
        """Process chunk with enhanced criteria checking"""
        print(f"\n[process_chunk] Processing chunk {chunk.position + 1} from document {chunk.document.id}")
        start_time = time.time()
        cache_key = self._get_cache_key(chunk.text)

        # Check cache
        if cache_key in self._cache:
            print("[process_chunk] Cache hit!")
            self.monitor.log_document_metric(
                chunk.document.id,
                f"chunk_{chunk.position}_cache_hit",
                True
            )
            return self._cache[cache_key]

        print("[process_chunk] Cache miss - processing chunk")
        with self.monitor.stage(ProcessStage.EXTRACT):
            print("[process_chunk] Analyzing chunk with GPT-4")
            
            function_schema = {
                "name": "analyze_governance_content",
                "parameters": ChunkAnalysisSchema.schema()
            }
            
            response = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": self._construct_prompt(chunk.text, summary)
                }],
                temperature=0.3,
                functions=[function_schema],
                function_call={"name": "analyze_governance_content"}
            )

            print("[process_chunk] Received response from GPT-4")
            content = response.choices[0].message.function_call.arguments
            extraction_time = time.time() - start_time
            
            analysis_data = json.loads(content)
            print(f"[process_chunk] Analysis data meets criteria.......:" , analysis_data)
            # Skip if criteria not met
            if analysis_data['criteria_met'] == False:
                print("[process_chunk] Chunk does not meet governance criteria")
                return None

            print("[process_chunk] Chunk meets criteria, processing practices")
            practices = []
            
            for practice_data in analysis_data.get('practices', []):
                confidence_score = self._calculate_confidence_score(
                    practice_data,
                    chunk.word_count
                )
                
                practice = BestPractice.objects.create(
                    document=chunk.document,
                    text=practice_data.get("practice", ""),
                    context=practice_data.get("context", ""),
                    impact=practice_data.get("impact", ""),
                    page_number=chunk.page_number,
                    extraction_time=extraction_time,
                    confidence_score=confidence_score,
                    keywords=practice_data.get("evidence", "").split(),
                    themes=[practice_data.get("category", "")],
                    is_best_practice=practice_data.get("is_best_practice", True)  # Added line
                )
                practices.append(practice)

            print(f"[process_chunk] Created {len(practices)} practice records")
            
            # Cache the most confident practice for this chunk
            if practices:
                best_practice = max(practices, key=lambda p: p.confidence_score)
                self._cache[cache_key] = best_practice
            
            return practices if practices else None

    def _calculate_confidence_score(self, practice_data: Dict, word_count: int) -> float:
        """Enhanced confidence calculation"""
        print(f"\n[_calculate_confidence_score] Starting confidence calculation")
        score = 1.0

        # Core criteria checks
        if word_count < 50:
            score *= 0.8
        elif word_count > 500:
            score *= 0.9

        # Evidence quality
        evidence = practice_data.get('evidence', '')
        if evidence and len(evidence.split()) > 10:
            score *= 1.1

        # Category alignment
        category = practice_data.get('category', '')
        if any(cat.lower() in category.lower() 
               for cats in self.categories.values() 
               for cat in cats):
            score *= 1.1

        # Required fields check
        required_fields = ['practice', 'category', 'context', 'impact', 'evidence']
        missing_fields = [f for f in required_fields if not practice_data.get(f)]
        if missing_fields:
            score *= 0.7

        final_score = max(0.0, min(1.0, score))
        return final_score