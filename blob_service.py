import json
import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

blob_service = BlobServiceClient.from_connection_string(
    os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)

container_name = os.getenv("AZURE_CONTAINER_NAME")
blob_name = os.getenv("AZURE_BLOB_NAME")


def read_students():
    container = blob_service.get_container_client(container_name)
    blob = container.get_blob_client(blob_name)

    try:
        data = blob.download_blob().readall()
        return json.loads(data)
    except:
        return []


def write_students(students):
    container = blob_service.get_container_client(container_name)
    blob = container.get_blob_client(blob_name)
    blob.upload_blob(json.dumps(students), overwrite=True)
