import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import ConfigBase, Section, crypto


class TestCryptoAes:
    """AesCrypto 加解密"""

    def test_basic_encrypt_decrypt(self, tmp_dir):
        aes = crypto.AesCrypto(key='test-key', file_path=os.path.join(tmp_dir, 'aes.enc'))
        data = {'A': {'x': 1}, 'B': [1, 2, 3]}
        enc = aes.encrypt(data)
        assert aes.decrypt(enc) == data

    def test_config_integration(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'aes_config.enc')

        class C(ConfigBase):
            _crypto = crypto.AesCrypto(key='master-key', file_path=file_path)
            s = Section('S')
            port = s.add('port', default=8080)

        C.port.value = 9090
        with open(file_path, encoding='utf-8') as f:
            raw = f.read()
        assert 'port' not in raw

        class C2(ConfigBase):
            _crypto = crypto.AesCrypto(key='master-key', file_path=file_path)
            s = Section('S')
            port = s.add('port', default=8080)

        assert C2.port.value == 9090

    def test_bad_key_fails(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'aes_bad.enc')

        class C(ConfigBase):
            _crypto = crypto.AesCrypto(key='correct-key', file_path=file_path)
            s = Section('S')
            port = s.add('port', default=8080)

        file_path2 = os.path.join(tmp_dir, 'aes_wrong.enc')
        shutil.copy(file_path, file_path2)

        with pytest.raises(Exception):
            class C2(ConfigBase):
                _crypto = crypto.AesCrypto(key='wrong-key', file_path=file_path2)
                s = Section('S')
                port = s.add('port', default=8080)

    def test_tampered_ciphertext_fails(self, tmp_dir):
        aes = crypto.AesCrypto(key='k', file_path=os.path.join(tmp_dir, 'tamper.enc'))
        enc = aes.encrypt({'x': 1})
        tampered = enc[:-5] + 'xxxxx'
        with pytest.raises(ValueError):
            aes.decrypt(tampered)
