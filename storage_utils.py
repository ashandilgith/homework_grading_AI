from google.cloud import storage
import os

def upload_file(source_file, destination_blob_name):
    """
    Uploads a file object to the Google Cloud Storage Bucket.
    """
    # 1. Get Config from .env
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    bucket_name = os.environ["BUCKET_NAME"]
    
    # 2. Connect to the Client with EXPLICIT Project ID
    # This fixes the "Project was not passed" error
    storage_client = storage.Client(project=project_id)
    
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    # 3. Ensure we are reading from the start of the file
    source_file.seek(0)
    
    # 4. Upload
    blob.upload_from_file(source_file)

    return blob.public_url