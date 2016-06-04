
from base import SLICER_SLIC3R
from flavor_makerbot import MakerBotFlavor


class Slic3rPrintFile(MakerBotFlavor):

    slicer_type = SLICER_SLIC3R
    # Tune this to make filament flow fit your needs
    FLOW_MULTIPLIER = 0.365 # ok for MK8 drive gear

    def __init__(self, debug=False):
        super().__init__(debug=debug)
