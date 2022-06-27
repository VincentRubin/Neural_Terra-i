import os
currentPath = os.getcwd()

import configparser
settings = configparser.ConfigParser()

import sys

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
import itertools
import matplotlib.pyplot as plt

# https://stackoverflow.com/questions/24816237/ipython-notebook-clear-cell-output-in-code
from IPython.display import clear_output

GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
HashMap = snappy.jpy.get_type('java.util.HashMap')

System = jpy.get_type('java.lang.System')
System.gc()

PrintWriterProgressMonitor = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
FileOutputStream = jpy.get_type('java.io.FileOutputStream')
ProductData = jpy.get_type('org.esa.snap.core.datamodel.ProductData')
Product = jpy.get_type('org.esa.snap.core.datamodel.Product')
GeoPos = jpy.get_type('org.esa.snap.core.datamodel.GeoPos')
PixelPos = jpy.get_type('org.esa.snap.core.datamodel.PixelPos')

from keras.datasets import mnist
from keras.models import Model
from keras.layers.core import Dense, Dropout, Flatten
#from tensorflow.keras.optimizers import RMSprop
from keras.utils import np_utils
from keras.layers.convolutional import Conv2D, MaxPooling2D, UpSampling2D
from keras.layers import Input, BatchNormalization
from sklearn import metrics as me
from scipy import stats
from keras import models
from keras import layers
from sklearn.preprocessing import Normalizer

import tensorflow as tf

folderStart = "K:/TM/data_output/subset_start"
folderResult = "K:/TM/data_output/subset_rotated"

print("IT WORKS !")