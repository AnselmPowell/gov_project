# src/vector_store/test_vector_store.py
import asyncio
from django.test import TestCase
from django.conf import settings
from asgiref.sync import sync_to_async
from vector_store.services import VectorService
from vector_store.models import VectorDocument

class TestVectorStore:
    def __init__(self):
        self.vector_service = VectorService()
        self.sample_documents = [
            {
                "content": "Free shipping is available on orders over $50. Orders placed before 2 PM EST ship the same day.",
                "metadata": {"category": "shipping", "importance": "high"}
            },
            {
                "content": "Returns must be initiated within 30 days of purchase. Items must be unworn with original tags.",
                "metadata": {"category": "returns", "importance": "high"}
            },
            {
                "content": "We accept Visa, Mastercard, American Express, and PayPal as payment methods.",
                "metadata": {"category": "payment", "importance": "medium"}
            },
            {
                "content": "Our loyalty program offers 1 point for every dollar spent. 100 points equals $5 in store credit.",
                "metadata": {"category": "loyalty", "importance": "medium"}
            }
        ]

    async def run_search_test(self):
        """Test vector similarity search"""
        print("\nInserting test documents...")
        
        # # Insert test documents
        # for doc in self.sample_documents:
        #     try:
        #         document = await self.vector_service.create_document(
        #             content=doc["content"],
        #             metadata=doc["metadata"]
        #         )
        #         print(f"Inserted document {document.id}: {doc['metadata']['category']}")
        #     except Exception as e:
        #         print(f"Error inserting document: {str(e)}")

        # print("\nTest data inserted successfully")

        # Test queries
        test_queries = [
            {
                "query": "How does shipping work, and available options?",
                "expected_category": ["shipping", "payments"],
            },
            # {
            #     "query": "What's your return policy?",
            #     "expected_category": "returns"
            # },
            # {
            #     "query": "How can I pay for my order?",
            #     "expected_category": "payment"
            # }
        ]

        print("\nTesting similarity search...")
        for test in test_queries:
            try:
                results = await self.vector_service.similarity_search(
                    query=test["query"],
                    limit=4,
                    threshold=0.8,
                    metadata_filters=test['expected_category']
                )
                
                print(f"\nQuery: {test['query']}")
                print(f"Expected Category: {test['expected_category']}")
                print("\nResults:")
                
                if not results:
                    print("No matching results found")
                else:
                    for i, result in enumerate(results, 1):
                        print(f"\nResult {i}:")
                        print(f"Category: {result.metadata.get('category')}")
                        print(f"Content: {result.contents}")
                        
                        # Print match indicator
                        if result.metadata.get('category') in test['expected_category']:
                            print("✓ Category matches expected")
                        else:
                            print("✗ Category does not match expected")
                    
            except Exception as e:
                print(f"Error in search: {str(e)}")
                import traceback
                print(traceback.format_exc())

def run_test():
    """Run the vector store test"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        test = TestVectorStore()
        loop.run_until_complete(test.run_search_test())
    finally:
        loop.close()

if __name__ == '__main__':
    run_test()