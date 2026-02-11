import sys
import os

# Add backend directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.core.config import settings
from pymilvus import connections, utility

def reset_collection():
    print(f"Connecting to Milvus...")
    try:
        # Pymilvus 2.x logic
        if settings.MILVUS_URI:
            print(f"Running with URI configuration: {settings.MILVUS_URI}")
            # If URI starts with https, it's Zilliz Cloud usually
            connections.connect(alias="default", uri=settings.MILVUS_URI, token=settings.MILVUS_TOKEN)
        elif settings.MILVUS_HOST:
            print(f"Running with Host configuration: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST, 
                port=settings.MILVUS_PORT, 
                user=settings.MILVUS_USER, 
                password=settings.MILVUS_PASSWORD
            )
        else:
             print("No Milvus configuration found. Please check your .env file.")
             return

        collection_name = settings.MILVUS_COLLECTION
        print(f"Checking collection: {collection_name}")
        
        if utility.has_collection(collection_name):
            print(f"Collection '{collection_name}' exists. Dropping it...")
            utility.drop_collection(collection_name)
            print("Dropped successfully.")
        else:
            print(f"Collection '{collection_name}' does not exist.")
            
    except Exception as e:
        print(f"Error resetting collection: {e}")

if __name__ == "__main__":
    reset_collection()
