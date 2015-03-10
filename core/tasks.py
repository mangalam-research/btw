from btw.celery import app

@app.task
def get_btw_env():
    from btw.settings._env import env
    return env
