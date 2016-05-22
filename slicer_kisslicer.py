
import logging
import re

from base import PrintFile

log = logging.getLogger("Cubifier")

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