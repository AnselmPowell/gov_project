# src/vector_store/management/commands/test_vector_store.py
from django.core.management.base import BaseCommand
from vector_store.test_vector_store import run_test

class Command(BaseCommand):
    help = 'Test vector store functionality with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting vector store test...')
        run_test()
        self.stdout.write(self.style.SUCCESS('Test completed'))



