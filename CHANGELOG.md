# Changelog

所有版本变更记录在此文件中维护。

格式参考：[Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)

---

## [Unreleased]

### 新增

- **存储层拆分为格式与加密两个正交抽象**：`BaseFormat` 负责 `dict ↔ 文本`，`BaseCipher` 负责 `文本 ↔ 文本`
- `JsonFormat` / `YamlFormat` / `TomlFormat`：明文格式实现，按原生格式落盘
- `NoCipher`：默认不加密，原样读写
- `AesGcmCipher`：AES-256-GCM（AEAD）加密器，企业级首选，机密性与完整性一体
- `ChaCha20Poly1305Cipher`：ChaCha20-Poly1305（AEAD）加密器，适合无 AES 硬件加速的设备
- `SignedCipher`：HMAC-SHA256 完整性签名，内容保持明文可读，签名附加在文件末尾
- AEAD 加密器支持 `key_env` 环境变量注入密钥、`key_id` 密钥版本标识
- **新增 `ConfigFile(path, format, cipher)`**：统一文件读写、批量落盘、schema 迁移与并发防护入口
- 新增 `DecryptError` 异常，统一表示解密失败 / 签名校验失败 / 文件被篡改
- **新增 `ConfigBase` 入口**：`class C(ConfigBase)` 即可声明配置，普通类继承、无元类，对新用户更熟悉、更易读
- **`Section.field()` 替代 `Section.add()`**：统一显式写法 `width = screen.field(default=1280)`；`option` 省略时自动使用左侧类属性名，需要不同键名时传 `option='listen_port'`
- 新增 `SchemaError` / `ConfigKeyError` / `LockError` 异常，分别表示 schema 迁移错误、配置项不存在、文件锁超时，均继承 `ConfBaseError` 并兼容对应的内建异常
- 配置项声明时自动深拷贝 `list` / `dict` 默认值，多个配置项可安全复用同一默认值常量

### 变更（破坏性）

- **`_crypto` 拆分为 `_path` / `_format` / `_cipher`**：路径、格式、加密分别声明；`_path` 原样使用，未指定时按类名生成 `{类名小写}{格式后缀}{加密后缀}`
- **移除 `Crypto` 基类**：格式与加密拆分为 `BaseFormat` 与 `BaseCipher`，两者通过文本衔接，可自由组合
- **`JsonConfig` 更名为 `ConfigFile`**：构造签名改为 `ConfigFile(path, format=None, cipher=None)`
- **加密器更名**：`AesCrypto` → `AesCipher`，`AesGcmCrypto` → `AesGcmCipher`，`ChaCha20Poly1305Crypto` → `ChaCha20Poly1305Cipher`
- **格式类更名**：`PlainJson` → `JsonFormat`，`PlainYaml` → `YamlFormat`，`PlainToml` → `TomlFormat`
- **`SignedCrypto` → `SignedCipher`**：签名由独立的 `.sig` 文件改为文件末尾注释行，不再产生附属文件
- 加密器接口改为文本级：`encrypt(text: str) -> str` / `decrypt(text: str) -> str`，不再直接处理 dict
- 加载阶段的解密 / 签名失败直接抛 `DecryptError`，不再统一包装为 `ParseError`
- **`AesCipher` 移除 `ttl_seconds` 参数**：Fernet 的 ttl 依赖明文内嵌时间戳，行为不稳定且未测试；长期存储请使用带 `key_id` 的 AEAD 加密器
- **移除未使用的 `ConfigFile.reset_section()`**：重置请使用 `Section.reset()`
- **移除 `ConfigMeta` 元类入口**：统一使用 `class C(ConfigBase)` 声明配置类；`conf_base/metaclass.py` 更名为 `conf_base/config_base.py`
- **移除 `XorCrypto`**：XOR + Base64 仅为混淆，不提供安全保证。请迁移到 `SignedCipher`（需保留明文）或 `AesGcmCipher`（需加密）
- **移除多 section 切换**：`Section` 只接受一个 section 名，删除 `set_use_section()`、`section_tuple` 与 `ConfigProperty.set_section()`。同一格式需要多份数据时，请定义多个独立 Section（如 `Section('Level')`、`Section('Level2')`）
- `on_change()` 移除 `section` 过滤参数；回调签名仍为 `callback(section, option, value)`
- **模块 `conf_base/Error.py` 更名为 `conf_base/error.py`**：符合 PEP 8 模块命名，避免大小写敏感文件系统下的导入不一致
- **配置类禁止相互继承**：`class Child(SomeConfig)` 在类创建时直接抛 `TypeError`。配置项描述符与 `ConfigFile` 都是类级绑定，继承会导致父子类共享同一份配置数据或子类停留在半初始化状态
- **直接给 Section 属性赋值改为抛 `WriteError`**：`section.width = 1600` 此前会静默创建实例属性并遮蔽配置项，现在必须使用 `section['width'] = 1600` 或 `section.width.value = 1600`
- **JSON 非字符串字典键改为报错**：此前 `json.dumps({1: 'a'})` 会静默转成 `{"1": "a"}`，现在与 YAML / TOML 一致抛 `ConfigValueError`
- **带加密后缀的路径可正确推断格式**：`app.yaml.enc` 现在按 YAML 处理，此前会静默退回 JSON
- 迁移版本冲突 / 迁移缺失 / 迁移返回非字典改抛 `SchemaError`，缺失配置项改抛 `ConfigKeyError`，文件锁超时改抛 `LockError`，均可通过 `except ConfBaseError` 捕获

### 修复

- `auto_reload` 不再覆盖尚未落盘的修改：`_dirty` 为真或处于 `batch()` 中时跳过重载。此前在 batch 块内读取其他配置项会触发重新加载，把本批已写但未提交的值丢弃，并在退出时落盘旧数据
- 默认值不再被配置数据共享引用：声明时深拷贝，`set_option` / `get_option` 写入容器时同样拷贝。此前直接修改 `.value` 返回的 list/dict 会同时污染默认值，导致 `reset()` 静默无效
- `default_options` 返回深拷贝，修改返回值不再影响内部默认值
- `Section.update()` 传入 `PropertyProxy` 时写入其当前值，与 `C.option = proxy` 行为一致
- `batch()` 现在具备保存点语义：块内抛异常时恢复进入前的配置快照，不会把半批修改落盘；嵌套时每层各自保存快照，内层异常只回滚内层修改（即使异常被内层调用方吞掉），外层修改照常提交
- 类型代理的读改写操作（`append`/`update`/`pop`/`toggle`/`increment`/`setdefault` 等）整体持有线程锁，多线程并发修改不再丢失更新
- 环境变量解析抛出的非 `ValueError` 异常（如 `datetime` 收到字符串）统一包装为 `ConfigValueError`，不再裸抛 `TypeError`
- `_prune_unknown` 清理时跳过所有下划线开头的内部字段，与 `to_dict()` 的过滤规则保持一致
- `reset()`（单项或整个 Section）改为走完整的 `set_value` 流程：环境变量覆盖与 `read_only` 不再被绕过，校验失败时 Section 重置整体回滚
- 配置文件中 section 被手写成标量时抛出 `ParseError` 并指出位置，不再在类创建阶段抛出难以理解的 `TypeError`
- JSON 序列化失败（如写入 `set`）统一包装为 `ConfigValueError`，与 YAML / TOML 的错误类型一致
- 文件 `_schema_version` 高于代码目标版本时抛出 `ValueError`，不再静默把版本号降级写回；迁移函数返回非字典同样报错
- 写入值与当前值相同时跳过落盘，避免无意义的磁盘 I/O
- 迁移失败时不再缓存文件指纹，下次读取会重新加载而不是误用半迁移的内存数据
- 修复 `auto_reload` 在时间戳精度较低的文件系统上漏检：文件刚被改写时 `(mtime_ns, size)` 指纹可能与上次完全相同，现在文件修改后的 100ms 内强制重读，避免读到旧配置
- validator 自身抛出的异常统一包装为 `ConfigValueError`，原始异常保存在 `__cause__`，不再以未处理异常的形式传播到业务代码
- `dict` / `list` 的子类（如 `OrderedDict`）写入时自动归一化为基础容器，不再被类型校验拒绝；标量仍要求类型严格相等，避免 `bool` 被当作 `int`
- `PropertyProxy` 与非代理对象比较时改为比较实际值，`Config.port == 8080` 不再静默返回 `False`
- 启动时不再静默删除文件中未知的 section / option，新增 `_prune_unknown = True` 可按需开启严格同步
- Windows 下 `os.replace` 被杀毒软件或索引服务短暂占用导致 `PermissionError` 时自动重试，避免随机写入失败
- `_auto_reload` 改为先比对文件指纹（mtime + size），文件未变化时跳过文件锁与解析，单次读取从约 0.8 ms 降至约 5 µs
- `section['key']` / `section.key` 现在与 `.value` 一致地应用环境变量覆盖
- 同一 Section 内重复添加同名 option 现在会立即抛出 `ValueError`（此前会静默覆盖默认值，导致两个属性指向同一存储位置）

---

## [v0.0.7] - 2026-10-20

### 新增

- 环境变量覆盖功能：`env_key` 参数支持 `环境变量 > 配置文件 > 默认值` 优先级链
- 类型自动解析：bool/int/float/list/dict/str 自动从字符串转换
- 环境变量覆盖的值禁止回写配置文件（`WriteError`）
- `has_env_override` / `env_key` 属性检测环境变量覆盖
- Schema 版本迁移：`_schema_version` + `_migrate` 字典实现配置文件自动升级
- 链式多版本迁移：v1→v2→v3 自动执行迁移函数链
- 缺失迁移函数启动即报错（`ValueError`）
- 配置文件锁（可选）：`filelock` 支持多进程共享配置文件
- `_use_file_lock` / `_lock_timeout` 类属性控制文件锁
- 锁超时抛 `TimeoutError`，等待配置文件解锁
- Section 级 `update(**kwargs)` 批量写入（自动合并为单次落盘）
- Section 级 `reset()` 批量重置所有配置项（含多 section）
- 多配置类隔离：移除全局单例，每个配置类独立 `JsonConfig` 和配置文件
- 损坏配置文件明确报 `ParseError`，不再抛原始 JSON 异常
- 统一异常基类 `ConfBaseError`，所有框架异常继承它
- `ConfigTypeError` / `ConfigValueError` / `WriteError` 具体异常类
- `Section.current_options` / `default_options` 批量读取字典
- `str(section)` 显示当前值（多 section 全部分开显示）
- `section['option']` 改为返回当前值（之前返回默认值）
- `on_change` 变更通知：支持普通调用、装饰器、按 section 过滤
- 类型代理：`BoolProxy.toggle()` / `NumberProxy.increment()` / ListProxy / DictProxy
- ListProxy：append/extend/insert/remove/pop/clear/sort/reverse/`__setitem__`/`__delitem__`
- DictProxy：`__setitem__`/`__delitem__`/pop/update/setdefault/clear/get/keys/values/items
- 批量落盘：`batch()` 上下文管理器，N 次修改 1 次落盘
- 配置类级 `to_dict()` 全量导出深拷贝（过滤 `_schema_version` 等内部字段）
- `add()` 新增 `validator` 自定义校验函数
- `section['option']` 返回当前值、`'option' in section` 判断存在
- `setup.py` extras_require：filelock 可选依赖

### 重构

- 移除 `fix_type` 参数，配置值类型始终锁定为 default 的类型
- 移除全局单例 `SingletonMeta`，改为每个配置类独立实例
- `Crypto` 基类 `file_path` 改为实例属性
- `XorCrypto` / `PlainJson` 合并为统一框架
- 清理 metaclass 中已废弃的配置项（section/option 删除即生效）

---

##  - 2026-10-11

### 新增

- validator 自定义校验函数
- 默认值自动落盘（首次启动写入缺失项）
- ConfigMeta 清理废弃 section/option（代码删除即生效）

---

##  - 2026-10-10

### 新增

- Section 多配置块切换：`set_use_section('Level2')`
- `read_only` 只读配置项
- `auto_reload` 外部修改自动重载

---

##  - 2026-10-09

### 新增

- PlainJson / XorCrypto 加解密器
- 原子文件写入（临时文件 + os.replace）
- `threading.RLock` 线程安全

---

##  - 2026-09-25

### 初始版本

- 声明式配置框架
- ConfigMeta 元类
- Section / ConfigProperty / PropertyProxy
