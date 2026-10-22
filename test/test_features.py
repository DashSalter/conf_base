import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import ConfigBase, Section, crypto
from conf_base.Error import ConfigValueError, WriteError


class TestFeatures:
    """validator / read_only / 独立 Section / on_change / 类型代理"""

    def test_validator(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'valid.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port', validator=lambda x: x > 0)

        with pytest.raises(Exception):
            C.port.value = -1

    def test_validator_exception_wrapped(self, tmp_dir):
        """validator 自身抛异常时包装为 ConfigValueError，并保留原始异常"""
        file_path = os.path.join(tmp_dir, 'validator_exc.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port',
                           validator=lambda v: 1 / 0 > v)

        with pytest.raises(ConfigValueError) as exc_info:
            C.port.value = 9090
        assert isinstance(exc_info.value.__cause__, ZeroDivisionError)

    def test_type_check(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'type.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port')

        with pytest.raises(Exception):
            C.port.value = 'not_int'

    def test_read_only(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'ro.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            name = s.field(default='locked', option='name', read_only=True)

        with pytest.raises(WriteError):
            C.name.value = 'new'

    def test_independent_sections(self, tmp_dir):
        """同一数据格式可定义多个独立 Section，互不影响"""
        file_path = os.path.join(tmp_dir, 'levels.json')
        default = {'name': '', 'age': 0}

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            level1 = Section('Level')
            data1 = level1.field(default=dict(default), option='done')
            level2 = Section('Level2')
            data2 = level2.field(default=dict(default), option='done')

        C.data1['name'] = 'Tom'
        C.data2['name'] = 'Tom2'
        assert C.data1.value == {'name': 'Tom', 'age': 0}
        assert C.data2.value == {'name': 'Tom2', 'age': 0}

        class C2(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            level1 = Section('Level')
            data1 = level1.field(default=dict(default), option='done')
            level2 = Section('Level2')
            data2 = level2.field(default=dict(default), option='done')

        assert C2.data1.value['name'] == 'Tom'
        assert C2.data2.value['name'] == 'Tom2'

    def test_section_requires_single_name(self):
        with pytest.raises(TypeError):
            Section('Level', 'Level2')

    def test_duplicate_option_rejected(self, tmp_dir):
        with pytest.raises(ValueError, match='已存在'):
            class C(ConfigBase):
                _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'dup.json'))
                s = Section('S')
                first = s.field(default=1, option='port')
                second = s.field(default=2, option='port')

    def test_option_defaults_to_attribute_name(self, tmp_dir):
        """省略 option 时使用左侧类属性名作为配置键名"""
        file_path = os.path.join(tmp_dir, 'auto_name.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080)
            host = s.field(default='127.0.0.1')

        assert C.s.get_options() == ['port', 'host']
        assert C.port.option == 'port'

        C.port.value = 9090
        import json
        with open(file_path, encoding='utf-8') as f:
            saved = json.load(f)
        assert saved['S'] == {'port': 9090, 'host': '127.0.0.1'}

    def test_list_proxy(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'listp.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            items = s.field(default=[1, 2], option='items')

        C.items.append(3)
        assert C.items.value == [1, 2, 3]
        C.items[0] = 99
        assert C.items.value == [99, 2, 3]

    def test_dict_proxy(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'dictp.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            db = s.field(default={'host': 'localhost'}, option='db')

        C.db['port'] = 5432
        assert C.db.value == {'host': 'localhost', 'port': 5432}

    def test_on_change(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'onchange.json')
        received = []

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port')

        @C.port.on_change
        def cb(section, option, value):
            received.append((section, option, value))

        C.port.value = 9090
        assert len(received) == 1
        assert received[0] == ('S', 'port', 9090)

    def test_reset_section(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'reset.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            lvl = Section('Level')
            done = lvl.field(default=[1, 2, 3], option='done')

        C.done.value = [7, 8]
        C.lvl.reset()
        assert C.lvl.current_options == {'done': [1, 2, 3]}

    def test_toggle(self, tmp_dir):
        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 't.json'))
            s = Section('S')
            flag = s.field(default=False, option='flag')

        assert C.flag.toggle() is True
        assert C.flag.toggle() is False

    def test_increment(self, tmp_dir):
        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'i.json'))
            s = Section('S')
            cnt = s.field(default=10, option='cnt')

        assert C.cnt.increment() == 11
        assert C.cnt.increment(5) == 16
        assert C.cnt.increment(-3) == 13

    def test_is_default(self, tmp_dir):
        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'd.json'))
            s = Section('S')
            port = s.field(default=8080, option='port')

        assert C.port.is_default is True
        C.port.value = 9090
        assert C.port.is_default is False

    def test_list_proxy_full(self, tmp_dir):
        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'lp.json'))
            s = Section('S')
            items = s.field(default=[1, 2, 3], option='items')

        C.items.extend([4, 5])
        assert C.items.value == [1, 2, 3, 4, 5]

        C.items.insert(0, 99)
        assert C.items.value == [99, 1, 2, 3, 4, 5]

        popped = C.items.pop()
        assert popped == 5
        assert C.items.value == [99, 1, 2, 3, 4]

        C.items.remove(99)
        assert C.items.value == [1, 2, 3, 4]

        C.items.sort(reverse=True)
        assert C.items.value == [4, 3, 2, 1]

        C.items.reverse()
        assert C.items.value == [1, 2, 3, 4]

        C.items.clear()
        assert C.items.value == []

    def test_dict_proxy_full(self, tmp_dir):
        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'dp.json'))
            s = Section('S')
            db = s.field(default={'a': 1, 'b': 2}, option='db')

        popped = C.db.pop('b')
        assert popped == 2
        assert C.db.value == {'a': 1}

        C.db.update({'c': 3, 'd': 4})
        assert C.db.value == {'a': 1, 'c': 3, 'd': 4}

        v = C.db.setdefault('e', 5)
        assert v == 5
        assert C.db.value['e'] == 5

        v2 = C.db.setdefault('a', 99)  # 已存在
        assert v2 == 1
        assert C.db.value['a'] == 1  # 不覆盖

        C.db.clear()
        assert C.db.value == {}

    def test_batch_nested(self, tmp_dir):
        """batch 嵌套只落盘一次"""
        file_path = os.path.join(tmp_dir, 'nest.json')

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.field(default=8080, option='port')
            name = s.field(default='x', option='name')

        jf = C.port._parent._config_file
        with jf.batch():
            with jf.batch():  # 嵌套
                C.port.value = 1
            C.name.value = 'y'
        # 退出最外层后落盘
        import json
        with open(file_path, encoding='utf-8') as f:
            saved = json.load(f)
        assert saved['S']['port'] == 1
        assert saved['S']['name'] == 'y'

    def test_on_change_multiple(self, tmp_dir):
        """同一配置项注册多个回调"""
        r1, r2 = [], []

        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'multi_cb.json'))
            s = Section('S')
            port = s.field(default=8080, option='port')

        @C.port.on_change
        def cb1(section, option, value):
            r1.append(value)

        @C.port.on_change
        def cb2(section, option, value):
            r2.append(value)

        C.port.value = 9090
        C.port.value = 7070
        assert r1 == [9090, 7070]
        assert r2 == [9090, 7070]

    def test_default_options(self, tmp_dir):
        class C(ConfigBase):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'def.json'))
            s = Section('S')
            port = s.field(default=8080, option='port')
            name = s.field(default='x', option='name')

        C.port.value = 9090
        assert C.s.default_options == {'port': 8080, 'name': 'x'}
        assert C.s.current_options == {'port': 9090, 'name': 'x'}


class TestAutoReload:
    """auto_reload 被动热更新"""

    def test_reload_on_read(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'reload.json')
        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'S': {'port': 3306}}, f)

        class C(ConfigBase):
            _crypto = crypto.PlainJson(file_path)
            _auto_reload = True
            s = Section('S')
            port = s.field(default=8080, option='port')

        assert C.port.value == 3306

        # 外部修改文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'S': {'port': 5432}}, f)

        assert C.port.value == 5432  # 重新读取拿到新值
