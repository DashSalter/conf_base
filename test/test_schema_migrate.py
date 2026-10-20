import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from conf_base import ConfigMeta, Section, crypto


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

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            _schema_version = 2
            _migrate = {1: migrate}
            s = Section('Setting')
            bgm = s.add('bgm', default=1.0)
            screen = s.add('screen', default=3)

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

        class C(metaclass=ConfigMeta):
            _crypto = crypto.PlainJson(file_path)
            _schema_version = 3
            _migrate = {1: m1, 2: m2}
            audio = Section('Audio')
            bgm = audio.add('bgm', default=1.0)
            display = Section('Display')
            screen = display.add('screen', default=3)
            game = Section('Game')
            name = game.add('name', default='default')

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
            class C(metaclass=ConfigMeta):
                _crypto = crypto.PlainJson(file_path)
                _schema_version = 3
                _migrate = {1: m1}
                s = Section('Setting')
                bgm = s.add('bgm', default=1.0)
