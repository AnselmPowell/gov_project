# src/governance_analysis/services/theme_analyzer.py
from typing import Dict, Set, List, Optional
from openai import OpenAI
from django.conf import settings
import json
import time
from collections import Counter
from ..models import BestPractice
from .monitoring.system_monitor import ProcessStage, SystemMonitor

from pydantic import BaseModel
from typing import List

class ThemeAnalysisSchema(BaseModel):
    themes: List[str]
    keywords: List[str]

class ThemeAnalyzer:
    """Efficient theme analysis with theme consistency"""
    def __init__(self, monitor: SystemMonitor):
        print("\n[ThemeAnalyzer] Initializing analyzer")
        self.llm = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.monitor = monitor
        self.known_themes: Set[str] = set()
        self.theme_frequency: Counter = Counter()
        self._cache = {}
        print("[ThemeAnalyzer] Initialization complete")
        print(f"[ThemeAnalyzer] Current known themes: {len(self.known_themes)}")

    def _construct_theme_prompt(self, practice: BestPractice) -> str:
        """Construct prompt with theme guidance"""
        print("\n[_construct_theme_prompt] Constructing theme analysis prompt")
        top_themes = [theme for theme, _ in self.theme_frequency.most_common(5)]
        print(f"[_construct_theme_prompt] Top themes for context: {top_themes}")
        
        prompt = f"""
        Common Themes: {json.dumps(top_themes)}
        
        Best Practice: {practice.text}
        Context: {practice.context}
        Impact: {practice.impact}
        
        Task: Analyze this best practice to identify:
        1. Key governance themes (max 3) - Consider using existing themes if relevant
        2. Specific keywords (max 5) that capture the core concepts
        
        Ensure themes are consistent and keywords are specific.
        """
        print(f"[_construct_theme_prompt] Prompt constructed, length: {len(prompt)}")
        return prompt

    def _get_cache_key(self, practice: BestPractice) -> str:
        """Generate cache key for practice"""
        print(f"\n[_get_cache_key] Generating cache key for practice ID: {practice.id}")
        key = f"{practice.id}:{practice.extraction_time}"
        print(f"[_get_cache_key] Generated key: {key}")
        return key

    def analyze_practice(self, practice: BestPractice) -> Dict:
        """Analyze practice with caching and theme consistency"""
        print(f"\n[analyze_practice] Starting analysis for practice ID: {practice.id}")
        start_time = time.time()
        cache_key = self._get_cache_key(practice)

        if cache_key in self._cache:
            print("[analyze_practice] Cache hit! Returning cached analysis")
            self.monitor.log_document_metric(
                practice.document.id,
                f"practice_{practice.id}_cache_hit",
                True
            )
            cached_result = self._cache[cache_key]
            print(f"[analyze_practice] Cached result: {cached_result}")
            return cached_result

        print("[analyze_practice] Cache miss - performing analysis")
        with self.monitor.stage(ProcessStage.ANALYZE):
            self.monitor.log_document_metric(
                practice.document.id,
                f"analyzing_practice_{practice.id}",
                "started"
            )
            print("[analyze_practice] Analysis stage started")

            function_schema = {
                "name": "analyze_theme",
                "parameters": ThemeAnalysisSchema.schema()
            }

            print("[analyze_practice] Sending request to GPT-4")
            response = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": self._construct_theme_prompt(practice)
                }],
                temperature=0.3,
                functions=[function_schema],
                function_call={"name": "analyze_theme"}
            )
            print("[analyze_practice] Received response from GPT-4")

            print("[analyze_practice] Parsing analysis response")
            analysis_content = response.choices[0].message.function_call.arguments
            analysis = json.loads(analysis_content)
            analysis_time = time.time() - start_time
            print(f"[analyze_practice] Analysis parsed: {analysis}")
            print(f"[analyze_practice] Analysis time: {analysis_time:.2f} seconds")

            print("[analyze_practice] Updating theme tracking")
            print(f"[analyze_practice] Previous known themes: {self.known_themes}")
            self.known_themes.update(analysis['themes'])
            self.theme_frequency.update(analysis['themes'])
            print(f"[analyze_practice] Updated known themes: {self.known_themes}")
            print(f"[analyze_practice] Theme frequencies: {dict(self.theme_frequency)}")

            print("[analyze_practice] Updating practice record")
            practice.themes = analysis['themes']
            practice.keywords = analysis['keywords']
            practice.analysis_time = analysis_time
            practice.save()
            print("[analyze_practice] Practice record updated")

            result = {
                'practice_id': practice.id,
                'themes': analysis['themes'],
                'keywords': analysis['keywords'],
                'duration': analysis_time
            }
            print(f"[analyze_practice] Result prepared: {result}")

            print("[analyze_practice] Updating cache")
            self._cache[cache_key] = result
            print(f"[analyze_practice] Current cache size: {len(self._cache)}")

            if len(self._cache) > 1000:
                print("[analyze_practice] Cache size limit reached, removing oldest entry")
                self._cache.pop(next(iter(self._cache)))

            print("[analyze_practice] Analysis complete")
            return practice

    def get_theme_statistics(self) -> Dict:
        """Get theme usage statistics"""
        print("\n[get_theme_statistics] Generating theme statistics")
        stats = {
            'total_themes': len(self.known_themes),
            'theme_frequency': dict(self.theme_frequency),
            'top_themes': [theme for theme, _ in self.theme_frequency.most_common(5)]
        }
        print(f"[get_theme_statistics] Statistics generated: {stats}")
        return stats