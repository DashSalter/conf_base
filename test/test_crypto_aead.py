"""AEAD 加密（AES-GCM / ChaCha20-Poly1305）与 HMAC 签名完整性测试。"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from conf_base import (
    AesGcmCipher,
    ChaCha20Poly1305Cipher,
    ConfigBase,
    HmacCipher,
    Section,
)
from conf_base.error import DecryptError

cryptography = pytest.importorskip('cryptography')

KEY = 'correct-horse-battery-staple'
PLAIN = '{"Server": {"port": 8080, "hosts": ["a", "b"]}}'


@pytest.fixture
def aead_key(monkeypatch):
    """通过环境变量注入密钥，验证 key_env 读取链路。"""
    monkeypatch.setenv('CONF_BASE_KEY', KEY)
    return KEY


class TestAesGcm:
    """AES-256-GCM：往返、随机 nonce、错误密钥、篡改检测"""

    def test_roundtrip(self, tmp_dir):
        enc = AesGcmCipher(key=KEY)
        assert enc.decrypt(enc.encrypt(PLAIN)) == PLAIN

    def test_nonce_is_random(self, tmp_dir):
        enc = AesGcmCipher(key=KEY)
        first = json.loads(enc.encrypt(PLAIN))
        second = json.loads(enc.encrypt(PLAIN))
        assert first['nonce'] != second['nonce']
        assert first['data'] != second['data']

    def test_env_key(self, tmp_dir, aead_key):
        enc = AesGcmCipher()
        assert enc.decrypt(enc.encrypt(PLAIN)) == PLAIN

    def test_missing_key(self, tmp_dir, monkeypatch):
        monkeypatch.delenv('CONF_BASE_KEY', raising=False)
        with pytest.raises(ValueError):
            AesGcmCipher()

    def test_short_key_rejected(self, tmp_dir):
        with pytest.raises(ValueError):
            AesGcmCipher(key='short')

    def test_wrong_key_rejected(self, tmp_dir):
        cipher_text = AesGcmCipher(key=KEY).encrypt(PLAIN)
        with pytest.raises(DecryptError):
            AesGcmCipher(key='another-key-of-enough-length').decrypt(cipher_text)

    def test_tampered_payload_rejected(self, tmp_dir):
        enc = AesGcmCipher(key=KEY)
        envelope = json.loads(enc.encrypt(PLAIN))
        payload = bytearray(envelope['data'].encode('ascii'))
        payload[0] = ord('A') if payload[0] != ord('A') else ord('B')
        envelope['data'] = payload.decode('ascii')
        with pytest.raises(DecryptError):
            enc.decrypt(json.dumps(envelope))

    def test_tampered_key_id_rejected(self, tmp_dir):
        enc = AesGcmCipher(key=KEY)
        envelope = json.loads(enc.encrypt(PLAIN))
        envelope['kid'] = 'v2'
        with pytest.raises(DecryptError):
            enc.decrypt(json.dumps(envelope))

    def test_garbage_text_rejected(self, tmp_dir):
        enc = AesGcmCipher(key=KEY)
        with pytest.raises(DecryptError):
            enc.decrypt('not-a-valid-envelope')

    def test_config_roundtrip(self, tmp_dir):
        path = os.path.join(tmp_dir, 'app.enc')

        class C(ConfigBase):
            _path = path
            _cipher = AesGcmCipher(key=KEY)
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')

        C.port.value = 9090
        C.hosts.append('b')

        class C2(ConfigBase):
            _path = path
            _cipher = AesGcmCipher(key=KEY)
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')

        assert C2.port.value == 9090
        assert C2.hosts.value == ['a', 'b']


class TestChaCha20Poly1305:
    """ChaCha20-Poly1305：往返与篡改检测"""

    def test_roundtrip(self, tmp_dir):
        enc = ChaCha20Poly1305Cipher(key=KEY)
        assert enc.decrypt(enc.encrypt(PLAIN)) == PLAIN

    def test_tampered_payload_rejected(self, tmp_dir):
        enc = ChaCha20Poly1305Cipher(key=KEY)
        envelope = json.loads(enc.encrypt(PLAIN))
        envelope['data'] = envelope['data'][:-2] + 'AA'
        with pytest.raises(DecryptError):
            enc.decrypt(json.dumps(envelope))


class TestHmacCipher:
    """HMAC-SHA256 签名：明文可读 + 防文件级篡改"""

    def test_roundtrip_plaintext(self, tmp_dir):
        enc = HmacCipher(key=KEY)
        body = enc.encrypt(PLAIN)
        assert 'port' in body  # 内容仍是明文
        assert enc.decrypt(body) == PLAIN

    def test_tampered_file_rejected(self, tmp_dir):
        enc = HmacCipher(key=KEY)
        body = enc.encrypt(PLAIN)
        tampered = body.replace('8080', '9090')
        with pytest.raises(DecryptError):
            enc.decrypt(tampered)

    def test_missing_signature_rejected(self, tmp_dir):
        enc = HmacCipher(key=KEY)
        with pytest.raises(DecryptError):
            enc.decrypt(PLAIN)

    def test_wrong_sign_key_rejected(self, tmp_dir):
        body = HmacCipher(key=KEY).encrypt(PLAIN)
        other = HmacCipher(key='another-key-of-enough-length')
        with pytest.raises(DecryptError):
            other.decrypt(body)

    def test_read_only_item_file_tamper_detected(self, tmp_dir):
        """read_only 只防运行时写入，签名才能防手工改文件。"""
        path = os.path.join(tmp_dir, 'locked.json')

        class C(ConfigBase):
            _path = path
            _cipher = HmacCipher(key=KEY)
            s = Section('Setting')
            api_key = s.field(default='real', option='api_key', read_only=True)

        assert C.api_key.value == 'real'  # 触发默认值落盘

        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content.replace('"real"', '"hacked"'))

        with pytest.raises(DecryptError):
            class C2(ConfigBase):
                _path = path
                _cipher = HmacCipher(key=KEY)
                s = Section('Setting')
                api_key = s.field(default='real', option='api_key', read_only=True)

        assert C.api_key.value == 'real'
