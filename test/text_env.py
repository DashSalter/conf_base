import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conf_base import ConfigMeta, Section, crypto
from conf_base.Error import WriteError, ConfigValueError

"""
环境变量覆盖功能测试
优先级：环境变量 > 配置文件 > 默认值
"""

# 清理测试文件和环境变量
_tmp = '_test_env.json'
for k in ['MYAPP_PORT', 'MYAPP_BGM', 'MYAPP_DEBUG', 'MYAPP_HOSTS', 'MYAPP_DB', 'MYAPP_BAD']:
    os.environ.pop(k, None)
if os.path.exists(_tmp):
    os.remove(_tmp)


# ================================================================
# 场景 1：基础覆盖（env > file > default）
# ================================================================
print('=' * 50)
print('场景 1：基础覆盖')
print('=' * 50)

# 先写一个配置文件
with open(_tmp, 'w', encoding='utf-8') as f:
    json.dump({'Setting': {'port': 3306, 'bgm': 0.5, 'debug': False}}, f)

os.environ['MYAPP_PORT'] = '8080'
os.environ['MYAPP_DEBUG'] = 'true'

class TestConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson(_tmp)

    setting = Section('Setting')
    port = setting.add('port', default=3306, env_key='MYAPP_PORT')       # env 覆盖
    bgm = setting.add('bgm', default=1.0, env_key='MYAPP_BGM')           # env 不存在 → 文件值
    debug = setting.add('debug', default=False, env_key='MYAPP_DEBUG')   # env 覆盖 bool
    hosts = setting.add('hosts', default=['127.0.0.1'], env_key='MYAPP_HOSTS')  # list

assert TestConfig.port.value == 8080, f"port 应为 8080(env)，实际 {TestConfig.port.value}"
assert TestConfig.bgm.value == 0.5, f"bgm 应为 0.5(file)，实际 {TestConfig.bgm.value}"
assert TestConfig.debug.value == True
assert TestConfig.port.has_env_override == True
assert TestConfig.bgm.has_env_override == False
print(f'✅ 优先级链: port={TestConfig.port.value}(env), bgm={TestConfig.bgm.value}(file), debug={TestConfig.debug.value}(env)')
print(TestConfig.to_dict())
print(TestConfig.setting)
print(TestConfig.port)
# ================================================================
# 场景 2：环境变量禁止回写
# ================================================================
print('\n' + '=' * 50)
print('场景 2：环境变量禁止回写')
print('=' * 50)

try:
    TestConfig.port.value = 9999
    print('❌ 应该报错')
except WriteError as e:
    print(f'✅ 正确拦截: {e}')


# ================================================================
# 场景 3：List/Dict 类型解析
# ================================================================
print('\n' + '=' * 50)
print('场景 3：List/Dict 类型解析')
print('=' * 50)

os.environ['MYAPP_HOSTS'] = '["10.0.0.1", "10.0.0.2"]'
os.environ['MYAPP_DB'] = '{"host": "db.local", "port": 5432}'

# 重新建配置类让 ConfigMeta 注入
_tmp2 = '_test_env2.json'
if os.path.exists(_tmp2):
    os.remove(_tmp2)

class TestConfig2(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson(_tmp2)
    setting = Section('Setting')
    hosts = setting.add('hosts', default=['127.0.0.1'], env_key='MYAPP_HOSTS')
    db = setting.add('db', default={'host': 'localhost', 'port': 3306}, env_key='MYAPP_DB')
    name = setting.add('name', default='myapp', env_key='MYAPP_NAME')

assert TestConfig2.hosts.value == ['10.0.0.1', '10.0.0.2']
assert TestConfig2.db.value == {'host': 'db.local', 'port': 5432}
print(f'✅ list/dict 解析: hosts={TestConfig2.hosts.value}, db={TestConfig2.db.value}')


# ================================================================
# 场景 4：环境变量类型错误 → 清晰报错
# ================================================================
print('\n' + '=' * 50)
print('场景 4：环境变量类型错误 → 清晰报错')
print('=' * 50)

os.environ['MYAPP_BAD'] = 'not_a_number'
_tmp3 = '_test_env3.json'
if os.path.exists(_tmp3):
    os.remove(_tmp3)

class TestConfig3(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson(_tmp3)
    s = Section('S')
    port = s.add('port', default=3306, env_key='MYAPP_BAD')

try:
    _ = TestConfig3.port.value
    print('❌ 应该报错')
except ConfigValueError as e:
    print(f'✅ 正确报错: {e}')


# ================================================================
# 场景 5：移除环境变量后恢复文件值
# ================================================================
print('\n' + '=' * 50)
print('场景 5：移除环境变量后恢复文件值')
print('=' * 50)

os.environ.pop('MYAPP_PORT', None)
# 重新启动（环境变量已移除）
_tmp4 = '_test_env4.json'
with open(_tmp4, 'w', encoding='utf-8') as f:
    json.dump({'Setting': {'port': 3306}}, f)

class TestConfig4(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson(_tmp4)
    s = Section('Setting')
    port = s.add('port', default=3306, env_key='MYAPP_PORT')

assert TestConfig4.port.value == 3306
assert TestConfig4.port.has_env_override == False
print(f'✅ env 移除后恢复文件值: port={TestConfig4.port.value}')


# ================================================================
# 场景 6：current_options 也反映 env 覆盖
# ================================================================
print('\n' + '=' * 50)
print('场景 6：current_options 反映 env 覆盖')
print('=' * 50)

os.environ['MYAPP_PORT'] = '9090'
# 重新启动让 ConfigMeta 注入
class TestConfig5(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson(_tmp4)
    s = Section('Setting')
    port = s.add('port', default=3306, env_key='MYAPP_PORT')
    bgm = s.add('bgm', default=1.0)

opts = TestConfig5.s.current_options
assert opts['port'] == 9090
assert opts['bgm'] == 1.0
print(f'✅ current_options: {opts}')

# 清理临时文件
for f in [_tmp, _tmp2, _tmp3, _tmp4]:
    if os.path.exists(f):
        os.remove(f)
for k in ['MYAPP_PORT', 'MYAPP_BGM', 'MYAPP_DEBUG', 'MYAPP_HOSTS', 'MYAPP_DB', 'MYAPP_BAD', 'MYAPP_NAME']:
    os.environ.pop(k, None)

print('\n🎉 全部 6 个场景通过 ✅')
