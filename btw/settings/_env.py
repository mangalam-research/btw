import os
import sys
import re

HOME_CONFIG = os.path.join(os.environ["HOME"], ".config/btw/settings")
ETC_CONFIG = "/etc/btw/settings"

HOME_SECRET = os.path.join(os.environ["HOME"], ".config/btw/secrets")
ETC_SECRET = "/etc/btw/secrets"

CURDIR = os.path.dirname(os.path.abspath(__file__))
TOPDIR = os.path.dirname(os.path.dirname(CURDIR))

env_re = re.compile("^[-a-zA-Z0-9_]+$")

# Determine the name of our environment.
env = os.environ.get("BTW_ENV", None)
if env is None:
    for path in (TOPDIR, HOME_CONFIG, ETC_CONFIG):
        env_path = os.path.join(path, "env")
        try:
            env = open(env_path, 'r').read().strip()
        except OSError:
            pass

    if env is not None and not env_re.fullmatch(env):
        raise ValueError(f"env must match {env_re}; got: {env}")

if env is None:
    raise ValueError("can't get running environment value!")

if not os.environ.get("BTW_ENV_SUPPRESS_MESSAGE"):
    sys.stderr.write("Environment is set to: " + env + "\n")


def find_config(name):
    for path in (HOME_CONFIG, ETC_CONFIG):
        conf_path = os.path.join(path, env, name + ".py")
        if os.path.exists(conf_path):
            return open(conf_path).read()
    # We return either an open file (see above) or an empty
    # string because exec accepts both.
    return ""

def read_secret(s):
    for path in (HOME_SECRET, ETC_SECRET):
        conf_path = os.path.join(path, env)
        if os.path.exists(conf_path):
            s.read_secret_file(conf_path)

# This function is not used by BTW itself but it can be used in settings file
# to load another settings file, using a literal name.
def find_literal_file(name):
    for path in (HOME_CONFIG, ETC_CONFIG):
        conf_path = os.path.join(path, name)
        if os.path.exists(conf_path):
            return open(conf_path).read()
    # We return either an open file (see above) or an empty
    # string because exec accepts both.
    return ""
