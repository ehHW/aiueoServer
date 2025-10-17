from pathlib import Path
import environ, os

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- 1. 初始化 environ ----------
env = environ.Env(
    DEBUG=(bool, False),                       # 缺省 False
    ALLOWED_HOSTS=(list, []),                  # 逗号分隔
    CORS_ALLOW_ALL_ORIGINS=(bool, False),
    CORS_ALLOW_CREDENTIALS=(bool, True),
    CHANNEL_LAYER_REDIS_HOST=(str, "redis"),   # 容器名或 ip
    CHANNEL_LAYER_REDIS_PORT=(int, 6379),
    MYSQL_HOST=(str, "127.0.0.1"),
    MYSQL_PORT=(int, 3306),
    MYSQL_NAME=(str, "aiueo"),
    MYSQL_USER=(str, "root"),
    MYSQL_PASSWORD=(str, ""),
    STATIC_URL=(str, "/static/"),
)

# ---------- 2. 读 .env（仅本地开发） ----------
# Docker 里不要挂载 .env，所以这里读不到也不报错
environ.Env.read_env(BASE_DIR / ".env")

# ---------- 3. 密钥 ----------
SECRET_KEY = env("SECRET_KEY")

# ---------- 4. 常规开关 ----------
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------- 5. CORS ----------
CORS_ALLOW_ALL_ORIGINS = env("CORS_ALLOW_ALL_ORIGINS")
CORS_ALLOW_CREDENTIALS = env("CORS_ALLOW_CREDENTIALS")
# 如果 CORS_ALLOW_ALL_ORIGINS=False，可额外设置白名单
# CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# ---------- 6. Channel Layers ----------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (env("CHANNEL_LAYER_REDIS_HOST"), env("CHANNEL_LAYER_REDIS_PORT")),
                # { "password": '030827' }
            ],
        },
    },
}

# ---------- 7. MySQL ----------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("MYSQL_NAME"),
        "USER": env("MYSQL_USER"),
        "PASSWORD": env("MYSQL_PASSWORD"),
        "HOST": env("MYSQL_HOST"),
        "PORT": env("MYSQL_PORT"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}



# SECRET_KEY = "django-insecure-k7n$3=559(4tcut@mvir4tnccd5q$d#m#(o7#zr7-#e_frfq*3"

# DEBUG = True

# ALLOWED_HOSTS = [
#     '117.68.10.96',
#     'frp-end.com',
#     'localhost',
#     '127.0.0.1'
# ]

# CORS_ORIGIN_WHITELIST = [
#     'http://127.0.0.1:5173',
#     'http://localhost:5173',
#     'https://frp-end.com:54895',
#     'http://aiueo'
# ]

# 允许携带 Cookie
# CORS_ALLOW_ALL_ORIGINS = False  # 必须关闭，否则无法设置CORS_ALLOW_CREDENTIALS
# CORS_ALLOW_CREDENTIALS = True
# ACCESS_CONTROL_ALLOW_ORIGIN = 'http://127.0.0.1:5173'


INSTALLED_APPS = [
    # "corsheaders",
    'channels',
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "user.apps.UserConfig",
    "chat.apps.ChatConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "aiueoServer.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates']  # 在这查找模板
        ,
        "APP_DIRS": True,  # 在app的templates文件夹下查找模板, 需安装app
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "aiueoServer.wsgi.application"
ASGI_APPLICATION = "aiueoServer.asgi.application"

# 配置通道层，使用Redis作为后端（可选，但生产环境推荐）
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {
#             "hosts": [
#                 ("aiueo_redis", 6379),
#                 #     {
#                 #         "password": "030827",
#                 # }
#             ],
#         },
#     },
# }


# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.mysql",
#         "NAME": "aiueo",
#         "USER": "root",
#         "PASSWORD": "hy030827",
#         "HOST": "aiueo_mysql",
#         "PORT": "3306",
#         "OPTIONS": {
#             "charset": "utf8mb4",
#         }
#     }
# }


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
