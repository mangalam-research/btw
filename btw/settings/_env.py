from __future__ import print_function
import os
import StringIO

HOME_CONFIG=os.path.join(os.environ["HOME"], ".config/btw")
ETC_CONFIG="/etc/btw"

# Determine the name of our environment.
env = os.environ.get("BTW_ENV", None)
if env is None:
    for path in (HOME_CONFIG, ETC_CONFIG):
        env_path = os.path.join(path, "env")
        env = open(env_path, 'r').read().strip() if os.path.exists(env_path) else None

        if env == "":
            raise ValueError("env cannot be an empty string")

        if env is not None:
            break

if env is None:
    raise ValueError("can't get running environment value!")

print("Environment is set to:", env)

def find_config(name):
    for path in (HOME_CONFIG, ETC_CONFIG):
        conf_path = os.path.join(path, name + "." + env + ".py")
        if os.path.exists(conf_path):
            return open(conf_path)
    # We return either an open file (see above) or an empty
    # string because exec accepts both.
    return ""
