import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import ConfigBase, Section


class TestSchemaMigrate:
    """schema 版本迁移"""

    def test_v1_to_v2_rename(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'v1v2.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'Setting': {'bgm_volume': 0.8, 'screen': 5}}, f)

        def migrate(data):
            if 'Setting' in data and 'bgm_volume' in data['Setting']:
                data['Setting']['bgm'] = data['Setting'].pop('bgm_volume')
            return data

        class C(ConfigBase):
            _path = file_path
            _schema_version = 2
            _migrate = {1: migrate}
            s = Section('Setting')
            bgm = s.field(default=1.0, option='bgm')
            screen = s.field(default=3, option='screen')

        assert C.bgm.value == 0.8
        assert C.screen.value == 5

        with open(file_path, encoding='utf-8') as f:
            saved = json.load(f)
        assert saved['_schema_version'] == 2
        assert 'bgm_volume' not in saved['Setting']

    def test_chain_migration(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'chain.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'Setting': {'bgm_volume': 0.5, 'screen': 3, 'name': 'test'}}, f)

        def m1(data):
            if 'Setting' in data and 'bgm_volume' in data['Setting']:
                data['Setting']['bgm'] = data['Setting'].pop('bgm_volume')
            return data

        def m2(data):
            if 'Setting' in data:
                s = data.pop('Setting')
                data['Audio'] = {'bgm': s.pop('bgm', 1.0)}
                data['Display'] = {'screen': s.pop('screen', 3)}
                data['Game'] = {'name': s.pop('name', 'default')}
            return data

        class C(ConfigBase):
            _path = file_path
            _schema_version = 3
            _migrate = {1: m1, 2: m2}
            audio = Section('Audio')
            bgm = audio.field(default=1.0, option='bgm')
            display = Section('Display')
            screen = display.field(default=3, option='screen')
            game = Section('Game')
            name = game.field(default='default', option='name')

        assert C.bgm.value == 0.5
        assert C.screen.value == 3
        assert C.name.value == 'test'

    def test_missing_migration_raises(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'missing.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'Setting': {'bgm_volume': 0.5}}, f)

        def m1(data):
            return data

        with pytest.raises(ValueError, match='schema 迁移缺失'):
            class C(ConfigBase):
                _path = file_path
                _schema_version = 3
                _migrate = {1: m1}
                s = Section('Setting')
                bgm = s.field(default=1.0, option='bgm')

    def test_newer_file_version_rejected(self, tmp_dir):
        """文件版本高于代码目标版本时拒绝降级，且不改写文件"""
        file_path = os.path.join(tmp_dir, 'newer.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'_schema_version': 3, 'Setting': {'bgm': 0.5}}, f)

        with pytest.raises(ValueError, match='高于代码声明'):
            class C(ConfigBase):
                _path = file_path
                _schema_version = 2
                _migrate = {1: lambda d: d}
                s = Section('Setting')
                bgm = s.field(default=1.0, option='bgm')

        with open(file_path, encoding='utf-8') as f:
            assert json.load(f)['_schema_version'] == 3

    def test_migration_must_return_dict(self, tmp_dir):
        file_path = os.path.join(tmp_dir, 'bad_migrate.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'_schema_version': 1, 'Setting': {'bgm': 0.5}}, f)

        with pytest.raises(ValueError, match='必须返回字典'):
            class C(ConfigBase):
                _path = file_path
                _schema_version = 2
                _migrate = {1: lambda d: None}
                s = Section('Setting')
                bgm = s.field(default=1.0, option='bgm')
