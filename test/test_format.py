import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import ConfigBase, Section, crypto
from conf_base.Error import ConfigValueError, ParseError


class TestYamlFormat:
    """YAML 存储：往返读写、元组归一化、非法数据明确报错"""

    def test_roundtrip(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'app.yaml')

        class C(ConfigBase):
            _crypto = crypto.PlainYaml(file_path)
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')
            db = s.field(default={'host': 'localhost', 'port': 5432}, option='db')

        C.port.value = 9090
        C.hosts.append('b')
        C.db['host'] = 'db.local'

        class C2(ConfigBase):
            _crypto = crypto.PlainYaml(file_path)
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')
            db = s.field(default={'host': 'localhost', 'port': 5432}, option='db')

        assert C2.port.value == 9090
        assert C2.hosts.value == ['a', 'b']
        assert C2.db.value == {'host': 'db.local', 'port': 5432}

    def test_tuple_value_becomes_list(self, tmp_dir):
        yaml = crypto.PlainYaml(os.path.join(tmp_dir, 'tuple.yaml'))
        data = yaml.decrypt(yaml.encrypt({'S': {'pos': (1, 2)}}))
        assert data['S']['pos'] == [1, 2]

    def test_none_is_supported(self, tmp_dir):
        yaml = crypto.PlainYaml(os.path.join(tmp_dir, 'none.yaml'))
        data = yaml.decrypt(yaml.encrypt({'S': {'x': None}}))
        assert data['S']['x'] is None

    def test_tuple_key_rejected(self, tmp_dir):
        yaml = crypto.PlainYaml(os.path.join(tmp_dir, 'badkey.yaml'))
        with pytest.raises(ConfigValueError, match='键必须是字符串'):
            yaml.encrypt({'S': {(1, 2): 'x'}})

    def test_unsupported_type_rejected(self, tmp_dir):
        yaml = crypto.PlainYaml(os.path.join(tmp_dir, 'badtype.yaml'))
        with pytest.raises(ConfigValueError, match='不支持 set 类型'):
            yaml.encrypt({'S': {'x': {1, 2}}})

    def test_non_dict_root_raises_parse_error(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'list.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('- 1\n- 2\n')

        with pytest.raises(ParseError):
            class C(ConfigBase):
                _crypto = crypto.PlainYaml(file_path)
                s = Section('S')
                port = s.field(default=8080, option='port')


class TestTomlFormat:
    """TOML 存储：往返读写、元组归一化、None 与非法键明确报错"""

    def test_roundtrip(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'app.toml')

        class C(ConfigBase):
            _crypto = crypto.PlainToml(file_path)
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')
            db = s.field(default={'host': 'localhost', 'port': 5432}, option='db')

        C.port.value = 9090
        C.hosts.append('b')
        C.db['host'] = 'db.local'

        class C2(ConfigBase):
            _crypto = crypto.PlainToml(file_path)
            s = Section('Server')
            port = s.field(default=8080, option='port')
            hosts = s.field(default=['a'], option='hosts')
            db = s.field(default={'host': 'localhost', 'port': 5432}, option='db')

        assert C2.port.value == 9090
        assert C2.hosts.value == ['a', 'b']
        assert C2.db.value == {'host': 'db.local', 'port': 5432}

    def test_tuple_value_becomes_list(self, tmp_dir):
        toml = crypto.PlainToml(os.path.join(tmp_dir, 'tuple.toml'))
        data = toml.decrypt(toml.encrypt({'S': {'pos': (1, 2)}}))
        assert data['S']['pos'] == [1, 2]

    def test_none_rejected(self, tmp_dir):
        toml = crypto.PlainToml(os.path.join(tmp_dir, 'none.toml'))
        with pytest.raises(ConfigValueError, match='不支持 null'):
            toml.encrypt({'S': {'x': None}})

    def test_tuple_key_rejected(self, tmp_dir):
        toml = crypto.PlainToml(os.path.join(tmp_dir, 'badkey.toml'))
        with pytest.raises(ConfigValueError, match='键必须是字符串'):
            toml.encrypt({'S': {(1, 2): 'x'}})

    def test_invalid_file_raises_parse_error(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'broken.toml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('x = [\n')

        with pytest.raises(ParseError):
            class C(ConfigBase):
                _crypto = crypto.PlainToml(file_path)
                s = Section('S')
                port = s.field(default=8080, option='port')
