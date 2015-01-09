import os
import subprocess
import re
import inspect

filename = inspect.getframeinfo(inspect.currentframe()).filename
dirname = os.path.dirname(os.path.abspath(filename))

from selenium.webdriver.firefox.webdriver import FirefoxProfile, FirefoxBinary
from selenium.webdriver.chrome.options import Options
import selenic

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

# If we are running in something like Buildbot or Jenkins, we don't
# want to have the logs be turned on because we forgot to turn them
# off. So unless LOGS is set to "force", we turn off the logs when
# running in that environment.
if LOGS and LOGS != "force" and \
   (os.environ.get('BUILDBOT') or os.environ.get('JENKINS_HOME')):
    LOGS = False

class Config(selenic.Config):

    def make_selenium_desired_capabilities(self):
        ret = super(Config, self).make_selenium_desired_capabilities()

        if self.browser == "INTERNETEXPLORER":
            ret["requireWindowFocus"] = True

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
describe = subprocess.check_output(["git", "describe"])

caps = {
    # We have to turn this on...
    "nativeEvents": True,
    "name": name,
    # As of 2014-06-30 2.42.2 fails to load on Saucelabs...
    "selenium-version": "2.43.0",
    "chromedriver-version": "2.11",
    "build": describe
}

if not LOGS:
    caps["record-screenshots"] = "false"
    caps["record-video"] = "false"
    caps["record-logs"] = "false"
    caps["sauce-advisor"] = "false"

with open(os.path.join(dirname, "./browsers.txt")) as browsers:
    for line in browsers.readlines():
        line = line.strip()
        if line.startswith("#") or len(line) == 0:
            continue  # Skip comments and blank lines
        parts = line.split(",")
        if len(parts) == 3:
            Config(*parts)
        elif len(parts) == 4:
            assert parts[-1].upper() == "REMOTE"
            parts = parts[:-1] + [caps, True]
            Config(*parts)
        else:
            raise ValueError("bad line: " + line)

#
# The config is obtained from the TEST_BROWSER environment variable.
#
browser_env = os.environ.get("TEST_BROWSER", None)
if browser_env:
    # When invoked from a Jenkins setup, the spaces that would
    # normally appear in names like "Windows 8.1" will appear as
    # underscores instead. And the separators will be "-" rather than
    # ",".
    parts = re.split(r"[,-]", browser_env.replace("_", " "))
    CONFIG = selenic.get_config(
        platform=parts[0] or None, browser=parts[1] or None,
        version=parts[2] or None)

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

    profile = FirefoxProfile()
    # profile.set_preference("webdriver.log.file",
    #                        "/tmp/firefox_webdriver.log")
    # profile.set_preference("webdriver.firefox.logfile",
    #                         "/tmp/firefox.log")
    FIREFOX_PROFILE = profile

# May be required to get native events.
# FIREFOX_BINARY = FirefoxBinary("/home/ldd/src/firefox-24/firefox")

# Location of the BTW server.
SERVER = "http://localhost"
