import math
import statistics
import re

test = 0.123456
print("S%.5f" %test)

EXTRUDER_SPEED_RE = re.compile(b"^G1 E(\d+\.\d+) F(\d+\.\d+)$")
MOVE_SPEED_RE = re.compile(b"^G1 X([-]*\d+\.\d+) Y([-]*\d+\.\d+) E(\d+\.\d+) F(\d+\.\d+)$")

testspd = b"G1 E0.00000 F2400.00000"
testmv = b"G1 X-12.673 Y-13.136 E0.04643 F1500.000"
testmv2 = b"G1 X-12.673 Y-13.136 E0.04643"

res = EXTRUDER_SPEED_RE.match(testspd)
res2 = EXTRUDER_SPEED_RE.search(testspd)

print(res.groups())
print(res2)

res3 = MOVE_SPEED_RE.match(testmv)


print(res3.groups())


def calculate_path_length(prev_position, new_position):

    x_len = prev_position[0] - new_position[0]
    y_len = prev_position[1] - new_position[1]
    path_len = math.sqrt((x_len * x_len) + (y_len * y_len))
    return path_len

def calculate_extrusion_length(prev_position, new_position):
    length = abs(prev_position - new_position)
    return length


def calculate_feed_rate(path_len, extrusion_length):
    rate = path_len / extrusion_length
    return rate


vals = [((0.0, 31.536), (-32.5, 31.536), (0.0, 2.3007)),
        ((-32.5, 31.536), (-34.743, 31.139), (2.3007, 2.46202)),
        ((-34.743, 31.139), (-36.713, 29.996), (2.46202, 2.62328)),
        ((-36.713, 29.996), (-38.172, 28.247), (2.62328, 2.78453)),
        ((-38.172, 28.247), (-39.036, 25.000), (2.78453, 3.02236))]

print("START")
feed_rates = []
for i, j, k in vals:

    path_len = calculate_path_length(i, j)
    extrusion_length = calculate_extrusion_length(k[0], k[1])
    feed_rate = calculate_feed_rate(path_len, extrusion_length)
    feed_rates.append(feed_rate)
    print(path_len, extrusion_length, feed_rate)
print("END")

print(statistics.mean(feed_rates))

path_len = calculate_path_length((0.0, 31.536), (-32.5, 31.536))
print (path_len)
print(calculate_path_length((-32.5, 31.536), (-34.743, 31.139)))
print(calculate_path_length((-34.743, 31.139), (-36.713, 29.996)))
print(calculate_path_length((-36.713, 29.996), (-38.172, 28.247)))
print(calculate_path_length((-38.172, 28.247), (-39.036, 25.000)))

print(calculate_path_length((-5.0, 0.0), (5.0, 0.0)))
print(calculate_path_length((5.0, 0.0), (-5.0, 0.0)))

extrusion_length = calculate_extrusion_length(0.0, 2.3007)
print (extrusion_length)
print(calculate_extrusion_length(2.4, 2.300))

feed_rate = calculate_feed_rate(path_len, extrusion_length)
print(feed_rate)

#G1 X0.000 Y31.536 F3600.000 ; move to first skirt point
#G1 E0.00000 F2400.00000 ; unretract

#G1 X-32.500 Y31.536 E2.30077 F1500.000 ; skirt
#G1 X-34.743 Y31.139 E2.46202 ; skirt
#G1 X-36.713 Y29.996 E2.62328 ; skirt
#G1 X-38.172 Y28.247 E2.78453 ; skirt
#G1 X-39.036 Y25.000 E3.02236 ; skirt

import process

pf = process.Slic3rPrintFile()
pf.process('/mnt/hgfs/E/3DModels/Calibration_Cube/WallCalibration_s3.bfb')