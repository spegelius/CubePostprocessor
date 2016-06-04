
import logging
import math
import os

log = logging.getLogger("Cubifier")

SLICER_CURA = "Cura"
SLICER_KISSLICER = "KISSlicer"
SLICER_SIMPLIFY3D = "Simplify3d"
SLICER_SLIC3R = "Slic3r"


class PrintFile:
    slicer_type = None
    EXTRUSION_SPEED_CMD = b"M108"
    EXTRUDER_TEMP_CMD = b"M104"
    EXTRUDER_ON_CMD = b"M101"
    EXTRUDER_OFF_CMD = b"M103"
    UNUSED_CMDS = [b"G90",
                   b"G92",
                   b"M82",
                   b"G28",
                   b"M18",
                   b"M17",
                   b"M112",
                   b"M135"]

    def __init__(self, debug=False):
        self.debug = debug
        if debug:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)
        self.settings = {}
        self.lines = []
        self.gcode_file = None
        self.line_index = 0

    def remove_comments(self):

        self.line_index = 0
        while True:
            try:
                if self.lines[self.line_index].startswith(b";"):
                    self.lines.pop(self.line_index)
                    continue
                self.lines[self.line_index] = self.lines[self.line_index].split(b";")[0].strip()
                self.line_index += 1
            except IndexError:
                return

    def open_file(self, gcode_file):

        self.gcode_file = gcode_file
        # open file
        try:
            gf = open(gcode_file, 'rb')
        except Exception as e:
            log.error("Cannot open file %s" % gcode_file)
            return 1

        # remove extra EOL and empty lines
        self.lines = [l.strip() for l in gf.readlines() if l.strip()]
        gf.close()

    def save_new_file(self):
        # save new file
        self.remove_comments()
        _dir, fname = os.path.split(self.gcode_file)
        name, ext = os.path.splitext(fname)
        newfile = os.path.join(_dir,  name + "_cb.bfb")
        try:
            with open(newfile, "wb") as nf:
                result = b"\r\n".join(self.lines)
                nf.write(result)
                log.info("Wrote new file: %s" % newfile)
                return newfile
        except Exception as e:
            log.error("Could not save file, error: %s" % e)
            return 1

    def update_extruder_speed(self, current_cmd, multiplier):
        current_speed = current_cmd.split(b" ")[1].strip()[1:]
        new_val = b"M108 S%.1f" % (float(current_speed) * multiplier)
        return new_val

    def read_line(self, index=None):
        if not index:
            l_index = self.line_index
        else:
            l_index = index
        if self.lines[l_index ].startswith(b";"):
            return self.lines[l_index ], None
        vals = self.lines[l_index ].strip().split(b";", 1)
        l = vals[0].strip()
        if len(vals) == 2:
            return l, vals[1]
        return l, None

    def calculate_path_length(self, prev_position, new_position):

        x_len = prev_position[0] - new_position[0]
        y_len = prev_position[1] - new_position[1]

        path_len = math.sqrt((x_len * x_len) + (y_len * y_len))
        return path_len

    def calculate_extrusion_length(self, prev_position, new_position):
        length = abs(prev_position - new_position)
        return length

    def calculate_feed_rate(self, path_len, extrusion_length):
        if not path_len or not extrusion_length:
            return 0.005 # hat constant instead of 0 extrusion. Bug in Slic3r?
        rate = 1 / (path_len / extrusion_length)
        return rate

    def delete_line(self, index=None):
        if not index:
            l_index = self.line_index
        else:
            l_index = index
        self.lines.pop(l_index)
        self.line_index -= 1

    def remove_unused_cmds(self):
        self.line_index = 0
        while True:
            try:
                if self.lines[self.line_index].split()[0] in self.UNUSED_CMDS:
                    self.lines.pop(self.line_index)
                    continue
                self.line_index += 1
            except IndexError:
                return