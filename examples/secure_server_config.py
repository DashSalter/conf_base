"""示例 3：服务端配置的加密落盘与 Schema 迁移。

演示：

- ``AesGcmCipher``：AES-256-GCM 加密写入，明文里只有信封头（算法与 nonce），配置值不可见
- Schema 迁移：文件是 v1、代码是 v2，加载时自动跑迁移链并回写为 v2

运行：

    pip install conf_base[aes]
    python examples/secure_server_config.py
"""

import json

from conf_base import AesGcmCipher, ConfigBase, Section

# 演示用密钥，至少 16 字节；真实项目从环境变量 CONF_BASE_KEY 或密钥管理服务读取
_DEMO_KEY = 'demo-key-change-me-at-least-16-bytes'


class ServerConfig(ConfigBase):
    """加密落盘的服务端配置。"""

    _path = 'demo_server.json.enc'
    _cipher = AesGcmCipher(key=_DEMO_KEY, key_id='v1')

    server = Section('Server')
    host = server.field(default='0.0.0.0')
    port = server.field(default=8080)
    secret = server.field(default='change-me')


def demo_encryption() -> None:
    ServerConfig.secret.value = 'super-secret-token'

    with open(ServerConfig._path, 'rb') as fh:
        blob = fh.read()
    print(f'磁盘上共 {len(blob)} 字节，前 60 字节是信封头（算法与 nonce）：')
    print(f'  {blob[:60]!r}')
    print(f'用同一密钥读回：secret={ServerConfig.secret.value!r}')

# ---------------------------------------------------------------------------
# Schema 迁移：旧文件是 v1（Server.threads），新代码是 v2（Server.workers）
# ---------------------------------------------------------------------------

_LEGACY_PATH = 'demo_migrated.json'
_LEGACY_DATA = {
    '_schema_version': 1,
    'Server': {'host': '10.0.0.5', 'port': 9000, 'threads': 8},
}

# 先写一份 v1 文件，再定义 v2 配置类，类创建时就会触发迁移
with open(_LEGACY_PATH, 'w', encoding='utf-8') as _fh:
    json.dump(_LEGACY_DATA, _fh, ensure_ascii=False, indent=2)


def migrate_v1_to_v2(config):
    """把 v1 的 Server.threads 改名为 v2 的 Server.workers。"""
    data = dict(config)
    server = dict(data.get('Server', {}))
    server['workers'] = server.pop('threads', 4)
    data['Server'] = server
    return data


class MigratedConfig(ConfigBase):
    """当前代码期望的 v2 结构。"""

    _path = _LEGACY_PATH
    _schema_version = 2
    _migrate = {1: migrate_v1_to_v2}

    server = Section('Server')
    host = server.field(default='127.0.0.1')
    port = server.field(default=8000)
    workers = server.field(default=4)


def demo_migration() -> None:
    print('v1 文件内容：')
    print(f'  {_LEGACY_DATA}')
    print('加载后的内存配置（已迁移）：')
    print(f'  {MigratedConfig.to_dict()}')
    with open(MigratedConfig._path, encoding='utf-8') as fh:
        print('迁移结果已回写磁盘：')
        print(''.join(f'  {line}' for line in fh.readlines()))


if __name__ == '__main__':
    print('== 1. 加密落盘 ==')
    demo_encryption()
    print('\n== 2. Schema 迁移 ==')
    demo_migration()
