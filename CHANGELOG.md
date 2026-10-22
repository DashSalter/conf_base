# Changelog

所有版本变更记录在此文件中维护。

格式参考：[Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)

---

## [Unreleased]

### 新增

- `AesGcmCrypto`：AES-256-GCM（AEAD）加密器，企业级首选，机密性与完整性一体
- `ChaCha20Poly1305Crypto`：ChaCha20-Poly1305（AEAD）加密器，适合无 AES 硬件加速的设备
- `SignedCrypto`：HMAC-SHA256 完整性签名包装器，可为 PlainJson/Yaml/Toml 提供防篡改校验
- AEAD 加密器支持 `key_env` 环境变量注入密钥、`key_id` 密钥版本标识
- 新增 `DecryptError` 异常，统一表示解密失败 / 签名校验失败 / 文件被篡改

### 变更（破坏性）

- **移除 `XorCrypto`**：XOR + Base64 仅为混淆，不提供安全保证。请迁移到 `SignedCrypto`（需保留明文）或 `AesGcmCrypto`（需加密）
- **移除多 section 切换**：`Section` 只接受一个 section 名，删除 `set_use_section()`、`section_tuple` 与 `ConfigProperty.set_section()`。同一格式需要多份数据时，请定义多个独立 Section（如 `Section('Level')`、`Section('Level2')`）
- `on_change()` 移除 `section` 过滤参数；回调签名仍为 `callback(section, option, value)`

### 修复

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
