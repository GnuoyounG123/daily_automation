class RSAEncryptor:
    @staticmethod
    def encrypt(password: str, modulus: str, exponent: str) -> str:
        """
        使用RSA公钥加密密码（浙大SSO定制算法）
        
        算法流程（参考Dart实现）：
        1. 密码转UTF-8字节，再转十六进制字符串
        2. 十六进制转BigInt
        3. RSA加密: c = m^e mod n
        4. 结果补零到128位
        
        Args:
            password: 明文密码
            modulus: 十六进制模数
            exponent: 十六进制指数
        
        Returns:
            十六进制加密后的密码（128位）
        """
        # 1. 密码转UTF-8字节，再转十六进制
        pwd_bytes = password.encode('utf-8')
        pwd_hex = ''.join([format(b, '02x') for b in pwd_bytes])
        
        # 2. 解析公钥参数
        n = int(modulus, 16)
        e = int(exponent, 16)
        
        # 3. 密码十六进制转BigInt
        m = int(pwd_hex, 16)
        
        # 4. RSA加密: c = m^e mod n
        c = pow(m, e, n)
        
        # 5. 结果补零到128位
        encrypted_hex = format(c, 'x').zfill(128)
        
        return encrypted_hex