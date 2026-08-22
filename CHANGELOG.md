# Changelog
由于本变更日志首次创建于项目版本`v1.3.0`，且距离上次提交版本`v1.2.6`有相当长一段时间，所以暂时仅记载了包括`v1.3.0`开始的所有变更，其余旧日志请自行查询本仓库的[Commits](https://github.com/SumaRoder/SecPluginPySdk/commits)。

## [v1.3.1] - 2026-08-22
### ✨ New Features | 新增功能
- [plugin.py](src/secplugin/plugin.py) 装饰器`on_msg`支持设置当前 handler 的并发策略。`ConcurrencyMode`可选`SYNC`(同步阻塞执行)、`ASYNC`(默认。无限制执行)，以及`POOL`(最多`max_concurrent`个并发)
- [plugin.py](src/secplugin/plugin.py) 装饰器`on_msg`支持设置当前 handler 的顺序策略。`ordered`为`True`时顺序执行，反之亦反
- [plugin.py](src/secplugin/plugin.py) 对于指令`Heartbeat`新增处理器`on_heartbeat_msg_handler`
- [cmd.py](src/secplugin/cmd.py) 指令集新增`Sync`
- [__init__.py](src/secplugin/__init__.py) 添加导出项`ConcurrencyMode`
### 🐛 Bug Fixes | Bug修复
- 无
### ⚡ Performance Improvements | 性能改进
- 无
### ⏪ Changes | 变更
- [pyproject.toml](pyproject.toml) `setuptools`变更为更现代的`hatchling`
- [pyproject.toml](pyproject.toml) `optional-dependencies`(可选依赖)中的`colorlog`与`watchdog`已合并到`dependencies`(依赖)
- [cmd.py](src/secplugin/cmd.py) 删除过时的指令`SyncOicq`以及函数`authenticate`
### 📝 Documentation | 文档
- 无

## [v1.3.0] - 2026-08-22
### ✨ New Features | 新增功能
- 装饰器`on_msg`支持设置当前 handler 的并发策略（目前支持不完整，请待下个版本）
### 🐛 Bug Fixes | Bug修复
- 修复 handler 执行出现异常时默认忽略的问题
### ⚡ Performance Improvements | 性能改进
- 无
### ⏪ Changes | 变更
- 无
### 📝 Documentation | 文档
- 无
