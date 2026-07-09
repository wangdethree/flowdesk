"""FlowDesk 的 WSGI 应用入口，用于传统同步服务部署。"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
