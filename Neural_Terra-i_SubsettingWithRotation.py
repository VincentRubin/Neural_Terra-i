import os
currentPath = os.getcwd()

import configparser
settings = configparser.ConfigParser()
settings._interpolation = configparser.ExtendedInterpolation()
settings.read(currentPath + "/config/main_config.ini")

libs_path = settings.get('Main-Config', 'libs')
output_path = settings.get('Main-Config', 'output_path') + "/subset_end"

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

def createFolder(LocalityPath):
    if not os.path.exists(LocalityPath):
        os.makedirs(LocalityPath)

def getProductDim(pathRotated, pathReference, index):
	
	pathRotatedInput = os.path.join(pathRotated,'*.dim')
	filesRotated = glob.glob(pathRotatedInput)
	
	pathReferenceInput = os.path.join(pathReference,'*.dim')
	filesReference = glob.glob(pathReferenceInput)
	
	if len(filesRotated) == 0:
		print("No product found")
		
		f = open("product.txt", "a")
		f.truncate(0)
		f.write(str(-1))
		f.close()
		
		sys.exit(0)
	
	if len(filesRotated) > len(filesReference):
		print("Some references files are missing")
		
		f = open("product.txt", "a")
		f.truncate(0)
		f.write(str(-1))
		f.close()
		
		sys.exit(0)
		
	if len(filesRotated) < len(filesReference):
		print("Some rotated files are missing")
		
		f = open("product.txt", "a")
		f.truncate(0)
		f.write(str(-1))
		f.close()
		
		sys.exit(0)
		
	if index >= len(filesReference):
		
		print("Subsetting Finished")
		
		f = open("product.txt", "a")
		f.truncate(0)
		f.write(str(-1))
		f.close()
		
		sys.exit(0)
		
	products = []
	products.append(ProductIO.readProduct(filesRotated[index]))
	products.append(ProductIO.readProduct(filesReference[index]))
	
	return products

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

def subsettingWithRotationWriteAsDim(product, reference, bandIndex):
    
    # Create buffer
    channelCorrected = array.array('f', (float("NaN") for i in range(0, subsetSizeX * subsetSizeY)))
    
    channel = product.getBands()[bandIndex]
    channelStart = reference.getBands()[bandIndex]
    channelName = channelStart.getName()
    productName = reference.getName()
    channel.loadRasterData()

    w = channelStart.getRasterWidth()
    h = channelStart.getRasterHeight()
    
    geoCodingStart = channelStart.getGeoCoding()
    geoCoding = channel.getGeoCoding()

    geoPosCurrent = None
    pixelPosCurrent = None

    startX = marginX
    startY = marginY

    nbSubset = int((w - 2 * marginX) / subsetSizeX) * int((h - 2 * marginY) / subsetSizeY)
    nbSubsetDone = 1

    subsetPosX = 0
    subsetPosY = 0

    while(True):

        while(True):

            msg = "subsetting advancement : " + str(nbSubsetDone) + "/" + str(nbSubset) + "(" + str("{:.2f}".format(nbSubsetDone / nbSubset * 100)) + "%)"

            for y in range(0, subsetSizeY):

                clear_output(wait=True)
                print(msg)
                print("Current Subset : " + str("{:.2f}".format(y / subsetSizeY * 100)) + "%")

                for x in range(0, subsetSizeX):

                    geoPosCurrent = geoCodingStart.getGeoPos(PixelPos(x + startX, y + startY), geoPosCurrent)
                    pixelPosCurrent = geoCoding.getPixelPos(geoPosCurrent, pixelPosCurrent)

                    # Row Major
                    channelCorrected[y * subsetSizeX + x] = channel.getPixelFloat(
                        int(pixelPosCurrent.getX()), 
                        int(pixelPosCurrent.getY()))

            fileName = productName + "_SUBSET_ROTA_" + str(channelName) + str(subsetSizeX) + "_" + str(subsetSizeY) + "_" + str(subsetPosX) + "_" + str(subsetPosY)

            productNew = Product(fileName, product.getProductType(), subsetSizeX, subsetSizeY)

            snappy.ProductUtils.copyGeoCoding(product, productNew)
            snappy.ProductUtils.copyMetadata(product, productNew)    

            productNew.addBand(channelName, ProductData.TYPE_FLOAT32)

            writer = ProductIO.getProductWriter('BEAM-DIMAP')
            productNew.setProductWriter(writer)
            productNew.writeHeader(output_path + "/" + fileName +  ".dim")

            bandNew = productNew.getBand(channelName)
            bandNew.writePixels(startX - marginX, startY - marginY, subsetSizeX, subsetSizeY, channelCorrected)

            productNew.closeIO()

            startX += subsetSizeX
            subsetPosX += 1
            nbSubsetDone += 1

            if startX + subsetSizeX > w - marginX:
                startX = marginX
                subsetPosX = 0
                break

        startY += subsetSizeY
        subsetPosY += 1

        if startY + subsetSizeY > h - marginY:
            break

    del channelCorrected
    channel.unloadRasterData()
            
    print("subsettingWithRotationWriteAsDim - END")
	
def subsettingWithRotationWriteAsArray(product, reference, bandIndex, limit):
    
    print("subsettingWithRotationWriteAsArray - START")
    
    # Create buffer
    channelCorrected = []
    
    channel = product.getBands()[bandIndex]
    channelStart = reference.getBands()[bandIndex]
    channelName = channelStart.getName()
    productName = reference.getName()
    channel.loadRasterData()

    w = channelStart.getRasterWidth()
    h = channelStart.getRasterHeight()
    
    geoCodingStart = channelStart.getGeoCoding()
    geoCoding = channel.getGeoCoding()

    geoPosCurrent = None
    pixelPosCurrent = None

    startX = marginX
    startY = marginY

    nbSubset = int((w - 2 * marginX) / subsetSizeX) * int((h - 2 * marginY) / subsetSizeY)
    nbSubsetDone = 1

    subsetPosX = 0
    subsetPosY = 0
    
    nbWrited = 0
	
    while(True):

        while(True):
            
            createFolder(output_path + "/" + str(productName) + "_" + str(subsetPosX) + "_" + str(subsetPosY))
            
            msg = "subsetting advancement : " + str(nbSubsetDone) + "/" + str(nbSubset) + " - (" + str("{:.2f}".format(nbSubsetDone / nbSubset * 100)) + "%)"

            for y in range(0, subsetSizeY):
                
                if os.path.exists(output_path + "/" + str(productName) + "_" + str(subsetPosX) + "_" + str(subsetPosY) + "/" + str(channelName) + ".npz"):
                    break
                
                channelCorrected.append([])

                print(msg)
                print("Current Subset : " + str("{:.2f}".format(y / subsetSizeY * 100)) + "%")

                for x in range(0, subsetSizeX):

                    geoPosCurrent = geoCodingStart.getGeoPos(PixelPos(x + startX, y + startY), geoPosCurrent)
                    pixelPosCurrent = geoCoding.getPixelPos(geoPosCurrent, pixelPosCurrent)
                    
                    channelCorrected[y].append(channel.getPixelFloat(
                        int(pixelPosCurrent.getX()), 
                        int(pixelPosCurrent.getY())))
						
                print("\033[A\033[A")
                print("\033[A\033[A")
            
            if not os.path.exists(output_path + "/" + str(productName) + "_" + str(subsetPosX) + "_" + str(subsetPosY) + "/" + str(channelName) + ".npz"):
                	
                np.savez_compressed(output_path + "/" + str(productName) + "_" + str(subsetPosX) + "_" + str(subsetPosY) + "/" + str(channelName), channelCorrected)
                nbWrited += 1
        
            channelCorrected.clear()

            startX += subsetSizeX
            subsetPosX += 1
            nbSubsetDone += 1

            if startX + subsetSizeX > w - marginX or nbWrited >= limit:
                startX = marginX
                subsetPosX = 0
                break

        startY += subsetSizeY
        subsetPosY += 1

        if startY + subsetSizeY > h - marginY or nbWrited >= limit:
            break

    del channelCorrected
    channel.unloadRasterData()
          
    print(msg)
		  
    print("subsettingWithRotationWriteAsArray - END")
	
    return nbSubset == nbSubsetDone - 1
    
def compresseSubsetting(path):
    
    print("temp")

if len(sys.argv) < 5 :
	
	print("You need to precise : path_to_rotated_file, path_to_reference_file, limit, product index and band index (Ex : python script.py pathRotated pathReference 100 0 0)")
	sys.exit(0)

pathRotated = sys.argv[1]
pathReference = sys.argv[2]
limit = int(sys.argv[3])
productIndex = int(sys.argv[4])
bandIndex = int(sys.argv[5])

if limit < 1 :
	
	print("Limit must be greater than 0")
	sys.exit(0)
	
if productIndex < 0 :
	
	print("Product index must be greater or equal 0")
	sys.exit(0)
	
if bandIndex < 0 :
	
	print("Band index must be greater or equal 0")
	sys.exit(0)

tempProduct = getProductDim(pathRotated, pathReference, productIndex)

productRotated = tempProduct[0]
productReferences = tempProduct[1]

result = subsettingWithRotationWriteAsArray(productRotated, productReferences, bandIndex, limit)

if result == True:
	
	if bandIndex == len(productRotated.getBands()) - 1:
		f = open("product.txt", "a")
		f.truncate(0)
		f.write(str(productIndex + 1))
		f.close()
		
		f = open("band.txt", "a")
		f.truncate(0)
		f.write(str(0))
		f.close()
		
	else:
		f = open("product.txt", "a")
		f.truncate(0)
		f.write(str(productIndex))
		f.close()
	
		f = open("band.txt", "a")
		f.truncate(0)
		f.write(str(bandIndex + 1))
		f.close()
else:
    f = open("product.txt", "a")
    f.truncate(0)
    f.write(str(productIndex))
    f.close()
	
    f = open("band.txt", "a")
    f.truncate(0)
    f.write(str(bandIndex))
    f.close()