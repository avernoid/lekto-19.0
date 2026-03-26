import os
from odoo.tools import config
from cryptography.fernet import Fernet

def _get_cipher():
    """Get Odoo's default encryption cipher"""
    secret_key = config.get('db_secret') or os.getenv('ODOO_DB_SECRET')

    if not secret_key:
        # raise ValueError('The "db_secret" is not configured in Odoo or as an environment variable')
        return False, None
    return True, Fernet(secret_key.encode('utf-8'))

def encrypt_credential(param):
    """Encrypt the password / sessionid using Odoo's encryption key."""
    valid_encryption, cipher = _get_cipher()

    if valid_encryption and cipher:
        return cipher.encrypt(param.encode()).decode()
    else:
        return param

def decrypt_credential(encrypted_param):
    """Decrypt the password / sessionid using Odoo's encryption key."""
    valid_encryption, cipher = _get_cipher()
    if valid_encryption and cipher:
        return cipher.decrypt(encrypted_param.encode()).decode()
    else:
        return encrypted_param
