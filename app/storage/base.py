from abc import ABC, abstractmethod
import logging
from datetime import timedelta
from typing import Any, Dict

logger = logging.getLogger(__name__)

class StorageProvider(ABC):
    """
    Base interface for all storage providers.
    """

    @abstractmethod
    async def upload_file(
        self,
        local_file_path: str,
        destination_path: str,
        content_type: str | None = None,
    ) -> str:
        """
        Upload local file to storage.

        Returns:
            Storage path.
        """
        pass

    @abstractmethod
    async def download_file(self, file_path: str, destination_path: str) -> str:
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        pass
    
    @abstractmethod
    async def file_exist(self, file_path: str) -> bool:
        pass

    @abstractmethod
    async def get_meta_data(self, file_path: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_signed_url(self, file_path: str, expiration: int = 3600) -> str:
        pass