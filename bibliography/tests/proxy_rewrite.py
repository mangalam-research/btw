#
# This filters out the API keys from the recorded transactions.
#

import re
key_re = re.compile(r"([&?]key=)[^&]+")
id_re = re.compile(r"^(/(?:groups|users)/)\d+/")

def request(flow):
    flow.request.path = id_re.sub(r"\1none/",
                                  key_re.sub(r"\1none", flow.request.path))
