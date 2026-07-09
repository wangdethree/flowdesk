"""FlowDesk 项目配置。"""

from pathlib import Path

# BASE_DIR 指向项目根目录，后续文件路径都基于它拼接。
BASE_DIR = Path(__file__).resolve().parent.parent


# 开发阶段先直接写在这里，部署前再迁移到环境变量。
SECRET_KEY = 'django-insecure-l!-7(@(i0hi0we*md-du@zf+bc@@i3=8cc)^5rlmp+9jg3bbik'

# DEBUG=True 只用于本地开发，生产环境必须关闭。
DEBUG = True

ALLOWED_HOSTS = []


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'apps.audit',
    'apps.analytics',
    'apps.common',
    'apps.users',
    'apps.tickets',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# 第一版先用 SQLite 降低启动成本，后续再切换到 MySQL。
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Django 内置密码强度校验。
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF 默认要求登录访问，单个公开接口再显式设置 AllowAny。
REST_FRAMEWORK = {
    # drf-spectacular 负责根据 DRF 的 Serializer/ViewSet 自动生成 OpenAPI 接口描述。
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # 列表接口默认分页，避免数据量变大后一次返回太多记录。
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'FlowDesk API',
    'DESCRIPTION': '企业工单流转系统后端接口文档',
    'VERSION': '1.0.0',
    # schema 默认对外开放，方便开发阶段查看接口；生产环境可以放到内网或加权限。
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
}
