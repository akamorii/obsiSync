import base64
import hashlib
import os
from cryptography.fernet import Fernet, InvalidToken
from dotenv import dotenv_values
from setSettings import ENV_FILE


class Crypt:
    _SALT_SIZE = 16
    _ITERATIONS = 600_000

    def __init__(self, secret=None):
        secret = secret or dotenv_values(ENV_FILE).get("SECRET_KEY")
        if not secret:
            raise RuntimeError("SECRET_KEY not found in .env, run setSettings.py")
        self._secret = secret.encode()


    def _fernet(self, salt):
        # ключ из .env хэшируется PBKDF2-SHA256 с солью, соль хранится в начале файла
        key = hashlib.pbkdf2_hmac("sha256", self._secret, salt, Crypt._ITERATIONS)
        return Fernet(base64.urlsafe_b64encode(key))


    def encryptFile(self, src, dst):
        salt = os.urandom(Crypt._SALT_SIZE)
        with open(src, "rb") as f:
            token = self._fernet(salt).encrypt(f.read())
        with open(dst, "wb") as f:
            f.write(salt + token)


    def decryptFile(self, src, dst):
        with open(src, "rb") as f:
            blob = f.read()
        salt, token = blob[:Crypt._SALT_SIZE], blob[Crypt._SALT_SIZE:]
        try:
            data = self._fernet(salt).decrypt(token)
        except InvalidToken:
            raise RuntimeError(f"can't decrypt '{os.path.basename(src)}': wrong SECRET_KEY or corrupted file")
        with open(dst, "wb") as f:
            f.write(data)
