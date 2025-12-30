from google.cloud import storage
import os

# Try to get bucket name from environment, else use a placeholder for testing
BUCKET_NAME = os.environ.get("BUCKET_NAME", "iskole-dev-bucket")

def upload_to_gcs(file_obj, username):
    """
    Uploads a file directly to Google Cloud Storage.
    Returns: The secure 'gs://' path or a signed URL.
    """
    try:
        # Auto-authenticates using the Service Account in Cloud Run
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        
        # Naming convention: username/filename to prevent collisions
        blob_name = f"{username}/{file_obj.name}"
        blob = bucket.blob(blob_name)
        
        # Reset file pointer to start
        file_obj.seek(0)
        blob.upload_from_file(file_obj, content_type=file_obj.type)
        
        return f"gs://{BUCKET_NAME}/{blob_name}"
    except Exception as e:
        print(f"Storage Error: {e}")
        return None