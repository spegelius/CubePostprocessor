#!/usr/bin/env python

"""
# CubePostprocessor

Just a post processor make life easier with Cube 2 from 3DSystems.

Support KISSlicer 1.5b, Cura 15.04.04 and Slic3r 1.2.9.

With all slicer g-code, it cleans the file after processing (removes comments and extra lines, makes sure EOL is Windows)

With KISS
 - allows for solid and infill extrusion amount tuning

With Cura
 - change first layer temp 10 C higher than rest of the print

With Slicer
 - converts Makerware (Makerbot) style g-code to Cube (BfB) format

Disclaimer: i'm not responsible if anything, good or bad, happens due to use of this script.

Version 0.5
"""


import logging
import math
import re
import os
import statistics
import sys

fmt = logging.Formatter(fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
filehandler = logging.FileHandler("process.log")
filehandler.setFormatter(fmt)
streamhandler = logging.StreamHandler(stream=sys.stdout)
streamhandler.setFormatter(fmt)
log = logging.getLogger("CubePostProcessor")
log.setLevel(logging.INFO)
log.addHandler(filehandler)
log.addHandler(streamhandler)


## Globals

# Tune this to make Slic3r filament flow fir your needs
SLIC3R_FLOW_MULTIPLIER = 0.0006

class PrintFile:
    EXTRUSION_SPEED_CMD = b"M108"
    EXTRUDER_TEMP_CMD = b"M104"
    EXTRUDER_ON_CMD = b"M101"
    EXTRUDER_OFF_CMD = b"M103"

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

        index = 0
        while True:
            try:
                if self.lines[index].startswith(b";"):
                    self.lines.pop(index)
                    continue
                self.lines[index] = self.lines[index].split(b";")[0].strip()
                index += 1
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
        newfile = os.path.join(_dir,  name + "_cb" + ext)
        try:
            with open(newfile, "wb") as nf:
                result = b"\r\n".join(self.lines)
                nf.write(result)
                log.info("Wrote new file: %s" % newfile)
        except Exception as e:
            log.error("Could not save file, error: %s" % e)
            return 1

    def update_extruder_speed(self, current_cmd, multiplier):
        current_speed = current_cmd.split(b" ")[1].strip()[1:]
        new_val = b"M108 S%.1f" % (float(current_speed) * multiplier)
        return new_val

    def read_line(self, index):
        if self.lines[index].startswith(b";"):
            return self.lines[index], None
        vals = self.lines[index].strip().split(b";", 1)
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
        rate = path_len / extrusion_length
        return rate

    def delete_line(self, index):
        self.lines.pop(index)
        self.line_index -= 1


class Slic3rPrintFile(PrintFile):

    EXTRUDER_RETRACT_RE = re.compile(b"^G1 E([-]*\d+\.\d+) F(\d+\.\d+)$")
    Z_MOVE_RE = re.compile(b"^G1 Z([-]*\d+\.\d+) F(\d+\.\d+)$")
    EXTRUSION_MOVE_RE = re.compile(b"^G1 X([-]*\d+\.\d+) Y([-]*\d+\.\d+) E(\d+\.\d+)")
    EXTRUSION_MOVE_SPEED_RE = re.compile(b"^G1 X([-]*\d+\.\d+) Y([-]*\d+\.\d+) E(\d+\.\d+) F(\d+\.\d+)$")
    MOVE_HEAD_RE = re.compile(b"^G1 X([-]*\d+\.\d+) Y([-]*\d+\.\d+) F(\d+\.\d+)$")
    SPEED_RE = re.compile(b"^G1 F(\d+)$")

    def __init__(self, debug=False):
        super().__init__(debug=debug)
        self.feed_rates = []

    def process(self, gcode_file):
        self.open_file(gcode_file)
        self.check_header()
        self.patch_extrusion()
        self.patch_moves()
        self.save_new_file()

    def check_header(self):
        index = 0
        while index < len(self.lines):
            # remove first line that Slic3r adds. We have no valve?
            if self.lines[index].startswith(b"M127"):
                self.lines.pop(index)
                break
            index += 1

    def add_extrusion_speed_line(self, extruder_on_index):
        # calculate mean and use it to set feed rate
        feed_rate = statistics.mean([rate for rate, speed in self.feed_rates])
        flow_rate = feed_rate * self.feed_rates[0][1] * SLIC3R_FLOW_MULTIPLIER
        self.lines.insert(extruder_on_index, b"M108 S%.1f" % float(flow_rate))
        #print(flow_rate, self.feed_rates[0][1])
        self.line_index += 1
        self.feed_rates = []

    def patch_extrusion(self):
        self.line_index = 0
        prev_position = (0.0, 0.0)
        extruder_on_index = 0
        prev_filament_pos = 0
        current_speed = 0

        while True:
            try:
                l, comment = self.read_line(self.line_index)
            except IndexError:
                break
            cmds = l.split()

            if cmds[0] == self.EXTRUDER_ON_CMD:
                if self.feed_rates and extruder_on_index:
                    self.add_extrusion_speed_line(extruder_on_index)
                extruder_on_index = self.line_index

            elif cmds[0] == self.EXTRUDER_OFF_CMD:
                # remove extra extruder off lines
                if not extruder_on_index:
                    self.delete_line(self.line_index)
                else:
                    self.add_extrusion_speed_line(extruder_on_index)
                    extruder_on_index = 0
            elif self.EXTRUSION_MOVE_RE.match(l):
                # read feed rate and add it to feed rate list
                if extruder_on_index:
                    if cmds[-1].startswith(b"F"):
                        values = self.EXTRUSION_MOVE_SPEED_RE.match(l).groups()
                        current_speed = float(values[3])
                    else:
                        values = self.EXTRUSION_MOVE_RE.match(l).groups()
                    position = (float(values[0]), float(values[1]))
                    path_len = self.calculate_path_length(prev_position, position)
                    filament_pos = float(values[2])
                    extrusion_len = self.calculate_extrusion_length(prev_filament_pos, filament_pos)
                    feed_rate = self.calculate_feed_rate(path_len, extrusion_len)
                    self.feed_rates.append((feed_rate, current_speed))
                    prev_position = position
                    prev_filament_pos = filament_pos
            elif self.SPEED_RE.match(l):
                # speed setting, not needed
                if extruder_on_index:
                    self.add_extrusion_speed_line(extruder_on_index)
                    self.lines[self.line_index] = self.EXTRUDER_OFF_CMD
                    extruder_on_index = 0
                else:
                    self.delete_line(self.line_index)
            elif self.EXTRUDER_RETRACT_RE.match(l):
                # extruder extract, not needed
                self.delete_line(self.line_index)
                # get filament position
                values = self.EXTRUDER_RETRACT_RE.match(l).groups()
                prev_filament_pos = float(values[0])
            elif self.MOVE_HEAD_RE.match(l):
                # if head is moving without extrusion, turn extruder off
                if extruder_on_index:
                    self.add_extrusion_speed_line(extruder_on_index)
                    self.lines.insert(self.line_index, self.EXTRUDER_OFF_CMD)
                    self.line_index += 1
                    extruder_on_index = 0
                values = self.MOVE_HEAD_RE.match(l).groups()
                prev_position = (float(values[0]), float(values[1]))

            self.line_index += 1

    def patch_moves(self):
        self.line_index = 0
        current_speed = 0
        current_z = 0

        def get_move_gcode(x, y, z, speed):
            return b"G1 X%.2f Y%.2f Z%.2f F%.2f" % (x, y, z, speed)

        while True:
            try:
                l, comment = self.read_line(self.line_index)
            except IndexError:
                break
            cmds = l.split()
            if self.Z_MOVE_RE.match(l):
                values = self.Z_MOVE_RE.match(l)
                current_z = float(values.groups()[0])
                self.delete_line(self.line_index)
            elif self.EXTRUSION_MOVE_RE.match(l):
                if cmds[-1].startswith(b"F"):
                    values = self.EXTRUSION_MOVE_SPEED_RE.match(l).groups()
                    current_speed = float(values[3])
                else:
                    values = self.EXTRUSION_MOVE_RE.match(l).groups()
                self.lines[self.line_index] = get_move_gcode(float(values[0]), float(values[1]), current_z, current_speed)
            elif self.MOVE_HEAD_RE.match(l):
                values = self.MOVE_HEAD_RE.match(l).groups()
                self.lines[self.line_index] = get_move_gcode(float(values[0]), float(values[1]), current_z, float(values[2]))
            self.line_index += 1


class KissPrintFile(PrintFile):

    SOLID_SETTING_KEY = b'bed_C'
    INFILL_SETTING_KEY = b'destring_speed_mm_per_s'
    LOOPS_INSIDEOUT = b'loops_insideout'

    SETTINGS_TO_READ = [SOLID_SETTING_KEY,
                        INFILL_SETTING_KEY,
                        LOOPS_INSIDEOUT]
    HEADER_STOP = b"*** G-code Prefix ***"

    LAYER_BEGIN_RE = re.compile(b"; BEGIN_LAYER_OBJECT")
    LAYER_END_RE = re.compile(b"; END_LAYER_OBJECT")
    SOLID_START_RE = re.compile(b"; 'Solid Path'")
    INFILL_START_RE = re.compile(b"; 'Sparse Infill Path'")
    EXTRUDER_ON_RE = re.compile(b"; extruder on")
    EXTRUDER_OFF_RE = re.compile(b"; extruder(s) off")
    PERIMETER_PATH_RE = re.compile(b"; 'Perimeter Path'")
    LOOP_PATH_RE = re.compile(b"; 'Loop Path'")
    PATH_RE = re.compile(b"; '.* Path'")

    def __init__(self, debug=False):
        super().__init__(debug=debug)

    def read_initial_settings(self):

        def read_setting_value(line):
            return line.split(b"=")[1].strip()

        for l in self.lines:
            if l.count(self.HEADER_STOP):
                return
            for setting in self.SETTINGS_TO_READ:
                if l.count(setting):
                    self.settings[setting] = read_setting_value(l)

    def patch_solid_extrusion(self):
        self.patch_extrusion(self.SOLID_START_RE, self.SOLID_SETTING_KEY, "solid")

    def patch_infill_extrusion(self):
        self.patch_extrusion(self.INFILL_START_RE, self.INFILL_SETTING_KEY, "infill")

    def patch_extrusion(self, start_re, setting_key, _type):
        multiplier = 1.0
        if setting_key in self.settings:
            ml = self.settings[setting_key]
            if ml == "100":
                log.info("Value of 100 set for %s extrusion, nothing to do" % _type)
                return
            solid_multiplier = float(ml) / 100
            log.info("Using multiplier %s for %s extrusion" % (solid_multiplier, _type))

        last_extrusion_speed = None
        last_extrusion_speed_line = None

        section_start = False

        index = 0
        while index < len(self.lines):
            l = self.lines[index]
            if l.startswith(self.EXTRUSION_SPEED_CMD):
                last_extrusion_speed = l
                last_extrusion_speed_line = index
            if start_re.match(l):
                section_start = True
            if section_start and self.EXTRUDER_ON_RE.match(l):
                new_val = self.update_extruder_speed(last_extrusion_speed, multiplier)
                self.lines[last_extrusion_speed_line] = new_val
                log.debug("Update line %s with value %s" % (last_extrusion_speed_line, new_val))
            if section_start and self.EXTRUDER_OFF_RE.match(l):
                section_start = False
            index += 1

    def _patch_perimeter(self, start_line, end_line):
        # WIP
        perimeters = []
        perimeter_start = None
        paths = []

        index = start_line
        while index < end_line:
            l = self.lines[index]
            if self.PATH_RE.match(l):
                paths.append(l)
                if self.PERIMETER_PATH_RE.match(l):
                    perimeter_start = index + 1
                else:
                    perimeter_count = 0
            elif perimeter_start and self.EXTRUDER_OFF_RE.match(l):
                # end of path
                perimeters.append((perimeter_start, index))
                perimeter_start = None

    def patch_perimeters(self):

        index = 0
        layer_start = 0
        while index < len(self.lines):
            l = self.lines[index]

            if self.LAYER_BEGIN_RE.match(l):
                layer_start = index + 1
            elif self.LAYER_END_RE.match(l):
                self._patch_perimeter(layer_start, index)

            index += 1

    def process(self, gcode_file):
        self.open_file(gcode_file)
        self.read_initial_settings()
        self.patch_solid_extrusion()
        self.patch_infill_extrusion()
        self.save_new_file()


class CuraPrintFile(PrintFile):

    LAYER_START_RE = re.compile(b';LAYER:')

    def __init__(self, debug=False):
        super().__init__(debug=debug)

    def process(self, gcode_file):
        self.open_file(gcode_file)
        #self.patch_auto_retraction()
        self.patch_first_layer_temp()
        self.save_new_file()

    def patch_auto_retraction(self):
        # remove retraction setting. Cube uses it's own setting for this apparently, so disable Cura's option
        # NOT NEEDE probably, Cura's setting seems to work
        index = 0
        while True:
            try:
                l = self.lines[index]
            except IndexError:
                break
            if l.startswith(b";enable auto-retraction"):
                self.lines.pop(index + 1)
                log.info("Removed auto rectraction command")
                return
            index += 1

    def patch_first_layer_width(self):
        # NOT NEEDED. Cura has first layer width parameter :)
        first_layer = False
        index = 0
        while True:
            try:
                l = self.lines[index]
            except IndexError:
                break
            if self.LAYER_START_RE.match(l):
                if not first_layer:
                    first_layer = True
                else:
                    # another layer starts, bail out
                    return
            elif l.startswith(self.EXTRUSION_SPEED_CMD):
                new_speed = self.update_extruder_speed(l, 1.1)
                self.lines[index] = new_speed
            index += 1

    def patch_first_layer_temp(self):
        # set temp for first layer, +10 for the setting at the beginning of the file
        layer_nr = 0
        temp_value = None
        temp_index = None
        index = 0
        while True:
            try:
                l = self.lines[index]
            except IndexError:
                break
            if self.LAYER_START_RE.match(l):
                layer_nr += 1
                if layer_nr == 1:
                    # layer starts. patch temp setting
                    layer_nr = 1
                    if temp_value:
                        new_value = ("%s" % (temp_value + 10)).encode()
                        self.lines[temp_index] = b"%s S%s" % (self.EXTRUDER_TEMP_CMD, new_value)
                        log.info("Patch first layer temp with line: %s" % self.lines[temp_index].decode())
            elif l.startswith(self.EXTRUDER_TEMP_CMD):
                # store temp value and line
                temp_value = int(l.split(b" ")[1].strip()[1:])
                if temp_value >= 280:
                    # 280 is the max
                    return
                temp_index = index
            elif layer_nr > 1 and l == self.EXTRUDER_OFF_CMD:
                if temp_value:
                    new_value = ("%s" % (temp_value)).encode()
                    self.lines.insert(index + 1, b"%s S%s" % (self.EXTRUDER_TEMP_CMD, new_value))
                    log.info("Add original temp line after first layer; %s" % self.lines[index].decode())
                return
            index += 1


def detect_file_type(gcode_file):
    with open(gcode_file, 'r') as gf:
        line1 = gf.readline()
        if line1.startswith('; KISSlicer'):
            log.info("Detected KISSlicer format")
            return KissPrintFile
        elif line1.startswith('; CURA'):
            log.info("Detected Cura format")
            return CuraPrintFile
        elif line1.startswith('; generated by Slic3r'):
            log.info("Detected Slic3r format")
            return Slic3rPrintFile
        else:
            log.error("No supported gcode file detected. Is comments enabled on Kisslicer or '; CURA' header added to Cura start.gcode?")
            exit(1)

if __name__ == "__main__":
    debug = False
    if len(sys.argv) < 2:
        log.error("Need argument for file to process")
        exit(1)
    if len(sys.argv) == 3 and sys.argv[2] == "--debug":
        debug = True

    print_type = detect_file_type(sys.argv[1])
    pf = print_type(debug=debug)
    pf.process(sys.argv[1])
