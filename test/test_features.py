import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import ConfigMeta, Section, crypto
from conf_base.Error import WriteError


class TestFeatures:
    """validator / read_only / 多 section / on_change / 类型代理"""

    def test_validator(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'valid.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.add('port', default=8080, validator=lambda x: x > 0)

        with pytest.raises(Exception):
            C.port.value = -1

    def test_type_check(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'type.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.add('port', default=8080)

        with pytest.raises(Exception):
            C.port.value = 'not_int'

    def test_read_only(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'ro.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            name = s.add('name', default='locked', read_only=True)

        with pytest.raises(WriteError):
            C.name.value = 'new'

    def test_multi_section_switch(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'multi.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            lvl = Section('Level', 'Level2')
            done = lvl.add('done', default=[1, 2])

        C.lvl.set_use_section('Level2')
        C.done.value = [3, 4]
        assert C.done.value == [3, 4]

        C.lvl.set_use_section('Level')
        C.done.value = [5, 6]
        assert C.done.value == [5, 6]

        C.lvl.set_use_section('Level2')
        assert C.done.value == [3, 4]

    def test_list_proxy(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'listp.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            items = s.add('items', default=[1, 2])

        C.items.append(3)
        assert C.items.value == [1, 2, 3]
        C.items[0] = 99
        assert C.items.value == [99, 2, 3]

    def test_dict_proxy(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'dictp.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            db = s.add('db', default={'host': 'localhost'})

        C.db['port'] = 5432
        assert C.db.value == {'host': 'localhost', 'port': 5432}

    def test_on_change(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'onchange.json')
        received = []

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.add('port', default=8080)

        @C.port.on_change
        def cb(section, option, value):
            received.append((section, option, value))

        C.port.value = 9090
        assert len(received) == 1
        assert received[0] == ('S', 'port', 9090)

    def test_on_change_section_filter(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'filter.json')
        level_received = []
        level2_received = []

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            lvl = Section('Level', 'Level2')
            done = lvl.add('done', default=[1])

        @C.done.on_change(section='Level')
        def cb_level(section, option, value):
            level_received.append((section, value))

        @C.done.on_change(section='Level2')
        def cb_level2(section, option, value):
            level2_received.append((section, value))

        C.lvl.set_use_section('Level')
        C.done.value = [2]
        assert level_received == [('Level', [2])]
        assert level2_received == []

        C.lvl.set_use_section('Level2')
        C.done.value = [3]
        assert level2_received == [('Level2', [3])]

    def test_reset_clears_both_sections(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'reset_multi.json')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            lvl = Section('Level', 'Level2')
            done = lvl.add('done', default=[1, 2, 3])

        C.lvl.set_use_section('Level')
        C.done.value = [7, 8]
        C.lvl.set_use_section('Level2')
        C.done.value = [9]

        C.lvl.reset()
        assert C.lvl.current_options['Level']['done'] == [1, 2, 3]
        assert C.lvl.current_options['Level2']['done'] == [1, 2, 3]
