import os
import re
import sys

from mitmproxy import io

(_, inpath, outpath) = sys.argv

key_re = re.compile(r"([&?]key=)[^&]+")
id_re = re.compile(r"^(/(?:groups|users)/)\d+/")

inf = open(inpath, 'rb')
freader = io.FlowReader(inf)
outf = open(outpath, 'wb')
fwriter = io.FlowWriter(outf)
for i in freader.stream():
    i.request.path = id_re.sub(r"\1none/",
                               key_re.sub(r"\1none", i.request.path))
    fwriter.add(i)
outf.close()
inf.close()
