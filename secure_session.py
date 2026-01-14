"""
Secure session management with encrypted API key storage
"""

from cryptography.fernet import Fernet
import os
import base64
from hashlib import sha256
import logging

logger = logging.getLogger(__name__)


class SecureSessionManager:
    """
    Manages encryption and decryption of sensitive session data.
    API keys are encrypted before storage using Fernet symmetric encryption.
    """

    def __init__(self, secret_key: str = None):
        """
        Initialize the secure session manager.

        Args:
            secret_key: Secret key for encryption (from environment/config)
        """
        if not secret_key:
            secret_key = os.environ.get('SECRET_KEY')

        if not secret_key:
            raise ValueError(
                "SECRET_KEY must be set in environment or .env file. "
                "Generate one with: python3 -c 'import secrets; print(secrets.token_hex(32))'"
            )

        # Derive encryption key from SECRET_KEY
        key_material = sha256(str(secret_key).encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key_material))

        logger.info("SecureSessionManager initialized")

    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt API key before storing in session.

        Args:
            api_key: Plaintext API key

        Returns:
            Encrypted API key as base64 string
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        try:
            encrypted = self.cipher.encrypt(api_key.encode())
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Error encrypting API key: {e}")
            raise

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt API key from session.

        Args:
            encrypted_key: Encrypted API key from session

        Returns:
            Decrypted API key as plaintext

        Raises:
            ValueError: If decryption fails (invalid key or tampered data)
        """
        if not encrypted_key:
            raise ValueError("Encrypted key cannot be empty")

        try:
            decrypted = self.cipher.decrypt(encrypted_key.encode())
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Error decrypting API key: {e}")
            raise ValueError("Failed to decrypt API key - session may be corrupted")

    def encrypt_dict(self, data: dict) -> dict:
        """
        Encrypt all string values in a dictionary.

        Args:
            data: Dictionary with string values to encrypt

        Returns:
            Dictionary with encrypted values
        """
        encrypted_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                encrypted_data[key] = self.encrypt_api_key(value)
            else:
                encrypted_data[key] = value
        return encrypted_data

    def decrypt_dict(self, encrypted_data: dict) -> dict:
        """
        Decrypt all encrypted string values in a dictionary.

        Args:
            encrypted_data: Dictionary with encrypted string values

        Returns:
            Dictionary with decrypted values
        """
        decrypted_data = {}
        for key, value in encrypted_data.items():
            if isinstance(value, str) and key.endswith('_enc'):
                # Only decrypt fields that end with _enc
                decrypted_data[key.replace('_enc', '')] = self.decrypt_api_key(value)
            else:
                decrypted_data[key] = value
        return decrypted_data
