# 路线图

本文件说明 conf_base 已经做到哪、接下来想做什么、以及明确不做什么。
**它是一份公开承诺的边界，不是发布日期表**；具体进度以 issue 和 commit 为准。

## 已经具备（0.4.x）

- `ConfigBase` + `Section` + `field()` 的声明式配置类，值为默认值的类型
- 三种明文格式：JSON / YAML / TOML，按文件后缀自动推断
- 五种加密器：`NoCipher` / `SignedCipher` / `AesCipher` / `AesGcmCipher` / `ChaCha20Poly1305Cipher`
- 环境变量覆盖（`env_key`），且被覆盖项禁止回写
- `batch()` 批量落盘与保存点回滚、`transaction()` 独占锁
- Schema 版本迁移链（`_schema_version` + `_migrate`）
- `_auto_reload` 指纹热重载、原子写入、Windows 写入重试
- 类型代理语义化方法（`toggle` / `increment` / `append` / ...）、`on_change` 回调
- 114 个测试用例、mypy strict、Python 3.8–3.14 CI 矩阵
- `examples/` 三个可直接运行的示例（CLI / 游戏 / 加密服务端）
- 中英双语文档：`README.md` 与 `README.en.md`
- `config_path` 公开路径接口，`to_dict()` 带静态类型签名

## 下一步（0.5.x）

按优先级排列，欢迎认领：

1. **文档站**：以 `docs/` 组织 API 参考 + 使用指南（mkdocs-material 或 Sphinx 均可）
2. **内置校验器集合**：`in_range` / `is_url` / `is_path` / `matches` 等常用 `validator` 工具函数
3. **性能基准脚本**：用 `benchmark/` 对比 conf_base 与 python-dotenv / dynaconf 的读取开销，给出可复现数字
4. **覆盖率提升**：从 87% 提到 92% 以上，优先补加密器与迁移分支
5. **英文文档同步机制**：在 CI 里加一个检查，中文 README 变动时提醒同步 `README.en.md`

## 候选 / 讨论中

以下想法尚未定案，想推进请先开 issue：

- `BaseFormat` 的第三方注册入口（让下游不需要改 conf_base 源码就能加格式）
- 内置配置项热加载钩子（文件变更时触发 `on_change`）
- 只读配置视图（`read_only_view()`，供业务层防误写）
- 更细的锁策略（读写分离的 `SharedLock`）

## 明确不做

这些边界写在这里，是为了避免反复讨论：

- 远程 / 分布式配置中心、多节点实时同步（请用 Nacos / Apollo / Consul / etcd）
- Redis / MySQL 等远程存储后端（如需要，自行实现 `BaseFormat` / `BaseCipher` 适配）
- 每秒级高频写入场景（请用数据库）
- 多用户并发编辑同一文件（请用数据库 + 乐观锁）
- 配置类之间的相互继承（架构上禁止）
- 取代 pydantic 做复杂嵌套模型与字段级校验

## 好上手的任务（good first issue）

适合第一次参与的开源贡献，难度由低到高：

| # | 任务 | 难度 | 备注 |
|---|---|---|---|
| 1 | 写 `examples/` 下的三个最小示例 | 低 | 直接参考 README 快速开始，跑通即可 |
| 2 | `.gitee/ISSUE_TEMPLATE` 与 `.github` 对齐 | 低 | Gitee 侧目前没有 issue 模板 |
| 3 | 给五个加密器补「什么时候用哪个」对照表与迁移示例 | 低 | 加在 README 或新文档里 |
| 4 | 统一文档中「不支持 / 未来计划」的标注方式 | 低 | 现在分散在 README 与 CHANGELOG |
| 5 | 补 `test/` 未覆盖分支，覆盖率提到 92% | 中 | 先跑 `--cov-report=term-missing` 看缺口 |
| 6 | 写 `benchmark/` 对比脚本并给出数字 | 中 | 结论要可复现，注明硬件与 Python 版本 |
| 7 | 英文 README | 中 | 与中文版逐节对齐 |

参与方式见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。想认领某个任务，直接在 issue 里留言即可，不用等分配。

## 标签约定

| 标签 | 含义 |
|---|---|
| `good first issue` | 适合新手，有明确验收标准 |
| `help wanted` | 维护者欢迎外部实现 |
| `docs` | 纯文档改动 |
| `enhancement` | 新功能 |
| `bug` | 缺陷 |
| `breaking` | 需要主版本号变更的改动 |
