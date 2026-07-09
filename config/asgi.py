"""FlowDesk 的 ASGI 应用入口，用于异步服务部署。"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
