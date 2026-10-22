import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import ConfigBase, Section, crypto
from conf_base.Error import WriteError, ConfigValueError


class TestEnvOverride:
    """环境变量优先级链 + 类型自动解析 + 写入保护"""

    def test_priority_chain(self, tmp_dir, clean_env):
        os.environ['MYAPP_PORT'] = '9999'
        file_path = os.path.join(tmp_dir, 'env.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'S': {'port': 3306, 'bgm': 0.5}}, f)

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port', env_key='MYAPP_PORT')
            bgm = s.field(default=1.0, option='bgm', env_key='MYAPP_BGM')

        assert C.port.value == 9999
        assert C.bgm.value == 0.5
        assert C.port.has_env_override is True
        assert C.bgm.has_env_override is False

    def test_type_auto_parse(self, tmp_dir, clean_env):
        os.environ['APP_DEBUG'] = 'true'
        os.environ['APP_COUNT'] = '42'
        os.environ['APP_RATE'] = '0.75'
        os.environ['APP_HOSTS'] = '["h1", "h2"]'

        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'types.json'))
            s = Section('S')
            debug = s.field(default=False, option='debug', env_key='APP_DEBUG')
            count = s.field(default=0, option='count', env_key='APP_COUNT')
            rate = s.field(default=1.0, option='rate', env_key='APP_RATE')
            hosts = s.field(default=[], option='hosts', env_key='APP_HOSTS')

        assert C.debug.value is True
        assert C.count.value == 42
        assert C.rate.value == 0.75
        assert C.hosts.value == ['h1', 'h2']

    def test_write_protected_when_env_override(self, tmp_dir, clean_env):
        os.environ['APP_PORT'] = '8080'

        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'wp.json'))
            s = Section('S')
            port = s.field(default=0, option='port', env_key='APP_PORT')

        with pytest.raises(WriteError):
            C.port.value = 9999

    def test_bad_env_value(self, tmp_dir, clean_env):
        os.environ['APP_PORT'] = 'not_a_number'

        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'bad.json'))
            s = Section('S')
            port = s.field(default=0, option='port', env_key='APP_PORT')

        with pytest.raises(ConfigValueError):
            _ = C.port.value

    def test_env_removed_restores_file(self, tmp_dir, clean_env):
        file_path = os.path.join(tmp_dir, 'restore.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'S': {'port': 3306}}, f)

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port', env_key='APP_PORT')

        assert C.port.value == 3306

    def test_section_access_applies_env(self, tmp_dir, clean_env, monkeypatch):
        """Section 的属性/索引访问与 .value 保持一致，同样应用环境变量覆盖"""
        monkeypatch.setenv('MYAPP_PORT', '9999')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'sec_env.json'))
            s = Section('S')
            port = s.field(default=8080, option='port', env_key='MYAPP_PORT')

        assert C.s.port == 9999
        assert C.s['port'] == 9999
        assert C.s.current_options['port'] == 9999
