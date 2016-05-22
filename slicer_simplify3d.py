import logging
import re

from slicer_slic3r import Slic3rPrintFile

log = logging.getLogger("Cubifier")

class Simplify3dPrintFile(Slic3rPrintFile):

    def __init__(self, debug=False):
        super().__init__(debug=debug)

