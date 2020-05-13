#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPLv3 license (ASTRA toolbox)

Script to reconstruct tomographic X-ray data (ice cream crystallisation process)
obtained at Diamond Light Source (UK synchrotron), beamline I13

Dependencies: 
    * astra-toolkit, install conda install -c astra-toolbox astra-toolbox
    * CCPi-RGL toolkit (for regularisation), install with 
    conda install ccpi-regulariser -c ccpi -c conda-forge
    or conda build of  https://github.com/vais-ral/CCPi-Regularisation-Toolkit

<<<
IF THE SHARED DATA ARE USED FOR PUBLICATIONS/PRESENTATIONS etc., PLEASE CITE:
E. Guo et al. 2018. Revealing the microstructural stability of a 
three-phase soft solid (ice cream) by 4D synchrotron X-ray tomography.
Journal of Food Engineering, vol.237
>>>
@author: Daniil Kazantsev: https://github.com/dkazanc
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt

# loading data 
datapathfile = '../../data/data_icecream.h5'
h5f = h5py.File(datapathfile, 'r')
data_norm = h5f['icecream_normalised'][:]
data_raw = h5f['icecream_raw'][:]
angles_rad = h5f['angles'][:]
h5f.close()
data_norm = np.swapaxes(data_norm[:,:,0],0,1)
data_raw = np.swapaxes(data_raw[:,:,0],0,1)
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("%%%%%%%%%%%%Reconstructing with FBP method %%%%%%%%%%%%%%%%%")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
from tomobar.methodsDIR import RecToolsDIR

N_size = 2000
angles_number,detectorHoriz = np.shape(data_norm)

RectoolsDIR = RecToolsDIR(DetectorsDimH = detectorHoriz, # Horizontal detector dimension
                    DetectorsDimV = None,                # Vertical detector dimension (3D case)
                    CenterRotOffset = 92,                # Center of Rotation scalar
                    AnglesVec = angles_rad,              # A vector of projection angles in radians
                    ObjSize = N_size,                    # Reconstructed object dimensions (scalar)
                    device_projector='gpu')

FBPrec = RectoolsDIR.FBP(data_norm)

plt.figure()
#plt.imshow(FBPrec[500:1500,500:1500], vmin=0, vmax=1, cmap="gray")
plt.imshow(FBPrec, vmin=0, vmax=1, cmap="gray")
plt.title('FBP reconstruction')
#%%
from tomobar.methodsIR import RecToolsIR
# set parameters and initiate a class object
Rectools = RecToolsIR(DetectorsDimH =  detectorHoriz, # Horizontal detector dimension
                    DetectorsDimV = None,            # Vertical detector dimension (3D case)
                    CenterRotOffset = 92,          # Center of Rotation scalar
                    AnglesVec = angles_rad,          # A vector of projection angles in radians
                    ObjSize = N_size,                # Reconstructed object dimensions (scalar)
                    datafidelity='PWLS',             # Data fidelity, choose from LS, KL, PWLS
                    device_projector='gpu')

# prepare dictionaries with parameters:
_data_ = {'projection_norm_data' : data_norm,
          'projection_raw_data' :data_raw,
          'OS_number' : 6} # data dictionary

lc = Rectools.powermethod(_data_) # calculate Lipschitz constant (run once to initialise)

_algorithm_ = {'iterations' : 20,
               'lipschitz_const' : lc}

# Run CGLS reconstrucion algorithm 
RecCGLS = Rectools.CGLS(_data_, _algorithm_)

plt.figure()
plt.imshow(RecCGLS, vmin=0, vmax=0.3, cmap="gray")
plt.title('CGLS reconstruction')
plt.show()
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing with FISTA PWLS-OS-TV method % %%%%%%%%%%%%%%")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
# adding regularisation
_regularisation_ = {'method' : 'PD_TV',
                    'regul_param' : 0.0012,
                    'iterations' : 80,
                    'device_regulariser': 'gpu'}

RecFISTA_TV = Rectools.FISTA(_data_, _algorithm_, _regularisation_)

plt.figure()
plt.imshow(RecFISTA_TV, vmin=0, vmax=0.2, cmap="gray")
plt.title('FISTA-PWLS-OS-TV reconstruction')
plt.show()
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing with FISTA PWLS-HUBER-OS-TV method % %%%%%%%%")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
_data_.update({'huber_threshold' : 40.0})

RecFISTA_TV_hub = Rectools.FISTA(_data_, _algorithm_, _regularisation_)

plt.figure()
plt.imshow(RecFISTA_TV_hub, vmin=0, vmax=0.2, cmap="gray")
plt.title('FISTA-PWLS-HUBER-OS-TV reconstruction')
plt.show()
#%%
from ccpi.filters.regularisers import PatchSelect
print ("Pre-calculating weights for non-local patches...")

pars = {'algorithm' : PatchSelect, \
        'input' : RecCGLS,\
        'searchwindow': 7, \
        'patchwindow': 2,\
        'neighbours' : 13 ,\
        'edge_parameter':0.8}
H_i, H_j, Weights = PatchSelect(pars['input'], pars['searchwindow'],pars['patchwindow'],pars['neighbours'],
              pars['edge_parameter'], 'gpu')

plt.figure()
plt.imshow(Weights[0,:,:], vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing with FISTA PWLS-OS-NLTV method %%%%%%%%%%%%%%")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
_regularisation_ = {'method' : 'NLTV',
                    'regul_param' :0.0005,
                    'iterations' : 5,
                    'NLTV_H_i'  : H_i,\
                    'NLTV_H_j'  : H_j,\
                    'NLTV_Weights'  : Weights,\
                    'device_regulariser': 'gpu'}

RecFISTA_regNLTV = Rectools.FISTA(_data_, _algorithm_, _regularisation_)
fig = plt.figure()
plt.imshow(RecFISTA_regNLTV, vmin=0, vmax=0.2, cmap="gray")
plt.title('FISTA PWLS-OS-NLTV reconstruction')
plt.show()
#fig.savefig('ice_NLTV.png', dpi=200)
#%%
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("%%%%%%Reconstructing with ADMM LS-NLTV method %%%%%%%%%%%%%%%%")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
_algorithm_ = {'iterations' : 5,
               'ADMM_rho_const' : 500.0}

_regularisation_ = {'method' : 'PD_TV',
                    'regul_param' : 0.015,
                    'iterations' : 80,
                    'device_regulariser': 'gpu'}

# Run ADMM-LS-TV reconstrucion algorithm
RecADMM_LS_TV = Rectools.ADMM(_data_, _algorithm_, _regularisation_)

fig = plt.figure()
plt.imshow(RecADMM_LS_TV, vmin=0, vmax=0.2, cmap="gray")
#plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('ADMM LS-TV reconstruction')
plt.show()
#%%
