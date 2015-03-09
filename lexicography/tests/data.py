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
    "01+02",  # Bad separator
    "01.02|01|02",  # Extra separator...
    "01.02.",  # Final period
    ".01.02",  # Initial period
    "1.02",  # 1 digit initial
    "001.02",  # 3 digits initial
    "01.2",  # 1 digit secondary
    "01.002",  # 3 digits secondary
    "01.02|2",  # 1 digit after suffix
    "01.02|002",  # 3 digits after suffix
    "01.02|01.2",  # 1 digit after suffix, secondary
    "01.02|01.002",  # 3 digits after suffix, secondary
    "01.02|.01",  # Initial period after suffix
    u"0१.002",  # Indian numeral,
]

valid_sf_cases = [
    u"\u00a0 01.02",  # Leading non-breakable space
]
