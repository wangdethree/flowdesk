# Day 9：环境变量配置

## 今天完成了什么

- 新增环境变量读取工具：`config/env.py`。
- 支持读取字符串、布尔值和列表型环境变量。
- 将 `SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS` 接入环境变量。
- 新增 `.env.example` 示例配置文件。
- 补充环境变量工具测试。

## 为什么需要环境变量？

不同环境的配置通常不一样：

- 本地开发可以打开 `DEBUG`。
- 测试环境可能使用测试域名。
- 生产环境必须关闭 `DEBUG`。
- 生产环境的 `SECRET_KEY` 不能提交到代码仓库。

如果这些配置都写死在 `settings.py` 里，代码就很难安全部署，也容易把敏感信息提交到 GitHub。

## 当前支持的环境变量

| 变量 | 作用 | 示例 |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django 密钥 | `replace-me-with-a-random-secret-key` |
| `DJANGO_DEBUG` | 是否开启调试模式 | `true` 或 `false` |
| `DJANGO_ALLOWED_HOSTS` | 允许访问的域名或 IP | `localhost,127.0.0.1` |
| `SQLITE_DATABASE_PATH` | SQLite 数据库文件路径 | `db.sqlite3` |

## 本地使用方式

复制示例文件：

```bash
cp .env.example .env
```

当前项目暂时没有自动加载 `.env` 文件，后续 Docker 或部署阶段会继续完善。

现在本地运行时，如果没有设置环境变量，项目会使用开发默认值，保证你可以直接启动。

## 为什么 `.env` 不能提交？

`.env` 里通常会放真实密钥、数据库密码、第三方 API Key 等敏感信息。

所以 `.gitignore` 里忽略了 `.env`，只提交 `.env.example`。  
`.env.example` 只展示需要哪些配置，不保存真实密钥。

## 核心概念

### 什么是环境变量？

环境变量是操作系统或运行环境提供给程序的配置项。程序启动时读取这些值，用来决定运行行为。

### 为什么 `DEBUG=false` 需要特殊处理？

环境变量读取出来都是字符串。字符串 `"false"` 在 Python 中仍然是真值，如果直接判断就会出错。

所以我们写了 `get_bool_env()`，把 `"true"`、`"false"` 这类字符串显式转换成布尔值。

### 为什么 `ALLOWED_HOSTS` 要解析成列表？

Django 的 `ALLOWED_HOSTS` 需要列表格式：

```python
['localhost', '127.0.0.1']
```

但环境变量只能存字符串，所以我们用英文逗号分隔，再通过 `get_list_env()` 转成列表。

## 面试题

1. 为什么生产环境不能开启 `DEBUG`？
2. 为什么不能把 `SECRET_KEY` 提交到代码仓库？
3. `.env` 和 `.env.example` 有什么区别？
4. 为什么环境变量里的布尔值需要手动转换？
5. `ALLOWED_HOSTS` 是做什么的？
6. 为什么配置读取逻辑要封装成工具函数？

## 简短回答

1. `DEBUG=True` 会暴露错误详情和内部信息，生产环境有安全风险。
2. `SECRET_KEY` 泄露可能影响签名、Session、Token 等安全机制。
3. `.env` 保存真实配置，不提交；`.env.example` 保存示例配置，可以提交。
4. 环境变量都是字符串，`"false"` 如果不转换仍然会被当成真值。
5. `ALLOWED_HOSTS` 限制哪些域名或 IP 可以访问 Django 服务。
6. 封装工具函数可以统一解析规则，减少配置代码重复。

## 面试时怎么讲今天的内容

我把 FlowDesk 的核心 Django 配置改成了环境变量驱动，包括 `SECRET_KEY`、`DEBUG` 和 `ALLOWED_HOSTS`。为了避免在 settings 里到处写环境变量解析逻辑，我封装了 `get_env()`、`get_bool_env()` 和 `get_list_env()`，并补充了测试。真实敏感配置放在 `.env` 中并通过 `.gitignore` 忽略，仓库只保留 `.env.example` 作为配置模板。
