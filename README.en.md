# ConfBase

English | [简体中文](README.md)

[![Python](https://img.shields.io/badge/python-%3E%3D3.8-blue)](https://www.python.org/)
[![CI](https://github.com/DashSalter/conf_base/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/DashSalter/conf_base/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-164%20passed-brightgreen)](test/)
[![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen)](test/)

conf_base is a Python configuration library built on a Section-Field model, with multi-format
storage, encryption, hot reload and schema migration.

## How it compares

| Capability | conf_base | python-dotenv | dynaconf | pydantic-settings | Hydra |
|---|---|---|---|---|---|
| Declarative schema + defaults | ✅ | ❌ | ⚠️ | ✅ | ✅ |
| JSON / YAML / TOML | ✅ | ❌ (`.env` only) | ✅ | ✅ (format plugin required) | ⚠️ (mostly YAML) |
| Environment variable override | ✅ | ✅ | ✅ | ✅ | ⚠️ (custom resolver) |
| Built-in encryption at rest | ✅ AES-GCM / ChaCha20-Poly1305 | ❌ | ❌ | ❌ | ❌ |
| Tamper-proof signature | ✅ HMAC-SHA256 | ❌ | ❌ | ❌ | ❌ |
| Schema version migration | ✅ | ❌ | ❌ | ❌ | ❌ |
| Batched writes / change callbacks | ✅ | ❌ | ⚠️ | ❌ | ❌ |
| Required runtime dependencies | 0 | 0 | yes | pydantic v2 | omegaconf etc. |
| Learning curve | low | low | medium | medium | high |

Rules of thumb:

- Only need to read/write `.env` → `python-dotenv`
- Need strong typing, nested models, serialization → `pydantic-settings` / `pydantic`
- Need multiple environments, layered merging, remote backends → `dynaconf`
- Need config sweeps for experiment matrices → `Hydra`
- **Local single-machine config file + encryption / signatures / migration / zero dependencies** → `conf_base`

> The ✅/⚠️ marks are compiled from each project's official documentation (Oct 2026) and may change
> between releases; corrections are welcome via an issue.

## When to use it

**Good fit**

- Local configuration for desktop apps and game clients
- CLI tools and scripts that need parameters and preferences
- Config files for single-machine services and small web services
- Projects that want JSON / YAML / TOML in one API
- Configuration that must be encrypted, signed or migrated across versions
- Need for batched updates, change callbacks and per-section reset

**Not a good fit**

| Scenario | Better choice |
|---|---|
| Distributed config center, multi-node real-time sync | Nacos / Apollo / Consul / etcd |
| Remote storage such as Redis / MySQL | A config center, or implement `BaseFormat` / `BaseCipher` |
| Writes at hundreds of operations per second | A database, or a config center |
| Very large configs or binary payloads | A database or object storage |
| Complex nested models and field-level validation | pydantic / pydantic-settings |
| Multiple users editing one file concurrently | A database with optimistic locking |
| Adding/removing options at runtime | A dynamic config center |
| Reusing options through class inheritance | Inherit `ConfigBase` directly and redeclare them (config classes cannot inherit from each other) |
| Config auditing, access control, rollback | A config center or a secrets manager |

> ConfBase is a lightweight "local file + declarative config" tool. It is not a config-center
> client, and it is not a pydantic replacement.

## Installation

```bash
pip install conf_base
```

Optional extras:

| Feature | Command |
|---|---|
| YAML format | `pip install conf_base[yaml]` |
| TOML format | `pip install conf_base[toml]` |
| Encryption / signing | `pip install conf_base[aes]` |
| Multi-process file lock | `pip install conf_base[filelock]` |

## Quick start

A game client's configuration:

```python
from conf_base import ConfigBase, Section


class GameConfig(ConfigBase):
    # Config file path; the format is inferred from the suffix (JSON when there is none)
    _path = 'config/game.json'

    # Video
    screen = Section('Screen')
    width = screen.field(default=1280, validator=lambda v: v >= 800)
    height = screen.field(default=720)
    fullscreen = screen.field(default=False)

    # Audio
    audio = Section('Audio')
    bgm_volume = audio.field(default=0.8, validator=lambda v: 0 <= v <= 1)
    mute = audio.field(default=False)

    # Save data
    save = Section('Save')
    unlocked_levels = save.field(default=[1])
```

Defining the class creates `config/game.json` and writes any missing defaults:

```json
{
    "_schema_version": 1,
    "Screen": {
        "width": 1280,
        "height": 720,
        "fullscreen": false
    },
    "Audio": {
        "bgm_volume": 0.8,
        "mute": false
    },
    "Save": {
        "unlocked_levels": [
            1
        ]
    }
}
```

The layout is exactly the class: section names on the top level, option names below them, and
values equal to the `default`s in code. `_schema_version` is internal, used for migration, and
`to_dict()` does not export it.

Reading and writing look like plain attributes:

```python
# Read
GameConfig.width.value                      # 1280
GameConfig.screen.current_options           # {'width': 1280, 'height': 720, ...}

# Write: type and validator are checked, then the file is saved
GameConfig.width.value = 1920
GameConfig.bgm_volume.value = 0.5
GameConfig.bgm_volume.value = 1.5           # ❌ ConfigValueError (outside 0~1)

# Type-specific helpers
GameConfig.fullscreen.toggle()              # False -> True
GameConfig.width.increment(100)             # 1920 -> 2020
GameConfig.unlocked_levels.append(2)        # [1] -> [1, 2]

# Batched update: everything is written once
GameConfig.audio.update(bgm_volume=0.6, mute=True)

# Full export
GameConfig.to_dict()
# {'Screen': {...}, 'Audio': {...}, 'Save': {...}}
```

Three runnable examples (CLI tool, game client, encrypted server with migration) live in
[`examples/`](examples/); each file runs on its own:

```bash
python examples/cli_config.py
python examples/game_config.py
python examples/secure_server_config.py
```

## Core usage

### 1. Declaring options

Arguments of `Section.field()`:

```python
port = server.field(
    default=8080,                          # default value; its type fixes the option type
    option='port',                         # key name, defaults to the attribute name
    validator=lambda v: 1 <= v <= 65535,   # optional, returning False rejects the write
    read_only=False,                       # optional, True forbids runtime changes
    env_key='APP_PORT',                    # optional, allows an env var override
)
# Here option equals the attribute name, so it can be omitted; use option='listen_port' otherwise.
# IDE support: __set_name__ infers the name, and field() returns a typed proxy
# (BoolProxy/NumberProxy/ListProxy/DictProxy) with helpers like toggle() and increment().
```

An option's type is always locked to the type of its `default`; writing another type raises
`ConfigTypeError`.

### 2. Reading

Four equivalent ways:

```python
GameConfig.width.value                  # descriptor
GameConfig.screen['width']              # section indexing
GameConfig.screen.width                 # section attribute (read-only syntax)
GameConfig.screen.current_options       # the whole section
```

> `section.width` is read-only. To write, use `section['width'] = 1600` or
> `section.width.value = 1600`; `section.width = 1600` raises `WriteError`, which prevents an
> instance attribute from shadowing the option without ever reaching the file.

`default_options` / `current_options` / `to_dict()` all return copies, so mutating the result never
touches internal state.

Bulk export:

```python
GameConfig.screen.default_options   # defaults of one section
GameConfig.to_dict()                # deep copy of everything
```

### 3. Writing

```python
# Single option
GameConfig.width.value = 1920
GameConfig.width.set_value(1920)        # equivalent

# Several options of one section (a single write)
GameConfig.audio.update(bgm_volume=0.6, mute=True)

# Group arbitrary operations into one write
with GameConfig.audio.batch():
    GameConfig.bgm_volume.value = 0.4
    GameConfig.mute.toggle()
```

> Loops that update config dozens of times should wrap the body in `batch()` to turn dozens of
> disk writes into one.

`batch()` works like a savepoint: if any statement inside raises, the whole block is rolled back
instead of persisting a half-applied batch. Nested blocks are independent savepoints — an inner
failure rolls back only the inner changes, and an inner exception that is swallowed does not undo
the outer changes. Read-modify-write helpers (`append`, `update`, `toggle`, `increment`) hold the
thread lock for the whole operation, so concurrent calls never lose updates.

### 4. Typed proxies

Each option gets helpers based on its default type:

| Default type | Proxy | Extra methods |
|---|---|---|
| `bool` | `BoolProxy` | `toggle()` |
| `int` / `float` | `NumberProxy` | `increment(n=1)` |
| `list` | `ListProxy` | `append` `extend` `insert` `remove` `pop` `clear` `sort` `reverse`, plus index access |
| `dict` | `DictProxy` | `pop` `update` `setdefault` `clear` `get` `keys` `values` `items`, plus key access |
| anything else | `PropertyProxy` | `value` `default` `reset` `is_default` `on_change` |

Every proxy exposes `value`, `reset()`, `is_default` and `on_change()`; all writes are validated
and saved.

```python
GameConfig.unlocked_levels.append(2)
GameConfig.unlocked_levels.remove(1)
GameConfig.unlocked_levels[0] = 3
GameConfig.screen['width'] = 1600
```

> `field()` carries generic type information, so an IDE infers `GameConfig.width` as
> `NumberProxy` and completes `increment()` for you.

### 5. Validation and read-only options

A write is checked in this order: env var override → read_only → type → validator.

```python
net = Section('Net')
port = net.field(default=8080, validator=lambda v: 1 <= v <= 65535)
token = net.field(default='', read_only=True)

port.value = 'big'      # ❌ ConfigTypeError: wrong type
port.value = 999999     # ❌ ConfigValueError: validator rejected it
token.value = 'new'     # ❌ WriteError: read-only
```

A validator that returns `False` raises `ConfigValueError`; a validator that raises is also wrapped
into `ConfigValueError` with the original exception kept in `__cause__`, so raw exceptions never
leak into application code.

Common checks do not need a hand-written lambda — `conf_base.validators` ships ready-made factories:

```python
from conf_base.validators import in_range, is_path, is_url, length, matches, one_of

class AppConfig(ConfigBase):
    server = Section('Server')
    port = server.field(default=8080, validator=in_range(1, 65535))
    bind = server.field(default='127.0.0.1', validator=matches(r'\d{1,3}(\.\d{1,3}){3}'))
    hook = server.field(default='https://example.com/hook', validator=is_url())
    log_dir = server.field(default='logs', validator=is_path())
    level = server.field(default='info', validator=one_of('debug', 'info', 'warning', 'error'))
    tags = server.field(default=['a'], validator=length(1, 5))
```

| Factory | Purpose | Notes |
|---|---|---|
| `in_range(minimum, maximum, inclusive=True)` | numeric range | only `int` / `float`; `True` / `False` are not numbers here |
| `one_of(*choices, ignore_case=False)` | enumeration | `ignore_case` applies to strings only |
| `matches(pattern, flags=0)` | regex | whole-string match (same as `re.fullmatch`); accepts a compiled pattern |
| `is_url(schemes=('http', 'https'))` | URL shape | structural check only, no network call |
| `is_path(must_exist=False, kind=None)` | path | `kind` may be `'file'` or `'dir'` |
| `length(minimum, maximum)` | length | works on `str` / `list` / `dict` / `tuple` |

These factories only decide validity — they never coerce types, which are still dictated by `default`.
They compose, too:

```python
validator=lambda v: in_range(1, 65535)(v) and v % 2 == 1
```

`reset()` (single option or whole section) goes through the same checks: options overridden by an
env var or marked `read_only` raise `WriteError`, and the section reset is rolled back.

### 6. Change callbacks

```python
@GameConfig.bgm_volume.on_change
def on_volume_change(section, option, value):
    print(f'{section}.{option} is now {value}')


# Plain calls work too
GameConfig.width.on_change(lambda section, option, value: save_now())
```

Callbacks have the signature `callback(section, option, value)` and fire after `value=`,
`set_value()`, `update()`, `reset()` and proxy writes.

### 7. Resetting

```python
GameConfig.width.reset()        # one option back to its default
GameConfig.screen.reset()       # whole section in one write
```

## Multiple homogeneous sections

When the same shape of data exists in several instances (multiple save slots, several levels),
declare one section per instance:

```python
DEFAULT_LEVEL = {'score': 0, 'stars': 0, 'cleared': False}

class GameConfig(ConfigBase):
    _path = 'config/game.json'

    level1 = Section('Level1')
    data1 = level1.field(default=DEFAULT_LEVEL, option='data')

    level2 = Section('Level2')
    data2 = level2.field(default=DEFAULT_LEVEL, option='data')


GameConfig.data1['score'] = 1200
GameConfig.data2['score'] = 800

GameConfig.level1.reset()       # only Level1 changes; Level2 is untouched
```

`list` / `dict` defaults are deep-copied when the option is declared, so the same constant can be
reused without sharing state between sections — no `dict(DEFAULT_LEVEL)` required.

## Environment variable overrides

Environment variables are the usual way to inject configuration at deploy time; precedence is:

```
environment variable  >  config file  >  default
```

```python
class ServerConfig(ConfigBase):
    _path = 'config/server.enc'
    _cipher = AesGcmCipher()          # reads CONF_BASE_KEY when no key is given

    net = Section('Net')
    host = net.field(default='0.0.0.0', env_key='APP_HOST')
    port = net.field(default=8080, env_key='APP_PORT')
    debug = net.field(default=False, env_key='APP_DEBUG')
    db_pass = net.field(default='', env_key='APP_DB_PASS', read_only=True)
```

Environment variables are always strings; conf_base parses them according to the `default` type:

| Default type | Example value | Parsed result |
|---|---|---|
| `int` | `"8080"` | `8080` |
| `float` | `"0.5"` | `0.5` |
| `bool` | `"true"` / `"1"` / `"yes"` | `True` |
| `bool` | `"false"` / `"0"` / `"no"` | `False` |
| `list` | `'["10.0.0.1", "10.0.0.2"]'` | list (JSON) |
| `dict` | `'{"host": "db.local"}'` | dict (JSON) |
| `str` | `"hello"` | `"hello"` |

Parsing failures raise `ConfigValueError` immediately. `list` / `dict` must use JSON syntax, e.g.
`APP_HOSTS='["10.0.0.1","10.0.0.2"]'`.

Options with `default=None` have no type to infer from, so they do not support `env_key`; if the
variable is set, reading raises `ConfigValueError`.

Options overridden by an environment variable cannot be written back, which keeps deploy-time
values out of the file:

```python
ServerConfig.port.value = 9090   # ❌ WriteError: overridden by APP_PORT
ServerConfig.port.has_env_override   # True
```

## Storage formats and encryption

Storage is split into two orthogonal parts, configured by `_format` and `_cipher`:

```
write: dict --format.serialize--> text --cipher.encrypt--> file
read:  file --cipher.decrypt--> text --format.deserialize--> dict
```

| Class | Role | Description | Requires |
|---|---|---|---|
| `JsonFormat` | format | plain JSON, the default | none |
| `YamlFormat` | format | plain YAML, native layout | `conf_base[yaml]` |
| `TomlFormat` | format | plain TOML, native layout | `conf_base[toml]` |
| `NoCipher` | cipher | no encryption, the default | none |
| `SignedCipher` | cipher | plain text + HMAC-SHA256 signature: readable, not editable | none |
| `AesCipher` | cipher | AES-128-CBC + HMAC (Fernet) | `conf_base[aes]` |
| `AesGcmCipher` | cipher | AES-256-GCM (AEAD), recommended | `conf_base[aes]` |
| `ChaCha20Poly1305Cipher` | cipher | ChaCha20-Poly1305 (AEAD) | `conf_base[aes]` |

### Path, format and cipher

```python
from conf_base import AesGcmCipher, ConfigBase, Section, YamlFormat


class AppConfig(ConfigBase):
    _path = 'config/app.yaml'      # explicit path: used verbatim, never rewritten
    _format = YamlFormat()         # optional: inferred from the _path suffix
    _cipher = AesGcmCipher()       # encrypted and written to the same path

    s = Section('Server')
    port = s.field(default=8080)
```

- `_path` is used as given; when omitted it is generated from the class name as
  `{lowercase class name}{format suffix}{cipher suffix}`, e.g. `appconfig.json`, `appconfig.yaml.enc`
- `_format` is inferred from the suffix when omitted (`.json` / `.yaml` / `.yml` / `.toml`); the
  cipher suffix is stripped first, so `app.yaml.enc` is still treated as YAML; unknown suffixes
  fall back to `JsonFormat`
- A suffix that conflicts with an explicit format (e.g. `_path='app.yaml'` with `JsonFormat()`)
  raises `ValueError` at class creation
- `_cipher` defaults to `NoCipher`

| Declaration | Resulting file name |
|---|---|
| everything omitted | `appconfig.json` |
| `_format = YamlFormat()` | `appconfig.yaml` |
| `_format = YamlFormat()` + `_cipher = AesGcmCipher()` | `appconfig.yaml.enc` |
| `_path = 'app.conf'` | `app.conf` (unknown suffix, treated as JSON) |

The effective path (explicit or generated) is always available as `config_path`, so there is no
need to touch the underscore-prefixed `_path`:

```python
AppConfig.config_path        # 'config/app.yaml'
```

JSON / YAML / TOML validate data before writing and report impossible values clearly:

| Data | Behaviour |
|---|---|
| `tuple` | converted to `list` |
| non-string dict keys | `ConfigValueError` naming the location (JSON no longer stringifies keys silently) |
| `set` / `bytes` / custom objects | `ConfigValueError` |
| `None` | supported by JSON / YAML; `ConfigValueError` for TOML |
| `datetime` / `date` / `time` | native in YAML / TOML; `ConfigValueError` for JSON |

> The file is written in the selected format, but every save re-serializes from the in-memory dict,
> so hand-written comments and formatting are not preserved.

### Signatures (readable content, tamper-evident)

```python
_cipher = SignedCipher(key='signing-key')   # reads CONF_BASE_SIGN_KEY when key is omitted
```

The signature is appended as a comment line (`# conf_base-signature: v1:<hex>`), so no extra file
is created. On load the signature is verified before parsing; manual edits, a missing signature or
a wrong key all raise `DecryptError`.

### Encryption (invisible content, integrity checked)

```python
# AES-256-GCM; reads CONF_BASE_KEY when no key is given
_cipher = AesGcmCipher(key_id='v1')

# Devices without AES hardware acceleration
_cipher = ChaCha20Poly1305Cipher()

# Compatibility with existing data
_cipher = AesCipher(key='my-app-key')
```

AEAD ciphers use a fresh random nonce per write, so identical plaintext yields different ciphertext;
the envelope records the algorithm and `key_id`, and a wrong key, tampered ciphertext or mismatched
key version all fail to decrypt.

Key handling:

| Approach | How |
|---|---|
| Environment variable (recommended) | `AesGcmCipher()` with `CONF_BASE_KEY` |
| Secrets manager | `AesGcmCipher(key=vault.get('app/secret'))` |
| Hard-coded | local debugging only; never commit it |

### Custom formats and ciphers

Format and cipher are independent; subclass either one to plug in any storage:

```python
from typing import Any, Dict

from conf_base import BaseCipher, BaseFormat


class MyFormat(BaseFormat):
    extension = '.dat'

    def serialize(self, data: Dict[str, Any]) -> str:
        ...

    def deserialize(self, text: str) -> Dict[str, Any]:
        ...


class MyCipher(BaseCipher):
    extension = ''          # suffix appended to generated names; '' keeps the name unchanged

    def encrypt(self, text: str) -> str:
        ...

    def decrypt(self, text: str) -> str:
        ...


class AppConfig(ConfigBase):
    _format = MyFormat()
    _cipher = MyCipher()
```

## Schema migration

The config file records `_schema_version`; on startup, functions in `_migrate` upgrade old data to
the current structure:

```python
def migrate_v1_to_v2(data: dict) -> dict:
    """Rename bgm_volume to bgm"""
    setting = data.get('Setting', {})
    if 'bgm_volume' in setting:
        setting['bgm'] = setting.pop('bgm_volume')
    return data


class GameConfig(ConfigBase):
    _path = 'config/game.json'
    _schema_version = 2
    _migrate = {1: migrate_v1_to_v2}

    audio = Section('Audio')
    bgm = audio.field(default=1.0)
```

| Situation | Behaviour |
|---|---|
| Brand-new file | created at the target version |
| File version < target | migrations run in order, then the version is written back |
| File version = target | nothing happens |
| File version > target | `ValueError` at startup; the version is never downgraded |
| A migration step is missing | `ValueError` at startup |
| A migration returns a non-dict | `ValueError` at startup |

Options added after a migration do not need to be filled in by it — defaults are applied
automatically. Unknown sections / options in the file are preserved by default so hand-edited
content is not lost; set `_prune_unknown = True` to delete anything the code no longer declares.

> Deletion by `_prune_unknown` is irreversible. A `UserWarning` lists every removed `section.option`
> before it happens, so watch the startup log; if you keep hand-written fields, leave the switch off
> or back up the file first.

`_schema_version` is internal and is never exported by `to_dict()`.

## Concurrency and performance

**Thread safety**: a `threading.RLock` is always in effect.

**Multi-process**: with `filelock` installed, a file lock prevents processes from overwriting each
other's writes.

```python
class AppConfig(ConfigBase):
    _use_file_lock = False      # disable the lock (each process uses its own file)
    _lock_timeout = 30.0        # seconds to wait for the lock, 10 by default
```

**Reloading external edits**: by default the file is read once at class creation and everything
afterwards is served from memory. To pick up ops edits without a restart:

```python
class ServerConfig(ConfigBase):
    _path = 'config/server.json'
    _auto_reload = True         # compare the file fingerprint on read; reparse only when changed
```

Rough numbers (JSON file, ~300 bytes):

| Operation | Time |
|---|---|
| Single read | ~0.3 µs (memory only) |
| Single read with `auto_reload` | ~5 µs (includes the fingerprint check) |
| Single save | ~2 ms |
| `batch()` of three writes | ~2.3 ms |

Reads are effectively free and writes are disk-bound; batch hot paths with `batch()`.

> The fingerprint is `(mtime_ns, size)`. Filesystems with coarse timestamps (NTFS is ~15 ms) can
> report the same mtime for a just-written file, so a file is force-reparsed for 100 ms after a
> modification and the fingerprint cache resumes afterwards.

## Web backend integration

A config class is a module-level singleton: loading, migration and defaults all happen at class
creation, so an import failure is a startup failure and no extra init hook is needed.

```python
# config.py
from conf_base import ConfigBase, Section


class AppConfig(ConfigBase):
    _path = 'config/app.json'
    _auto_reload = True                 # ops edits take effect on the next read

    server = Section('Server')
    host = server.field(default='0.0.0.0', env_key='APP_HOST')
    port = server.field(default=8000, env_key='APP_PORT')

    db = Section('DB')
    url = db.field(default='sqlite:///app.db', env_key='APP_DB_URL', read_only=True)
```

```python
# main.py
from typing import Dict

from fastapi import FastAPI

from config import AppConfig

app = FastAPI()


@app.get('/health')
def health() -> Dict[str, int]:
    return {'port': AppConfig.port.value}
```

When you need to inject the class (e.g. to swap it in tests), add a dependency:

```python
from typing import Type

from fastapi import Depends


def get_config() -> Type[AppConfig]:
    return AppConfig


@app.get('/health')
def health(config: Type[AppConfig] = Depends(get_config)) -> Dict[str, int]:
    return {'port': config.port.value}
```

For Flask, a one-shot snapshot is the simplest approach:

```python
from flask import Flask

from config import AppConfig

app = Flask(__name__)
app.config.update(AppConfig.to_dict())   # copies current values once; no live link afterwards
```

Notes:

- **Take one snapshot per request.** `_auto_reload` performs a fingerprint check on every `.value`
  read (~5 µs). When a request needs several options, do `snapshot = AppConfig.to_dict()` once
  instead of reading in a loop.
- **`.env` is loaded externally.** conf_base only reads `os.environ` and never parses `.env` files.
  Use `python-dotenv`'s `load_dotenv()` locally and container env vars in production. Environment
  variables are read live, but a process that is already running will not observe later injections.
- **Each worker keeps its own copy** (`uvicorn --workers`, gunicorn). The file lock prevents
  corruption, **not** merging of concurrent writes. Keep web config read-mostly, and write through a
  single process or a dedicated admin endpoint.
- **Flask's `app.config.update()` copies once**, so later changes to `AppConfig` do not reach
  `app.config` and vice versa.

## Relationship to pydantic / pydantic-settings

They solve different problems and are not substitutes for each other (see "How it compares" above
for the wider table):

| | conf_base | pydantic-settings |
|---|---|---|
| Modelling | type inferred from `default` + descriptors | type annotations + validators |
| Data source | file first (env > file > default) | env first; files must be wired in |
| Writes back to file | yes (saved as soon as validation passes) | no |
| Encryption / signing / migration | built in | none |

Interop is two explicit conversions:

```python
from pydantic import BaseModel


class ServerModel(BaseModel):
    host: str
    port: int


# conf_base -> pydantic: validated again by the model rules
server = ServerModel(**AppConfig.server.current_options)

# pydantic -> conf_base: written field by field, still checked by conf_base
AppConfig.server.update(**server.model_dump())
```

`Section.update()` raises `ConfigKeyError` for fields the model has but the section does not, rather
than ignoring them silently.

Automatic two-way bridging is not recommended: pydantic-settings prioritizes environment variables
and supports arbitrary nesting, while conf_base persists to a file and carries encryption and
migration. The semantics are not equivalent, so automatic mapping necessarily loses information.
In a pydantic codebase, the recommended split is: **pydantic for request/response and domain
models, conf_base for the persisted configuration.**

## Exceptions

All runtime configuration errors inherit from `ConfBaseError` and can be caught together:

```python
import conf_base.error as E

try:
    GameConfig.width.value = -1
except E.ConfBaseError as exc:
    print(f'config error: {exc}')
```

| Exception | Raised when |
|---|---|
| `ConfBaseError` | base class of every framework exception |
| `ConfigTypeError` | a write's type differs from the default's type |
| `ConfigValueError` | validator fails, validator raises, env var cannot be parsed, or a format cannot express a value |
| `WriteError` | writing a read-only option, writing an env-overridden option, or assigning to a section attribute |
| `ConfigKeyError` | the section / option does not exist (also a `KeyError`) |
| `ParseError` | the config file is corrupt and cannot be parsed |
| `DecryptError` | decryption or signature verification fails, or the file was tampered with |
| `SchemaError` | `_schema_version` is above the code's target, or a migration is missing / returns a non-dict (also a `ValueError`) |
| `LockError` | waiting for the multi-process file lock timed out (also a `TimeoutError`) |

During loading, decryption / signature failures raise `DecryptError` directly; other read or parse
problems are wrapped in `ParseError`. The original exception is kept in `__cause__`.

Declaration-time mistakes (e.g. `_format` is not a `BaseFormat`, or a path suffix conflicts with
the format) still raise plain `TypeError` / `ValueError`.

## API reference

### ConfigBase

> A config class must inherit `ConfigBase` **directly**. `class Child(SomeConfig)` raises
> `TypeError` at class creation: option descriptors and the `ConfigFile` are class-level bindings,
> so inheritance would make parent and child share one dataset.

| Member | Description |
|---|---|
| `_path` | config file path; generated from the class name when omitted |
| `_format` | `JsonFormat` / `YamlFormat` / `TomlFormat`; inferred from the path suffix when omitted |
| `_cipher` | cipher; `NoCipher` when omitted |
| `_auto_reload` | check the file fingerprint on read and reload when it changed; default `False` |
| `_prune_unknown` | delete sections / options the code no longer declares at startup; default `False` (keep); a `UserWarning` lists the removed keys |
| `_use_file_lock` / `_lock_timeout` | process-lock switch and timeout; default `True` / `10.0` |
| `_schema_version` / `_migrate` | target version and migration functions |
| `to_dict()` | deep copy of the whole configuration |
| `config_path` | effective config file path (read-only, injected; equals `_path`, or the generated name when `_path` is omitted) |
| `config_node` | registered sections → option names |

### Section

| Member | Description |
|---|---|
| `field(default='', option=None, validator=None, read_only=False, env_key=None)` | declare an option; `option` defaults to the attribute name |
| `update(**kwargs)` | update several options in one write |
| `batch()` | context manager that writes once on exit |
| `reset()` | reset every option in this section |
| `current_options` / `default_options` | dict of current values / defaults |
| `section['key']` / `section.key` | read one option (returns the **current value**, not a proxy) |
| `'key' in section` | whether the option exists |

> Read and write through `Config.option`, e.g. `CliConfig.theme.value = 'light'`.
> `CliConfig.general.theme` already returns the current value (`str`), so adding `.value` raises
> `AttributeError`; only `Config.theme` is the proxy with `.value` / `.toggle()` and friends.

### Option proxies

| Member | Description |
|---|---|
| `.value` | current value, readable and writable |
| `.set_value(value)` | write a value |
| `.default` | default value (read-only) |
| `.reset()` | restore the default |
| `.is_default` | whether the current value equals the default |
| `.on_change(callback)` | register a change callback; usable as a decorator |
| `.section` / `.option` | owning section and option name |
| `.has_env_override` / `.env_key` | whether an env var overrides it / the variable name |

## Project layout

```
conf_base/
├── __init__.py       # public exports
├── config_base.py    # ConfigBase bootstrap
├── config_file.py    # file IO + batched writes
├── format.py         # JsonFormat / YamlFormat / TomlFormat
├── cipher.py         # NoCipher / SignedCipher / AesCipher / AEAD
├── descriptor.py     # ConfigProperty + typed proxies
├── section.py        # Section blocks
└── error.py          # unified exception hierarchy
```

## Tests and CI

164 tests, 88% total coverage. Locally:

```bash
pip install -e .[dev]
python -m pytest test/ -v --cov=conf_base
python -m mypy conf_base
```

GitHub Actions runs the Python 3.8–3.14 matrix, strict `mypy` and a packaging check on every push
and pull request.

## Contributing

- Bug reports and feature requests: use the [issue templates](.github/ISSUE_TEMPLATE)
- Code changes: read [CONTRIBUTING.md](CONTRIBUTING.md) first
- Not sure where to start: pick a `good first issue` from [ROADMAP.md](ROADMAP.md)
- The primary repository is on GitHub ([DashSalter/conf_base](https://github.com/DashSalter/conf_base));
  Gitee ([kuangjianke/conf_base](https://gitee.com/kuangjianke/conf_base)) is a mirror

## License

MIT License
