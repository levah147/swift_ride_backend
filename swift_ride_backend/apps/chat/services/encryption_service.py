"""
Service for message encryption and decryption.
"""

import base64
from cryptography.fernet import Fernet
from django.conf import settings


class EncryptionService:
    """
    Service for encrypting and decrypting messages.
    """
    
    @staticmethod
    def get_encryption_key():
        """
        Get encryption key from settings or generate one.
        """
        # In production, this should be stored securely
        key = getattr(settings, 'CHAT_ENCRYPTION_KEY', None)
        
        if not key:
            # Generate a new key (for development only)
            key = Fernet.generate_key()
            print(f"Generated encryption key: {key.decode()}")
        
        if isinstance(key, str):
            key = key.encode()
        
        return key
    
    @staticmethod
    def encrypt_message(message_content):
        """
        Encrypt a message.
        """
        try:
            key = EncryptionService.get_encryption_key()
            fernet = Fernet(key)
            
            # Encrypt the message
            encrypted_content = fernet.encrypt(message_content.encode())
            
            # Return base64 encoded string
            return base64.b64encode(encrypted_content).decode()
        
        except Exception as e:
            print(f"Encryption error: {e}")
            return None
    
    @staticmethod
    def decrypt_message(encrypted_content):
        """
        Decrypt a message.
        """
        try:
            key = EncryptionService.get_encryption_key()
            fernet = Fernet(key)
            
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_content.encode())
            
            # Decrypt the message
            decrypted_content = fernet.decrypt(encrypted_bytes)
            
            return decrypted_content.decode()
        
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
