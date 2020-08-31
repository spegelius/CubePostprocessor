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
Version 0.7



## Installation

### Install cube-utils:
git clone https://github.com/devincody/cube-utils
cd cube-utils
make
make install

### Install CubePostprocessor:
git clone https://github.com/devincody/CubePostprocessor
cd CubePostprocessor
python setup.py install
