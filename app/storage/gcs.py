import logging

import os
from google.cloud import storage
from google.cloud.storage import Bucket

from app.core.config import settings
from app.core.exceptions import StorageException
from app.storage.base import StorageProvider

logger = logging.getLogger(__name__)


class GoogleCloudStorage(StorageProvider):

    def __init__(self) -> None:
        try:
            if settings.google_application_credentials and os.path.exists(settings.google_application_credentials):
                self.client = storage.Client.from_service_account_json(
                    settings.google_application_credentials
                )
            else:
                self.client = storage.Client()
            
            self.bucket: Bucket = self.client.bucket(
                settings.gcs_bucket_name
            )

            logger.info(
                "Connected to GCS bucket: %s",
                settings.gcs_bucket_name,
            )

        except Exception as e:
            logger.exception(
                "Failed to initialize Google Cloud Storage."
            )

            raise StorageException(
                message="Unable to initialize Google Cloud Storage.",
                provider="gcs",
                error_code="init_failed"
            ) from e

    async def upload_file(
        self,
        local_file_path: str,
        destination_path: str,
        content_type: str | None = None,
    ) -> str:
        blob = self.bucket.blob(destination_path)
        if content_type:
            blob.upload_from_filename(local_file_path, content_type=content_type)
        else:
            blob.upload_from_filename(local_file_path)
        logger.info("Uploaded file to %s", destination_path)
        return destination_path

    async def download_file(self, file_path: str, destination_path: str) -> str:
        blob = self.bucket.blob(file_path)
        blob.download_to_filename(destination_path)
        logger.info("downloaded to path %s", destination_path)
        return destination_path

    async def delete_file(self, file_path: str) -> bool:
        blob = self.bucket.blob(file_path)
        blob.delete()
        logger.info("Deleted file from %s", file_path)
        return True
    
    async def file_exist(self, file_path: str) -> bool:
        blob = self.bucket.blob(file_path)
        logger.info("file path %s", file_path)
        return blob.exists()

    async def get_meta_data(self, file_path: str) -> dict:
        blob = self.bucket.blob(file_path)
        if blob is None:
            return {}

        return {
            "size": blob.size,
            "content_type": blob.content_type,
            "created": blob.time_created,
            "updated": blob.updated,
        }

    async def get_signed_url(self, file_path: str, expiration: int = 3600) -> str:
        from datetime import timedelta
        blob = self.bucket.blob(file_path)
        return blob.generate_signed_url(expiration=timedelta(seconds=expiration))