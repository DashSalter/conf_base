import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import ConfigBase, JsonFormat, NoCipher, Section, TomlFormat, YamlFormat
from conf_base.error import ConfigValueError, ParseError


class TestYamlFormat:
    """YAML 存储：往返读写、元组归一化、非法数据明确报错"""

    def test_roundtrip(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'app.yaml')

        class C(ConfigBase):
            _path = file_path
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')
            db = s.field(default={'host': 'localhost', 'port': 5432}, option='db')

        C.port.value = 9090
        C.hosts.append('b')
        C.db['host'] = 'db.local'

        class C2(ConfigBase):
            _path = file_path
            _format = YamlFormat()
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')
            db = s.field(default={'host': 'localhost', 'port': 5432}, option='db')

        assert C2.port.value == 9090
        assert C2.hosts.value == ['a', 'b']
        assert C2.db.value == {'host': 'db.local', 'port': 5432}

    def test_tuple_value_becomes_list(self, tmp_dir):
        yaml = YamlFormat()
        data = yaml.deserialize(yaml.serialize({'S': {'pos': (1, 2)}}))
        assert data['S']['pos'] == [1, 2]

    def test_none_is_supported(self, tmp_dir):
        yaml = YamlFormat()
        data = yaml.deserialize(yaml.serialize({'S': {'x': None}}))
        assert data['S']['x'] is None

    def test_tuple_key_rejected(self, tmp_dir):
        yaml = YamlFormat()
        with pytest.raises(ConfigValueError, match='键必须是字符串'):
            yaml.serialize({'S': {(1, 2): 'x'}})

    def test_unsupported_type_rejected(self, tmp_dir):
        yaml = YamlFormat()
        with pytest.raises(ConfigValueError, match='不支持 set 类型'):
            yaml.serialize({'S': {'x': {1, 2}}})

    def test_non_dict_root_raises_parse_error(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'list.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('- 1\n- 2\n')

        with pytest.raises(ParseError):
            class C(ConfigBase):
                _path = file_path
                s = Section('S')
                port = s.field(default=8080, option='port')


class TestTomlFormat:
    """TOML 存储：往返读写、元组归一化、None 与非法键明确报错"""

    def test_roundtrip(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'app.toml')

        class C(ConfigBase):
            _path = file_path
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')
            db = s.field(default={'host': 'localhost', 'port': 5432}, option='db')

        C.port.value = 9090
        C.hosts.append('b')
        C.db['host'] = 'db.local'

        class C2(ConfigBase):
            _path = file_path
            _format = TomlFormat()
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')
            db = s.field(default={'host': 'localhost', 'port': 5432}, option='db')

        assert C2.port.value == 9090
        assert C2.hosts.value == ['a', 'b']
        assert C2.db.value == {'host': 'db.local', 'port': 5432}

    def test_tuple_value_becomes_list(self, tmp_dir):
        toml = TomlFormat()
        data = toml.deserialize(toml.serialize({'S': {'pos': (1, 2)}}))
        assert data['S']['pos'] == [1, 2]

    def test_none_rejected(self, tmp_dir):
        toml = TomlFormat()
        with pytest.raises(ConfigValueError, match='不支持 null'):
            toml.serialize({'S': {'x': None}})

    def test_tuple_key_rejected(self, tmp_dir):
        toml = TomlFormat()
        with pytest.raises(ConfigValueError, match='键必须是字符串'):
            toml.serialize({'S': {(1, 2): 'x'}})

    def test_invalid_file_raises_parse_error(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'broken.toml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('x = [\n')

        with pytest.raises(ParseError):
            class C(ConfigBase):
                _path = file_path
                s = Section('S')
                port = s.field(default=8080, option='port')


class TestJsonFormat:
    """JSON 序列化错误统一为 ConfigValueError"""

    def test_unsupported_type_raises_config_value_error(self, tmp_dir):
        fmt = JsonFormat()
        with pytest.raises(ConfigValueError, match='不支持 set 类型'):
            fmt.serialize({'S': {'x': {1, 2}}})

    def test_non_str_key_raises(self):
        """JSON 不再把 {1: 'a'} 静默转成 {'1': 'a'}"""
        fmt = JsonFormat()
        with pytest.raises(ConfigValueError, match='字典键必须是字符串'):
            fmt.serialize({'S': {1: 'a'}})


class TestStorageTarget:
    """_path / _format / _cipher 的解析规则"""

    def test_generated_path(self, tmp_dir, monkeypatch):
        monkeypatch.chdir(tmp_dir)

        class AppConfig(ConfigBase):
            _format = YamlFormat()
            s = Section('S')
            port = s.field(default=8080, option='port')

        assert os.path.exists(os.path.join(tmp_dir, 'appconfig.yaml'))

    def test_explicit_path_used_as_is(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'app.conf')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080, option='port')

        # 后缀无法识别时按 JSON 写入，路径本身不做任何改写
        assert os.path.exists(file_path)
        with open(file_path, encoding='utf-8') as f:
            assert '"_schema_version"' in f.read()

    def test_format_suffix_conflict(self, tmp_dir):
        with pytest.raises(ValueError, match='后缀'):
            class C(ConfigBase):
                _path = os.path.join(tmp_dir, 'app.yaml')
                _format = JsonFormat()
                s = Section('S')
                port = s.field(default=8080, option='port')

    def test_invalid_format_type(self, tmp_dir):
        with pytest.raises(TypeError, match='_format'):
            class C(ConfigBase):
                _format = 'yaml'
                s = Section('S')
                port = s.field(default=8080, option='port')

    def test_cipher_suffix_format_inference(self, tmp_dir):
        """'app.yaml.enc' 应推断为 YAML，而不是静默退回 JSON"""
        class EncCipher(NoCipher):
            extension = '.enc'

        file_path = os.path.join(tmp_dir, 'app.yaml.enc')

        class C(ConfigBase):
            _path = file_path
            _cipher = EncCipher()
            s = Section('S')
            port = s.field(default=8080)

        with open(file_path, encoding='utf-8') as f:
            assert 'port: 8080' in f.read()
