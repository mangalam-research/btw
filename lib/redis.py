import os

from .settings import join_prefix

class Config:

    def __init__(self):
        from django.conf import settings
        self.prefix = prefix = settings.BTW_REDIS_SITE_PREFIX

        self.run_path = run_path = os.path.join(settings.BTW_RUN_PATH, "redis")
        self.pidfile_path = os.path.join(run_path, join_prefix(prefix,
                                                               "redis.pid"))
        self.socket_dir_path = socket_dir_path = \
            settings.BTW_REDIS_SOCKET_DIR_PATH
        self.sockfile_path = os.path.join(socket_dir_path,
                                          join_prefix(prefix, "redis.sock"))
        self.dumpfile_name = dumpfile_name = join_prefix(prefix, "dump.rdb")
        self.dir_path = dir_path = \
            os.path.join(settings.TOPDIR, "var", "lib", "redis")
        self.dumpfile_path = os.path.join(dir_path, dumpfile_name)
        self.generated_config_path = os.path.join(
            run_path,
            join_prefix(prefix, "redis.conf"))
        self.logging_path = logging_path = \
            os.path.join(settings.BTW_LOGGING_PATH, "redis")
        self.logfile_path = os.path.join(logging_path,
                                         join_prefix(prefix,
                                                     "redis-server.log"))
        self.password = settings.BTW_REDIS_PASSWORD

        self._generated_config = None

    @property
    def generated_config(self):
        if self._generated_config is not None:
            return self._generated_config

        with open(os.path.join(os.path.dirname(__file__), "..",
                               "btw_management", "management", "templates",
                               "redis.conf")) as f:
            template = f.read()

        self._generated_config = ret = template.format(
            pidfile_path=self.pidfile_path,
            sockfile_path=self.sockfile_path,
            logfile_path=self.logfile_path,
            dir_path=self.dir_path,
            dumpfile_name=self.dumpfile_name,
            redis_pass=self.password)

        return ret
