
from base import SLICER_SLIC3R
from flavor_makerbot import MakerBotFlavor

class Slic3rPrintFile(MakerBotFlavor):

    slicer_type = SLICER_SLIC3R

    def __init__(self, debug=False):
        super().__init__(debug=debug)


