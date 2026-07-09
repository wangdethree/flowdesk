# 第一版使用 slim 镜像，体积比完整 Python 镜像小，适合 Web 服务部署。
FROM python:3.11-slim

# Python 不写 .pyc 文件，日志直接输出到终端，便于 docker logs 查看。
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 先复制 requirements.txt 再安装依赖，可以更好利用 Docker 构建缓存。
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r /app/requirements.txt

# 再复制项目代码。上面的依赖层不变时，改业务代码不会重复安装依赖。
COPY . /app

EXPOSE 8000

# 容器启动时先执行迁移，再用 Gunicorn 启动 WSGI 服务。
# 这里用 sh -c 是为了顺序执行两条命令。
CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
