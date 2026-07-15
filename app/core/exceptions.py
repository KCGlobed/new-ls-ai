class AppException(Exception):
    """
    Base exception for the application.
    """

    def __init__(
        self,
        message: str,
    ):
        self.message = message
        super().__init__(message)



class StorageException(AppException):
    """
    Raised when any storage operation fails.
    """
    def __init__(self, message: str, provider: str, error_code: str):
        self.error_code = error_code
        self.provider = provider
        super().__init__(message)
