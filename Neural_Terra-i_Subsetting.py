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

outFormat = 'ESRI Shapefile'

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

bandNamesC = []
bandNamesC.append("Amplitude_VH")
bandNamesC.append("Amplitude_VV")
bandNamesC.append("elevation")

def createFolder(LocalityPath):
    if not os.path.exists(LocalityPath):
        os.makedirs(LocalityPath)

def getProductDim(path, index):

	pathInput = os.path.join(path,'*.dim')
	files = glob.glob(pathInput)

	if len(files) == 0:
		print("No product found")

		f = open("product.txt", "a")
		f.truncate(0)
		f.write(str(-1))
		f.close()

		sys.exit(0)

	if index >= len(files):

		print("Subsetting Finished")

		f = open("product.txt", "a")
		f.truncate(0)
		f.write(str(-1))
		f.close()

		sys.exit(0)

	return ProductIO.readProduct(files[index])

def getProductList():
    productList = []
    unzipAllFileArchives(folderPath)
    for folder in os.listdir(folderPath):
        product = ProductIO.readProduct(os.path.join(folderPath,folder, "manifest.safe"))
        productList.append(product)
    return productList

def getProductListDim(paths):

    products = []

    for path in paths :

        lbs_input_path = os.path.join(path,'*.dim')
        files = glob.glob(lbs_input_path)

        for f in files:
            product = ProductIO.readProduct(f)
            products.append(product)

    return products

def subsettingWriteAsArray(product, limit):

    print("subsettingWriteAsArray - START")

    # Create buffer
    channels = []

    productName = product.getName()

    w = product.getBands()[0].getRasterWidth()
    h = product.getBands()[0].getRasterHeight()

    startX = marginX
    startY = marginY

    nbSubset = int((w - 2 * marginX) / subsetSizeX) * int((h - 2 * marginY) / subsetSizeY)
    nbSubsetDone = 1

    subsetPosX = 0
    subsetPosY = 0

    nbWrited = 0

    subsetSize = subsetSizeX * subsetSizeY

    createFolder(output_path)

    while(True):

        while(True):

            msg = "subsetting advancement : " + str(nbSubsetDone) + "/" + str(nbSubset) + " - (" + str("{:.2f}".format(nbSubsetDone / nbSubset * 100)) + "%)"

            print(msg)

            for band in product.getBands():

                if os.path.exists(output_path + "/" + str(productName) + "_" + str(subsetPosX) + "_" + str(subsetPosY) + ".npz"):
                    break

				if band.getName() in bandNamesC:

					channels.append(array.array('f', (float("NaN") for i in range(0, subsetSize)))) # int : i, float : f
					band.readPixels(startX, startY, subsetSizeX, subsetSizeY, channels[-1])

            for grid in product.getTiePointGrids():

                if os.path.exists(output_path + "/" + str(productName) + "_" + str(subsetPosX) + "_" + str(subsetPosY) + ".npz"):
                    break

                gridRaster = product.getRasterDataNode(grid.getName())

                channels.append(array.array('f', (float("NaN") for i in range(0, subsetSize)))) # int : i, float : f
                gridRaster.readPixels(startX, startY, subsetSizeX, subsetSizeY, channels[-1])

            if not os.path.exists(output_path + "/" + str(productName) + "_" + str(subsetPosX) + "_" + str(subsetPosY) + ".npz"):

                for i in range(len(channels)):
                    channels[i] = np.array_split(channels[i], subsetSizeX)

                np.savez_compressed(output_path + "/" + str(productName) + "_" + str(subsetPosX) + "_" + str(subsetPosY), channels)
                nbWrited += 1

            channels.clear()

            startX += subsetSizeX
            subsetPosX += 1
            nbSubsetDone += 1

            print("\033[A\033[A")

            if startX + subsetSizeX > w - marginX or nbWrited >= limit:
                startX = marginX
                subsetPosX = 0
                break

        startY += subsetSizeY
        subsetPosY += 1

        if startY + subsetSizeY > h - marginY or nbWrited >= limit:
            break

    del channels

    print(msg)

    print("subsettingWriteAsArray - END")

    return nbSubset == nbSubsetDone - 1

if len(sys.argv) < 3 :

	print("You need to precise : path_to_file, limit, product index and band index (Ex : python script.py path 100 0)")
	sys.exit(0)

pathFile = sys.argv[1]
limit = int(sys.argv[2])
productIndex = int(sys.argv[3])

if limit < 1 :

	print("Limit must be greater than 0")
	sys.exit(0)

if productIndex < 0 :

	print("Product index must be greater or equal 0")
	sys.exit(0)

product = getProductDim(pathFile, productIndex)

print(product.getBandNames())

result = subsettingWriteAsArray(product, limit)

f = open("product.txt", "a")
f.truncate(0)

if result == True:
    f.write(str(productIndex + 1))
else:
    f.write(str(productIndex))

f.close()
