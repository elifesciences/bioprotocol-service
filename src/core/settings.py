"""
Django settings for core project.

Generated by 'django-admin startproject' using Django 2.2.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
from os.path import join
import configparser as configparser

PROJECT_NAME = "bioprotocol"

# Build paths inside the project like this: os.path.join(SRC_DIR, ...)
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.dirname(os.path.dirname(__file__))  # ll: /path/to/lax/src/
PROJECT_DIR = os.path.dirname(SRC_DIR)  # ll: /path/to/lax/

CFG_NAME = "app.cfg"
DYNCONFIG = configparser.SafeConfigParser(
    **{"allow_no_value": True, "defaults": {"dir": SRC_DIR, "project": PROJECT_NAME}}
)
DYNCONFIG.read(join(PROJECT_DIR, CFG_NAME))  # ll: /path/to/lax/app.cfg


def cfg(path, default=0xDEADBEEF):
    lu = {
        "True": True,
        "true": True,
        "False": False,
        "false": False,
    }  # cast any obvious booleans
    try:
        bits = path.split(".")
        if len(bits) == 1:  # read whole section as dict
            return {key: lu.get(val, val) for key, val in DYNCONFIG.items(bits[0])}
        val = DYNCONFIG.get(*bits)
        return lu.get(val, val)
    except (
        configparser.NoOptionError,
        configparser.NoSectionError,
    ):  # given key in section hasn't been defined
        if default == 0xDEADBEEF:
            raise ValueError("no value/section set for setting at %r" % path)
        return default
    except Exception as err:
        print("error on %r: %s" % (path, err))


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = cfg("general.secret-key")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = cfg("general.debug")
assert isinstance(
    DEBUG, bool
), "'debug' must be either True or False as a boolean, not %r" % (DEBUG,)

ALLOWED_HOSTS = cfg("general.allowed-hosts", "").split(",")

# Application definition

INSTALLED_APPS = [
    #'django.contrib.admin',
    #'django.contrib.auth',
    "django.contrib.contenttypes",
    #'django.contrib.sessions',
    #'django.contrib.messages',
    #'django.contrib.staticfiles',
    "bp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    #'django.contrib.sessions.middleware.SessionMiddleware',
    "django.middleware.common.CommonMiddleware",
    #"django.middleware.csrf.CsrfViewMiddleware",
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #"django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                #'django.contrib.auth.context_processors.auth',
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "core.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": cfg("database.engine"),
        "NAME": cfg("database.name"),
        "USER": cfg("database.user"),
        "PASSWORD": cfg("database.password"),
        "HOST": cfg("database.host"),
        "PORT": cfg("database.port"),
    }
}

SQS = cfg("sqs")

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "syslog": {
            "level": "DEBUG",
            "class": "logging.handlers.SysLogHandler",
            # "formatter": "verbose",
            "facility": "local1",
            "address": "/dev/log",
        }
    },
    "loggers": {"": {"handlers": ["syslog"], "level": "INFO"}},
}

APPEND_SLASH = False
