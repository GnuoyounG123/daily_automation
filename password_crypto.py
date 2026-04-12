#!/usr/bin/env python3
"""密码加密模块 - 使用Fernet对称加密替代Base64编码"""

import base64
from pathlib import Path


class PasswordCrypto:
    """Fernet对称加密密码管理器

    - 首次使用自动生成密钥文件 .secret_key
    - 加密后以 fernet: 前缀存储
    - 兼容旧的 enc: (base64) 前缀格式
    - .secret_key 应加入 .gitignore，不提交到仓库
    """

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self._key = None
        self._fernet = None
        self._load_or_create_key()

    def _load_or_create_key(self):
        key_file = self.project_dir / ".secret_key"
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            self._fernet = None
            return

        if key_file.exists():
            key_data = key_file.read_bytes().strip()
            if len(key_data) == 44:
                self._key = key_data
                self._fernet = Fernet(self._key)
                return

        self._key = Fernet.generate_key()
        key_file.write_bytes(self._key)
        self._fernet = Fernet(self._key)

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        if self._fernet is None:
            return "enc:" + base64.b64encode(plaintext.encode('utf-8')).decode('utf-8')
        encrypted = self._fernet.encrypt(plaintext.encode('utf-8'))
        return "fernet:" + encrypted.decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        if ciphertext.startswith("fernet:"):
            if self._fernet is None:
                return ciphertext
            try:
                decrypted = self._fernet.decrypt(ciphertext[7:].encode('utf-8'))
                return decrypted.decode('utf-8')
            except Exception:
                return ciphertext
        if ciphertext.startswith("enc:"):
            try:
                return base64.b64decode(ciphertext[4:]).decode('utf-8')
            except Exception:
                return ciphertext
        return ciphertext
