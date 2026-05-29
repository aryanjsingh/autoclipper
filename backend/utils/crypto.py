"""
Encryption utility
Used for encrypting and storing sensitive information such as cookies
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

# Get encryption key
def get_encryption_key():
    """Get encryption key"""
    # Get key from environment variable, generate one if not set
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        # Generate new key
        key = Fernet.generate_key()
        logger.warning("ENCRYPTION_KEY environment variable is not set, using temporary key. Please set the environment variable to keep data secure.")
    
    if isinstance(key, str):
        key = key.encode()
    
    return key

def encrypt_data(data: str) -> str:
    """Encrypt data"""
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt data: {str(e)}")
        raise

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data"""
    try:
        key = get_encryption_key()
        f = Fernet(key)
        decoded_data = base64.b64decode(encrypted_data.encode())
        decrypted_data = f.decrypt(decoded_data)
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt data: {str(e)}")
        raise
