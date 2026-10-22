"""AEAD 加密（AES-GCM / ChaCha20-Poly1305）与 HMAC 签名完整性测试。"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from conf_base import ConfigBase, Section, crypto
from conf_base.Error import DecryptError, ParseError

cryptography = pytest.importorskip('cryptography')

KEY = 'correct-horse-battery-staple'


@pytest.fixture
def aead_key(monkeypatch):
    """通过环境变量注入密钥，验证 env_key 读取链路。"""
    monkeypatch.setenv('CONF_BASE_KEY', KEY)
    return KEY


class TestAesGcm:
    """AES-256-GCM：往返、随机 nonce、错误密钥、篡改检测"""

    def test_roundtrip(self, tmp_dir):
        enc = crypto.AesGcmCrypto(key=KEY, file_path=os.path.join(tmp_dir, 'a.enc'))
        data = {'Server': {'port': 8080, 'hosts': ['a', 'b']}}
        assert enc.decrypt(enc.encrypt(data)) == data

    def test_nonce_is_random(self, tmp_dir):
        enc = crypto.AesGcmCrypto(key=KEY, file_path=os.path.join(tmp_dir, 'a.enc'))
        first = json.loads(enc.encrypt({'S': {'v': 1}}))
        second = json.loads(enc.encrypt({'S': {'v': 1}}))
        assert first['nonce'] != second['nonce']
        assert first['data'] != second['data']

    def test_env_key(self, tmp_dir, aead_key):
        enc = crypto.AesGcmCrypto(file_path=os.path.join(tmp_dir, 'a.enc'))
        assert enc.decrypt(enc.encrypt({'S': {'v': 1}})) == {'S': {'v': 1}}

    def test_missing_key(self, tmp_dir, monkeypatch):
        monkeypatch.delenv('CONF_BASE_KEY', raising=False)
        with pytest.raises(ValueError):
            crypto.AesGcmCrypto(file_path=os.path.join(tmp_dir, 'a.enc'))

    def test_short_key_rejected(self, tmp_dir):
        with pytest.raises(ValueError):
            crypto.AesGcmCrypto(key='short', file_path=os.path.join(tmp_dir, 'a.enc'))

    def test_wrong_key_rejected(self, tmp_dir):
        path = os.path.join(tmp_dir, 'a.enc')
        cipher_text = crypto.AesGcmCrypto(key=KEY, file_path=path).encrypt({'S': {'v': 1}})
        with pytest.raises(DecryptError):
            crypto.AesGcmCrypto(key='another-key-of-enough-length', file_path=path).decrypt(cipher_text)

    def test_tampered_payload_rejected(self, tmp_dir):
        path = os.path.join(tmp_dir, 'a.enc')
        enc = crypto.AesGcmCrypto(key=KEY, file_path=path)
        envelope = json.loads(enc.encrypt({'S': {'v': 1}}))
        payload = bytearray(envelope['data'].encode('ascii'))
        payload[0] = ord('A') if payload[0] != ord('A') else ord('B')
        envelope['data'] = payload.decode('ascii')
        with pytest.raises(DecryptError):
            enc.decrypt(json.dumps(envelope))

    def test_tampered_key_id_rejected(self, tmp_dir):
        path = os.path.join(tmp_dir, 'a.enc')
        enc = crypto.AesGcmCrypto(key=KEY, file_path=path)
        envelope = json.loads(enc.encrypt({'S': {'v': 1}}))
        envelope['kid'] = 'v2'
        with pytest.raises(DecryptError):
            enc.decrypt(json.dumps(envelope))

    def test_garbage_text_rejected(self, tmp_dir):
        enc = crypto.AesGcmCrypto(key=KEY, file_path=os.path.join(tmp_dir, 'a.enc'))
        with pytest.raises(DecryptError):
            enc.decrypt('not-a-valid-envelope')

    def test_config_roundtrip(self, tmp_dir):
        path = os.path.join(tmp_dir, 'app.enc')

        class C(ConfigBase):
            _crypto = crypto.AesGcmCrypto(key=KEY, file_path=path)
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')

        C.port.value = 9090
        C.hosts.append('b')

        class C2(ConfigBase):
            _crypto = crypto.AesGcmCrypto(key=KEY, file_path=path)
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')

        assert C2.port.value == 9090
        assert C2.hosts.value == ['a', 'b']


class TestChaCha20Poly1305:
    """ChaCha20-Poly1305：往返与篡改检测"""

    def test_roundtrip(self, tmp_dir):
        enc = crypto.ChaCha20Poly1305Crypto(key=KEY, file_path=os.path.join(tmp_dir, 'c.enc'))
        data = {'Level': {'done': [1, 2, 3]}}
        assert enc.decrypt(enc.encrypt(data)) == data

    def test_tampered_payload_rejected(self, tmp_dir):
        path = os.path.join(tmp_dir, 'c.enc')
        enc = crypto.ChaCha20Poly1305Crypto(key=KEY, file_path=path)
        envelope = json.loads(enc.encrypt({'S': {'v': 1}}))
        envelope['data'] = envelope['data'][:-2] + 'AA'
        with pytest.raises(DecryptError):
            enc.decrypt(json.dumps(envelope))


class TestSignedCrypto:
    """HMAC-SHA256 签名：明文可读 + 防文件级篡改"""

    def test_roundtrip_plaintext(self, tmp_dir):
        path = os.path.join(tmp_dir, 'plain.json')
        enc = crypto.SignedCrypto(crypto.PlainJson(path), key=KEY)
        body = enc.encrypt({'S': {'v': 1}})
        assert 'v' in body  # 内容仍是明文 JSON
        assert os.path.exists(enc.signature_path)
        assert enc.decrypt(body) == {'S': {'v': 1}}

    def test_tampered_file_rejected(self, tmp_dir):
        path = os.path.join(tmp_dir, 'plain.json')
        enc = crypto.SignedCrypto(crypto.PlainJson(path), key=KEY)
        body = enc.encrypt({'S': {'v': 1}})
        tampered = body.replace('1', '2')
        with pytest.raises(DecryptError):
            enc.decrypt(tampered)

    def test_missing_signature_rejected(self, tmp_dir):
        enc = crypto.SignedCrypto(crypto.PlainJson(os.path.join(tmp_dir, 'plain.json')), key=KEY)
        with pytest.raises(DecryptError):
            enc.decrypt('{"S": {"v": 1}}')

    def test_wrong_sign_key_rejected(self, tmp_dir):
        path = os.path.join(tmp_dir, 'plain.json')
        body = crypto.SignedCrypto(crypto.PlainJson(path), key=KEY).encrypt({'S': {'v': 1}})
        other = crypto.SignedCrypto(crypto.PlainJson(path), key='another-key-of-enough-length')
        with pytest.raises(DecryptError):
            other.decrypt(body)

    def test_read_only_item_file_tamper_detected(self, tmp_dir):
        """read_only 只防运行时写入，签名才能防手工改文件。"""
        path = os.path.join(tmp_dir, 'locked.json')

        class C(ConfigBase):
            _crypto = crypto.SignedCrypto(crypto.PlainJson(path), key=KEY)
            s = Section('Setting')
            api_key = s.field(default='real', option='api_key', read_only=True)

        assert C.api_key.value == 'real'  # 触发默认值落盘

        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content.replace('"real"', '"hacked"'))

        with pytest.raises(ParseError):
            class C2(ConfigBase):
                _crypto = crypto.SignedCrypto(crypto.PlainJson(path), key=KEY)
                s = Section('Setting')
                api_key = s.field(default='real', option='api_key', read_only=True)

        assert C.api_key.value == 'real'
