import os
import subprocess
import inspect

from selenium.webdriver.firefox.webdriver import FirefoxProfile, FirefoxBinary
from selenium.webdriver.chrome.options import Options
import selenic

filename = inspect.getframeinfo(inspect.currentframe()).filename
dirname = os.path.dirname(os.path.abspath(filename))

# Support for older versions of our build setup which do not use builder_args
if 'builder_args' not in globals():
    builder_args = {
        # The config is obtained from the TEST_BROWSER environment variable.
        'browser': os.environ.get("TEST_BROWSER", None),
        'service': "saucelabs"
    }

if 'REMOTE_SERVICE' not in globals():
    REMOTE_SERVICE = builder_args.get("service")

SERVICE_LOG_PATH = "/tmp/log"

#
# LOGS determines whether Selenium tests will capture logs. Turning it
# on makes the tests much slower.
#
# False (or anything considered False): no logging.
#
# True: turns logging on but **automatically turned off in builders!**
# (Builders = buildbot, jenkins, etc.)
#
# "force": turns logging on, **even when using builders**.
#
#
if "LOGS" not in globals():
    LOGS = False

# Detect whether we are running in a builder like Buildbot. (Note that
# this is unrelated to selenic's Builder class.)
in_builder = os.environ.get('BUILDBOT')

# If we are running in a builder, we don't want to have the logs be
# turned on because we forgot to turn them off. So unless LOGS is set
# to "force", we turn off the logs when running in that environment.
if LOGS and LOGS != "force" and in_builder:
    LOGS = False

class Config(selenic.Config):

    def make_selenium_desired_capabilities(self):
        ret = super(Config, self).make_selenium_desired_capabilities()

        if self.browser == "INTERNETEXPLORER":
            ret["requireWindowFocus"] = True
            ret["maxDuration"] = 4200

        ret["tags"] = [self.browser]
        return ret

#
# SELENIUM_NAME will appear suffixed after the default "Wed Test" name...
#
name = "BTW Test"
suffix = os.environ.get("SELENIUM_NAME", None)
if suffix:
    name += ": " + suffix

# Grab the current build number.

# When we create a docker image, there is no git information available.
# The scripts that create the docker image instead store the version
# information into a file that we can read. If the file is there, read it
# and use that information.

describe = None
try:
    describe = open("./DEPLOYED", 'r').read().strip()
except FileNotFoundError:
    pass

if describe is None:
    # The file was absent: use git.
    describe = \
        subprocess.check_output(["git", "describe"]).decode("utf8").strip()

caps = {
    "name": name,
    "maxDuration": 2400,
    "build": describe
}

if REMOTE_SERVICE == "saucelabs":
    if not LOGS:
        caps.update({
            "record-screenshots": "false",
            "record-video": "false",
            "record-logs": "false",
            "sauce-advisor": "false"
        })
elif REMOTE_SERVICE == "browserstack":
    caps.update({
        'project': 'BTW',
        'resolution': '1920x1080',
    })

    if LOGS:
        caps.update({
            'browserstack.debug': True
        })
    else:
        caps.update({
            'browserstack.video': False
        })

with open(os.path.join(dirname, "./browsers.txt")) as browsers:
    for line in browsers.readlines():
        line = line.strip()
        if line.startswith("#") or len(line) == 0:
            continue  # Skip comments and blank lines
        parts = line.split(",")
        if len(parts) == 3:
            parts = parts + [caps, False]
            Config(*parts)
        elif len(parts) == 4:
            assert parts[-1].upper() == "REMOTE"
            parts = parts[:-1] + [caps, True]
            Config(*parts)
        else:
            raise ValueError("bad line: " + line)


# The 'browser' argument determines what browser we load.
browser_env = builder_args.get('browser')

if not browser_env:
    # Yep, we now have a default! But not when we are running in a builder.
    # In a builder we have to explicitly tell what browser we want.
    browser_env = 'Linux,CH,' if not in_builder else None

if browser_env is None:
    raise ValueError("you must specify a browser to run")

parts = [part or None for part in browser_env.split(",")]
CONFIG = selenic.get_config(platform=parts[0], browser=parts[1],
                            version=parts[2])

if CONFIG.browser == "CHROME":
    CHROME_OPTIONS = Options()
    #
    # This prevents getting message shown in Chrome about
    # --ignore-certificate-errors
    #
    # --test-type is an **experimental** option. Reevaluate this
    # --use.
    #
    CHROME_OPTIONS.add_argument("test-type")

    # Tried these to see if they were stopping a slowdown with Chrome,
    # did not work.
    # CHROME_OPTIONS.add_argument('--dns-prefetch-disable')
    # CHROME_OPTIONS.add_argument('--no-proxy-server')

profile = FirefoxProfile()
# profile.set_preference("webdriver.log.file",
#                        "/tmp/firefox_webdriver.log")
# profile.set_preference("webdriver.firefox.logfile",
#                         "/tmp/firefox.log")
FIREFOX_PROFILE = profile

CHROMEDRIVER_PATH = "chromedriver"
SC_TUNNEL_PATH = "sc"
BSLOCAL_PATH = "BrowserStackLocal"

if CONFIG.remote and not REMOTE_SERVICE:
    raise ValueError("you must pass a service argument to behave")

# May be required to get native events.
# FIREFOX_BINARY = FirefoxBinary("/home/ldd/src/firefox-24/firefox")

# Location of the BTW server.
SERVER = "http://localhost"

LOGS = False

config_path = "./local_config/selenium_config.py"
with open(config_path) as config:
    exec(compile(config.read(), config_path, "exec"))
