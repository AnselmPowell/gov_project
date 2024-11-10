# governance_analysis/management/commands/test_gov_pipeline.py

from django.core.management.base import BaseCommand
from django.conf import settings
from ...tests.test_gov_pipeline import run_test

class Command(BaseCommand):
    help = 'Run the governance analysis pipeline test'

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.SUCCESS('Starting governance analysis pipeline test...')
        )
        try:
            run_test()
            self.stdout.write(
                self.style.SUCCESS('Pipeline test completed successfully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Pipeline test failed: {str(e)}')
            )