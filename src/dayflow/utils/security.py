"""Security utilities for API key storage and data encryption."""

import keyring
from typing import Optional
from cryptography.fernet import Fernet


class SecureStorage:
    """Secure storage for API keys and sensitive data using Windows Credential Manager."""

    SERVICE_NAME = "Dayflow"

    @classmethod
    def save_api_key(cls, provider: str, api_key: str) -> None:
        """
        Save API key securely in Windows Credential Manager.

        Args:
            provider: AI provider name (gemini, openai, etc.)
            api_key: The API key to store
        """
        keyring.set_password(cls.SERVICE_NAME, f"{provider}_api_key", api_key)

    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]:
        """
        Retrieve API key from Windows Credential Manager.

        Args:
            provider: AI provider name

        Returns:
            API key or None if not found
        """
        return keyring.get_password(cls.SERVICE_NAME, f"{provider}_api_key")

    @classmethod
    def delete_api_key(cls, provider: str) -> None:
        """
        Delete API key from Windows Credential Manager.

        Args:
            provider: AI provider name
        """
        try:
            keyring.delete_password(cls.SERVICE_NAME, f"{provider}_api_key")
        except keyring.errors.PasswordDeleteError:
            pass  # Key doesn't exist

    @classmethod
    def has_api_key(cls, provider: str) -> bool:
        """
        Check if API key exists for provider.

        Args:
            provider: AI provider name

        Returns:
            True if API key exists
        """
        return cls.get_api_key(provider) is not None


class DataEncryption:
    """Data encryption utilities using Fernet symmetric encryption."""

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize encryption with a key.

        Args:
            key: Encryption key (32 url-safe base64-encoded bytes)
                 If None, generates a new key
        """
        if key is None:
            key = Fernet.generate_key()
        self.cipher = Fernet(key)
        self.key = key

    def encrypt(self, data: str) -> bytes:
        """
        Encrypt string data.

        Args:
            data: String to encrypt

        Returns:
            Encrypted bytes
        """
        return self.cipher.encrypt(data.encode())

    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Decrypt encrypted data.

        Args:
            encrypted_data: Encrypted bytes

        Returns:
            Decrypted string
        """
        return self.cipher.decrypt(encrypted_data).decode()

    @staticmethod
    def generate_key() -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
