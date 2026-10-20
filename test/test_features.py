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

    def test_toggle(self, tmp_dir):
        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 't.json'))
            s = Section('S')
            flag = s.add('flag', default=False)

        assert C.flag.toggle() is True
        assert C.flag.toggle() is False

    def test_increment(self, tmp_dir):
        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'i.json'))
            s = Section('S')
            cnt = s.add('cnt', default=10)

        assert C.cnt.increment() == 11
        assert C.cnt.increment(5) == 16
        assert C.cnt.increment(-3) == 13

    def test_is_default(self, tmp_dir):
        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'd.json'))
            s = Section('S')
            port = s.add('port', default=8080)

        assert C.port.is_default is True
        C.port.value = 9090
        assert C.port.is_default is False

    def test_list_proxy_full(self, tmp_dir):
        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'lp.json'))
            s = Section('S')
            items = s.add('items', default=[1, 2, 3])

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
        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'dp.json'))
            s = Section('S')
            db = s.add('db', default={'a': 1, 'b': 2})

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

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            s = Section('S')
            port = s.add('port', default=8080)
            name = s.add('name', default='x')

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

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'multi_cb.json'))
            s = Section('S')
            port = s.add('port', default=8080)

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
        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(os.path.join(tmp_dir, 'def.json'))
            s = Section('S')
            port = s.add('port', default=8080)
            name = s.add('name', default='x')

        C.port.value = 9090
        assert C.s.default_options == {'port': 8080, 'name': 'x'}
        assert C.s.current_options == {'port': 9090, 'name': 'x'}


class TestXorCrypto:
    """XorCrypto 零依赖加解密"""

    def test_basic(self, tmp_dir):
        xc = crypto.XorCrypto(key=b'secret_key_16b!!', file_path=os.path.join(tmp_dir, 'xor.enc'))
        data = {'A': {'x': 1}}
        enc = xc.encrypt(data)
        assert xc.decrypt(enc) == data

    def test_key_too_short(self, tmp_dir):
        with pytest.raises(ValueError, match='密钥长度'):
            crypto.XorCrypto(key=b'short', file_path=os.path.join(tmp_dir, 'bad.enc'))

    def test_configmeta_integration(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'xor_cfg.enc')

        class C(metaclass=ConfigMeta):
            _crypto = crypto.XorCrypto(key=b'my_master_key_16!!', file_path=file_path)
            s = Section('S')
            port = s.add('port', default=8080)

        C.port.value = 9090
        with open(file_path, encoding='utf-8') as f:
            raw = f.read()
        assert 'port' not in raw  # 明文不暴露
        assert C.port.value == 9090

    def test_tampered_fails(self, tmp_dir):
        xc = crypto.XorCrypto(key=b'my_master_key_16!!', file_path=os.path.join(tmp_dir, 'tamper.enc'))
        enc = xc.encrypt({'x': 1})
        tampered = enc[:-5] + 'xxxxx'
        with pytest.raises(Exception):
            xc.decrypt(tampered)


class TestAutoReload:
    """auto_reload 被动热更新"""

    def test_reload_on_read(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'reload.json')
        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'S': {'port': 3306}}, f)

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            _auto_reload = True
            s = Section('S')
            port = s.add('port', default=8080)

        assert C.port.value == 3306

        # 外部修改文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'S': {'port': 5432}}, f)

        assert C.port.value == 5432  # 重新读取拿到新值
