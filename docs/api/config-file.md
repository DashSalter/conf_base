# ConfigFile

`ConfigFile` 是存储层：负责「dict ↔ 文本 ↔ 文件」的往返，以及迁移、批量写入、并发控制。`ConfigBase` 在类创建时实例化它并绑定到描述符上。

一般不需要直接用 `ConfigFile`。需要它的场景只有两种：自己实现 `ConfigBase` 的等价物，或者写测试替身。

## 一次读写

```python
from conf_base import ConfigFile, JsonFormat

cf = ConfigFile('demo.json', format=JsonFormat())   # 构造时自动 load_config()
cf.get_option('Server', 'port', 8080)               # 第三个参数是缺省值
cf.set_option('Server', 'port', 9000)               # 立即落盘
cf.to_dict()                                        # {'Server': {'port': 9000}}
cf.del_option('Server', 'workers')
cf.del_section('Cache')
```

## 写入是原子的

`write_config()` 的流程：

1. 序列化成文本
2. 需要时加密
3. 写到同目录的临时文件
4. `os.replace(tmp, target)` 原子替换

所以读者永远看不到写了一半的文件。Windows 上目标被占用时 `os.replace` 会抛 `PermissionError`，框架自动重试 5 次。

## 批量与事务

```python
with cf.batch():          # 只写内存，退出时一次落盘；异常整块回滚
    cf.set_option('Server', 'port', 8000)
    cf.set_option('Server', 'workers', 8)

with cf.transaction():    # 可重入独占锁，保护「读—改—写」
    ...
```

`batch()` 带保存点：嵌套时内层失败只回滚内层。

## 迁移

`load()` 时比较文件里的 `_schema_version` 与代码里的：

| 情况 | 行为 |
|---|---|
| 相等 | 什么都不做 |
| 文件更低 | 依次执行 `_migrate` 链，成功后回写文件 |
| 文件更高 | 抛 `SchemaError` |

迁移函数抛出的异常原样冒泡，且此时不落盘，原文件保持不变。

## 热重载

`_auto_reload = True` 时，每次读取前用 `(mtime_ns, size)` 指纹比对磁盘文件，变了就重新加载。Windows 的文件时间戳精度约 100ms，框架对「可疑窗口」内的大小变化做了额外判断。

## 多进程锁

装了 `filelock` 且 `_use_file_lock = True` 时，写操作会先拿文件锁；等锁超时抛 `LockError`。

同一进程内的线程安全由 `threading.RLock` 保证，与 `filelock` 无关——没装 `filelock` 也不会出现同进程写坏。

## API

::: conf_base.ConfigFile
