import base64
import json
import os
import platform
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.logging_config import get_logger
logger = get_logger(__name__)

class SecretsManager:
    """
    Manages sensitive credentials securely.
    In production: use HashiCorp Vault or AWS Secrets Manager.
    For ISRO deployment: uses encrypted local file store.
    """

    def __init__(self, encryption_key: str | None = None):
        if encryption_key is None:
            encryption_key = os.getenv("SECRETS_ENCRYPTION_KEY")
            
        if encryption_key is None:
            # Fallback: Derive key from machine-specific data
            # Not cryptographically strong against advanced attacks, but prevents casual plaintext scraping
            machine_data = f"{platform.node()}_{platform.machine()}_{platform.system()}"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"soc_static_salt",
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(machine_data.encode()))
            self.fernet = Fernet(key)
        else:
            self.fernet = Fernet(encryption_key.encode())

    def encrypt_secret(self, plaintext: str) -> str:
        """Encrypt with Fernet symmetric encryption."""
        token = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(token).decode('utf-8')

    def decrypt_secret(self, ciphertext: str) -> str:
        """Decrypt from base64 encoded Fernet token."""
        token = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
        return self.fernet.decrypt(token).decode('utf-8')

    def _read_secrets_file(self, secrets_file: str) -> dict:
        path = Path(secrets_file)
        if not path.exists():
            return {}
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read secrets file", error=str(e))
            return {}

    def _write_secrets_file(self, secrets_dict: dict, secrets_file: str):
        path = Path(secrets_file)
        # Ensure file permissions are restrictive
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(mode=0o600, exist_ok=True)
        try:
            with open(path, 'w') as f:
                json.dump(secrets_dict, f, indent=2)
            os.chmod(path, 0o600)
        except Exception as e:
            logger.error("Failed to write secrets file", error=str(e))

    def store_secret(self, name: str, value: str, secrets_file: str = ".secrets"):
        """Append encrypted secret to .secrets file (JSON format)."""
        secrets_dict = self._read_secrets_file(secrets_file)
        encrypted_val = self.encrypt_secret(value)
        secrets_dict[name] = encrypted_val
        self._write_secrets_file(secrets_dict, secrets_file)

    def load_secret(self, name: str, secrets_file: str = ".secrets") -> str | None:
        """Load and decrypt from .secrets file."""
        secrets_dict = self._read_secrets_file(secrets_file)
        if name not in secrets_dict:
            return None
        try:
            return self.decrypt_secret(secrets_dict[name])
        except Exception as e:
            logger.error(f"Failed to decrypt secret: {name}", error=str(e))
            return None

    def rotate_secret(self, name: str, new_value: str, secrets_file: str = ".secrets"):
        """Update secret with new encrypted value."""
        self.store_secret(name, new_value, secrets_file)

    @staticmethod
    def generate_jwt_secret() -> str:
        """Generate cryptographically secure 64-byte hex secret."""
        return secrets.token_hex(64)

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, list[str]]:
        """Check: min 12 chars, uppercase, lowercase, digit, special char."""
        failures = []
        if len(password) < 12:
            failures.append("Password must be at least 12 characters long.")
        if not any(c.isupper() for c in password):
            failures.append("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in password):
            failures.append("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in password):
            failures.append("Password must contain at least one digit.")
        special_chars = "!@#$%^&*()_+-=[]{}|;':,./<>?"
        if not any(c in special_chars for c in password):
            failures.append(f"Password must contain at least one special character.")
            
        return len(failures) == 0, failures
