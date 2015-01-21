from btw.celery import app
import os

@app.task
def get_btw_env():
    return os.environ.get("BTW_ENV")
