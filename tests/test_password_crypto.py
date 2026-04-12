import unittest
import tempfile
from pathlib import Path


class TestPasswordCrypto(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        from password_crypto import PasswordCrypto
        tmpdir = tempfile.mkdtemp()
        crypto = PasswordCrypto(Path(tmpdir))
        original = "my_secret_password"
        encrypted = crypto.encrypt(original)
        self.assertNotEqual(encrypted, original)
        self.assertTrue(encrypted.startswith("fernet:"))
        decrypted = crypto.decrypt(encrypted)
        self.assertEqual(decrypted, original)

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_decrypt_plain_text(self):
        from password_crypto import PasswordCrypto
        tmpdir = tempfile.mkdtemp()
        crypto = PasswordCrypto(Path(tmpdir))
        plain = "plain_password"
        self.assertEqual(crypto.decrypt(plain), plain)

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_decrypt_legacy_base64(self):
        from password_crypto import PasswordCrypto
        tmpdir = tempfile.mkdtemp()
        crypto = PasswordCrypto(Path(tmpdir))
        import base64
        legacy = "enc:" + base64.b64encode(b"old_password").decode()
        result = crypto.decrypt(legacy)
        self.assertEqual(result, "old_password")

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_key_persistence(self):
        from password_crypto import PasswordCrypto
        tmpdir = tempfile.mkdtemp()
        crypto1 = PasswordCrypto(Path(tmpdir))
        encrypted = crypto1.encrypt("test123")

        crypto2 = PasswordCrypto(Path(tmpdir))
        decrypted = crypto2.decrypt(encrypted)
        self.assertEqual(decrypted, "test123")

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
