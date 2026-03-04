# core/security.py
class SecretManager:
    _instance = None
    _password = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecretManager, cls).__new__(cls)
        return cls._instance

    def set_password(self, password: str):
        """Securely store the sudo password in memory."""
        self._password = password

    def get_password(self) -> str:
        """Retrieve the stored password."""
        return self._password

    def has_password(self) -> bool:
        """Check if a password has been stored."""
        return self._password is not None

    def clear(self):
        """Clear the stored password."""
        self._password = None
