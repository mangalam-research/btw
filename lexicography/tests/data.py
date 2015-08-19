# -*- encoding: utf-8 -*-
#
# This module is meant to contain immutable data that should be shared
# among test cases.
#

# Test cases for invalid sematic fields.
invalid_sf_cases = [
    "01x",  # Errant suffix
    "abcd",  # Junk
    "",  # Empty text
    "01+02n",  # Bad separator
    "01.02|01|02n",  # Extra separator...
    "01.02n.",  # Final period
    ".01.02n",  # Initial period
    "1.02n",  # 1 digit initial
    "001.02n",  # 3 digits initial
    "01.2n",  # 1 digit secondary
    "01.002n",  # 3 digits secondary
    "01.02|2n",  # 1 digit after suffix
    "01.02|002n",  # 3 digits after suffix
    "01.02|01.2n",  # 1 digit after suffix, secondary
    "01.02|01.002n",  # 3 digits after suffix, secondary
    "01.02|.01n",  # Initial period after suffix
    u"0१.002n",  # Indian numeral,
]

valid_sf_cases = [
    u"\u00a0 01.02n",  # Leading non-breakable space
]
