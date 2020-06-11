"""
Django settings for dms_backend project.

Generated by 'django-admin startproject' using Django 3.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""
import os
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# we must turn on debug settings explicit production is default
# one might think to use to_bool from data.views but that adds a
# well hidden circular dependency. Resulting in the informative error
# SECRET_KEY is not defined
if 'DEBUG' in os.environ and bool(int(os.environ.get('DEBUG'))):
    DEBUG = True
    SECRET_KEY = "zpy%3y%d27c0@wg+b_7!6uvaf^t6zztt@fz!7euop1yz7ip0!4"
    # Database
    # https://docs.djangoproject.com/en/3.0/ref/settings/#databases
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        }
    }
    MEDIA_ROOT = os.path.join(BASE_DIR, "files")
else:
    DEBUG = False
    SECRET_KEY = os.environ.get('DMS_SECRET')
    STATIC_ROOT = os.environ.get('DMS_STATIC_ROOT')
    MEDIA_ROOT = os.environ.get('DMS_MEDIA_ROOT')
    DATABASES = {
        "default": {
            "ENGINE": os.environ.get("SQL_ENGINE"),
            "NAME": os.environ.get("SQL_DATABASE"),
            "USER": os.environ.get("SQL_USER"),
            "PASSWORD": os.environ.get("SQL_PASSWORD"),
            "HOST": os.environ.get("SQL_HOST"),
            "PORT": os.environ.get("SQL_PORT"),
        }
    }
    log_level = os.getenv('DMS_LOG_LEVEL', 'INFO')
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'level': log_level,
                'class': 'logging.FileHandler',
                'filename': os.getenv('DMS_LOG'),
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'level': log_level,
                'propagate': False,
            },
        },
    }

ALLOWED_HOSTS = ["dmsapi.klima.tu-berlin.de", "130.149.72.77", "127.0.0.1", "localhost"]
AUTH_USER_MODEL = "custom_auth.User"

STATIC_URL = "/static/"
# Allow requests from localhost / frontend
CORS_ORIGIN_ALLOW_ALL = True

# Even without CSRF
CSRF_TRUSTED_ORIGINS = [
    "localhost:8080",
    "dmsapi.klima.tu-berlin.de"
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # our "app"
    "dms_backend.apps.DmsBackendConfig",
    "data.apps.DataConfig",
    # Third-Party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "guardian",
    "django_filters",
    # our stuff
    "auth.apps.AuthConfig",
]


REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "multipart",
    "TEST_REQUEST_RENDERER_CLASSES": [
        "rest_framework.renderers.MultiPartRenderer",
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.TemplateHTMLRenderer",
    ],
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # add corsheaders to work its magic
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dms_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = "dms_backend.wsgi.application"


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",},
]

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",  # default
    "guardian.backends.ObjectPermissionBackend",
    "auth.kb_auth.KBBackend"
)

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# always store files in TmpFolder. See data/views/FileView before changing. It might break !!!
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler'
]

# FILE Folder
MEDIA_URL = "/files/"
