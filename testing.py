import re
import os

test = "; 'Solid Path', 2.4 [RPM], 15.0 [head mm/s]"

solid = re.compile("; 'Solid Path'")

print(solid.match(test))

spl = solid.split(test)
print(spl)

print (float("120") / 100)

print(os.path.split("/jee/juu/joh.txc"))

print(os.path.splitext("jee.jeext"))

PATH_RE = re.compile("; '.* Path'")

print(PATH_RE.match("; 'Loop Path', 1.5 [RPM], 10.0 [head mm/s]"))