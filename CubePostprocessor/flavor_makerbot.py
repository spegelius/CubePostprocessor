import logging
import re
import statistics

from CubePostprocessor.base import *

log = logging.getLogger("Cubifier")

class MakerBotFlavor(PrintFile):

    EXTRUDER_RETRACT_RE = re.compile(b"^G1 E([-]*\d+\.\d+) F(\d+\.*\d*)$")
    Z_MOVE_RE = re.compile(b"^G1 Z([-]*\d+\.\d+) F(\d+\.*\d*)$")
    EXTRUSION_MOVE_RE = re.compile(b"^G1 X([-]*\d+\.\d+) Y([-]*\d+\.\d+) E(\d+\.\d+)")
    EXTRUSION_MOVE_SPEED_RE = re.compile(b"^G1 X([-]*\d+\.\d+) Y([-]*\d+\.\d+) E(\d+\.\d+) F(\d+\.*\d*)$")
    MOVE_HEAD_RE = re.compile(b"^G1 X([-]*\d+\.\d+) Y([-]*\d+\.\d+) F(\d+\.*\d*)$")
    SPEED_RE = re.compile(b"^G1 F(\d+\.*\d*)$")
    EXTRUDER_POSITION_RE = re.compile(b"^G92 E0$")

    FLOW_MULTIPLIER = 1 # change this in inheriting classes

    def __init__(self, debug=False):
        super().__init__(debug=debug)
        self.feed_rates = []

    def process(self, gcode_file):
        self.open_file(gcode_file)
        self.check_header()
        self.patch_extrusion()
        self.patch_moves()
        self.patch_fan_on_off()
        self.check_temp_change()
        return self.save_new_file()

    def check_header(self):
        # Remove lines before Cube header
        self.line_index = 0
        while True:
            try:
                l, comment = self.read_line(self.line_index)
                if l.startswith(b"^Firmware"):
                    break
                else:
                    self.delete_line(self.line_index)
            except IndexError:
                break
            self.line_index += 1

    def patch_fan_on_off(self):
        self.line_index = 0
        while True:
            try:
                l, comment = self.read_line(self.line_index)
                if l.startswith(b"M127"):
                    self.lines[self.line_index] = l.replace(b"M127", b"M107")
                elif l.startswith(b"M126"):
                    self.lines[self.line_index] = l.replace(b"M126", b"M106")
            except IndexError:
                break
            self.line_index += 1

    def add_extrusion_speed_line(self, extruder_on_index):
        # calculate mean and use it to set feed rate
        feed_rate = statistics.mean([rate for rate, speed in self.feed_rates])
        flow_rate = feed_rate * self.feed_rates[0][1] * self.FLOW_MULTIPLIER
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

        # for preserving the first extruder off cmd
        ext_off_line_count = 0

        simplify3d_extruder_position_index = -1

        while True:
            try:
                l, comment = self.read_line(self.line_index)
            except IndexError:
                break
            cmds = l.split()
            if cmds[0] == self.EXTRUDER_ON_CMD:
                # Extruder on. Slic3r format
                if self.feed_rates and extruder_on_index:
                    self.add_extrusion_speed_line(extruder_on_index)
                extruder_on_index = self.line_index

            elif cmds[0] == self.EXTRUDER_OFF_CMD:
                # remove extra extruder off lines
                if extruder_on_index:
                    self.add_extrusion_speed_line(extruder_on_index)
                    extruder_on_index = 0
                elif ext_off_line_count:
                    self.delete_line()

            elif self.slicer_type == SLICER_SIMPLIFY3D and self.EXTRUDER_POSITION_RE.match(l):
                # extruder position reset. Simplify3d format
                prev_filament_pos = 0
                simplify3d_extruder_position_index = self.line_index

            elif self.EXTRUSION_MOVE_RE.match(l):

                if self.slicer_type == SLICER_SIMPLIFY3D and self.EXTRUSION_MOVE_SPEED_RE.match(l):
                    # Simplify3D specific
                    self.lines[simplify3d_extruder_position_index] = self.EXTRUDER_ON_CMD
                    extruder_on_index = simplify3d_extruder_position_index
                    values = self.EXTRUSION_MOVE_SPEED_RE.match(l).groups()
                    current_speed = float(values[3])

                # read feed rate and add it to feed rate list
                if extruder_on_index:
                    if self.slicer_type == SLICER_SLIC3R and cmds[-1].startswith(b"F"):
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
                # speed setting, not needed. G1 F900
                if extruder_on_index:
                    self.add_extrusion_speed_line(extruder_on_index)
                    self.lines[self.line_index] = self.EXTRUDER_OFF_CMD
                    ext_off_line_count += 1
                    extruder_on_index = 0
                else:
                    self.delete_line(self.line_index)
            elif self.EXTRUDER_RETRACT_RE.match(l):
                # extruder retract, not needed. G1 E-2.00000 F2400.00000
                self.delete_line(self.line_index)
                # get filament position
                values = self.EXTRUDER_RETRACT_RE.match(l).groups()
                prev_filament_pos = float(values[0])
            elif self.MOVE_HEAD_RE.match(l):
                # if head is moving without extrusion, turn extruder off
                if extruder_on_index:
                    self.add_extrusion_speed_line(extruder_on_index)
                    self.lines.insert(self.line_index, self.EXTRUDER_OFF_CMD)
                    ext_off_line_count += 1
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
            return b"G1 X%.3f Y%.3f Z%.3f F%.1f" % (x, y, z, speed)

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

    def check_temp_change(self):
        self.line_index = 0
        extruder_on = False
        while True:
            try:
                l, comment = self.read_line(self.line_index)
            except IndexError:
                break
            cmds = l.split()
            if cmds[0] == self.EXTRUDER_ON_CMD:
                extruder_on = True
            elif cmds[0] == self.EXTRUDER_OFF_CMD:
                extruder_on = False
            elif cmds[0] == self.EXTRUDER_TEMP_CMD and extruder_on:
                self.lines.insert(self.line_index, self.EXTRUDER_OFF_CMD)
                self.line_index += 1
            self.line_index += 1