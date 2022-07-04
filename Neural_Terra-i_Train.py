import os
currentPath = os.getcwd()

import configparser
settings = configparser.ConfigParser()
settings._interpolation = configparser.ExtendedInterpolation()
settings.read(currentPath + "/config/main_config.ini")

libs_path = settings.get('Main-Config', 'libs')

folderStart = settings.get('Main-Config', 'subset_start_path')
folderResult = settings.get('Main-Config', 'subset_end_path')
bandTrained = settings.get('Main-Config', 'band_trained')
historyModelPath = settings.get('Main-Config', 'history_model_path')

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

import pandas as pd

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

def getProductList(path, search):

    #products = []
    products = []

    lbs_input_path = os.path.join(path, search)
    files = glob.glob(lbs_input_path)

    for f in files:
        temp = np.load(f)
        products.append(temp['arr_0'])

    return products

def getProductList2(path, search): #TEMP

    products = []

    for pathF in os.listdir(path):

        for pathF2 in os.listdir(path + "/" + pathF):

            if search in pathF2:
                temp = np.load(path + "/" + pathF + "/" + pathF2)
                products.append(temp['arr_0'])

    return products

def getProductFileList(path, search):

    lbs_input_path = os.path.join(path, search)
    files = glob.glob(lbs_input_path)

    return files
print("-------------------------------------------")
print("LOADING DATA...")

subsetStarts = getProductList(folderStart, '*.npz')

if bandTrained == "VV":

    Y = getProductList2(folderResult, 'VV.npz')
else:
    Y = getProductList2(folderResult, 'VH.npz')

X = []

for x_ in subsetStarts:

    if bandTrained == "VV":
        X.append(x_[1:])
    else:
        temp = []
        temp.append(x_[0])
        temp.append(x_[2:])

        X.append(temp)

del subsetStarts

nbTrain = int(len(X) * 0.70)

X_trainL = X[:nbTrain]
Y_trainL = Y[:nbTrain]

X_testL = X[nbTrain:]
Y_testL = Y[nbTrain:]

#X_trainL = X[:10000]
#Y_trainL = Y[:10000]

#X_testL = X[10000:12000]
#Y_testL = Y[10000:12000]

del X
del Y

print("X_trainL : " + str(len(X_trainL)))
print("Y_trainL : " + str(len(Y_trainL)))
print("X_testL : " + str(len(X_testL)))
print("Y_testL : " + str(len(Y_testL)))

# Convert list in numpy.array

X_train = np.array(X_trainL)
del X_trainL

Y_train = np.array(Y_trainL)
del Y_trainL

X_test = np.array(X_testL)
del X_testL

Y_test = np.array(Y_testL)
del Y_testL

# Reshape X from (nbSamples, 7, xSize, ySize) to (nbSamples, xSize, ySize, 7)

X_train = np.swapaxes(X_train, 1, 2)
X_train = np.swapaxes(X_train, 2, 3)

X_test = np.swapaxes(X_test, 1, 2)
X_test = np.swapaxes(X_test, 2, 3)

# Reshape Y from (nbSamples, xSize, ySize) to (nbSamples, xSize, ySize, 1)

Y_train = Y_train.reshape(len(Y_train), len(Y_train[0]), len(Y_train[0][0]), 1).astype('float32')
Y_test = Y_test.reshape(len(Y_test), len(Y_test[0]), len(Y_test[0][0]), 1).astype('float32')

# Create model

#l0 = Input(shape=(height, width, 9), name='l0')

#l0 = Input(shape=(len(subsetResults[0]), len(subsetResults[0][0]), 7), name='l0')

l0 = Input(shape=(50, 50, 7), name='l0')
l0_n = BatchNormalization()(l0)

l1 = Conv2D(7, (5, 5), padding='same', activation='relu', name='l1')(l0_n)
l1_mp = MaxPooling2D((2, 2), name='l1_mp')(l1)

l2 = Conv2D(7, (3, 3), padding='same', activation='relu', name='l2')(l1_mp)
#l2_mp = MaxPooling2D((5, 5), name='l2_mp')(l2)

#l22 = Conv2D(14, (5, 5), padding='same', activation='relu', name='l22')(l2)

l3 = Conv2D(7, (5, 5), padding='same', activation='relu', name='l3')(l2)
l3_us = UpSampling2D((2, 2))(l3)

l4 = Conv2D(1, (5, 5), padding='same', activation='relu', name='l4')(l3_us)
l4_us = UpSampling2D((2, 2))(l4)

l45 = Conv2D(1, (3, 3), padding='same', activation='relu', name='l45')(l4_us)
l45_mp = MaxPooling2D(pool_size=(2, 2), name='l45_mp')(l45)

l5 = Conv2D(1, (5, 5), padding='same', activation='relu', name='l5')(l45_mp)

#flat = Flatten(name='flat')(l4_us)

#l5 = Dense((250, 250), activation='relu', name='l5')(flat)

#l5 = Dense(n_classes, activation='softmax', name='l5')(l4)

print("TRAINING START...")

model = Model(inputs=l0, outputs=l5)
model.summary()

# Train model

batch_size = 1024
n_epoch = 100

#model.compile(loss='categorical_crossentropy', optimizer=RMSprop(), metrics=['accuracy'])
model.compile(loss='mean_absolute_percentage_error', optimizer='RMSprop', metrics=['mean_absolute_percentage_error'])
history = model.fit(X_train, Y_train, batch_size=batch_size, epochs=n_epoch, verbose=1, validation_data=(X_test, Y_test), use_multiprocessing=True)

f = open(historyModelPath + "/history.csv", "w+")
f.close()

# Save history and model
pd.DataFrame.from_dict(history.history).to_csv(historyModelPath + "/history.csv", index=False)
model.save(historyModelPath + "/model.h5")
