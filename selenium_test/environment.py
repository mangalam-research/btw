import os

_dirname = os.path.dirname(__file__)

local_conf_path = os.path.join(os.path.dirname(_dirname),
                               "build", "config", "selenium_local_config.py")


conf_path = os.path.join(os.path.dirname(_dirname),
                         "build", "config", "selenium_test_config.py")
conf = {"__file__": conf_path}
execfile(conf_path, conf)

config = conf["Config"](local_conf_path)

import selenic.util


def before_all(context):
    context.driver = config.get_driver()
    context.util = selenic.util.Util(context.driver)


def after_all(context):
    driver = context.driver
    config.set_test_status(driver.session_id, not context.failed)
    if not context.failed and "BEHAVE_NO_QUIT" not in os.environ:
        driver.quit()
