import os
currentPath = os.getcwd()

import configparser
settings = configparser.ConfigParser()
settings._interpolation = configparser.ExtendedInterpolation()
settings.read(currentPath + "/config/main_config.ini")

libs_path = settings.get('Main-Config', 'libs')
output_path = settings.get('Main-Config', 'output_path') + "/subset_start"

subsetSizeX = int(settings.get('Main-Config', 'subsetSizeX'))
subsetSizeY = int(settings.get('Main-Config', 'subsetSizeY'))
marginX = int(settings.get('Main-Config', 'marginX'))
marginY = int(settings.get('Main-Config', 'marginY'))

import sys
sys.path.append(libs_path)

from osgeo import gdal,ogr, osr
gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()

import snappy
from snappy import ProductIO
from snappy import HashMap
from snappy import GPF
from snappy import jpy

import os
import os.path
from collections import OrderedDict
from datetime import datetime
import datetime
from datetime import timedelta, date
import time

import numpy as np
import glob
from itertools import cycle
import math
import shutil
import json
import geojson
import random

import array
import numpy as np
import itertools
import matplotlib.pyplot as plt

# https://stackoverflow.com/questions/24816237/ipython-notebook-clear-cell-output-in-code
from IPython.display import clear_output

print("IT WORKS !")