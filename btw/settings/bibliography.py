from lib.settings import s

# All sensitive so init with empty dir.
s.ZOTERO_SETTINGS = {}

s.CACHES = lambda s: {**{
    "bibliography": {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': s.BTW_REDIS_CACHING_LOCATION,
        'KEY_PREFIX': s.BTW_GLOBAL_KEY_PREFIX + '!bibliography',
        'OPTIONS': {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        'TIMEOUT': 3153600000,
    }
}, **s.CACHES}

def set_bibliography_logging(s):
    old = s.LOGGING
    old["loggers"]["bibliography"] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': True,
    }
    old["loggers"]["zotero"] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': True,
    }
    return old

s.LOGGING = set_bibliography_logging
