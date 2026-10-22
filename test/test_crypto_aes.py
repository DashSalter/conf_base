import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import AesCipher, ConfigBase, Section
from conf_base.error import DecryptError

cryptography = pytest.importorskip('cryptography')


class TestAesCipher:
    """AesCipher 加解密"""

    def test_basic_encrypt_decrypt(self, tmp_dir):
        aes = AesCipher(key='test-key')
        text = '{"A": {"x": 1}, "B": [1, 2, 3]}'
        assert aes.decrypt(aes.encrypt(text)) == text

    def test_config_integration(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'aes_config.enc')

        class C(ConfigBase):
            _path = file_path
            _cipher = AesCipher(key='master-key')
            s = Section('S')
            port = s.field(default=8080, option='port')

        C.port.value = 9090
        with open(file_path, encoding='utf-8') as f:
            raw = f.read()
        assert 'port' not in raw

        class C2(ConfigBase):
            _path = file_path
            _cipher = AesCipher(key='master-key')
            s = Section('S')
            port = s.field(default=8080, option='port')

        assert C2.port.value == 9090

    def test_bad_key_fails(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'aes_bad.enc')

        class C(ConfigBase):
            _path = file_path
            _cipher = AesCipher(key='correct-key')
            s = Section('S')
            port = s.field(default=8080, option='port')

        file_path2 = os.path.join(tmp_dir, 'aes_wrong.enc')
        shutil.copy(file_path, file_path2)

        with pytest.raises(DecryptError):
            class C2(ConfigBase):
                _path = file_path2
                _cipher = AesCipher(key='wrong-key')
                s = Section('S')
                port = s.field(default=8080, option='port')

    def test_tampered_ciphertext_fails(self, tmp_dir):
        aes = AesCipher(key='k')
        enc = aes.encrypt('{"x": 1}')
        tampered = enc[:-5] + 'xxxxx'
        with pytest.raises(DecryptError):
            aes.decrypt(tampered)
