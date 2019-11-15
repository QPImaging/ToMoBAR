#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
* Script to generate 3D analytical phantoms and their projection data using TomoPhantom
* Synthetic flat fields are also genererated and noise incorporated into data 
together with normalisation errors. This simulates more challeneging data for 
reconstruction.
* tomobar is required for reconstruction

>>>>> Dependencies (reconstruction): <<<<<
1. ASTRA toolbox: conda install -c astra-toolbox astra-toolbox
2. tomobar: conda install -c dkazanc tomobar
or install from https://github.com/dkazanc/ToMoBAR

@author: Daniil Kazantsev
"""
import timeit
import os
import matplotlib.pyplot as plt
import numpy as np
import tomophantom
from tomophantom import TomoP3D
from tomophantom.supp.qualitymetrics import QualityTools
from tomophantom.supp.flatsgen import flats
from tomophantom.supp.normraw import normaliser_sim

print ("Building 3D phantom using TomoPhantom software")
tic=timeit.default_timer()
model = 13 # select a model number from the library
N_size = 256 # Define phantom dimensions using a scalar value (cubic phantom)
path = os.path.dirname(tomophantom.__file__)
path_library3D = os.path.join(path, "Phantom3DLibrary.dat")
#This will generate a N_size x N_size x N_size phantom (3D)
phantom_tm = TomoP3D.Model(model, N_size, path_library3D)
toc=timeit.default_timer()
Run_time = toc - tic
print("Phantom has been built in {} seconds".format(Run_time))

sliceSel = int(0.5*N_size)
#plt.gray()
plt.figure() 
plt.subplot(131)
plt.imshow(phantom_tm[sliceSel,:,:],vmin=0, vmax=1)
plt.title('3D Phantom, axial view')

plt.subplot(132)
plt.imshow(phantom_tm[:,sliceSel,:],vmin=0, vmax=1)
plt.title('3D Phantom, coronal view')

plt.subplot(133)
plt.imshow(phantom_tm[:,:,sliceSel],vmin=0, vmax=1)
plt.title('3D Phantom, sagittal view')
plt.show()

# Projection geometry related parameters:
Horiz_det = int(np.sqrt(2)*N_size) # detector column count (horizontal)
Vert_det = N_size # detector row count (vertical) (no reason for it to be > N)
angles_num = int(0.5*np.pi*N_size); # angles number
angles = np.linspace(0.0,179.9,angles_num,dtype='float32') # in degrees
angles_rad = angles*(np.pi/180.0)
#%%
print ("Building 3D analytical projection data with TomoPhantom")
projData3D_analyt= TomoP3D.ModelSino(model, N_size, Horiz_det, Vert_det, angles, path_library3D)

intens_max = 70
sliceSel = 100
plt.figure() 
plt.subplot(131)
plt.imshow(projData3D_analyt[:,sliceSel,:],vmin=0, vmax=intens_max)
plt.title('2D Projection (analytical)')
plt.subplot(132)
plt.imshow(projData3D_analyt[sliceSel,:,:],vmin=0, vmax=intens_max)
plt.title('Sinogram view')
plt.subplot(133)
plt.imshow(projData3D_analyt[:,:,sliceSel],vmin=0, vmax=intens_max)
plt.title('Tangentogram view')
plt.show()
#%%
print ("Simulate flat fields, add noise and normalise projections...")
flatsnum = 20 # generate 20 flat fields
flatsSIM = flats(Vert_det, Horiz_det, maxheight = 0.01, maxthickness = 1, sigma_noise = 0.2, sigmasmooth = 3, flatsnum=flatsnum)

plt.figure() 
plt.imshow(flatsSIM[0,:,:],vmin=0, vmax=1)
plt.title('A selected simulated flat-field')
#%%
# Apply normalisation of data and add noise
flux_intensity = 10000 # controls the level of noise (Poisson) 
sigma_flats = 200 # control the level of noise in flats (lower creates more ring artifacts)
projData3D_norm = normaliser_sim(projData3D_analyt, flatsSIM, sigma_flats, flux_intensity)

intens_max = 70
sliceSel = 120
plt.figure() 
plt.subplot(131)
plt.imshow(projData3D_norm[:,sliceSel,:],vmin=0, vmax=intens_max)
plt.title('2D Projection (erroneous)')
plt.subplot(132)
plt.imshow(projData3D_norm[sliceSel,:,:],vmin=0, vmax=intens_max)
plt.title('Sinogram view')
plt.subplot(133)
plt.imshow(projData3D_norm[:,:,sliceSel],vmin=0, vmax=intens_max)
plt.title('Tangentogram view')
plt.show()
#%%
# initialise tomobar DIRECT reconstruction class ONCE
from tomobar.methodsDIR import RecToolsDIR
Rectools = RecToolsDIR(DetectorsDimH = Horiz_det,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = Vert_det,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    CenterRotOffset = 0.0, # Center of Rotation (CoR) scalar (for 3D case only)
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    device = 'gpu')
#%%
print ("Reconstruction using FBP from tomobar")
recNumerical= Rectools.FBP(projData3D_norm) # FBP reconstruction

sliceSel = int(0.5*N_size)
max_val = 1
#plt.gray()
plt.figure() 
plt.subplot(131)
plt.imshow(recNumerical[sliceSel,:,:],vmin=0, vmax=max_val)
plt.title('3D Reconstruction, axial view')

plt.subplot(132)
plt.imshow(recNumerical[:,sliceSel,:],vmin=0, vmax=max_val)
plt.title('3D Reconstruction, coronal view')

plt.subplot(133)
plt.imshow(recNumerical[:,:,sliceSel],vmin=0, vmax=max_val)
plt.title('3D Reconstruction, sagittal view')
plt.show()

# calculate errors 
Qtools = QualityTools(phantom_tm, recNumerical)
RMSE = Qtools.rmse()
print("Root Mean Square Error is {}".format(RMSE))
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing with FISTA-OS method using tomobar")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
# initialise tomobar ITERATIVE reconstruction class ONCE
from tomobar.methodsIR import RecToolsIR
RectoolsIR = RecToolsIR(DetectorsDimH = Horiz_det,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = Vert_det,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    CenterRotOffset = 0.0, # Center of Rotation (CoR) scalar (for 3D case only)
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    datafidelity='LS',# data fidelity, choose LS, PWLS (wip), GH (wip), Student (wip)
                    nonnegativity='ENABLE', # enable nonnegativity constraint (set to 'ENABLE')
                    OS_number = 10, # the number of subsets, NONE/(or > 1) ~ classical / ordered subsets
                    tolerance = 1e-10, # tolerance to stop outer iterations earlier
                    device='gpu')
lc = RectoolsIR.powermethod() # calculate Lipschitz constant
#%%
# Run FISTA reconstrucion algorithm without regularisation
#RecFISTA = RectoolsIR.FISTA(projData3D_norm, iterationsFISTA = 5, lipschitz_const = lc)

# Run FISTA reconstrucion algorithm with 3D regularisation
RecFISTA_reg = RectoolsIR.FISTA(projData3D_norm, 
                                iterationsFISTA = 20, 
                                regularisation = 'FGP_TV', 
                                regularisation_parameter = 0.00015, 
                                regularisation_iterations = 300,
                                lipschitz_const = lc)


Qtools = QualityTools(phantom_tm, RecFISTA_reg)
RMSE_FISTA_TV = Qtools.rmse()
print("RMSE for FISTA-OS-TV is {}".format(RMSE_FISTA_TV))

sliceSel = int(0.5*N_size)
max_val = 1
plt.figure() 
plt.subplot(131)
plt.imshow(RecFISTA_reg[sliceSel,:,:],vmin=0, vmax=max_val)
plt.title('3D FISTA-TV Reconstruction, axial view')

plt.subplot(132)
plt.imshow(RecFISTA_reg[:,sliceSel,:],vmin=0, vmax=max_val)
plt.title('3D FISTA-TV Reconstruction, coronal view')

plt.subplot(133)
plt.imshow(RecFISTA_reg[:,:,sliceSel],vmin=0, vmax=max_val)
plt.title('3D FISTA-TV Reconstruction, sagittal view')
plt.show()
#%%
# Run FISTA reconstrucion algorithm with 3D regularisation
RecFISTA_Huber_TV = RectoolsIR.FISTA(projData3D_norm, 
                                iterationsFISTA = 20, 
                                huber_data_threshold = 1.0,
                                regularisation = 'FGP_TV', 
                                regularisation_parameter = 0.00015, 
                                regularisation_iterations = 300,
                                lipschitz_const = lc)

Qtools = QualityTools(phantom_tm, RecFISTA_Huber_TV)
RMSE_FISTA_HUBER_TV = Qtools.rmse()
print("RMSE for FISTA-OS-Huber-TV is {}".format(RMSE_FISTA_HUBER_TV))

sliceSel = int(0.5*N_size)
max_val = 1
plt.figure() 
plt.subplot(131)
plt.imshow(RecFISTA_Huber_TV[sliceSel,:,:],vmin=0, vmax=max_val)
plt.title('3D Huber Rec, axial')

plt.subplot(132)
plt.imshow(RecFISTA_Huber_TV[:,sliceSel,:],vmin=0, vmax=max_val)
plt.title('3D Huber Rec, coronal')

plt.subplot(133)
plt.imshow(RecFISTA_Huber_TV[:,:,sliceSel],vmin=0, vmax=max_val)
plt.title('3D Huber Rec, sagittal')
plt.show()
#%%
# Run FISTA reconstrucion algorithm with 3D regularisation and a better ring model
RecFISTA_HuberRING_TV = RectoolsIR.FISTA(projData3D_norm, 
                                iterationsFISTA = 20, 
                                huber_data_threshold = 1.0,
                                ring_model_slices_window= 8,
                                regularisation = 'FGP_TV', 
                                regularisation_parameter = 0.00015, 
                                regularisation_iterations = 300,
                                lipschitz_const = lc)

Qtools = QualityTools(phantom_tm, RecFISTA_HuberRING_TV)
RMSE_FISTA_HUBER_RING_TV = Qtools.rmse()
print("RMSE for FISTA-OS-Huber-Ring-TV is {}".format(RMSE_FISTA_HUBER_RING_TV))

sliceSel = int(0.5*N_size)
max_val = 1
plt.figure() 
plt.subplot(131)
plt.imshow(RecFISTA_HuberRING_TV[sliceSel,:,:],vmin=0, vmax=max_val)
plt.title('3D HuberRing Rec, axial')

plt.subplot(132)
plt.imshow(RecFISTA_HuberRING_TV[:,sliceSel,:],vmin=0, vmax=max_val)
plt.title('3D HuberRing Rec, coronal')

plt.subplot(133)
plt.imshow(RecFISTA_HuberRING_TV[:,:,sliceSel],vmin=0, vmax=max_val)
plt.title('3D HuberRing Rec, sagittal')
plt.show()
#%%