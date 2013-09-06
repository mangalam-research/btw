import _env

LEXICOGRAPHY_LOCK_EXPIRY=24 # Locks expire after 24 hours

exec _env.find_config("lexicography") in globals()
