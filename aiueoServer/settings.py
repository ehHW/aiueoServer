from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- 1. 初始化 environ ----------
env = environ.Env(
    DEBUG=(bool, False),                       # 缺省 False
    ALLOWED_HOSTS=(list, []),                  # 逗号分隔
    CORS_ALLOW_ALL_ORIGINS=(bool, False),
    CORS_ALLOW_CREDENTIALS=(bool, True),
    CHANNEL_LAYER_REDIS_HOST=(str, "redis"),
    CHANNEL_LAYER_REDIS_PORT=(int, 6379),
    MYSQL_HOST=(str, "127.0.0.1"),
    MYSQL_PORT=(int, 3306),
    MYSQL_NAME=(str, "aiueo"),
    MYSQL_USER=(str, "root"),
    MYSQL_PASSWORD=(str, ""),
    STATIC_URL=(str, "/static/"),
)

# ---------- 2. 读 .env ----------
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

INSTALLED_APPS = [
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
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "aiueoServer.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates']
        ,
        "APP_DIRS": True,
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
