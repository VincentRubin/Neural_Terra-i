import os
currentPath = os.getcwd()

import configparser
settings = configparser.ConfigParser()
settings._interpolation = configparser.ExtendedInterpolation()
settings.read(currentPath + "/config/main_config.ini")

folderStart = settings.get('Main-Config', 'subset_start_path')
folderResult = settings.get('Main-Config', 'subset_end_path')
bandTrained = settings.get('Main-Config', 'band_trained')
historyModelPath = settings.get('Main-Config', 'history_model_path')

import numpy as np
import glob
from itertools import cycle

import array
import numpy as np
import itertools
import matplotlib.pyplot as plt

import pandas as pd

from keras.datasets import mnist
from keras.models import Model
from keras.layers.core import Dense, Dropout, Flatten, Reshape
#from tensorflow.keras.optimizers import RMSprop
from keras.utils import np_utils
from keras.layers.convolutional import Conv2D, MaxPooling2D, UpSampling2D, SeparableConv2D
from keras.layers import Input, BatchNormalization
from sklearn import metrics as me
from scipy import stats
from keras import models
from keras import layers
from sklearn.preprocessing import Normalizer

import tensorflow as tf

import sys

def getProductList(path, search, permutations):

    products = []

    lbs_input_path = os.path.join(path, search)
    files = glob.glob(lbs_input_path)

    nbFiles = len(files)
    nbFilesDone = 0

    for index in permutations:

        print("LOADING DATA - X : " + str(nbFilesDone) + "/" + str(nbFiles) + " - (" + str("{:.2f}".format(nbFilesDone / nbFiles * 100)) + "%)")

        temp = np.load(files[index])
        products.append(temp['arr_0'])

        nbFilesDone += 1
        print("\033[A\033[A")

    print("LOADING DATA - X : " + str(nbFilesDone) + "/" + str(nbFiles) + " - (" + str("{:.2f}".format(nbFilesDone / nbFiles * 100)) + "%)")

    return products

def getProductList2(path, search, permutations):

    products = []

    folders = os.listdir(path)

    nbFiles = len(folders)
    nbFilesDone = 0

    for index in permutations:

        print("LOADING DATA - Y : " + str(nbFilesDone) + "/" + str(nbFiles) + " - (" + str("{:.2f}".format(nbFilesDone / nbFiles * 100)) + "%)")

        pathF = folders[index]

        for pathF2 in os.listdir(path + "/" + pathF):

            if search in pathF2:
                temp = np.load(path + "/" + pathF + "/" + pathF2)
                products.append(temp['arr_0'])

        nbFilesDone += 1
        print("\033[A\033[A")

    print("LOADING DATA - Y : " + str(nbFilesDone) + "/" + str(nbFiles) + " - (" + str("{:.2f}".format(nbFilesDone / nbFiles * 100)) + "%)")

    return products

def getIndicesPermutation(path, search):

    lbs_input_path = os.path.join(path, search)
    files = glob.glob(lbs_input_path)

    p = np.random.permutation(len(files))

    return p

def createModel():

    # Create model

    l0 = Input(shape=(50, 50, 7), name='l0')
    l0_n = BatchNormalization()(l0)

    l1 = Conv2D(7, (5, 5), padding='same', activation='tanh', name='l1')(l0_n)

    l2 = Conv2D(7, (3, 3), padding='same', activation='relu', name='l2')(l1)
    l2_pad = layers.ZeroPadding2D(padding=(2, 2))(l2)

    l3 = layers.LocallyConnected2D(14, (5, 5), activation='relu', name='l3')(l2_pad)

    l4 = Conv2D(7, (3, 3), padding='same', activation='selu', name='l4')(l3)

    l5 = Conv2D(14, (3, 3), padding='same', activation='softmax', name='l5')(l4)
    l5_pad = layers.ZeroPadding2D(padding=(2, 2))(l5)

    l6 = layers.LocallyConnected2D(7, (5, 5), activation='relu', name='l6')(l5_pad)
    l6_pad = layers.ZeroPadding2D(padding=(1, 1))(l6)

    l7 = layers.LocallyConnected2D(1, (3, 3), activation='relu', name='l7')(l6_pad)

    model = Model(inputs=l0, outputs=l7)
    model.summary()
    model.compile(loss='mean_absolute_percentage_error', optimizer='RMSprop', metrics=['mean_absolute_percentage_error'])

    return model

print("-------------------------------------------")

batch_size = int(sys.argv[1])
n_epoch = int(sys.argv[2])
initial_epoch = int(sys.argv[3])
nbEpochBetweenSave = int(sys.argv[4])
readModel = int(sys.argv[5])

permutations = getIndicesPermutation(folderStart, '*.npz')

subsetStarts = getProductList(folderStart, '*.npz', permutations)

if bandTrained == "VV":
    Y = getProductList2(folderResult, 'VV.npz', permutations)
else:
    Y = getProductList2(folderResult, 'VH.npz', permutations)

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

print("PREPARING DATA...")

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

print("X_train : " + str(len(X_trainL)))
print("Y_train : " + str(len(Y_trainL)))
print("X_test : " + str(len(X_testL)))
print("Y_test : " + str(len(Y_testL)))

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

# Create or read model

model = None
#historyFull = {}

if readModel == 1:
    model = tf.keras.models.load_model(historyModelPath + "/model.h5")
    #historyFull = pd.read_csv(historyModelPath + "/history.csv").to_dict()
else:
    model = createModel()

# Train model

print("TRAINING START...")
model.summary()

nbEpochDone = initial_epoch
nbEpochToBeDone = initial_epoch + nbEpochBetweenSave

while(nbEpochDone < n_epoch):

    print("TRAINING : (" + str(nbEpochDone) + " -> " + str(nbEpochToBeDone) + ") / " + str(n_epoch))

    history = model.fit(X_train, Y_train, batch_size=batch_size, epochs=nbEpochToBeDone, initial_epoch=nbEpochDone, verbose=1, validation_data=(X_test, Y_test), use_multiprocessing=False)

    # create file for history
    historyPath = historyModelPath + "/history_" + str(nbEpochDone) + "-" + str(nbEpochToBeDone - 1) + ".csv"

    f = open(historyPath, "w+")
    f.close()

    #historyFull += history.history

    # Save history and model
    pd.DataFrame.from_dict(history.history).to_csv(historyPath, index=False)
    model.save(historyModelPath + "/model_" + str(nbEpochToBeDone) + ".h5")

    nbEpochDone = nbEpochToBeDone
    nbEpochToBeDone += nbEpochBetweenSave

    print("-------------------------------------------")

# Save history and model
#pd.DataFrame.from_dict(historyFull).to_csv(historyModelPath + "/history.csv", index=True)
model.save(historyModelPath + "/model.h5")

print("TRAINING DONE !")
