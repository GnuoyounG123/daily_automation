import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.crypto import RSAEncryptor


def test_rsa_encrypt():
    """测试RSA加密"""
    password = "test_password"
    modulus = "a3b2c1d4e5f6"
    exponent = "10001"
    
    encrypted = RSAEncryptor.encrypt(password, modulus, exponent)
    
    assert encrypted is not None
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0
    print("RSA加密测试通过")


if __name__ == '__main__':
    test_rsa_encrypt()