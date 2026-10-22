import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conf_base import ConfigBase, Section, crypto


class TestBasicConfig:
    """基础读写、批量、重置、to_dict"""

    def test_read_write(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'basic.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            host = s.field(default='127.0.0.1', option='host')
            port = s.field(default=8080, option='port')

        assert C.host.value == '127.0.0.1'
        assert C.port.value == 8080

        C.port.value = 9090
        assert C.port.value == 9090

    def test_batch_update(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'batch.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port')
            host = s.field(default='127.0.0.1', option='host')

        C.s.update(port=9090, host='0.0.0.0')
        assert C.port.value == 9090
        assert C.host.value == '0.0.0.0'

    def test_section_reset(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'reset.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port')

        C.port.value = 9090
        C.s.reset()
        assert C.port.value == 8080

    def test_to_dict(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'todict.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port')

        d = C.to_dict()
        assert 'S' in d
        assert d['S']['port'] == 8080
        assert '_schema_version' not in d

    def test_section_item_access(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'access.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port')

        C.port.value = 9090
        assert C.s['port'] == 9090
        assert 'port' in C.s


class TestConfigBase:
    """ConfigBase 入口的读写、批量与回调"""

    def test_read_write_and_reload(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'base.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            host = s.field(default='127.0.0.1', option='host')
            port = s.field(default=8080, option='port')

        assert isinstance(C, type)
        C.port.value = 9090

        class C2(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            host = s.field(default='127.0.0.1', option='host')
            port = s.field(default=8080, option='port')

        assert C2.port.value == 9090
        assert C2.to_dict() == {'S': {'host': '127.0.0.1', 'port': 9090}}

    def test_batch_reset_and_callback(self, tmp_dir):
        events = []

        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'base_ops.json'))
            s = Section('S')
            port = s.field(default=8080, option='port')

        C.port.on_change(lambda section, option, value: events.append((section, option, value)))
        C.s.update(port=9090)
        assert C.port.value == 9090
        assert events[-1] == ('S', 'port', 9090)

        C.s.reset()
        assert C.port.value == 8080
        assert events[-1] == ('S', 'port', 8080)
