from django.apps import AppConfig


class AiConfig(AppConfig):
    """智能助手应用配置。"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai'
    verbose_name = '智能助手'
