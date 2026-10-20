import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import ConfigMeta, Section, crypto
from conf_base.Error import WriteError


class TestBasicConfig:
    """基础读写、批量、重置、to_dict"""

    def test_read_write(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'basic.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            host = s.add('host', default='127.0.0.1')
            port = s.add('port', default=8080)

        assert C.host.value == '127.0.0.1'
        assert C.port.value == 8080

        C.port.value = 9090
        assert C.port.value == 9090

    def test_batch_update(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'batch.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.add('port', default=8080)
            host = s.add('host', default='127.0.0.1')

        C.s.update(port=9090, host='0.0.0.0')
        assert C.port.value == 9090
        assert C.host.value == '0.0.0.0'

    def test_section_reset(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'reset.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.add('port', default=8080)

        C.port.value = 9090
        C.s.reset()
        assert C.port.value == 8080

    def test_to_dict(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'todict.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.add('port', default=8080)

        d = C.to_dict()
        assert 'S' in d
        assert d['S']['port'] == 8080
        assert '_schema_version' not in d

    def test_section_item_access(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'access.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.add('port', default=8080)

        C.port.value = 9090
        assert C.s['port'] == 9090
        assert 'port' in C.s
