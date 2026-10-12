import base64
import json
from typing import Any, Dict
from abc import ABCMeta, abstractmethod

"""
管理配置数据的输入输出
可以使用提供的加密类，或者继承Crypto来实现自己的加密配置文件
"""


class Crypto(metaclass=ABCMeta):
    """加解密接口协议"""

    def __init__(self, file_path: str = 'settings.txt'):
        self.file_path = file_path

    @abstractmethod
    def encrypt(self, data: Dict[str, Any]) -> str:
        """
        将字典加密为字符串。
        :param data: 待加密的字典数据
        :return: 加密后的字符串
        """
        ...

    @abstractmethod
    def decrypt(self, text: str) -> Dict[str, Any]:
        """
        将字符串解密回字典。
        :param text: 加密的字符串
        :return: 解密后的字典数据
        """
        ...


class PlainCrypto(Crypto):
    """明文加解密器"""

    def __init__(self, file_path: str = 'settings.json'):
        super().__init__(file_path)

    def encrypt(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, indent=4, sort_keys=False)

    def decrypt(self, text: str) -> Dict[str, Any]:
        return json.loads(text)


class XorCrypto(Crypto):
    """
    异或 + Base64 加解密器。
    对称加密，密钥需 >= 16 字节。生产环境建议使用更强的加密方式。
    :param key: 加密密钥，bytes 类型，长度需 >= 16
    """

    def __init__(self, file_path='settings_xor.enc', key: bytes = b"SecretKey1234567"):
        super().__init__(file_path)
        if len(key) < 16:
            raise ValueError(f"加密密钥长度需 >= 16 字节，当前 {len(key)} 字节")
        self._key = key

    @staticmethod
    def xor_encrypt(data: bytes, key: bytes) -> bytes:
        """异或加密/解密（对称，加密和解密是同一函数）。"""
        key_len = len(key)
        return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))

    def encrypt(self, data: Dict[str, Any]) -> str:
        """将字典加密为 Base64 字符串。"""
        json_str = json.dumps(data, ensure_ascii=False)
        encrypted = self.xor_encrypt(json_str.encode('utf-8'), self._key)
        return base64.b64encode(encrypted).decode('ascii')

    def decrypt(self, text: str) -> Dict[str, Any]:
        """将 Base64 加密字符串解密回字典。"""
        decoded = base64.b64decode(text)
        decrypted = self.xor_encrypt(decoded, self._key).decode('utf-8')
        return json.loads(decrypted)
