import logging
import re

from base import SLICER_SIMPLIFY3D
from flavor_makerbot import MakerBotFlavor

log = logging.getLogger("Cubifier")

class Simplify3dPrintFile(MakerBotFlavor):

    slicer_type = SLICER_SIMPLIFY3D

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
        replace_counter = 0
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
                    else:
                        self.lines[self.line_index] = temp_line
                        if replace_counter == 1:
                            break
                        replace_counter += 1
                elif not header:
                    self.delete_line(self.line_index)
            except IndexError:
                break
            self.line_index += 1