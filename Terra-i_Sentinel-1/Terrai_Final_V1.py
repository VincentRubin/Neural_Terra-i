########################################################
# Script file for Terra-i
# Author  : Louis Reymondin, Trong Phan Van, Thuy Nguyen
# Version : 3.0
# Creation date : Fri Feb 05 13:20:37 GMT-05:00 2018
########################################################

import configparser

import sys

import fiona
import rasterio
import rasterio.mask
import rasterio.merge

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

currentPath = os.getcwd()

settings = configparser.ConfigParser()
settings._interpolation = configparser.ExtendedInterpolation()
settings.read(currentPath + "/config/main_config.ini")

libs = settings.get('Main-Config', 'libs')
sys.path.append(libs)

outFormat = 'ESRI Shapefile'

#env_gdal = settings.get('Main-Config', 'gdal')
#os.environ['GDAL_DATA'] = env_gdal

GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
HashMap = snappy.jpy.get_type('java.util.HashMap')
BandDescriptor = jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
System = jpy.get_type('java.lang.System')
System.gc()

PrintWriterProgressMonitor = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
FileOutputStream = jpy.get_type('java.io.FileOutputStream')

opt = snappy.jpyutil.get_jvm_options()

projectName     = settings.get('Main-Config', 'project_name')
home            = settings.get('Main-Config', 'home_path')
log_path        = settings.get('Main-Config', 'log_path')
folderPath      = settings.get('Main-Config', 'folder_path')
studyAreaSHP    = settings.get('Main-Config', 'study_area')
forest_map      = settings.get('Forest-Config', 'forest_map')
epsg            = settings.get('Main-Config', 'epsg')
mapProjection   = settings.get('Main-Config', 'imageProjection')
startDate       = settings.get('Main-Config', 'startDate')
endDate         = settings.get('Main-Config', 'endDate')

processTimeInFunction = None	# Used to measure the time needed to processing the data in a function
writeTimeInFunction = None		# Used to measure the time needed to write the data in a function

with open(currentPath + "/config/parameters_zone10.json") as json_data_file:
    data = json.load(json_data_file)

def unzipAllFileArchives(folderPath, extension=".zip"):
    import os, zipfile
    os.chdir(folderPath)
    for item in os.listdir(folderPath):
        if item.endswith(extension):
            file_name = os.path.abspath(item)
            zip_ref = zipfile.ZipFile(file_name)
            zip_ref.extractall(folderPath)
            zip_ref.close()
            os.remove(file_name)

def getListOfFiles(folderPath):
    import os
    return os.listdir(folderPath)

def CreateFolder(LocalityPath):
    if not os.path.exists(LocalityPath):
        os.makedirs(LocalityPath)

def writeToLog(message, messageType='ERROR', log_path = log_path):
    import logging,os
    logger = logging.getLogger('')
    hdlr = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s', datefmt='%H:%M:%S')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    #print("Writing to log file: '{0}'".format(log_path))
    if (messageType.upper() == 'ERROR'):
        logger.error(message)
    elif (messageType.upper() == 'WARNING'):
        logger.warning(message)
    else:
        logger.info(message)
    logger.removeHandler(hdlr)

def removeProduct(file_path):
    if (os.path.exists(file_path)):
        shutil.rmtree(file_path)
    else:
        writeToLog("\t".join(["removeProduct", "Trying to remove non-existing file: {0}".format(file_path)]), "warning")

# Step 0
def GetProductList():
    productList = []
    unzipAllFileArchives(folderPath)

    for folder in os.listdir(folderPath):
        product = ProductIO.readProduct(os.path.join(folderPath,folder, "manifest.safe"))
        productList.append(product)
    return productList

# Step 1
def GetApplyOrbit(products, write_product):

    global writeTimeInFunction
    global processTimeInFunction

    startTimeProcess = time.time()

    orbit_list = []
    orbit_folder = os.path.join(home, projectName, 'Results', '1.ApplyOrbit', '')
    CreateFolder(orbit_folder)
    for product in products:
        orbit_name = product.getName() + '.dim'
        orbit_path = os.path.join(orbit_folder, orbit_name)

        #print("############## TEST ##############")
        #CreateFolder(orbit_folder + "\\TEST")
        #ProductIO.writeProduct(product, orbit_folder + "\\TEST", 'BEAM-DIMAP')

        if not os.path.exists(orbit_path):
            #print('Processing: ' + orbit_name)
            orbit_hashmap = HashMap()
            orbit_hashmap.put('continueOnFail', True)
            orbit_hashmap.put('Apply-Orbit-File', True)
            orbit = GPF.createProduct("Apply-Orbit-File", orbit_hashmap, product)

            orbit_list.append(orbit)

            #print("///////////////////////////////////////////////////")
            #print(orbit)
            #print("///////////////////////////////////////////////////")


            fileOutputStream = FileOutputStream(orbit_folder + "\\1.progress.txt")
            printWriterProgressMonitor = PrintWriterProgressMonitor(fileOutputStream)

            PWPM = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
            JavaSystem = jpy.get_type('java.lang.System')
            monitor = PWPM(JavaSystem.out)

            if write_product:
                startTimeWrite = time.time()
                ProductIO.writeProduct(orbit, orbit_path, 'BEAM-DIMAP', monitor)
                writeTimeInFunction = time.time() - startTimeWrite
            orbit.dispose()
            product.dispose()
            del orbit
            del product
            del orbit_hashmap
        else:
            writeToLog("\t".join(["GetApplyOrbit", "File " + "'" + orbit_name + "'" + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    del products
    products = None
    print('APPLY ORBIT..................................DONE\n')

    processTimeInFunction = time.time() - startTimeProcess

    return(orbit_list)

# Step 2
def GetRemoveThermalNoise(products, write_product):

    global writeTimeInFunction
    global processTimeInFunction

    startTimeProcess = time.time()

    if products == None:
        products = []
        orbit_input_path = os.path.join(home, projectName, 'Results', '1.ApplyOrbit', '*.dim')
        files = glob.glob(orbit_input_path)

        for f in files:
            product = ProductIO.readProduct(f)
            products.append(product)

    noise_list = []
    noise_folder = os.path.join(home,projectName,'Results','2.RemoveThermalNoise','')
    CreateFolder(noise_folder)
    for product in products:
        #print("--------------------------------------")
        #print("product : ")
        #print(product)
        #print(product.getProductReader())
        #print("--------------------------------------")
        noise_name = product.getName() + '.dim'
        noise_path = os.path.join(noise_folder,noise_name)
        if not os.path.exists(noise_path):
            print('Processing:' + noise_name)
            noise_hashmap = HashMap()
            noise_hashmap.put('removeThermalNoise',True)
            noise_hashmap.put('reIntroduceThermalNoise',False)
            noise = GPF.createProduct('ThermalNoiseRemoval',noise_hashmap,product)
            noise_list.append(noise)

            fileOutputStream = FileOutputStream(noise_folder + "\\2.progress.txt")
            printWriterProgressMonitor = PrintWriterProgressMonitor(fileOutputStream)

            PWPM = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
            JavaSystem = jpy.get_type('java.lang.System')
            monitor = PWPM(JavaSystem.out)

            if write_product:
                startTimeWrite = time.time()
                ProductIO.writeProduct(noise,noise_path,'BEAM-DIMAP', monitor)
                writeTimeInFunction = time.time() - startTimeWrite
            noise.dispose()
            product.dispose()
            del noise
            del noise_hashmap
            del product
        else:
            writeToLog("\t".join(["getRemoveThermalNoise", "File " + "'" + noise_name + "'" + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    del products
    products = None
    print('REMOVE THEMAL NOISE..........................DONE\n')

    processTimeInFunction = time.time() - startTimeProcess

    return(noise_list)

# Step 2.5
def GetRemoveBorderNoise(products, write_product):

    global writeTimeInFunction
    global processTimeInFunction

    startTimeProcess = time.time()

    if products == None:
        products = []
        noise_input_path = os.path.join(home, projectName, 'Results', '2.RemoveThermalNoise', '*.dim')
        files = glob.glob(noise_input_path)

        for f in files:
            product = ProductIO.readProduct(f)
            products.append(product)

    border_list = []
    border_folder = os.path.join(home, projectName, 'Results', '2.5.RemoveBorderNoise', '')
    CreateFolder(border_list)

    for product in products:
        border_name = product.getName() + '.dim'
        border_path = os.path.join(border_folder, border_name)

        if not os.path.exists(orbit_path):

            border_hashmap = HashMap()
            border_hashmap.put('removeThermalNoise',True)
            border_hashmap.put('reIntroduceThermalNoise',False)
            border = GPF.createProduct('ThermalNoiseRemoval', border_hashmap, product)

            border_list.append(border)

            fileOutputStream = FileOutputStream(border_folder + "\\1.progress.txt")
            printWriterProgressMonitor = PrintWriterProgressMonitor(fileOutputStream)

            PWPM = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
            JavaSystem = jpy.get_type('java.lang.System')
            monitor = PWPM(JavaSystem.out)

            if write_product:
                startTimeWrite = time.time()
                ProductIO.writeProduct(border, border_path, 'BEAM-DIMAP', monitor)
                writeTimeInFunction = time.time() - startTimeWrite

            border.dispose()
            product.dispose()

            del border
            del product
            del border_hashmap
        else:
            writeToLog("\t".join(["GetApplyBorderNoises", "File " + "'" + orbit_name + "'" + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    del products
    products = None
    print('REMOVE BORDER NOISE..................................DONE\n')

    processTimeInFunction = time.time() - startTimeProcess

    return(border_list)

# Step 3
def GetCalibration(products, write_product):

    global writeTimeInFunction
    global processTimeInFunction

    startTimeProcess = time.time()

    if products == None:
        products = []
        noise_input_path = os.path.join(home,projectName,'Results','2.RemoveThermalNoise','*.dim')
        #noise_input_path = os.path.join(home,projectName,'Results','2.5.RemoveBorderNoise','*.dim')
        files = glob.glob(noise_input_path)

        for f in files:
            product = ProductIO.readProduct(f)
            products.append(product)

    calib_list = []
    calib_folder = os.path.join(home,projectName,'Results','3.Calibration','')
    CreateFolder(calib_folder)
    for product in products:
        calib_name = product.getName() + '.dim'
        calib_path = os.path.join(calib_folder,calib_name)
        if not os.path.exists(calib_path):
            print('Processing:' + calib_name)
            calib_hashmap = HashMap()
            #calib_hashmap.put('auxFile','LATEST_AUX')
            calib_hashmap.put('outputSigmaBand',True)
            calib_hashmap.put('outputBetaBand',False) #outputBetaBand
            calib_hashmap.put('outputGammaBand',False)
            calib_hashmap.put('outputImageScaleInDb',False)
            calib = GPF.createProduct("Calibration",calib_hashmap,product)
            calib_list.append(calib)

            fileOutputStream = FileOutputStream(calib_folder + "\\3.progress.txt")
            printWriterProgressMonitor = PrintWriterProgressMonitor(fileOutputStream)

            PWPM = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
            JavaSystem = jpy.get_type('java.lang.System')
            monitor = PWPM(JavaSystem.out)

            if write_product:
                startTimeWrite = time.time()
                ProductIO.writeProduct(calib,calib_path,'BEAM-DIMAP', monitor)
                writeTimeInFunction = time.time() - startTimeWrite
            calib.dispose()
            product.dispose()
            calib_hashmap = None
            del calib
            del calib_hashmap
            del product
        else:
            print(calib_path + 'File already exist. Exit without changes and move to new image.')
            writeToLog("\t".join(["GetCalibration", "File " + "'" + calib_name + "'" + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    del products
    products = None
    print('RADIOMETRIC CALIBRATION......................DONE\n')

    processTimeInFunction = time.time() - startTimeProcess

    return(calib_list)

# Step 4
def GetSpeckleFilter(products, write_product):

    global writeTimeInFunction
    global processTimeInFunction

    startTimeProcess = time.time()

    if products == None:
        products = []
        cal_input_path = os.path.join(home,projectName,'Results','3.Calibration','*.dim')
        files = glob.glob(cal_input_path)

        for f in files:
            product = ProductIO.readProduct(f)
            products.append(product)

    speck_list = []
    speck_folder = os.path.join(home,projectName,'Results','4.SpeckleFilter','')
    CreateFolder(speck_folder)
    for product in products:
        speck_name = product.getName() + '.dim'
        speck_path = os.path.join(speck_folder,speck_name)
        if not os.path.isfile(speck_path):
            print('Processing:' + speck_name)
            speck_hashmap = HashMap()
            speck_hashmap.put('outputSigmaBand',True)
            speck_hashmap.put('filter','Gamma Map')
            speck_hashmap.put('filterSizeX',3)
            speck_hashmap.put('filterSizeY',3)
            speck_hashmap.put('estimateENL',True)
            speck_hashmap.put('enl', 1.0)
            speck = GPF.createProduct("Speckle-Filter",speck_hashmap,product)
            speck_list.append(speck)

            fileOutputStream = FileOutputStream(speck_folder + "\\4.progress.txt")
            printWriterProgressMonitor = PrintWriterProgressMonitor(fileOutputStream)

            PWPM = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
            JavaSystem = jpy.get_type('java.lang.System')
            monitor = PWPM(JavaSystem.out)

            if write_product:
                startTimeWrite = time.time()
                ProductIO.writeProduct(speck,speck_path,'BEAM-DIMAP', monitor)
                writeTimeInFunction = time.time() - startTimeWrite
            speck.dispose()
            product.dispose()
            del speck
            del speck_hashmap
            del product
        else:
            print(speck_path + 'File already exist. Exit without changes and move to new image.')
            writeToLog("\t".join(["getSpeckleFilter", "File " + "'" + speck_name + "'" + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    del products
    products = None
    print('SPECKLE FILTER...............................DONE')

    processTimeInFunction = time.time() - startTimeProcess

    return(speck_list)

# step 5

def isDuplicatedDate(product, products):
  c1 = product.split("_")[4]
  c2 = c1.split("T")[0]
  c  = sum(c2 in s for s in products)
  if c > 1:
    return True
  return False

def MosaicAll(write_product):

    global writeTimeInFunction
    global processTimeInFunction

    startTimeProcess = time.time()

    products = []

    spkFilter_input_path = os.path.join(home, projectName, 'Results', '4.SpeckleFilter', '*.dim')
    files = glob.glob(spkFilter_input_path)

    for f in files:
        product = ProductIO.readProduct(f)
        products.append(product)
        names = product.getName()

    mosaic_dataset = dict()
    mosaiking_list = []
    mosaic_folder = os.path.join(home, projectName, 'Results', '5.Mosaic', '')
    CreateFolder(mosaic_folder)

    list_of_sn = []
    for product in products:
        list_of_sn.append(product.getName())

    for product in products:
        if isDuplicatedDate(product.getName(), list_of_sn):
            mosaic_name = product.getName()
            mosaic_ds = mosaic_name[17:-42]
            if not mosaic_dataset.__contains__(mosaic_ds):
                mosaic_dataset[mosaic_ds] = list()
            mosaic_dataset[mosaic_ds].append(product)
        else:
            mosaiking_list.append(product)
            name_product = product.getName()[17:-42] + '.dim'
            mosaic_output_path = os.path.join(mosaic_folder, name_product)
            if not os.path.isfile(mosaic_output_path):
                if write_product:
                    startTimeWrite = time.time()
                    ProductIO.writeProduct(product, mosaic_output_path, 'BEAM-DIMAP')
                    writeTimeInFunction = time.time() - startTimeWrite
            else:
                writeToLog("\t".join(["GetMosaic", "File " + "'" + name_product + "'" + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    print('Mosaic Datasets:')

    for mds in mosaic_dataset:
        print('Mosaicing dataset ' + mds + ' ...')
        product_name = mosaic_name + '.dim'
        mosaic_path = os.path.join(mosaic_folder, product_name)
        if not os.path.isfile(mosaic_path):
            mosaic_hash = HashMap()
            mosaic = GPF.createProduct('SliceAssembly', mosaic_hash, mosaic_dataset[mds])
            print(mosaic)
            name = mosaic.getName()[17:-46]
            mosaic_output = mosaic_folder + name
            mosaiking_list.append(mosaic)
            print(mosaic.getName())
            if write_product:
                startTimeWrite = time.time()
                ProductIO.writeProduct(mosaic, mosaic_output, 'BEAM-DIMAP')
                writeTimeInFunction = time.time() - startTimeWrite
            mosaic.dispose()
            del mosaic
        else:
            writeToLog("\t".join(["GetSpeckleFilter", "File " + "'" + product_name + "'" + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    del products
    products = None
    print('FINISH MOSAICKING DATA...........................DONE')

    processTimeInFunction = time.time() - startTimeProcess

    return(mosaiking_list)

#step 6
def GetTerrainCorrection(products, write_product):

    global writeTimeInFunction
    global processTimeInFunction

    startTimeProcess = time.time()

    if products == None:
        products = []
        mosaic_input_path = os.path.join(home, projectName, 'Results', '5.Mosaic', '*.dim')
        #mosaic_input_path = os.path.join(home, projectName, 'Results', '4.SpeckleFilter', '*.dim')
        files = glob.glob(mosaic_input_path)

        for f in files:
            product = ProductIO.readProduct(f)
            products.append(product)
            name = product.getName()

    terrain_list = []
    terrain_folder = os.path.join(home, projectName, 'Results', '6.TerrainCorrection', '')
    CreateFolder(terrain_folder)
    for product in products:
        terrain_name = product.getName()  + '.dim'
        terrain_path = os.path.join(terrain_folder, terrain_name)
        if not os.path.isfile(terrain_path):
            print('Processing: ' + terrain_name)
            terrain_hashmap = HashMap()
            terrain_hashmap.put('demResamplingMethod', 'NEAREST_NEIGHBOUR')
            terrain_hashmap.put('imgResamplingMethod', 'NEAREST_NEIGHBOUR')
            terrain_hashmap.put('applyRadiometricNormalization', True)

            #print("--------------------------- STEP TEST 1 -------------------------")

            terrain_hashmap.put('demName', 'SRTM 3Sec') # SRTM 3Sec # SRTM 1Sec HGT

            #print("--------------------------- STEP TEST 2 -------------------------")

            terrain_hashmap.put('externalDEMApplyEGM', True)

            #print("--------------------------- STEP TEST 3 -------------------------")

            #terrain_hashmap.put('nodataValueAtSea', True)

            #print("--------------------------- STEP TEST 4 -------------------------")

            terrain_hashmap.put('pixelSpacingInMeter', 10.0)

            #print("--------------------------- STEP TEST 5 -------------------------")

            terrain_hashmap.put('mapProjection', mapProjection) #WGS84/UTM Zone 48N

            #print("--------------------------- STEP TEST 6 -------------------------")

            terrain = GPF.createProduct("Terrain-Correction", terrain_hashmap, product)

            #print("--------------------------- STEP TEST 7 -------------------------")

            terrain_list.append(terrain)

            fileOutputStream = FileOutputStream(terrain_folder + "\\6.progress.txt")
            printWriterProgressMonitor = PrintWriterProgressMonitor(fileOutputStream)

            PWPM = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
            JavaSystem = jpy.get_type('java.lang.System')
            monitor = PWPM(JavaSystem.out)

            if write_product:
                startTimeWrite = time.time()
                ProductIO.writeProduct(terrain, terrain_path, 'BEAM-DIMAP', monitor)
                writeTimeInFunction = time.time() - startTimeWrite
            terrain.dispose()
            product.dispose()
            del terrain
            del terrain_hashmap
            del product
        else:
            writeToLog("\t".join(["GetTerrainCorrection", "File " + "'" + terrain_name + "'" + " " +  "already exists. Exit without changes and move to new image."]),"WARNING")

    del products
    products = None
    print('TERRAIN CORRECTION..........................DONE')

    processTimeInFunction = time.time() - startTimeProcess

    print("--- Process time : %s seconds ---" % (processTimeInFunction))

    return(terrain_list)

# STEP 7 -- DONE
def GetCoregistration(write_product):
    products = []
    terrain_input_path = os.path.join(home,projectName,'Results','6.TerrainCorrection','*.dim')
    files = glob.glob(terrain_input_path)

    for f in files:
        product = ProductIO.readProduct(f)
        products.append(product)
        name = product.getName()

    coregistered_folder = os.path.join(home,projectName,'Results','7.Coregistered','')
    CreateFolder(coregistered_folder)

    input_stack  = dict()

    for product in products:
        stack_name = product.getName()
        if not input_stack.__contains__(stack_name): ## python 2: has_key is converted to __contains__ (python3)
            input_stack[stack_name] = list()
        input_stack[stack_name].append(product)

    list_stack = OrderedDict(sorted(list(input_stack.items()),key=lambda x: datetime.datetime.strptime(x[0], '%Y%m%d'))) # input_stack.items() in python 2 is converted to list(input_stack.items())
    print(list_stack)

    pair_stack = []
    index = 0
    max_index = len(list(list_stack.items())) - 1

    while(index < max_index):
        pair_stack.append([list(list_stack.items())[index][1],list(list_stack.items())[index + 1][1]])
        index += 1

    coregistered_list = []

    for i in pair_stack:
        coregistered_name = i[0][0].getName() + '_' + i[1][0].getName() + '.dim'
        coregistered_path = os.path.join(coregistered_folder,coregistered_name)

        if not os.path.isfile(coregistered_name):
            stack_hashmap = HashMap()
            stack_hashmap.put('extent','Master')
            stack_hashmap.put('resamplingType',None)
            stack_hashmap.put('initialOffsetMethod','Product Geolocation')
            stack = GPF.createProduct('CreateStack',stack_hashmap,[i[0][0], i[1][0]])

            correlation_hashmap = HashMap()
            correlation_hashmap.put('numGCPtoGenerate',2000)
            correlation_hashmap.put('coarseRegistrationWindowWidth','64')
            correlation_hashmap.put('coarseRegistrationWindowHeight','64')
            correlation_hashmap.put('rowInterpFactor','2')
            correlation_hashmap.put('columnInterpFactor','2')
            correlation_hashmap.put('maxIteration',10)
            correlation_hashmap.put('gcpTolerance',0.5)
            correlation = GPF.createProduct('Cross-Correlation',correlation_hashmap,stack)

            print('Processing: ' + coregistered_name)
            warp_hash = HashMap()
            warp_hash.put('rmsThreshold','1.0f')
            warp_hash.put('warpPolynomialOrder',1)
            warp_hash.put('interpolationMethod','Bilinear interpolation')
            warp = GPF.createProduct('Warp',warp_hash,correlation)
            warp_names = warp.getName()[:-6]
            warp_out = coregistered_folder + i[0][0].getName() + '_' + i[1][0].getName()
            coregistered_list.append(warp)
            if write_product:
                ProductIO.writeProduct(warp, warp_out,'BEAM-DIMAP')
            warp.dispose()
            correlation.dispose()
            stack.dispose()
            del warp
            del warp_hash
            del correlation
            del correlation_hashmap
            del stack
            del stack_hashmap
        else:
            writeToLog("\t".join(["getCoregistration", "File " + "'" + coregistered_name + "'" + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    del products
    products = None
    print('COREGISTRATION............................DONE')
    return(coregistered_list)

#STEP 8 -- DONE
def GetLineartodB(write_product):
    products = []
    cores_input_path = os.path.join(home,projectName,'Results','7.Coregistered','*.dim')
    files = glob.glob(cores_input_path)

    for f in files:
        product = ProductIO.readProduct(f)
        products.append(product)
        name = product.getName()

    lineartodb_list = []
    lineartodB_folder = os.path.join(home,projectName,'Results','8.LinearTodB','')
    CreateFolder(lineartodB_folder)
    for product in products:
        lineartodb_name = product.getName() + '.dim'
        lineartodb_path = os.path.join(lineartodB_folder,lineartodb_name)
        print(lineartodb_path)
        band_names = product.getBandNames()
        print("Bands: %s" % (list(band_names)))
        if not os.path.isfile(lineartodb_path):
            lineartodb_hashmap = HashMap()
            lineartodb_hashmap.put('outputImageScaleInDb', True)
            lineartodb = GPF.createProduct('LinearToFromdB',lineartodb_hashmap,product)
            print(lineartodb.getName())
            lineartodb_list.append(lineartodb)
            db_name = lineartodb.getName()[:-3]
            lineartodb_out = lineartodB_folder + db_name
            if write_product:
                ProductIO.writeProduct(lineartodb,lineartodb_out,'BEAM-DIMAP')
            lineartodb.dispose()
            product.dispose()
            del lineartodb
            del product
        else:
            print(lineartodb_path + 'File already exist. Exit without changes and move to new image.')
            writeToLog("\t".join(["getLineartodB", "File " + lineartodb_name + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    del products
    products = None
    print('LINEAR TO dB.................................DONE')
    return(lineartodb_list)

#STEP 9 -- DONE
def GetSubset(products, write_product):

    if products == None:
        products = []
        lbs_input_path = os.path.join(home,projectName,'Results','8.LinearTodB','*.dim')
        files = glob.glob(lbs_input_path)

        for f in files:
            product = ProductIO.readProduct(f)
            products.append(product)
            name = product.getName()

    wkt = "POLYGON ((-68.98335241413214 -9.522585117558615, -69.01204591114792 -9.677114942537044, \
    -69.10856820855027 -9.633184094606635, -69.06255339203875 -9.526780874576998, \
    -69.06255339203875 -9.526780874576998, -68.98335241413214 -9.522585117558615))"

    subset_list = []
    subset_folder = os.path.join(home,projectName,'Results','9.Subset','')
    CreateFolder(subset_folder)

    for product in products:
        subset_name = product.getName() + '.dim'
        subset_path = os.path.join(subset_folder,subset_name)
        if not os.path.isfile(subset_path):
            print('Processing: ' + subset_name)

            WKTReader = snappy.jpy.get_type('org.locationtech.jts.io.WKTReader')
            geom = WKTReader().read(wkt)
            subset_hashmap = HashMap()
            subset_hashmap.put('copyMetadata', True)
            subset_hashmap.put('geoRegion', geom)
            subset_hashmap.put('outputImageScaleInDb', False)
            subset = GPF.createProduct('Subset', subset_hashmap, product)
            subset_out = subset_folder + subset.getName()[7:]
            subset_list.append(subset)

            fileOutputStream = FileOutputStream(subset_folder + "\\9.progress.txt")
            printWriterProgressMonitor = PrintWriterProgressMonitor(fileOutputStream)

            PWPM = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
            JavaSystem = jpy.get_type('java.lang.System')
            monitor = PWPM(JavaSystem.out)

            if write_product:
                ProductIO.writeProduct(subset, subset_out, 'BEAM-DIMAP', monitor)
            subset.dispose()
            product.dispose()
            del subset
            del subset_hashmap
            del product
        else:
            writeToLog("\t".join(["getSubset", "File " + subset_name + " " + "already exists. Exit without changes and move to new image."]),"WARNING")
    del products
    products = None
    print('SUBSET PRODUCT..............................DONE')
    return(subset_list)

#step 10 -- DONE --
def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)

def isYearExport(product,products):
    start_date = datetime.datetime.strptime(startDate, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(endDate, '%Y-%m-%d')
    c1 = product.split("_")[1]
    c1 = datetime.datetime.strptime(c1, '%Y%m%d')
    if c1 in daterange(start_date, end_date):
        return True
    return False

def CalDifferenceImage(write_product1, write_product2):
    difference_folder = os.path.join(home, projectName, 'Results', '10.DifferenceImage', '')
    analysis_folder   = os.path.join(home, projectName, 'Results', '10.DifferenceImage', 'Analysis', '')
    diff_folder       = os.path.join(home, projectName, 'Results', '10.DifferenceImage', 'Differences', '')

    CreateFolder(difference_folder)
    CreateFolder(analysis_folder)
    CreateFolder(diff_folder)

    subset_input_path = os.path.join(home, projectName, 'Results', '9.Subset', '*.dim')
    files = glob.glob(subset_input_path)

    diff_list = []
    products = []

    for f in files:
        product = ProductIO.readProduct(f)
        products.append(product)
        file_name = product.getName()
        print('Processing: ' + file_name)

        list_of_sn = []
        for product in products:
            list_of_sn.append(product.getName())

        band_diff = []
        sigma = ['Sigma0_VH', 'Sigma0_VV']
        for band in sigma:
            list_band = product.getBands()
            list_band_name = product.getBandNames()

            list_frd_band   = {}
            for bn_idx, bn in enumerate(list_band_name):
                if band in bn:
                    list_frd_band[bn] = list_band[bn_idx]

            frd_bn1 = list(list_frd_band.keys())[0]
            frd_bn2 = list(list_frd_band.keys())[1]

            b1 = frd_bn1.split("_")[3]
            b2 = frd_bn2.split("_")[3]

            frd_d1  = datetime.datetime.strptime(b1, '%d%b%Y')
            frd_d2  = datetime.datetime.strptime(b2, '%d%b%Y')

            if frd_d1 < frd_d2:
                exp = frd_bn2 + '-' + frd_bn1
                bandmath1_hashmap = HashMap()
                bandmath1_hashmap.put('numberOne', product);
                bandmath1_hashmap.put('numberTwo', product);
                bandmath_name = b1 + '_' + b2 + '_' + '_' + band
            else:
                exp = frd_bn1 + '-' + frd_bn2
                bandmath1_hashmap = HashMap()
                bandmath1_hashmap.put('numberOne', product);
                bandmath1_hashmap.put('numberTwo', product);
                bandmath_name = b2 + '_' + b1 + '_' + '_' + band

            target_band1  = BandDescriptor()
            target_band1.name = band
            target_band1.type = 'float32'
            target_band1.expression = exp

            target_bands = jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', 1)
            target_bands[0] = target_band1

            bandmath2_hashmap = HashMap()
            bandmath2_hashmap.put('targetBands', target_bands)

            bandmath_product = GPF.createProduct('BandMaths', bandmath2_hashmap, bandmath1_hashmap)
            band_diff.append(bandmath_product)

            if isYearExport(product.getName(), list_of_sn):
                an_bandmath_path  = os.path.join(home, projectName, 'Results', '10.DifferenceImage', 'Analysis', file_name + band[6:])
                if write_product1:
                    anl_name = file_name + band[6:] + '.tif'
                    anl_path = os.path.join(analysis_folder, anl_name)
                    if not os.path.isfile(anl_path):
                        ProductIO.writeProduct(bandmath_product, an_bandmath_path, 'GeoTIFF')
                    else:
                        print(anl_path + ' ' + 'File already exist. Exit without changes and move to new image.')
            else:
                print(product.getName() + ': ' + 'Date is out of range analysis')

        NodeDescriptor = jpy.get_type('org.esa.snap.core.gpf.common.MergeOp$NodeDescriptor')
        include_1 = NodeDescriptor()
        include_1.setProductId('masterProduct')
        include_1.setNamePattern('bandmath_name')
        include_1.setNewName('Sigma0_VH')

        include_2 = NodeDescriptor()
        include_2.setProductId('slaveProduct')
        include_2.setName('bandmath_name')
        include_1.setNewName('Sigma0_VV')

        included_bands = jpy.array('org.esa.snap.core.gpf.common.MergeOp$NodeDescriptor', 2)
        included_bands[0] = include_1
        included_bands[1] = include_2

        bandmerge_hashmap = HashMap()
        bandmerge_hashmap.put('includes', included_bands)
        mergeband = GPF.createProduct('BandMerge', bandmerge_hashmap, band_diff)
        diff_list.append(mergeband)
        merge_out = diff_folder + file_name
        if write_product2:
            diff_name = file_name + '.dim'
            diff_outPath = os.path.join(diff_folder, diff_name)
            if not os.path.isfile(diff_outPath):
                ProductIO.writeProduct(mergeband, merge_out, 'BEAM-DIMAP')
            else:
                print(diff_outPath + ' ' + 'File already exist. Exit without changes and move to new image.')
        mergeband.dispose()
        bandmath_product.dispose()
        del mergeband
        del bandmath_product
        del product
    del products
    products = None
    print('DONE')
    return(diff_list)

### STEP 11. PROBABILITY DENSITY FUNTION  - CHANGE DETECTION #################################

### STEP 11.1 Calculate PDF ##################################################################
def pdfFunction(write_product):
    change_list = []
    change_folder = os.path.join(home,projectName,'Results','11.ChangeDetection','')
    CreateFolder(change_folder)

    products = []
    diff_input_path = os.path.join(home, projectName, 'Results', '10.DifferenceImage', 'Differences', '*.dim')
    files = glob.glob(diff_input_path)

    for f in files:
        product = ProductIO.readProduct(f)
        products.append(product)
        name = product.getName()

    for product in products:

        list_band = product.getBands()
        list_band_name = product.getBandNames()

        list_frd_band  = {}
        for bn_idx, bn in enumerate(list_band_name):
            list_frd_band[bn] = list_band[bn_idx]

        print("Bands:  %s" % (list(list_frd_band)))

        if 'VH_slv' in list(list_frd_band.keys())[1]:
            frd_bn_vv = list(list_frd_band.keys())[0]
            frd_bn_vh = list(list_frd_band.keys())[1]
            #print("Band VV:" + frd_bn_vv)
            #print("Band VH:" + frd_bn_vh)
        else:
            frd_bn_vv = list(list_frd_band.keys())[1]
            frd_bn_vh = list(list_frd_band.keys())[0]
            #print("Band VV:" + frd_bn_vv)
            #print("Band VH:" + frd_bn_vh)

        for i in data:
            expChanges  = '(1 - exp(-(((' + str(data[i]['o_vh']) + ' * ' + str(data[i]['o_vh']) + ' * (' + frd_bn_vv + ' * ' + frd_bn_vv + ' - 2 * ' + frd_bn_vv + ' * ' + str(data[i]['u_vv']) + ' + ' + str(data[i]['u_vv']) + ' * ' + str(data[i]['u_vv']) + ')) - (2 * ' + str(data[i]['p']) + ' * ' + str(data[i]['o_vv']) + ' * ' + str(data[i]['o_vh']) + ' * ('+ frd_bn_vh +' - ' + str(data[i]['u_vh']) + ') * ('+ frd_bn_vv +' - ' + str(data[i]['u_vv']) + ')) + (' + str(data[i]['o_vv']) + ' * ' + str(data[i]['o_vv']) + ' * ('+ frd_bn_vh +' * ' + frd_bn_vh + ' - 2 * ' + frd_bn_vh + ' * ' + str(data[i]['u_vh']) + ' + ' + str(data[i]['u_vh']) + ' * ' + str(data[i]['u_vh']) + ')))/(' + str(data[i]['o_vv']) + ' * ' + str(data[i]['o_vv']) + ' * ' + str(data[i]['o_vh']) + ' * ' + str(data[i]['o_vh']) + ' * (1 - ' + str(data[i]['p']) + ' * ' + str(data[i]['p']) + ')))/2)) > 0.99999'

            BandDescriptor = jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
            targetChange = BandDescriptor()
            targetChange.name = 'Changes'
            targetChange.type = 'Float32'
            targetChange.expression = expChanges

            targetChanges = jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor',1)
            targetChanges[0] = targetChange

            changes_hashmap = HashMap()
            changes_hashmap.put('targetBands',targetChanges)
            changes_temp_folder = os.path.join(home, projectName, 'Results', '11.ChangeDetection', 'temp', 'tif', '')
            CreateFolder(changes_temp_folder)

            change_temp_out = changes_temp_folder + product.getName() + '_' + i
            changes = GPF.createProduct('BandMaths', changes_hashmap, product)
            change_list.append(changes)

            changeDetection_name = changes.getName()[:-9] + '_' + i + '.tif'
            changeDetection_outPath = os.path.join(changes_temp_folder, changeDetection_name)
            if not os.path.isfile(changeDetection_outPath):
                if write_product:
                    ProductIO.writeProduct(changes, change_temp_out, 'GeoTIFF-BigTIFF')
                else:
                    writeToLog("\t".join(["pdfFunction", "File " + changeDetection_name + " " + "already exists. Exit without changes and move to new image."]),"WARNING")

        #changes.dispose()
        #del changes
        #del product

    #del products
    #products = None
    #print(change_list)
    return change_list

def extractByMask():
    inF         = os.path.join(home, projectName, 'Results', '11.ChangeDetection', 'temp', 'tif', '')
    ouF         = os.path.join(home, projectName, 'Results', '11.ChangeDetection', 'temp', 'clipped', '')
    maF         = settings.get('Forest-Config', 'shp_path')
    shp_name    = settings.get('Forest-Config', 'shp_name')
    shp_name    = shp_name.split(",")
    mp_name     = []

    for i in shp_name:
        mp_name.append(i)

    CreateFolder(ouF)
    for ip_name in os.listdir(inF):
        if ip_name.endswith(".tif"):

            ip = os.path.join(inF, ip_name)
            op = os.path.join(ouF, ip_name)

            if "H" in ip_name:
                ma = os.path.join(maF, mp_name[0])
            elif "M" in ip_name:
                ma = os.path.join(maF, mp_name[1])
            elif "L" in ip_name:
                ma = os.path.join(maF, mp_name[2])
            elif "P" in ip_name:
                ma = os.path.join(maF, mp_name[3])
            elif "N" in ip_name:
                ma = os.path.join(maF, mp_name[4])

            with fiona.open(ma, "r") as shapefile:
                features = [feature["geometry"] for feature in shapefile]

            with rasterio.open(ip) as src:
                out_image, out_transform = rasterio.mask.mask(src, features, nodata=-9999, crop=True) #invert=True
                out_meta = src.meta.copy()

            out_meta.update({ "driver": "GTiff", "height": out_image.shape[1], "width": out_image.shape[2], "transform": out_transform })

            with rasterio.open(op, "w", **out_meta) as dest:
                dest.write(out_image)

def mosaicTiff():
    outF = os.path.join(home, projectName, 'Results', '11.ChangeDetection', 'temp', 'clipped', '')
    ouFinal = os.path.join(home, projectName, 'Results', '11.ChangeDetection', '')

    raster_stack  = dict()
    for inRaster in os.listdir(outF):
        raster_name = inRaster[:-6]

        if not raster_stack.__contains__(raster_name):
            raster_stack[raster_name] = list()
        raster_stack[raster_name].append(inRaster)

    for key, value in iter(raster_stack.items()):
        exeList = []
        for item in value:
            exeList.append(rasterio.open(os.path.join(outF, item)))
        mosaicName = key + "_mosaic.tif"

        dest, output_transform = rasterio.merge.merge(exeList, None, None, -9999, 7)
        with exeList[0] as src:
            out_meta = src.meta.copy()

        #out_meta.update({ "driver": "GTiff", "height": dest.shape[1], "width": dest.shape[2], "transform": output_transform, "crs": "+proj=longlat +datum=WGS84 +ellps=WGS84 +towgs84=0,0,0"})

        out_meta.update({ "driver": "GTiff", "height": dest.shape[1], "width": dest.shape[2], "transform": output_transform})

        with rasterio.open(os.path.join(ouFinal, mosaicName), "w", **out_meta) as op:
            op.write(dest)

def ChangeDetection():
    pdfs = pdfFunction(True)
    extractbymask = extractByMask()
    combines = mosaicTiff()
    print('Calculating Change Detection...')
    removeProduct(os.path.join(home, projectName, 'Results', '11.ChangeDetection', 'temp'))

### 12. POST - CHANGE DETECTION ######
### 12.1 CONVERT RASTER TO SHAPEFILE --# --DONE
def createShape():
    cs_input_folder    = os.path.join(home,projectName,'Results','11.ChangeDetection')
    cs_output_folder   = os.path.join(home,projectName,'Results','12.Post-ChangeDetection', '1.Shape')
    CreateFolder(cs_output_folder)

    tifs = glob.glob(os.path.join(cs_input_folder,'*.tif'))
    for tif in tifs:
        tif_src = gdal.Open(tif,gdal.GA_ReadOnly)
        tif_band    = tif_src.GetRasterBand(1)

        shp_drv = ogr.GetDriverByName("ESRI Shapefile")
        shp     = os.path.join(cs_output_folder, os.path.splitext(os.path.basename(tif))[0] + ".shp")

        #if os.path.exists(shp):
        #    shp_drv.DeleteDataSource(shp)
        #    print 'Deleted'

        shp_src     = shp_drv.CreateDataSource(shp)
        shp_srs     = osr.SpatialReference()
        shp_srs.ImportFromWkt(tif_src.GetProjectionRef())
        shp_layer   = shp_src.CreateLayer(shp, srs = shp_srs)

        shp_field1  = ogr.FieldDefn("VALUE", ogr.OFTInteger)
        shp_layer.CreateField(shp_field1)

        shp_field2  = ogr.FieldDefn("AREA", ogr.OFTReal)
        shp_layer.CreateField(shp_field2)

        shp_result  = gdal.Polygonize(tif_band, tif_band.GetMaskBand(), shp_layer, 0, [], callback = None)

        shp_count   = shp_layer.GetFeatureCount()
        for shp_idx in range(shp_count):
            shp_ft  = shp_layer.GetFeature(shp_idx)
            shp_val = shp_ft.GetField('VALUE')
            if int(shp_val) < 1:
                shp_layer.DeleteFeature(shp_idx)

        shp_src.Destroy()
        tif_src = None

### 12.2 CONVERT PROJECTION -- DONE ------------ #####
def convertProject():
    cp_input_folder    = os.path.join(home, projectName, 'Results', '12.Post-ChangeDetection', '1.Shape')
    cp_output_folder   = os.path.join(home, projectName, 'Results', '12.Post-ChangeDetection', '2.ConvertProject')
    CreateFolder(cp_output_folder)
    shps = glob.glob(os.path.join(cp_input_folder, '*.shp'))
    for shp in shps:
        out_shp = os.path.join(cp_output_folder, os.path.splitext(os.path.basename(shp))[0] + ".shp")
        shp_drv = ogr.GetDriverByName('ESRI Shapefile')
        shp_src = shp_drv.Open(shp, 1)

        shpLayer = shp_src.GetLayer()

        inSpatialRef    = shp_src.GetLayer().GetSpatialRef()
        outSpatialRef   = osr.SpatialReference()

        project = inSpatialRef.GetAttrValue("AUTHORITY", 1)

        if project == '4326':
            outSpatialRef.ImportFromEPSG(int(epsg))
            coordTrans      = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

            shp_change_out_src     = shp_drv.CreateDataSource(out_shp)
            shp_change_out_layer   = shp_change_out_src.CreateLayer(out_shp, srs=outSpatialRef, geom_type = ogr.wkbMultiPolygon)

            inChangeLayerDefn = shp_src.GetLayer().GetLayerDefn()
            for i in range(0, inChangeLayerDefn.GetFieldCount()):
                fieldChangeDefn = inChangeLayerDefn.GetFieldDefn(i)
                shp_change_out_layer.CreateField(fieldChangeDefn)

            changeOutLayerDefn = shp_change_out_layer.GetLayerDefn()

            inChangeFeature = shp_src.GetLayer().GetNextFeature()
            while inChangeFeature:
                geom = inChangeFeature.GetGeometryRef()
                geom.Transform(coordTrans)
                outChangeFeature = ogr.Feature(changeOutLayerDefn)
                outChangeFeature.SetGeometry(geom)
                for i in range(0, changeOutLayerDefn.GetFieldCount()):
                    outChangeFeature.SetField(changeOutLayerDefn.GetFieldDefn(i).GetNameRef(), inChangeFeature.GetField(i))
                shp_change_out_layer.CreateFeature(outChangeFeature)
                outChangeFeature = None
                inChangeFeature = shp_src.GetLayer().GetNextFeature()

            for shp_ft in shp_change_out_layer:
                shp_geom = shp_ft.GetGeometryRef()
                shp_ft.SetField("AREA", shp_geom.GetArea())
                shp_change_out_layer.SetFeature(shp_ft)

            featureChangeCount = shp_change_out_layer.GetFeatureCount()
            for area in range(featureChangeCount):
                shp_ft  = shp_change_out_layer.GetFeature(area)
                shp_val = shp_ft.GetField('AREA')
                if int(shp_val) < 300:
                    shp_change_out_layer.DeleteFeature(area)

            # Save and close the shapefiles
            shp_src     = None
            shp_change_out_src = None
        else:
            outSpatialRef.ImportFromEPSG(int(epsg))
            shp_nochnage_output_src     = shp_drv.CreateDataSource(out_shp)
            shp_nochange_output_layer   = shp_nochnage_output_src.CreateLayer(out_shp, srs=outSpatialRef, geom_type = ogr.wkbMultiPolygon)

            inNoChangeLayerDefn = shp_src.GetLayer().GetLayerDefn()
            for i in range(0, inNoChangeLayerDefn.GetFieldCount()):
                fieldNoChangeDefn = inNoChangeLayerDefn.GetFieldDefn(i)
                shp_nochange_output_layer.CreateField(fieldNoChangeDefn)

            noChangeOutLayerDefn = shp_nochange_output_layer.GetLayerDefn()

            inNoChangeFeature = shp_src.GetLayer().GetNextFeature()

            while inNoChangeFeature:
                geom = inNoChangeFeature.GetGeometryRef()
                #geom.Transform(coordTrans)
                outNoChangeFeature = ogr.Feature(noChangeOutLayerDefn)
                outNoChangeFeature.SetGeometry(geom)
                for i in range(0, noChangeOutLayerDefn.GetFieldCount()):
                    outNoChangeFeature.SetField(noChangeOutLayerDefn.GetFieldDefn(i).GetNameRef(), inNoChangeFeature.GetField(i))
                shp_nochange_output_layer.CreateFeature(outNoChangeFeature)
                outNoChangeFeature = None
                inNoChangeFeature = shp_src.GetLayer().GetNextFeature()

            for shp_ft in shp_nochange_output_layer:
                shp_geom = shp_ft.GetGeometryRef()
                shp_ft.SetField("AREA", shp_geom.GetArea())
                shp_nochange_output_layer.SetFeature(shp_ft)

            featureNoChangeCount = shp_nochange_output_layer.GetFeatureCount()
            for area in range(featureNoChangeCount):
                shp_ft  = shp_nochange_output_layer.GetFeature(area)
                shp_val = shp_ft.GetField('AREA')
                if int(shp_val) < 300:
                    shp_nochange_output_layer.DeleteFeature(area)
            shp_src     = None
            shp_nochnage_output_src = None

### 12.3 INTERSECTION SHP WITH FOREST MAP #############
def intersection():
    is_input_files = os.path.join(home,projectName,'Results','12.Post-ChangeDetection','2.ConvertProject')
    is_output_folder = os.path.join(home,projectName,'Results','12.Post-ChangeDetection','3.Intersection')
    CreateFolder(is_output_folder)

    shps = glob.glob(os.path.join(is_input_files,'*.shp'))
    for shp in shps:
        out_shp = os.path.join(is_output_folder, os.path.splitext(os.path.basename(shp))[0] + ".shp")

        drv = ogr.GetDriverByName("ESRI Shapefile")

        #first = Polygon()
        inForest = drv.Open(forest_map, 0)
        forestLayer = inForest.GetLayer()

        #two = Polygon()
        inShapefile = drv.Open(shp, 0)
        shpLayer = inShapefile.GetLayer()

        inSpatialRef    = shpLayer.GetSpatialRef()

        dst_shp = drv.CreateDataSource(out_shp)
        layer_out_intersection = dst_shp.CreateLayer(shp, srs = inSpatialRef, geom_type = ogr.wkbPolygon)

        # create filed in new shp
        filedForest = forestLayer.GetLayerDefn().GetFieldCount()
        for f1 in range(0, filedForest):
            layer_out_intersection.CreateField(forestLayer.GetLayerDefn().GetFieldDefn(f1))
        #print filedForest

        shpFields = shpLayer.GetLayerDefn().GetFieldCount()
        for f2 in range(0, shpFields):
            layer_out_intersection.CreateField(shpLayer.GetLayerDefn().GetFieldDefn(f2))
        #print shpFields

        forFields = []
        for i in range(forestLayer.GetLayerDefn().GetFieldCount()):
            forField = forestLayer.GetLayerDefn().GetFieldDefn(i).GetName()
            forFields.append(forField)
        print(forFields)

        c1 = forestLayer.GetFeatureCount()
        c2 = shpLayer.GetFeatureCount()
        j = 0
        for i1 in range(0, c1):
            forestFeature = forestLayer.GetFeature(i1)
            forestGeom = forestFeature.GetGeometryRef()

            for i2 in range(0, c2):
                shpFeature = shpLayer.GetFeature(i2)
                shpGeom = shpFeature.GetGeometryRef()
                shpAttribute = shpFeature.GetField('AREA')
                if shpGeom.Intersects(forestGeom):
                    intersection = shpGeom.Intersection(forestGeom)
                    outFeature = ogr.Feature(layer_out_intersection.GetLayerDefn())
                    outFeature.SetGeometry(intersection)

                    for f1 in forFields:
                        forestAttribute = forestFeature.GetField(f1)
                        outFeature.SetField(outFeature.GetFieldIndex(f1), forestAttribute)

                    outFeature.SetField(outFeature.GetFieldIndex('AREA'), shpAttribute)
                    layer_out_intersection.CreateFeature(outFeature)
                    outFeature = None
                    #print(j)
                    j = j + 1
                    if j > 3:
                        break

        shp_dtich  = ogr.FieldDefn("DIENTICH", ogr.OFTReal)
        layer_out_intersection.CreateField(shp_dtich)

        for shp_ft in layer_out_intersection:
            shp_geom = shp_ft.GetGeometryRef()
            shp_ft.SetField("DIENTICH", shp_geom.GetArea())
            layer_out_intersection.SetFeature(shp_ft)

        featureCount = layer_out_intersection.GetFeatureCount()
        for area in range(featureCount):
            shp_ft  = layer_out_intersection.GetFeature(area)
            shp_val = shp_ft.GetField('DIENTICH')
            if int(shp_val) < 200:
                layer_out_intersection.DeleteFeature(area)

        dst_shp = None

### 12.4. CONVERT TO CENTROID POINT #######
def centroid():
    cs_input_folder = os.path.join(home,projectName,'Results','12.Post-ChangeDetection','3.Intersection')
    cs_output_folder = os.path.join(home,projectName,'Results','12.Post-ChangeDetection','4.Centroid')
    CreateFolder(cs_output_folder)
    shps = glob.glob(os.path.join(cs_input_folder, '*.shp'))
    for shp in shps:
        out_shp = os.path.join(cs_output_folder, os.path.splitext(os.path.basename(shp))[0] + ".shp")
        inDriver = ogr.GetDriverByName("ESRI Shapefile")
        inDataSource = inDriver.Open(shp, 1)
        inLayer = inDataSource.GetLayer()
        inFeature = inLayer.GetNextFeature()

        inSpatialRef    = inLayer.GetSpatialRef()

        outDriver = ogr.GetDriverByName("ESRI Shapefile")

        # Remove output shapefile if it already exists
        if os.path.exists(out_shp):
            outDriver.DeleteDataSource(out_shp)

        # Create the output shapefile
        outDataSource = outDriver.CreateDataSource(out_shp)
        outLayer = outDataSource.CreateLayer(out_shp, srs = inSpatialRef, geom_type=ogr.wkbPoint)

        # Add input Layer Fields to the output Layer
        inLayerDefn = inLayer.GetLayerDefn()

        for i in range(inLayerDefn.GetFieldCount()):
            fieldDefn = inLayerDefn.GetFieldDefn(i)
            if outLayer.CreateField(fieldDefn) != 0:
                print('Creating %s field failed.\n' % fieldDefn.GetNameRef())

        inLayer.ResetReading()
        inFeature = inLayer.GetNextFeature()

        # Add features to the ouput Layer
        while inFeature is not None:
            outLayerDefn = outLayer.GetLayerDefn()
            outFeature = ogr.Feature(outLayerDefn)

            for i in range(outLayerDefn.GetFieldCount()):
                outFeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))

            geom = inFeature.GetGeometryRef()
            centroid = geom.Centroid()
            outFeature.SetGeometry(centroid)

            if outLayer.CreateFeature(outFeature) !=0:
                print('Failed to create feature.\n')
                sys.exit(6)
            inFeature = inLayer.GetNextFeature()

        # Save and close DataSources
        inDataSource = None
        outDataSource = None

def PostChanges():
    convertshapes       = createShape()
    convertprojects     = convertProject()
    intersections       = intersection()
    centroids           = centroid()

def back():
    actions['main']()

def no_such_action():
    pass

def exit():
    sys.exit()

def PrintMenu():
    print("\n")
    print ("Please choose action you want to start: \n")
    print ("Apply Orbit...................1")
    print ("Remove Thermal Noise..........2")
    print ("Calibration...................3")
    print ("Speckle Filter................4")
    print ("Mosaic........................5")
    print ("Terrain-Correction............6")
    print ("Coregistration................7")
    print ("Lineart to Decibel............8")
    print ("Subset........................9")
    print ("Difference...................10")
    print ("Change Detection.............11")
    print ("Post - Change Detection......12")
    print ("Full - 1+2+3+4+6.............13")
    print ("Exit..........................0 \n")

def DoFullPreProcess(products, writeProduct):

    print("DoFullPreProcess - Start")

    processTime = []
    writeTime = []

    steps = []

    #orbits = GetApplyOrbit(products, False)
    orbits = GetApplyOrbit(products, True)
    processTime.append(processTimeInFunction)
    writeTime.append(writeTimeInFunction)
    steps.append("Apply orbit")

    #print("00000000000000000000000000000000000000000000000000000000000")
    #print(len(orbits))
    #print("00000000000000000000000000000000000000000000000000000000000")

    #noises = GetRemoveThermalNoise(orbits, False)
    noises = GetRemoveThermalNoise(None, True)
    processTime.append(processTimeInFunction)
    writeTime.append(writeTimeInFunction)
    steps.append("Remove thermal noise")

    #border = GetRemoveBorderNoise(None, True)
    #processTime.append(processTimeInFunction)
    #writeTime.append(writeTimeInFunction)
    #steps.append("Remove border noise")

    #calibs = GetCalibration(noises, False)
    calibs = GetCalibration(None, True)
    processTime.append(processTimeInFunction)
    writeTime.append(writeTimeInFunction)
    steps.append("Calibration")

    #specks = GetSpeckleFilter(calibs, False)
    specks = GetSpeckleFilter(None, True)
    processTime.append(processTimeInFunction)
    writeTime.append(writeTimeInFunction)
    steps.append("Speckle filter")

    MosaicAll(True)
    processTime.append(processTimeInFunction)
    writeTime.append(writeTimeInFunction)
    steps.append("Mosaic")

    #terrains = GetTerrainCorrection(specks, writeProduct)
    terrains = GetTerrainCorrection(None, writeProduct)
    processTime.append(processTimeInFunction)
    writeTime.append(writeTimeInFunction)
    steps.append("Terrain correction")

    for i in range(len(processTime)):
        print("----------- Step : " + steps[i] + " -----------")
        print("--- Process time : %s seconds ---" % (processTime[i] - writeTime[i]))
        print("--- Write time   : %s seconds ---" % (writeTime[i]))

    writeTimeAll = sum(writeTime)

    print("----------- All Steps -----------")
    print("--- Process time : %s seconds ---" % (sum(processTime) - writeTimeAll))
    print("--- Write time   : %s seconds ---" % (writeTimeAll))

    print("DoFullPreProcess - End")

    return terrains

def GetSubsetAll(products, write_product, nbSubsets, minSize, maxSize, margin):

    if products == None:
        products = []
        lbs_input_path = os.path.join(home,projectName,'Results','8.LinearTodB','*.dim')
        files = glob.glob(lbs_input_path)

        for f in files:
            product = ProductIO.readProduct(f)
            products.append(product)

    #wkt = "POLYGON ((-68.98335241413214 -9.522585117558615, -69.01204591114792 -9.677114942537044, \
    #-69.10856820855027 -9.633184094606635, -69.06255339203875 -9.526780874576998, \
    #-69.06255339203875 -9.526780874576998, -68.98335241413214 -9.522585117558615))"

    wkt = "POLYGON ((-68.50792260352144 -9.279529320076083, -68.60982063829297 -9.256648680818058, \
    -68.62772023116484 -9.336296001410416, -68.52577539972754 -9.359193953714152, \
    -68.50792260352144 -9.279529320076083))"

    # All Bresil

    wktAll = "POLYGON ((-67.89388193955018 -8.831075433948573, -70.10532385182502 -8.332040130888004, \
    -70.44316840808717 -9.808280894117233, -68.22389970556173 -10.312384423430005, \
    -67.89388193955018 -8.831075433948573))"

    # All Highlands

    # 1
    # wktAll = "POLYGON ((109.75731881612894 14.314795832267771, 107.54340277168437 14.73645137950223, \
    # 107.2610807914018 13.273442704782752, 109.45523070063814 12.849337152591264, \
    # 109.75731881612894 14.314795832267771))"

    # 2
    # wktAll = "POLYGON ((109.42270599178386 12.793727198887577, 107.24921733098107 13.213995274026088, \
    # 106.96641693341506 11.785251616689653, 109.12948812567193 11.361170217280756, \
    # 109.42270599178386 12.793727198887577))"

    # 3
    # wktAll = "POLYGON ((109.12970600381968 11.294560553165066, 106.94760375395673 11.72266223974242, \
    # 106.65468708647248 10.22628670851568, 108.82205975047616 9.79511696859958, \
    # 109.12970600381968 11.294560553165066))"

    # 4
    # wktAll = "POLYGON ((110.05927249720584 15.846834454167825, 107.8202015093934 16.266310292501107, \
    # 107.52736538953697 14.798658039739097, 109.75589699105613 14.374701520193574, \
    # 110.05927249720584 15.846834454167825))"

    # 5
    wktAll = "POLYGON ((109.1126328968922 11.294373198680825, 106.94391952363684 11.719755333130532, \
    106.64966718126783 10.216737315408235, 108.8037365960331 9.78826951165352, \
    109.1126328968922 11.294373198680825))"

    WKTReader = snappy.jpy.get_type('org.locationtech.jts.io.WKTReader')
    Coordinate = snappy.jpy.get_type('org.locationtech.jts.geom.Coordinate')
    CoordinateSequence = snappy.jpy.get_type('org.locationtech.jts.geom.impl.CoordinateArraySequenceFactory')
    GeometryFactory = snappy.jpy.get_type('org.locationtech.jts.geom.GeometryFactory')
    Geometry = snappy.jpy.get_type('org.locationtech.jts.geom.Geometry')

    geomAll = WKTReader().read(wktAll)

    maxH = geomAll.getCoordinates()[0].x
    minH = geomAll.getCoordinates()[0].x
    maxV = geomAll.getCoordinates()[0].y
    minV = geomAll.getCoordinates()[0].y

    for coor in geomAll.getCoordinates():
        if maxH < coor.x:
            maxH = coor.x

        if minH > coor.x:
            minH = coor.x

        if maxV < coor.y:
            maxV = coor.y

        if minV > coor.y:
            minV = coor.y

    maxH -= margin
    minH += margin
    maxV -= margin
    minV += margin

    subset_list = []
    subset_folder = os.path.join(home,projectName,'Results','9.Subset','')
    CreateFolder(subset_folder)

    for product in products:

        for i in range(nbSubsets):

            subset_name = product.getName() + "_" + str(i) + '.dim'
            subset_path = os.path.join(subset_folder, subset_name)

            if not os.path.isfile(subset_path):
                print('Processing: ' + subset_name)

                searchingZone = True

                while(searchingZone) :
                    sizeH = random.uniform(minSize, maxSize)
                    sizeV = random.uniform(minSize, maxSize)
                    startH = random.uniform(minH, maxH - sizeH)
                    startV = random.uniform(minV, maxV - sizeV)

                    coordinates = []
                    coordinates.append(Coordinate(startH, startV))
                    coordinates.append(Coordinate(startH, startV + sizeV))
                    coordinates.append(Coordinate(startH + sizeH, startV + sizeV))
                    coordinates.append(Coordinate(startH + sizeH, startV))
                    coordinates.append(coordinates[0]) # back to start

                    coordinateSequence = CoordinateSequence.instance().create(coordinates)

                    geometryFactory = GeometryFactory()

                    geom = geometryFactory.createPolygon(coordinateSequence)

                    searchingZone = (geom.within(geomAll) == False)

                subset_hashmap = HashMap()
                subset_hashmap.put('copyMetadata', True)
                subset_hashmap.put('geoRegion', geom)
                subset_hashmap.put('outputImageScaleInDb', False)
                subset = GPF.createProduct('Subset', subset_hashmap, product)
                subset_out = subset_folder + subset.getName()[7:] + "_" + str(i)
                subset_list.append(subset)

                fileOutputStream = FileOutputStream(subset_folder + "\\9.progress.txt")
                printWriterProgressMonitor = PrintWriterProgressMonitor(fileOutputStream)

                PWPM = jpy.get_type('com.bc.ceres.core.PrintWriterProgressMonitor')
                JavaSystem = jpy.get_type('java.lang.System')
                monitor = PWPM(JavaSystem.out)

                if write_product:
                    print("Writing : " + str(i))
                    ProductIO.writeProduct(subset, subset_out, 'BEAM-DIMAP', monitor)

                subset.dispose()
                del subset
                del subset_hashmap
            else:
                writeToLog("\t".join(["getSubset", "File " + subset_name + " " + "already exists. Exit without changes and move to new image."]),"WARNING")

        product.dispose()
        del product

    del products
    products = None
    print('SUBSET PRODUCT..............................DONE')
    return(subset_list)

def GetProductListDim():

    products = []
    lbs_input_path = os.path.join(folderPath,'*.dim')
    files = glob.glob(lbs_input_path)

    for f in files:
        product = ProductIO.readProduct(f)
        products.append(product)

    return products

def CompareTest(products):

    prodcut0 = products[0]
    prodcut1 = products[1]

    print("--------------- CompareTest ---------------")
    print(prodcut0.equals(prodcut0))
    print(prodcut0.equals(prodcut1))

    return None

def main():
    actions = {
        "1":    GetApplyOrbit,             # Parameters: 1 - Product List; 2 - True
        "2":    GetRemoveThermalNoise,     # Parameters: 1 - Orbit List; 2 - True
        "3":    GetCalibration,            # Parameters: 1 - RemovedThermalNoise List; 2 - True
        "4":    GetSpeckleFilter,          # Parameters: 1 - Calibration List; 2 - True
        "5":    MosaicAll,                 # Parameters: 1 - GetSpeckleFilter; 2 - True
        "6":    GetTerrainCorrection,      # Parameters: 1 - MosaicAll List; 2 - True
        "7":    GetCoregistration,         # Parameters: 1 - TerrainCorrection List; 2 - True
        "8":    GetLineartodB,             # Parameters: 1 - Coregistration List; 2 - True
        "9":    GetSubset,                 # Parameters: 1 - LinearToDecibel List; 2 - True
        "10":   CalDifferenceImage,        # Parameters: 1 - Subset List; 2 - True
        "11":   ChangeDetection,           # Parameters: 1 - Diff Image; 2 - False
        "12":   PostChanges,               # Parameters: 1 - Final Change; 2 - True
        "13":   DoFullPreProcess,          # Parameters: 1 - Product List; 2 - True
        "14":   GetSubsetAll,          	   # Parameters: 1 - Product List; 2 - True
        "0":    exit
    }

    products = GetProductList()
    #products = GetProductListDim()

    print("???????????????????????????????????")
    print(products[0])
    print("???????????????????????????????????")

    while True:

        PrintMenu()

        selection = input("Your selection: ")
        CallSelectedFunc = actions.get(selection, no_such_action)

        if selection == "1":
            orbits           = CallSelectedFunc(products, True)
        if selection == "2":
            noises           = CallSelectedFunc(True)
        if selection == "3":
            calibs           = CallSelectedFunc(True)
        if selection == "4":
            specks           = CallSelectedFunc(True)
        if selection == "5":
            mosaickings      = CallSelectedFunc(True)
        if selection == "6":
            terrains         = CallSelectedFunc(None, True)
        if selection == "7":
            coregistrations  = CallSelectedFunc(True)
        if selection == "8":
            lineartodbs      = CallSelectedFunc(True)
        if selection == "9":
            subsets          = CallSelectedFunc(products, True)
        if selection == "10":
            diffirences      = CallSelectedFunc(True,True)
        if selection == "11":
            changes          = CallSelectedFunc()
        if selection == "12":
            postchanges      = CallSelectedFunc()
        if selection == "13":
            doFullPreProcess = CallSelectedFunc(products, True)
        if selection == "14":
            getSubsetAll = CallSelectedFunc(products, True, 100, 0.05, 0.10, 0.1)
        if selection == "15":
            compareTest = CompareTest(products)
        if selection == "0":
            return

if __name__ == "__main__":
    main()
