import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import OrderedDict

import pytest
from conf_base import ConfigBase, Section
from conf_base.error import (
    ConfBaseError,
    ConfigKeyError,
    ConfigTypeError,
    ConfigValueError,
    ParseError,
    WriteError,
)


class TestFeatures:
    """validator / read_only / 独立 Section / on_change / 类型代理"""

    def test_validator(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'valid.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080, option='port', validator=lambda x: x > 0)

        with pytest.raises(Exception):
            C.port.value = -1

    def test_validator_exception_wrapped(self, tmp_dir):
        """validator 自身抛异常时包装为 ConfigValueError，并保留原始异常"""
        file_path = os.path.join(tmp_dir, 'validator_exc.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080, option='port',
                           validator=lambda v: 1 / 0 > v)

        with pytest.raises(ConfigValueError) as exc_info:
            C.port.value = 9090
        assert isinstance(exc_info.value.__cause__, ZeroDivisionError)

    def test_type_check(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'type.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080, option='port')

        with pytest.raises(Exception):
            C.port.value = 'not_int'

    def test_read_only(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'ro.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            name = s.field(default='locked', option='name', read_only=True)

        with pytest.raises(WriteError):
            C.name.value = 'new'

    def test_independent_sections(self, tmp_dir):
        """同一数据格式可定义多个独立 Section，互不影响"""
        file_path = os.path.join(tmp_dir, 'levels.json')
        default = {'name': '', 'age': 0}

        class C(ConfigBase):
            _path = file_path
            level1 = Section('Level')
            data1 = level1.field(default=dict(default), option='done')
            level2 = Section('Level2')
            data2 = level2.field(default=dict(default), option='done')

        C.data1['name'] = 'Tom'
        C.data2['name'] = 'Tom2'
        assert C.data1.value == {'name': 'Tom', 'age': 0}
        assert C.data2.value == {'name': 'Tom2', 'age': 0}

        class C2(ConfigBase):
            _path = file_path
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
                _path = os.path.join(tmp_dir, 'dup.json')
                s = Section('S')
                first = s.field(default=1, option='port')
                second = s.field(default=2, option='port')

    def test_option_defaults_to_attribute_name(self, tmp_dir):
        """省略 option 时使用左侧类属性名作为配置键名"""
        file_path = os.path.join(tmp_dir, 'auto_name.json')

        class C(ConfigBase):
            _path = file_path
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
            _path = file_path
            s = Section('S')
            items = s.field(default=[1, 2], option='items')

        C.items.append(3)
        assert C.items.value == [1, 2, 3]
        C.items[0] = 99
        assert C.items.value == [99, 2, 3]

    def test_dict_proxy(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'dictp.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            db = s.field(default={'host': 'localhost'}, option='db')

        C.db['port'] = 5432
        assert C.db.value == {'host': 'localhost', 'port': 5432}

    def test_on_change(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'onchange.json')
        received = []

        class C(ConfigBase):
            _path = file_path
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
            _path = file_path
            lvl = Section('Level')
            done = lvl.field(default=[1, 2, 3], option='done')

        C.done.value = [7, 8]
        C.lvl.reset()
        assert C.lvl.current_options == {'done': [1, 2, 3]}

    def test_toggle(self, tmp_dir):
        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 't.json')
            s = Section('S')
            flag = s.field(default=False, option='flag')

        assert C.flag.toggle() is True
        assert C.flag.toggle() is False

    def test_increment(self, tmp_dir):
        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'i.json')
            s = Section('S')
            cnt = s.field(default=10, option='cnt')

        assert C.cnt.increment() == 11
        assert C.cnt.increment(5) == 16
        assert C.cnt.increment(-3) == 13

    def test_is_default(self, tmp_dir):
        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'd.json')
            s = Section('S')
            port = s.field(default=8080, option='port')

        assert C.port.is_default is True
        C.port.value = 9090
        assert C.port.is_default is False

    def test_list_proxy_full(self, tmp_dir):
        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'lp.json')
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
            _path = os.path.join(tmp_dir, 'dp.json')
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
            _path = file_path
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
            _path = os.path.join(tmp_dir, 'multi_cb.json')
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
            _path = os.path.join(tmp_dir, 'def.json')
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
            _path = file_path
            _auto_reload = True
            s = Section('S')
            port = s.field(default=8080, option='port')

        assert C.port.value == 3306

        # 外部修改文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'S': {'port': 5432}}, f)

        assert C.port.value == 5432  # 重新读取拿到新值

    def test_reload_skips_unchanged_file(self, tmp_dir):
        """文件未变化时不重复读取磁盘，外部修改后才重新加载"""
        file_path = os.path.join(tmp_dir, 'reload_cache.json')

        class C(ConfigBase):
            _path = file_path
            _auto_reload = True
            s = Section('S')
            port = s.field(default=8080, option='port')

        C.port.value = 9090
        # 刚写完的文件 mtime 处于时间戳精度可疑窗口内，会被强制重读；
        # 把 mtime 往前推，确保后续读取走指纹缓存路径
        stat = os.stat(file_path)
        os.utime(file_path, ns=(stat.st_atime_ns, stat.st_mtime_ns - 1_000_000_000))
        assert C.port.value == 9090

        jf = C.port._parent._config_file
        calls = []
        original = jf.cipher.decrypt
        jf.cipher.decrypt = lambda content: (calls.append(1), original(content))[1]  # type: ignore[method-assign]

        for _ in range(5):
            assert C.port.value == 9090
        assert calls == []

        import json
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        data['S']['port'] = 1234
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        assert C.port.value == 1234
        assert len(calls) == 1


class TestValueTypeStrictness:
    """类型校验：容器子类归一化，标量保持严格"""

    def test_dict_subclass_normalized(self, tmp_dir):
        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'subclass.json')
            s = Section('S')
            db = s.field(default={'a': 1})

        C.db.value = OrderedDict(a=2)
        assert type(C.db.value) is dict
        assert C.db.value == {'a': 2}

    def test_scalar_subclass_rejected(self, tmp_dir):
        class MyInt(int):
            pass

        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'scalar.json')
            s = Section('S')
            num = s.field(default=1)

        with pytest.raises(ConfigTypeError, match='子类请先转换'):
            C.num.value = MyInt(2)
        with pytest.raises(ConfigTypeError):
            C.num.value = True


class TestProxyCompare:
    def test_proxy_compares_value(self, tmp_dir):
        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'eq.json')
            s = Section('S')
            port = s.field(default=8080)

        assert C.port == 8080
        assert not (C.port == 9090)
        assert C.port != 9090


class TestUnknownKeys:
    """启动时对未知 section/option 的处理"""

    def test_preserved_by_default(self, tmp_dir):
        import json
        file_path = os.path.join(tmp_dir, 'unknown.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080)

        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        data['Extra'] = {'x': 1}
        data['S']['ghost'] = 'keep'
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        class C2(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080)

        with open(file_path, encoding='utf-8') as f:
            after = json.load(f)
        assert after['Extra'] == {'x': 1}
        assert after['S']['ghost'] == 'keep'

    def test_prune_unknown_when_enabled(self, tmp_dir):
        import json
        file_path = os.path.join(tmp_dir, 'prune.json')

        class C(ConfigBase):
            _path = file_path
            _prune_unknown = True
            s = Section('S')
            port = s.field(default=8080)

        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        data['Extra'] = {'x': 1}
        data['_internal'] = 'keep'
        data['S']['ghost'] = 'keep'
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        class C2(ConfigBase):
            _path = file_path
            _prune_unknown = True
            s = Section('S')
            port = s.field(default=8080)

        with open(file_path, encoding='utf-8') as f:
            after = json.load(f)
        assert 'Extra' not in after
        assert 'ghost' not in after['S']
        # 框架内部字段（下划线开头）不参与清理
        assert after['_internal'] == 'keep'
        assert '_schema_version' in after

    def test_prune_unknown_emits_warning(self, tmp_dir):
        """开启清理时必须留下痕迹：警告中列出被删除的键"""
        import json
        file_path = os.path.join(tmp_dir, 'prune_warn.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080)

        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        data['Extra'] = {'x': 1}
        data['S']['ghost'] = 'keep'
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        with pytest.warns(UserWarning) as record:
            class C2(ConfigBase):
                _path = file_path
                _prune_unknown = True
                s = Section('S')
                port = s.field(default=8080)

        message = str(record[0].message)
        assert 'Extra' in message
        assert 'S.ghost' in message

    def test_prune_unknown_no_warning_when_clean(self, tmp_dir):
        """没有未知项时不应产生警告噪音"""
        import warnings
        file_path = os.path.join(tmp_dir, 'prune_clean.json')

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')

            class C(ConfigBase):
                _path = file_path
                _prune_unknown = True
                s = Section('S')
                port = s.field(default=8080)

            class C2(ConfigBase):
                _path = file_path
                _prune_unknown = True
                s = Section('S')
                port = s.field(default=8080)

        assert not [w for w in caught if issubclass(w.category, UserWarning)]


class TestBatchTransaction:
    """batch() 的事务语义：块内异常时回滚内存，不落盘半批修改"""

    def test_rollback_on_error(self, tmp_dir):
        import json
        file_path = os.path.join(tmp_dir, 'batch_rollback.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080)
            name = s.field(default='a')

        with pytest.raises(ConfigTypeError):
            with C.s.batch():
                C.port.value = 9090
                C.name.value = 123     # 类型错误，触发回滚

        assert C.port.value == 8080
        assert C.name.value == 'a'
        with open(file_path, encoding='utf-8') as f:
            assert json.load(f)['S'] == {'port': 8080, 'name': 'a'}

    def test_nested_batch_rolls_back_all(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'batch_nested.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080)
            name = s.field(default='a')

        with pytest.raises(ConfigTypeError):
            with C.s.batch():
                C.port.value = 9090
                with C.s.batch():
                    C.name.value = 123

        assert C.port.value == 8080
        assert C.name.value == 'a'

    def test_swallowed_inner_error_rolls_back_inner_only(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'batch_savepoint.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080)
            name = s.field(default='a')

        with C.s.batch():
            C.port.value = 9090
            try:
                with C.s.batch():
                    C.name.value = 'b'
                    raise RuntimeError('inner')
            except RuntimeError:
                pass
            # 内层回滚到进入前的数据，外层的修改保留
            assert C.name.value == 'a'
            assert C.port.value == 9090

        assert C.port.value == 9090
        assert C.name.value == 'a'


class TestResetValidation:
    """reset 与普通写入一样受环境变量 / read_only / validator 约束"""

    def test_reset_rejected_by_env_override(self, tmp_dir, monkeypatch):
        monkeypatch.setenv('APP_PORT', '9999')
        file_path = os.path.join(tmp_dir, 'reset_env.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080, env_key='APP_PORT')

        with pytest.raises(WriteError):
            C.port.reset()
        with pytest.raises(WriteError):
            C.s.reset()
        assert C.port.value == 9999

    def test_reset_rejected_by_read_only(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'reset_readonly.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            token = s.field(default='t', read_only=True)
            port = s.field(default=8080)

        C.port.value = 9090
        with pytest.raises(WriteError):
            C.s.reset()
        # 事务回滚：不会出现“部分重置”
        assert C.port.value == 9090


class TestWriteSkipping:
    """写入与当前值相同时跳过落盘"""

    def test_noop_write_skipped(self, tmp_dir, monkeypatch):
        file_path = os.path.join(tmp_dir, 'noop.json')

        class C(ConfigBase):
            _path = file_path
            s = Section('S')
            port = s.field(default=8080)

        cf = C.port._parent._config_file  # noqa: SLF001
        calls = []
        original = cf.write_config
        monkeypatch.setattr(cf, 'write_config',
                            lambda: (calls.append(1), original())[1])

        C.port.value = 8080     # 与当前值相同
        assert calls == []

        C.port.value = 9090
        assert len(calls) == 1


class TestMalformedConfig:
    """手写文件结构错误时给出明确的 ParseError"""

    def test_section_must_be_dict(self, tmp_dir):
        import json
        file_path = os.path.join(tmp_dir, 'bad_section.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'S': 5}, f)

        with pytest.raises(ParseError, match="section 'S' 必须是字典"):
            class C(ConfigBase):
                _path = file_path
                s = Section('S')
                port = s.field(default=8080)


class TestNoInheritance:
    """配置类不允许继承，避免父子类共享同一份配置数据"""

    def test_inheritance_rejected(self, tmp_dir):
        class Base(ConfigBase):
            _path = os.path.join(tmp_dir, 'base.json')

        with pytest.raises(TypeError, match='不支持继承'):
            class Child(Base):
                s = Section('S')
                port = s.field(default=8080)

    def test_mixin_before_config_base_allowed(self, tmp_dir):
        class Mixin:
            pass

        class C(Mixin, ConfigBase):
            _path = os.path.join(tmp_dir, 'mixin.json')
            s = Section('S')
            port = s.field(default=8080)

        assert C.port.value == 8080


class TestAutoReloadDirty:
    """auto_reload 不得覆盖尚未落盘的内存修改"""

    def test_batch_read_keeps_uncommitted_changes(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'reload_dirty.json')

        class C(ConfigBase):
            _path = file_path
            _auto_reload = True
            s = Section('S')
            a = s.field(default=1)
            b = s.field(default=2)

        with C.s.batch():
            C.a.value = 100
            assert C.b.value == 2       # 读取触发重载检查
            assert C.a.value == 100     # 未提交修改必须保留
        assert C.a.value == 100

    def test_reload_after_commit_still_works(self, tmp_dir):
        import json
        file_path = os.path.join(tmp_dir, 'reload_commit.json')

        class C(ConfigBase):
            _path = file_path
            _auto_reload = True
            s = Section('S')
            a = s.field(default=1)

        C.a.value = 100
        assert C.a.value == 100

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'_schema_version': 1, 'S': {'a': 7}}, f)
        assert C.a.value == 7


class TestDefaultValueIsolation:
    """默认值在类创建时拷贝，外部常量与配置数据互不影响"""

    def test_shared_default_object_not_polluted(self, tmp_dir):
        shared = {'hosts': ['a']}

        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'default_copy.json')
            s = Section('S')
            db = s.field(default=shared)

        # 直接修改 .value 返回的内部数据（不落盘），不应污染默认值与原始常量
        C.db.value['hosts'].append('b')
        assert shared == {'hosts': ['a']}
        assert C.db.default == {'hosts': ['a']}
        assert C.db.is_default is False

        C.db.reset()
        assert C.db.value == {'hosts': ['a']}
        assert shared == {'hosts': ['a']}

    def test_two_fields_with_same_default_are_independent(self, tmp_dir):
        base = [1]

        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'default_two.json')
            s = Section('S')
            a = s.field(default=base)
            b = s.field(default=base)

        C.a.value.append(2)
        assert C.b.value == [1]
        assert base == [1]


class TestSectionAttributeAssignment:
    """直接给 Section 属性赋值必须被拒绝，避免静默遮蔽配置项"""

    def test_rejected(self, tmp_dir):
        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'sec_attr.json')
            s = Section('S')
            width = s.field(default=1280)

        with pytest.raises(WriteError, match='不能直接给 Section 属性'):
            C.s.width = 1600
        assert C.s['width'] == 1280

    def test_update_accepts_proxy(self, tmp_dir):
        class A(ConfigBase):
            _path = os.path.join(tmp_dir, 'proxy_a.json')
            s = Section('S')
            a = s.field(default=5)

        class B(ConfigBase):
            _path = os.path.join(tmp_dir, 'proxy_b.json')
            s = Section('S')
            b = s.field(default=1)

        B.s.update(b=A.a)
        assert B.b.value == 5


class TestExceptionHierarchy:
    """KEY 错误统一为 ConfBaseError 子类，同时保持 KeyError 兼容"""

    def test_missing_option_raises_config_key_error(self, tmp_dir):
        class C(ConfigBase):
            _path = os.path.join(tmp_dir, 'keyerr.json')
            s = Section('S')
            a = s.field(default=1)

        with pytest.raises(ConfigKeyError):
            C.s['missing']
        with pytest.raises(ConfBaseError):
            C.s['missing']
        with pytest.raises(KeyError):
            C.s['missing']
        with pytest.raises(ConfigKeyError):
            C.s.update(missing=1)
