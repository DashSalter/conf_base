"""conf_base.validators 的单元测试。"""
import re

import pytest

from conf_base import ConfigBase, Section
from conf_base.error import ConfigValueError
from conf_base.validators import (
    in_range,
    is_path,
    is_url,
    length,
    matches,
    one_of,
)


class TestInRange:
    def test_inside(self):
        assert in_range(1, 10)(5)

    def test_inclusive_bounds(self):
        check = in_range(1, 10)
        assert check(1)
        assert check(10)

    def test_exclusive_bounds(self):
        check = in_range(1, 10, inclusive=False)
        assert not check(1)
        assert not check(10)
        assert check(5)

    def test_only_minimum(self):
        check = in_range(minimum=0)
        assert check(0)
        assert check(10 ** 6)
        assert not check(-1)

    def test_only_maximum(self):
        check = in_range(maximum=0)
        assert check(0)
        assert check(-100)
        assert not check(1)

    def test_float_values(self):
        assert in_range(0.5, 1.5)(1.0)
        assert not in_range(0.5, 1.5)(1.6)

    @pytest.mark.parametrize('value', [True, False])
    def test_rejects_bool(self, value):
        assert not in_range(0, 10)(value)

    @pytest.mark.parametrize('value', ['5', None, [5], {}])
    def test_rejects_non_number(self, value):
        assert not in_range(0, 10)(value)

    def test_requires_a_bound(self):
        with pytest.raises(ValueError):
            in_range()

    def test_rejects_non_numeric_bound(self):
        with pytest.raises(TypeError):
            in_range('1', 10)


class TestOneOf:
    def test_exact_match(self):
        check = one_of('debug', 'info', 'warning')
        assert check('info')
        assert not check('INFO')

    def test_case_insensitive(self):
        check = one_of('debug', 'info', ignore_case=True)
        assert check('INFO')
        assert check('Debug')

    def test_non_string_with_ignore_case(self):
        assert not one_of(1, 2, ignore_case=True)(1)

    def test_bool_not_confused_with_int(self):
        assert not one_of(1, 2)(True)
        assert one_of(True, False)(True)

    def test_requires_choices(self):
        with pytest.raises(ValueError):
            one_of()


class TestMatches:
    def test_full_match_semantics(self):
        check = matches(r'\d{3}-\d{4}')
        assert check('555-1234')
        assert not check('tel:555-1234')
        assert not check('555-12345')

    def test_compiled_pattern(self):
        check = matches(re.compile(r'[a-z]+'))
        assert check('hello')
        assert not check('hello1')

    def test_flags(self):
        assert matches('hello', flags=re.IGNORECASE)('HELLO')

    @pytest.mark.parametrize('value', [123, None, b'abc'])
    def test_rejects_non_string(self, value):
        assert not matches(r'\w+')(value)

    def test_rejects_bad_pattern(self):
        with pytest.raises(TypeError):
            matches(123)  # type: ignore[arg-type]


class TestIsUrl:
    def test_http_and_https(self):
        assert is_url()('http://example.com')
        assert is_url()('https://example.com/a/b?c=1#d')

    def test_scheme_case_insensitive(self):
        assert is_url()('HTTPS://example.com')

    def test_rejects_missing_scheme(self):
        assert not is_url()('example.com')
        assert not is_url()('/local/path')

    def test_rejects_missing_host(self):
        assert not is_url()('http:///path')

    def test_rejects_other_scheme(self):
        assert not is_url()('ftp://example.com')

    def test_custom_schemes(self):
        assert is_url(schemes=('ftp',))('ftp://example.com')
        assert not is_url(schemes=('ftp',))('https://example.com')

    @pytest.mark.parametrize('value', ['', None, 42])
    def test_rejects_non_string(self, value):
        assert not is_url()(value)

    def test_requires_scheme_names(self):
        with pytest.raises(ValueError):
            is_url(schemes=())


class TestIsPath:
    def test_plain_path(self):
        assert is_path()('C:/data/app.json')
        assert not is_path()('')

    def test_must_exist(self, tmp_path):
        target = tmp_path / 'a.txt'
        assert not is_path(must_exist=True)(str(target))
        target.write_text('x', encoding='utf-8')
        assert is_path(must_exist=True)(str(target))

    def test_kind(self, tmp_path):
        file_path = tmp_path / 'a.txt'
        file_path.write_text('x', encoding='utf-8')
        assert is_path(kind='file')(str(file_path))
        assert not is_path(kind='dir')(str(file_path))
        assert is_path(kind='dir')(str(tmp_path))
        assert not is_path(kind='file')(str(tmp_path))

    def test_rejects_bad_kind(self):
        with pytest.raises(ValueError):
            is_path(kind='socket')

    @pytest.mark.parametrize('value', [None, 1])
    def test_rejects_non_string(self, value):
        assert not is_path()(value)


class TestLength:
    def test_string(self):
        check = length(1, 3)
        assert check('a')
        assert check('abc')
        assert not check('')
        assert not check('abcd')

    def test_collections(self):
        assert length(2)([1, 2, 3])
        assert not length(2)([1])
        assert length(maximum=1)({'a': 1})

    def test_non_sized_value(self):
        assert not length(1)(42)

    def test_requires_a_bound(self):
        with pytest.raises(ValueError):
            length()

    def test_rejects_negative_bound(self):
        with pytest.raises(ValueError):
            length(minimum=-1)

    def test_rejects_min_greater_than_max(self):
        with pytest.raises(ValueError):
            length(3, 1)


class TestIntegration:
    def test_validator_accepts_and_rejects(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        class PortDemo(ConfigBase):
            server = Section('Server')
            port = server.field(default=8080, validator=in_range(1, 65535))

        assert PortDemo.port.value == 8080
        PortDemo.port.value = 65535
        assert PortDemo.port.value == 65535
        with pytest.raises(ConfigValueError):
            PortDemo.port.value = 70000
        assert PortDemo.port.value == 65535

    def test_validator_error_is_wrapped_in_config_value_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def boom(value):
            raise RuntimeError('boom')

        class BoomDemo(ConfigBase):
            server = Section('Server')
            opt = server.field(default='ok', validator=boom)

        with pytest.raises(ConfigValueError) as excinfo:
            BoomDemo.opt.value = 'bad'
        assert isinstance(excinfo.value.__cause__, RuntimeError)
        assert 'opt' in str(excinfo.value)
