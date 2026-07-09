# Day 10：Docker 容器化运行

## 今天完成了什么

- 新增 `gunicorn` 运行依赖。
- 新增 `Dockerfile`，用于构建 FlowDesk 后端镜像。
- 新增 `docker-compose.yml`，用于一条命令启动本地容器。
- 新增 `.dockerignore`，减少镜像构建上下文。
- 支持通过 `SQLITE_DATABASE_PATH` 配置 SQLite 数据库文件位置。

## 为什么要做 Docker？

本地开发时，我们可以直接用虚拟环境启动 Django：

```bash
.venv/bin/python manage.py runserver
```

但真实部署时，服务器环境不一定和本地一致。Docker 的作用是把 Python 版本、依赖、启动命令这些运行条件固定下来，让项目在不同机器上更容易跑起来。

面试里可以这样理解：

- `requirements.txt` 负责声明 Python 依赖。
- `Dockerfile` 负责描述如何构建运行环境。
- `docker-compose.yml` 负责描述服务如何启动、端口如何映射、数据如何持久化。

## Dockerfile 里每一步在做什么？

```dockerfile
FROM python:3.11-slim
```

选择 Python 3.11 的轻量镜像，体积比完整镜像更小。

```dockerfile
WORKDIR /app
```

设置容器内工作目录。后续命令默认都在 `/app` 下执行。

```dockerfile
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
```

先复制依赖文件并安装依赖。这样做可以利用 Docker 缓存：只改业务代码时，不需要每次重新安装依赖。

```dockerfile
COPY . /app
```

复制项目代码到容器里。

```dockerfile
CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
```

容器启动时先执行数据库迁移，再用 Gunicorn 启动 Django 服务。

## 为什么不用 runserver 部署？

`runserver` 是 Django 自带的开发服务器，适合本地调试，不适合生产部署。

Gunicorn 是更常见的 Python Web 服务启动方式。它会加载 Django 的 WSGI 应用，也就是这里的：

```text
config.wsgi:application
```

## docker-compose 做了什么？

当前 `docker-compose.yml` 只定义了一个服务：

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
```

含义是：从当前目录构建镜像，并把容器的 8000 端口映射到本机的 8000 端口。

所以容器启动后，本机可以访问：

```text
http://127.0.0.1:8000
```

## 为什么 SQLite 要放到 `/data/db.sqlite3`？

容器里的文件默认不稳定。容器删掉后，容器内部生成的数据也可能一起丢失。

所以我们把 SQLite 数据库文件放到 `/data/db.sqlite3`，并在 compose 中挂载命名卷：

```yaml
volumes:
  - flowdesk_sqlite:/data
```

这样数据库文件就会保存在 Docker 管理的 volume 里，容器重建后数据仍然可以保留。

## 为什么 `.dockerignore` 很重要？

构建 Docker 镜像时，Docker 会把当前目录作为构建上下文发送给构建器。

如果不忽略无关文件，`.venv`、`.git`、本地数据库、缓存文件都可能进入构建上下文，导致：

- 构建速度变慢。
- 镜像体积变大。
- 本地敏感配置被误打进镜像。

所以 `.dockerignore` 和 `.gitignore` 一样，都是为了减少不该进入目标环境的文件。

## 常用命令

构建并启动：

```bash
docker compose up --build
```

后台启动：

```bash
docker compose up --build -d
```

查看日志：

```bash
docker compose logs -f
```

停止并删除容器：

```bash
docker compose down
```

## 面试题

1. Dockerfile 和 docker-compose.yml 有什么区别？
2. 为什么 Dockerfile 里先复制 `requirements.txt`，再复制项目代码？
3. 为什么生产环境不用 Django 的 `runserver`？
4. Gunicorn 在 Django 部署里起什么作用？
5. `.dockerignore` 的作用是什么？
6. 为什么容器里的数据库文件需要挂载 volume？

## 简短回答

1. Dockerfile 描述镜像怎么构建，docker-compose.yml 描述服务怎么启动和组合。
2. 这样可以利用 Docker 缓存，业务代码变化时不必重复安装依赖。
3. `runserver` 是开发服务器，性能和稳定性不适合生产环境。
4. Gunicorn 负责加载 Django WSGI 应用，并对外提供 Web 服务。
5. `.dockerignore` 用来排除无关文件，减少构建上下文和敏感信息风险。
6. 容器重建可能丢失内部文件，volume 可以让数据独立于容器生命周期保存。

## 面试时怎么讲今天的内容

我给 FlowDesk 增加了 Docker 容器化运行能力。项目使用 Dockerfile 固定 Python 运行环境和依赖安装步骤，使用 Gunicorn 启动 Django WSGI 应用，并通过 docker-compose 暴露 8000 端口。因为第一版仍然使用 SQLite，所以我把数据库路径改成可配置的 `SQLITE_DATABASE_PATH`，在容器里把数据库放到 `/data/db.sqlite3`，再通过 Docker volume 做持久化。
