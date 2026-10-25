# 并发与性能

## 一次写入发生了什么

```
校验 → 修改内存 → 序列化 → 加密 → 写临时文件 → os.replace 原子替换
```

写盘走「临时文件 + `os.replace`」，所以读者永远看不到写了一半的文件：要么是旧内容，要么是新内容。

在 Windows 上，目标文件被其他进程短暂占用时 `os.replace` 会报 `PermissionError`；框架会自动重试 5 次再放弃。

## 批量写入 `batch()`

默认情况下**每次赋值都会落盘**。连续改十个字段就是十次写盘 + 十次序列化。

```python
with AppConfig.server.batch():
    AppConfig.host.value = '0.0.0.0'
    AppConfig.port.value = 8000
    AppConfig.debug.value = True
# 到这里才真正写一次盘
```

### 保存点语义

`batch()` 不是简单的「延迟写」——它带保存点：

```python
with AppConfig.server.batch():
    AppConfig.port.value = 8000
    AppConfig.port.value = 999999        # 抛 ConfigValueError
# 抛异常后整块回滚：port 仍然是旧值，磁盘没被动过
```

嵌套时内层只回滚内层：

```python
with AppConfig.server.batch():
    AppConfig.host.value = '0.0.0.0'
    try:
        with AppConfig.server.batch():
            AppConfig.port.value = '非法'   # 内层失败
    except ConfigTypeError:
        pass                                  # 吞掉内层异常
    AppConfig.port.value = 9000              # 外层继续，最终落盘
```

### 什么时候值得用

| 场景 | 建议 |
|---|---|
| 一次改 1–2 个字段 | 直接用 `.value =` |
| 一次改多个相关字段（要么全成要么全不成） | `batch()` |
| 循环里逐个写 | 必须 `batch()`，否则 N 次写盘 |

## 事务 `transaction()`

`transaction()` 提供的是**可重入的独占锁**，用于「读—改—写」序列不被同进程其他线程打断：

```python
with AppConfig.server.transaction():
    current = AppConfig.port.value
    AppConfig.port.value = current + 1
```

和 `batch()` 的区别：

| | `batch()` | `transaction()` |
|---|---|---|
| 目的 | 合并写盘 | 保护临界区 |
| 留内存 | 是，退出时统一落盘 | 否，写入立即落盘 |
| 异常 | 回滚本层修改 | 不回滚（已落盘的保持） |
| 可嵌套 | 是，保存点语义 | 是，同线程可重入 |

两者可以叠加：

```python
with AppConfig.server.transaction():
    with AppConfig.server.batch():
        ...
```

## 多进程文件锁

同进程用 `RLock` 就够；多进程同时写同一个文件时，装上 `filelock` 并开启：

```bash
pip install "conf-base[filelock]"
```

```python
class AppConfig(ConfigBase):
    _path = 'app.json'
    _use_file_lock = True          # 默认开启（装了 filelock 时）
    _lock_timeout = 10.0           # 等锁超时，秒
```

等锁超时抛 `LockError`（同时是 `TimeoutError`）。

!!! note "默认行为"
    装了 `filelock` 就默认加锁；没装则静默跳过，不会报错。同一进程内的线程安全由 `RLock` 保证，与 `filelock` 无关。

## 热重载 `_auto_reload`

默认情况下配置在类创建时读入内存，之后不再看磁盘。开了热重载后，每次读取都会检查文件指纹：

```python
class AppConfig(ConfigBase):
    _path = 'app.json'
    _auto_reload = True
```

判断依据是 `(mtime_ns, size)` 二元组：

- 指纹没变 → 直接用内存值，不读盘
- 指纹变了 → 重新加载并触发 `on_change`

文件系统时间戳精度有限（Windows 上约 100ms），框架对「时间戳可疑窗口」内的大小变化做了额外判断，避免同一毫秒内的两次写入被漏掉。

热重载适合「配置文件会被外部工具修改」的场景；不适合高频写入的文件，因为每次读都要 `stat()`。

## 性能参考

以下是同一台机器上的相对开销（Python 3.12，JSON + 无加密）：

| 操作 | 大致耗时 |
|---|---|
| 读一个已缓存的值 | 纳秒级，等同于属性访问 |
| 改一个值（含落盘） | 约 1ms 量级，取决于磁盘 |
| `batch()` 内改 50 个值 | 与改 1 个值同量级，只落盘一次 |
| 全量重载（1KB JSON） | 约数百微秒 |

**结论**：conf_base 适合启动时读、运行中偶尔改的配置。如果你的场景是每秒写入，说明配置应该换成数据库。

完整的 `benchmark/` 对比脚本还没有（见 [路线图](https://github.com/DashSalter/conf_base/blob/master/ROADMAP.md)）。
