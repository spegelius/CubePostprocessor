import logging
import re

from base import SLICER_SIMPLIFY3D
from flavor_makerbot import MakerBotFlavor

log = logging.getLogger("Cubifier")


class Simplify3dPrintFile(MakerBotFlavor):

    slicer_type = SLICER_SIMPLIFY3D
    # Tune this to make filament flow fit your needs
    FLOW_MULTIPLIER = 0.365 # ok for MK8 drive gear

    def __init__(self, debug=False):
        super().__init__(debug=debug)


    def process(self, gcode_file):
        self.open_file(gcode_file)
        self.check_header()
        self.patch_extrusion()
        self.patch_moves()
        self.patch_fan_on_off()
        self.check_temp_change()
        self.remove_unused_cmds()
        self.save_new_file()


    def check_header(self):
        # Read temperature setting and replace it belowe Cube header
        self.line_index = 0

        header = False
        temp_line = None
        while True:
            try:
                l, comment = self.read_line()
                if l.startswith(b"^"):
                    # set flag
                    header = True
                elif l.startswith(self.EXTRUDER_TEMP_CMD):
                    if not header:
                        temp_line = l
                        self.delete_line()
                    elif l.split()[1] == b"SFIRST_LAYER":
                        self.lines[self.line_index] = temp_line
                        break
                elif not header:
                    self.delete_line(self.line_index)
            except IndexError:
                break
            self.line_index += 1