#
# This filters out the API keys from the recorded transactions.
#

import re
key_re = re.compile(r"([&?]key=)[^&]+")
id_re = re.compile(r"^(/(?:groups|users)/)\d+/")

sequence = 0


def request(_context, flow):
    global sequence  # pylint: disable=global-statement
    flow.request.path = id_re.sub(r"\1none/",
                                  key_re.sub(r"\1none", flow.request.path))

    #
    # The X-BTW-Sequence thing is to work around an sequencing
    # issue. See the tech_notes.rst file section on testing the Zotero
    # code. We probably will be able to get rid of this when mitmproxy
    # 0.11 is released.
    #

    flow.request.headers["X-BTW-Sequence"] = [sequence]
    sequence += 1
