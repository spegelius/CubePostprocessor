import logging
import re

from base import PrintFile, SLICER_CURA

log = logging.getLogger("Cubifier")

class CuraPrintFile(PrintFile):

    slicer_type = SLICER_CURA
    LAYER_START_RE = re.compile(b';LAYER:')

    def __init__(self, debug=False):
        super().__init__(debug=debug)

    def process(self, gcode_file):
        self.open_file(gcode_file)
        #self.patch_auto_retraction()
        self.patch_first_layer_temp()
        return self.save_new_file()

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