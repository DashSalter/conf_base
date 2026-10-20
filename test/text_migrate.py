import json
import os
from conf_base import ConfigMeta, Section, crypto

"""
Schema 迁移功能测试
模拟配置文件版本升级时的字段重命名、section 重组等场景。
"""


# ================================================================
# 准备：模拟一个旧的 v1 配置文件
# ================================================================
def _make_old_file(filepath):
    """写一个旧版本配置文件（v1：字段名 bgm_volume）"""
    data = {
        '_schema_version': 1,
        'Setting': {
            'bgm_volume': 0.8,
            'screen_size': 5,
            'full_screen': True,
            'score': 1200,
        }
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ================================================================
# 场景 1：v1 → v2 字段重命名
# ================================================================
print('=' * 50)
print('场景 1：v1 → v2 字段重命名（bgm_volume → bgm）')
print('=' * 50)

_tmp = '_test_migrate_v1v2.json'
_make_old_file(_tmp)


def migrate_v1_to_v2(data):
    """v1→v2：bgm_volume → bgm"""
    if 'Setting' in data:
        s = data['Setting']
        if 'bgm_volume' in s:
            s['bgm'] = s.pop('bgm_volume')
    return data


class ConfigV2(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson(_tmp)
    _schema_version = 2
    _migrate = {1: migrate_v1_to_v2}

    setting = Section('Setting')
    bgm = setting.add('bgm', default=1.0)           # 新字段名
    screen_size = setting.add('screen_size', default=3)
    full_screen = setting.add('full_screen', default=False)
    score = setting.add('score', default=0)


# 验证迁移结果
assert ConfigV2.bgm.value == 0.8, f"bgm 应为 0.8，实际 {ConfigV2.bgm.value}"
assert ConfigV2.screen_size.value == 5
assert ConfigV2.score.value == 1200

# 检查文件
with open(_tmp, encoding='utf-8') as f:
    saved = json.load(f)
assert saved['_schema_version'] == 2
assert 'bgm' in saved['Setting']
assert 'bgm_volume' not in saved['Setting']
print(f'✅ 迁移后 bgm={ConfigV2.bgm.value}, 文件版本={saved["_schema_version"]}')

# 再次启动（已在 v2），不应该再次触发迁移
_bg_mtime = os.path.getmtime(_tmp)
class ConfigV2_Again(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson(_tmp)
    _schema_version = 2
    _migrate = {1: migrate_v1_to_v2}

    setting = Section('Setting')
    bgm = setting.add('bgm', default=1.0)
    screen_size = setting.add('screen_size', default=3)
    full_screen = setting.add('full_screen', default=False)
    score = setting.add('score', default=0)
print('✅ 再次启动不重复迁移')

os.remove(_tmp)

# ================================================================
# 场景 2：v1 → v2 → v3 多版本链式迁移（section 重组）
# ================================================================
print('\n' + '=' * 50)
print('场景 2：v1 → v3 链式迁移（Setting → Audio + Display）')
print('=' * 50)

_tmp = '_test_migrate_v1v3.json'
_make_old_file(_tmp)


def migrate_v2_to_v3(data):
    """v2→v3：Setting 拆成 Audio + Display"""
    if 'Setting' in data:
        s = data.pop('Setting')
        data['Audio'] = {'bgm': s.pop('bgm', 1.0), 'sfx': 0.7}
        data['Display'] = {
            'screen_size': s.pop('screen_size', 3),
            'full_screen': s.pop('full_screen', False),
        }
        # score 保留在 Game section
        if 'score' in s:
            data.setdefault('Game', {})['score'] = s.pop('score')
    return data


class ConfigV3(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson(_tmp)
    _schema_version = 3
    _migrate = {
        1: migrate_v1_to_v2,  # 先跑 v1→v2（bgm_volume→bgm）
        2: migrate_v2_to_v3,  # 再跑 v2→v3（section 重组）
    }

    audio = Section('Audio')
    bgm = audio.add('bgm', default=1.0)
    sfx = audio.add('sfx', default=0.5)  # v3 新增字段

    display = Section('Display')
    screen_size = display.add('screen_size', default=3)
    full_screen = display.add('full_screen', default=False)

    game = Section('Game')
    score = game.add('score', default=0)


# 验证
assert ConfigV3.bgm.value == 0.8
assert ConfigV3.sfx.value == 0.7  # 新增字段用默认值
assert ConfigV3.screen_size.value == 5
assert ConfigV3.full_screen.value == True
assert ConfigV3.score.value == 1200

with open(_tmp, encoding='utf-8') as f:
    saved = json.load(f)
assert saved['_schema_version'] == 3
assert 'Setting' not in saved  # 旧 section 被拆走
assert 'Audio' in saved and 'Display' in saved
assert saved['Audio']['bgm'] == 0.8
print(f'✅ 链式迁移完成，文件结构: {list(saved.keys())}')

os.remove(_tmp)

# ================================================================
# 场景 3：缺失迁移函数 → 报错
# ================================================================
print('\n' + '=' * 50)
print('场景 3：缺失迁移函数 → 报错')
print('=' * 50)

_tmp = '_test_migrate_missing.json'
_make_old_file(_tmp)

try:
    class ConfigBad(metaclass=ConfigMeta):
        _crypto = crypto.PlainJson(_tmp)
        _schema_version = 3
        _migrate = {1: migrate_v1_to_v2}  # 缺 v2→v3
except ValueError as e:
    print(f'✅ 正确报错: {e}')

os.remove(_tmp)

# ================================================================
# 场景 4：新文件启动（无旧版本）→ 直接用目标版本
# ================================================================
print('\n' + '=' * 50)
print('场景 4：全新文件启动')
print('=' * 50)

_tmp = '_test_migrate_new.json'
if os.path.exists(_tmp):
    os.remove(_tmp)


class ConfigNew(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson(_tmp)
    _schema_version = 2
    _migrate = {1: migrate_v1_to_v2}

    setting = Section('Setting')
    bgm = setting.add('bgm', default=1.0)
    screen_size = setting.add('screen_size', default=3)


with open(_tmp, encoding='utf-8') as f:
    saved = json.load(f)
assert saved['_schema_version'] == 2
assert saved['Setting']['bgm'] == 1.0
print(f'✅ 新文件版本号正确: _schema_version={saved["_schema_version"]}')

os.remove(_tmp)

print('\n🎉 全部 4 个场景通过 ✅')
