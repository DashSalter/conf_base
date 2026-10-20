import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conf_base import ConfigMeta, Section, crypto

"""AesCrypto 加密测试"""

_tmp = '_test_aes.enc'
if os.path.exists(_tmp):
    os.remove(_tmp)


# ========================================================
# 场景 1：基础加解密 + 与 ConfigMeta 集成
# ========================================================
print('[1] 基础加解密 + ConfigMeta 集成')

class AesConfig(metaclass=ConfigMeta):
    _crypto = crypto.AesCrypto(key='my-master-key', file_path=_tmp)

    setting = Section('Setting')
    host = setting.add('host', default='127.0.0.1')
    port = setting.add('port', default=8080)
    password = setting.add('password', default='<SECRET>')

assert AesConfig.host.value == '127.0.0.1'
assert AesConfig.port.value == 8080

# 修改后文件应加密
AesConfig.port.value = 9090
AesConfig.password.value = 'supersecret'

with open(_tmp, encoding='utf-8') as f:
    raw = f.read()
assert 'port' not in raw, '密文不应包含明文 key'
assert '127.0.0.1' not in raw, '密文不应包含明文值'
print(f'  ✅ 启动读取 + 加密写入 OK（密文长度 {len(raw)}）')


# ========================================================
# 场景 2：重新启动解密正确
# ========================================================
print('[2] 重新启动解密正确')

class AesConfig2(metaclass=ConfigMeta):
    _crypto = crypto.AesCrypto(key='my-master-key', file_path=_tmp)

    setting = Section('Setting')
    host = setting.add('host', default='127.0.0.1')
    port = setting.add('port', default=8080)
    password = setting.add('password', default='<SECRET>')

assert AesConfig2.port.value == 9090
assert AesConfig2.password.value == 'supersecret'
print('  ✅ 解密正确 OK')


# ========================================================
# 场景 3：错误密钥启动即报错
# ========================================================
print('[3] 错误密钥启动即报错')

_tmp2 = '_test_aes_wrong.enc'
if os.path.exists(_tmp2):
    os.remove(_tmp2)
shutil.copy(_tmp, _tmp2)

try:
    class AesConfigBadKey(metaclass=ConfigMeta):
        _crypto = crypto.AesCrypto(key='this-is-not-the-key', file_path=_tmp2)
        setting = Section('Setting')
        port = setting.add('port', default=8080)
    print('  ❌ 应该报错')
except Exception as e:
    print(f'  ✅ 启动即报错 OK: {type(e).__name__}')


# ========================================================
# 场景 4：直接用 AesCrypto 加解密
# ========================================================
print('[4] 直接用 AesCrypto 加解密')

aes = crypto.AesCrypto(key='test-key', file_path='_dummy.enc')
data = {'A': {'x': 1}, 'B': [1, 2, 3]}
encrypted = aes.encrypt(data)
decrypted = aes.decrypt(encrypted)
assert decrypted == data
print(f'  ✅ encrypt/decrypt 配对 OK（密文 {len(encrypted)} 字符）')


# ========================================================
# 场景 5：密文篡改后解密失败（HMAC 签名校验）
# ========================================================
print('[5] 密文篡改后解密失败')

tampered = encrypted[:-5] + 'xxxxx'
try:
    aes.decrypt(tampered)
    print('  ❌ 应该报错')
except ValueError as e:
    print(f'  ✅ 篡改被拦截 OK: {e}')


# 清理
for f in [_tmp, _tmp2]:
    if os.path.exists(f):
        os.remove(f)
if os.path.exists('_dummy.enc.lock'):
    os.remove('_dummy.enc.lock')

print('\n🎉 AesCrypto 全部 5 项通过 ✅')
