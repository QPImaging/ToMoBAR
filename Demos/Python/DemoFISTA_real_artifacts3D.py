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
model = 14 # select a model number from the library
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
angles_num = int(0.5*N_size); # angles number
angles = np.linspace(0.0,179.9,angles_num,dtype='float32') # in degrees
angles_rad = angles*(np.pi/180.0)

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

print ("Simulate flat fields, add noise and normalise projections...")
flatsnum = 20 # generate 20 flat fields
flatsSIM = flats(Vert_det, Horiz_det, maxheight = 0.01, maxthickness = 1, sigma_noise = 0.2, sigmasmooth = 3, flatsnum=flatsnum)

plt.figure() 
plt.imshow(flatsSIM[0,:,:],vmin=0, vmax=1)
plt.title('A selected simulated flat-field')

# Apply normalisation of data and add noise
flux_intensity = 7000 # controls the level of noise (Poisson) 
sigma_flats = 200 # control the level of noise in flats (lower creates more ring artifacts)
[projData3D_norm, projData3D_raw] = normaliser_sim(projData3D_analyt, flatsSIM, sigma_flats, flux_intensity)

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
Rectools = RecToolsDIR(DetectorsDimH = Horiz_det,     # Horizontal detector dimension
                    DetectorsDimV = Vert_det,        # Vertical detector dimension (3D case)
                    CenterRotOffset = None,          # Center of Rotation scalar 
                    AnglesVec = angles_rad,          # A vector of projection angles in radians
                    ObjSize = N_size,                # Reconstructed object dimensions (scalar)
                    device_projector='gpu')

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
Rectools = RecToolsIR(DetectorsDimH = Horiz_det,     # Horizontal detector dimension
                    DetectorsDimV = Vert_det,        # Vertical detector dimension (3D case)
                    CenterRotOffset = None,          # Center of Rotation scalar
                    AnglesVec = angles_rad,          # A vector of projection angles in radians
                    ObjSize = N_size,                # Reconstructed object dimensions (scalar)
                    datafidelity='LS',               # Data fidelity, choose from LS, KL, PWLS
                    device_projector='gpu')

_data_ = {'projection_norm_data' : projData3D_norm,
          'OS_number' : 10} # data dictionary

lc = Rectools.powermethod(_data_) # calculate Lipschitz constant (run once to initialise)

# Run FISTA reconstrucion algorithm without regularisation
_algorithm_ = {'iterations' : 20,
               'lipschitz_const' : lc}

# adding regularisation using the CCPi regularisation toolkit
_regularisation_ = {'method' : 'PD_TV',
                    'regul_param' :0.0003,
                    'iterations' : 80,
                    'device_regulariser': 'gpu'}

# Run FISTA reconstrucion algorithm with 3D regularisation
RecFISTA_reg = Rectools.FISTA(_data_, _algorithm_, _regularisation_)

Qtools = QualityTools(phantom_tm, RecFISTA_reg)
RMSE_FISTA_TV = Qtools.rmse()
print("RMSE for FISTA-OS-TV is {}".format(RMSE_FISTA_TV))

sliceSel = int(0.5*N_size)
max_val = 1
plt.figure() 
plt.subplot(131)
plt.imshow(RecFISTA_reg[sliceSel,:,:],vmin=0, vmax=max_val)
plt.title('3D FISTA-TV Recon, axial view')

plt.subplot(132)
plt.imshow(RecFISTA_reg[:,sliceSel,:],vmin=0, vmax=max_val)
plt.title('3D FISTA-TV Recon, coronal view')

plt.subplot(133)
plt.imshow(RecFISTA_reg[:,:,sliceSel],vmin=0, vmax=max_val)
plt.title('3D FISTA-TV Recon, sagittal view')
plt.show()
#%%
# Run FISTA reconstrucion algorithm with 3D regularisation and Huber data penalty
# adding Huber data fidelity threhsold
_data_.update({'huber_threshold' : 0.8})

RecFISTA_Huber_TV = Rectools.FISTA(_data_, _algorithm_, _regularisation_)

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

# adding RING minimisation component (better model for data with rings - different from GH!)
#data.update({'huber_threshold' : None})
_data_.update({'ring_weights_threshold' : 0.7})
_data_.update({'ring_tuple_halfsizes' : (9,7,9)})

# Run FISTA reconstrucion algorithm with 3D regularisation and a better ring model
RecFISTA_HuberRING_TV = Rectools.FISTA(_data_, _algorithm_, _regularisation_)

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
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing with FISTA-KL-OS method using tomobar")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
# initialise tomobar ITERATIVE reconstruction class ONCE
from tomobar.methodsIR import RecToolsIR
Rectools = RecToolsIR(DetectorsDimH = Horiz_det,     # Horizontal detector dimension
                    DetectorsDimV = Vert_det,        # Vertical detector dimension (3D case)
                    CenterRotOffset = None,          # Center of Rotation scalar
                    AnglesVec = angles_rad,          # A vector of projection angles in radians
                    ObjSize = N_size,                # Reconstructed object dimensions (scalar)
                    datafidelity='KL',               # Data fidelity, choose from LS, KL, PWLS
                    device_projector='gpu')

_data_ = {'projection_norm_data' : projData3D_norm,
          'OS_number' : 10} # data dictionary

lc = Rectools.powermethod(_data_) # calculate Lipschitz constant (run once to initialise)

# Run FISTA reconstrucion algorithm without regularisation
_algorithm_ = {'iterations' : 30,
               'lipschitz_const' : lc*0.3}

# adding regularisation using the CCPi regularisation toolkit
_regularisation_ = {'method' : 'PD_TV',
                    'regul_param' :0.0001,
                    'iterations' : 80,
                    'device_regulariser': 'gpu'}

# Run FISTA reconstrucion algorithm with 3D regularisation
RecFISTA_KL_reg = Rectools.FISTA(_data_, _algorithm_, _regularisation_)

Qtools = QualityTools(phantom_tm, RecFISTA_KL_reg)
RMSE_FISTA_KL_TV = Qtools.rmse()
print("RMSE for FISTA-OS-KL-TV is {}".format(RMSE_FISTA_KL_TV))

sliceSel = int(0.5*N_size)
max_val = 1
plt.figure() 
plt.subplot(131)
plt.imshow(RecFISTA_KL_reg[sliceSel,:,:],vmin=0, vmax=max_val)
plt.title('3D FISTA-KL-TV Recon, axial view')

plt.subplot(132)
plt.imshow(RecFISTA_KL_reg[:,sliceSel,:],vmin=0, vmax=max_val)
plt.title('3D FISTA-KL-TV Recon, coronal view')

plt.subplot(133)
plt.imshow(RecFISTA_KL_reg[:,:,sliceSel],vmin=0, vmax=max_val)
plt.title('3D FISTA-KL-TV Recon, sagittal view')
plt.show()
#%%