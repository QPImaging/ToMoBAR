# -*- coding: utf-8 -*-
"""
Created on Wed Aug 23 16:34:49 2017
@author: ofn77899
Based on DemoRD2.m
"""

import h5py
import numpy

from ccpi.reconstruction.FISTAReconstructor import FISTAReconstructor
import astra
import matplotlib.pyplot as plt
from ccpi.imaging.Regularizer import Regularizer
from ccpi.reconstruction.AstraDevice import AstraDevice
from ccpi.reconstruction.DeviceModel import DeviceModel

#from ccpi.viewer.CILViewer2D import *


def RMSE(signal1, signal2):
    '''RMSE Root Mean Squared Error'''
    if numpy.shape(signal1) == numpy.shape(signal2):
        err = (signal1 - signal2)
        err = numpy.sum( err * err )/numpy.size(signal1);  # MSE
        err = sqrt(err);                                   # RMSE
        return err
    else:
        raise Exception('Input signals must have the same shape')

filename = r'/home/ofn77899/Reconstruction/CCPi-FISTA_Reconstruction/src/Python/test/phantom3D256_projections.h5'
nx = h5py.File(filename, "r")
#getEntry(nx, '/')
# I have exported the entries as children of /
entries = [entry for entry in nx['/'].keys()]
print (entries)

projections = numpy.asarray(nx.get('/projections'), dtype="float32")
#Weights3D = numpy.asarray(nx.get('/Weights3D'), dtype="float32")
#angSize = numpy.asarray(nx.get('/angSize'), dtype=int)[0]
angles_rad = numpy.asarray(nx.get('/angles'), dtype="float32")
angSize = numpy.size(angles_rad)
image_size_x, image_size_y, image_size_z = \
              numpy.asarray(nx.get('/reconstruction_volume'), dtype=int)
det_col_count, det_row_count = \
              numpy.asarray(nx.get('/camera/size'))
#slices_tot = numpy.asarray(nx.get('/slices_tot'), dtype=int)[0]
detectorSpacingX, detectorSpacingY = numpy.asarray(nx.get('/camera/spacing'), dtype=int)

Z_slices = 20
#det_row_count = image_size_y
# next definition is just for consistency of naming
#det_col_count = image_size_x

detectorSpacingX = 1.0
detectorSpacingY = detectorSpacingX


proj_geom = astra.creators.create_proj_geom('parallel3d',
                                            detectorSpacingX,
                                            detectorSpacingY,
                                            det_row_count,
                                            det_col_count,
                                            angles_rad)

#vol_geom = astra_create_vol_geom(recon_size,recon_size,Z_slices);
##image_size_x = recon_size
##image_size_y = recon_size
##image_size_z = Z_slices
vol_geom = astra.creators.create_vol_geom( image_size_x,
                                           image_size_y,
                                           image_size_z)

## First pass the arguments to the FISTAReconstructor and test the
## Lipschitz constant
astradevice = AstraDevice(DeviceModel.DeviceType.PARALLEL3D.value,
                [proj_geom['DetectorRowCount'] ,
                 proj_geom['DetectorColCount'] ,
                 proj_geom['DetectorSpacingX'] ,
                 proj_geom['DetectorSpacingY'] ,
                 proj_geom['ProjectionAngles']
                 ],
                [
                    vol_geom['GridColCount'],
                    vol_geom['GridRowCount'], 
                    vol_geom['GridSliceCount'] ] )
## create the sinogram 
Sino3D = numpy.transpose(projections, axes=[1,0,2])

fistaRecon = FISTAReconstructor(proj_geom,
                                vol_geom,
                                Sino3D ,
                                #weights=Weights3D,
                                device=astradevice)

print ("Lipschitz Constant {0}".format(fistaRecon.pars['Lipschitz_constant']))
fistaRecon.setParameter(number_of_iterations = 4)
#fistaRecon.setParameter(Lipschitz_constant = 767893952.0)
fistaRecon.setParameter(ring_alpha = 21)
fistaRecon.setParameter(ring_lambda_R_L1 = 0.002)
#fistaRecon.setParameter(ring_lambda_R_L1 = 0)
subsets = 8
fistaRecon.setParameter(subsets=subsets)


#reg = Regularizer(Regularizer.Algorithm.FGP_TV)
#reg.setParameter(regularization_parameter=0.005,
#                          number_of_iterations=50)
reg = Regularizer(Regularizer.Algorithm.FGP_TV)
reg.setParameter(regularization_parameter=5e6,
                          tolerance_constant=0.0001,
                          number_of_iterations=50)

#fistaRecon.setParameter(regularizer=reg)
#lc = fistaRecon.getParameter('Lipschitz_constant')
#reg.setParameter(regularization_parameter=5e6/lc)

## Ordered subset
if True:
    #subsets = 8
    fistaRecon.setParameter(subsets=subsets)
    fistaRecon.createOrderedSubsets()
else:
    angles = fistaRecon.getParameter('projector_geometry')['ProjectionAngles']
    #binEdges = numpy.linspace(angles.min(),
    #                          angles.max(),
    #                          subsets + 1)
    binsDiscr, binEdges = numpy.histogram(angles, bins=subsets)
    # get rearranged subset indices
    IndicesReorg = numpy.zeros((numpy.shape(angles)))
    counterM = 0
    for ii in range(binsDiscr.max()):
        counter = 0
        for jj in range(subsets):
            curr_index = ii + jj  + counter
            #print ("{0} {1} {2}".format(binsDiscr[jj] , ii, counterM))
            if binsDiscr[jj] > ii:
                if (counterM < numpy.size(IndicesReorg)):
                    IndicesReorg[counterM] = curr_index
                counterM = counterM + 1
                
            counter = counter + binsDiscr[jj] - 1


if True:
    print ("Lipschitz Constant {0}".format(fistaRecon.pars['Lipschitz_constant']))
    print ("prepare for iteration")
    fistaRecon.prepareForIteration()
    
    

    print("initializing  ...")
    if True:
        # if X doesn't exist
        #N = params.vol_geom.GridColCount
        N = vol_geom['GridColCount']
        print ("N " + str(N))
        X = numpy.asarray(numpy.ones((image_size_x,image_size_y,image_size_z)),
                        dtype=numpy.float) * 0.001
        X = numpy.asarray(numpy.zeros((image_size_x,image_size_y,image_size_z)),
                        dtype=numpy.float) 
    else:
        #X = fistaRecon.initialize()
        X = numpy.load("X.npy")
    
    print (numpy.shape(X))
    X_t = X.copy()
    print ("initialized")
    proj_geom , vol_geom, sino , \
        SlicesZ, weights , alpha_ring = fistaRecon.getParameter(
            ['projector_geometry' , 'output_geometry',
             'input_sinogram', 'SlicesZ' ,  'weights', 'ring_alpha'])
    lambdaR_L1 , alpha_ring , weights , L_const= \
                       fistaRecon.getParameter(['ring_lambda_R_L1',
                                               'ring_alpha' , 'weights',
                                               'Lipschitz_constant'])

    #fistaRecon.setParameter(number_of_iterations = 3)
    iterFISTA = fistaRecon.getParameter('number_of_iterations')
    # errors vector (if the ground truth is given)
    Resid_error = numpy.zeros((iterFISTA));
    # objective function values vector
    objective = numpy.zeros((iterFISTA)); 

      
    t = 1
    

    ## additional for 
    proj_geomSUB = proj_geom.copy()
    fistaRecon.residual2 = numpy.zeros(numpy.shape(fistaRecon.pars['input_sinogram']))
    residual2 = fistaRecon.residual2
    sino_updt_FULL = fistaRecon.residual.copy()
    r_x = fistaRecon.r.copy()

    results = []
    print ("starting iterations")
##    % Outer FISTA iterations loop
    for i in range(fistaRecon.getParameter('number_of_iterations')):
##        % With OS approach it becomes trickier to correlate independent subsets, hence additional work is required
##        % one solution is to work with a full sinogram at times
##        if ((i >= 3) && (lambdaR_L1 > 0))
##            [sino_id2, sino_updt2] = astra_create_sino3d_cuda(X, proj_geom, vol_geom);
##            astra_mex_data3d('delete', sino_id2);
##        end
        # With OS approach it becomes trickier to correlate independent subsets,
        # hence additional work is required one solution is to work with a full
        # sinogram at times

        
        #t_old = t
        SlicesZ, anglesNumb, Detectors = \
                    numpy.shape(fistaRecon.getParameter('input_sinogram'))
        ## https://github.com/vais-ral/CCPi-FISTA_Reconstruction/issues/4
        r_old = fistaRecon.r.copy()
            
        if (i > 1 and lambdaR_L1 > 0) :
            for kkk in range(anglesNumb):
                 
                 residual2[:,kkk,:] = (weights[:,kkk,:]).squeeze() * \
                                       ((sino_updt_FULL[:,kkk,:]).squeeze() - \
                                        (sino[:,kkk,:]).squeeze() -\
                                        (alpha_ring * r_x)
                                        )
            #r_old = fistaRecon.r.copy()
            vec = fistaRecon.residual.sum(axis = 1)
            #if SlicesZ > 1:
            #    vec = vec[:,1,:] # 1 or 0?
            r_x = fistaRecon.r_x
            # update ring variable
            fistaRecon.r = (r_x - (1./L_const) * vec)

        # subset loop
        counterInd = 1
        geometry_type = fistaRecon.getParameter('projector_geometry')['type']
        angles = fistaRecon.getParameter('projector_geometry')['ProjectionAngles']
    
##        if geometry_type == 'parallel' or \
##           geometry_type == 'fanflat' or \
##           geometry_type == 'fanflat_vec' :
##            
##            for kkk in range(SlicesZ):
##                sino_id, sinoT[kkk] = \
##                         astra.creators.create_sino3d_gpu(
##                             X_t[kkk:kkk+1], proj_geomSUB, vol_geom)
##                sino_updt_Sub[kkk] = sinoT.T.copy()
##                
##        else:
##            sino_id, sino_updt_Sub = \
##                astra.creators.create_sino3d_gpu(X_t, proj_geomSUB, vol_geom)
##        
##        astra.matlab.data3d('delete', sino_id)
  
        for ss in range(fistaRecon.getParameter('subsets')):
            print ("Subset {0}".format(ss))
            X_old = X.copy()
            t_old = t
            print ("X[0][0][0] {0} t {1}".format(X[0][0][0], t))
            
            # the number of projections per subset
            numProjSub = fistaRecon.getParameter('os_bins')[ss]
            CurrSubIndices = fistaRecon.getParameter('os_indices')\
                             [counterInd:counterInd+numProjSub]
            shape = list(numpy.shape(fistaRecon.getParameter('input_sinogram')))
            shape[1] = numProjSub
            sino_updt_Sub = numpy.zeros(shape)
            
            #print ("Len CurrSubIndices {0}".format(numProjSub))
            mask = numpy.zeros(numpy.shape(angles), dtype=bool)
            cc = 0
            for j in range(len(CurrSubIndices)):
                mask[int(CurrSubIndices[j])] = True

            ## this is a reduced device
            rdev = fistaRecon.getParameter('device_model')\
                   .createReducedDevice(proj_par={'angles' : angles[mask]},
                                        vol_par={})
            proj_geomSUB['ProjectionAngles'] = angles[mask]

            

            if geometry_type == 'parallel' or \
               geometry_type == 'fanflat' or \
               geometry_type == 'fanflat_vec' :

                for kkk in range(SlicesZ):
                    sino_id, sinoT = astra.creators.create_sino3d_gpu (
                        X_t[kkk:kkk+1] , proj_geomSUB, vol_geom)
                    sino_updt_Sub[kkk] = sinoT.T.copy()
                    astra.matlab.data3d('delete', sino_id)
            else:
                # for 3D geometry (watch the GPU memory overflow in ASTRA < 1.8)
                sino_id, sino_updt_Sub = \
                     astra.creators.create_sino3d_gpu (X_t,
                                                       proj_geomSUB,
                                                       vol_geom)
                
                astra.matlab.data3d('delete', sino_id)
                
            


            ## RING REMOVAL
            residual = fistaRecon.residual
            
            
            if lambdaR_L1 > 0 :
                 print ("ring removal")
                 residualSub = numpy.zeros(shape)
    ##             for a chosen subset
    ##                for kkk = 1:numProjSub
    ##                    indC = CurrSubIndeces(kkk);
    ##                    residualSub(:,kkk,:) =  squeeze(weights(:,indC,:)).*(squeeze(sino_updt_Sub(:,kkk,:)) - (squeeze(sino(:,indC,:)) - alpha_ring.*r_x));
    ##                    sino_updt_FULL(:,indC,:) = squeeze(sino_updt_Sub(:,kkk,:)); % filling the full sinogram
    ##                end
                 for kkk in range(numProjSub):
                     #print ("ring removal indC ... {0}".format(kkk))
                     indC = int(CurrSubIndices[kkk])
                     residualSub[:,kkk,:] = weights[:,indC,:].squeeze() * \
                            (sino_updt_Sub[:,kkk,:].squeeze() - \
                             sino[:,indC,:].squeeze() - alpha_ring * r_x)
                     # filling the full sinogram
                     sino_updt_FULL[:,indC,:] = sino_updt_Sub[:,kkk,:].squeeze()

            else:
                #PWLS model
                # I guess we need to use mask here instead
                residualSub = weights[:,CurrSubIndices,:] * \
                              ( sino_updt_Sub - \
                                sino[:,CurrSubIndices,:].squeeze() )
            # it seems that in the original code the following like is not
            # calculated in the case of ring removal
            objective[i] = 0.5 * numpy.linalg.norm(residualSub)

            #backprojection
            if geometry_type == 'parallel' or \
               geometry_type == 'fanflat' or \
               geometry_type == 'fanflat_vec' :
                # if geometry is 2D use slice-by-slice projection-backprojection
                # routine
                x_temp = numpy.zeros(numpy.shape(X), dtype=numpy.float32)
                for kkk in range(SlicesZ):
                    
                    x_id, x_temp[kkk] = \
                             astra.creators.create_backprojection3d_gpu(
                                 residualSub[kkk:kkk+1],
                                 proj_geomSUB, vol_geom)
                    astra.matlab.data3d('delete', x_id)
                    
            else:
                x_id, x_temp = \
                      astra.creators.create_backprojection3d_gpu(
                          residualSub, proj_geomSUB, vol_geom)

                astra.matlab.data3d('delete', x_id)
                
            X = X_t - (1/L_const) * x_temp

        

            ## REGULARIZATION
            ## SKIPPING FOR NOW
            ## Should be simpli
            # regularizer = fistaRecon.getParameter('regularizer')
            # for slices:
            # out = regularizer(input=X)
            print ("regularizer")
            reg = fistaRecon.getParameter('regularizer')

            if reg is not None:
                X = reg(input=X,
                        output_all=False)

            t = (1 + numpy.sqrt(1 + 4 * t **2))/2
            X_t = X + (((t_old -1)/t) * (X-X_old))
            counterInd = counterInd + numProjSub - 1
        if i == 1:
            r_old = fistaRecon.r.copy()
            
        ## FINAL
        print ("final")
        lambdaR_L1 = fistaRecon.getParameter('ring_lambda_R_L1')
        if lambdaR_L1 > 0:
            fistaRecon.r = numpy.max(
                numpy.abs(fistaRecon.r) - lambdaR_L1 , 0) * \
                numpy.sign(fistaRecon.r)
            # updating r
            r_x = fistaRecon.r + ((t_old-1)/t) * (fistaRecon.r - r_old)
        

        if fistaRecon.getParameter('region_of_interest') is None:
            string = 'Iteration Number {0} | Objective {1} \n'
            print (string.format( i, objective[i]))
        else:
            ROI , X_ideal = fistaRecon.getParameter('region_of_interest',
                                                    'ideal_image')
            
            Resid_error[i] = RMSE(X*ROI, X_ideal*ROI)
            string = 'Iteration Number {0} | RMS Error {1} | Objective {2} \n'
            print (string.format(i,Resid_error[i], objective[i]))

        results.append(X[10])
    numpy.save("X_out_os.npy", X)

else:
    
    
    
    astradevice = AstraDevice(DeviceModel.DeviceType.PARALLEL3D.value,
                [proj_geom['DetectorRowCount'] ,
                 proj_geom['DetectorColCount'] ,
                 proj_geom['DetectorSpacingX'] ,
                 proj_geom['DetectorSpacingY'] ,
                 proj_geom['ProjectionAngles']
                 ],
                [
                    vol_geom['GridColCount'],
                    vol_geom['GridRowCount'], 
                    vol_geom['GridSliceCount'] ] )
    regul = Regularizer(Regularizer.Algorithm.FGP_TV)
    regul.setParameter(regularization_parameter=5e6,
                       number_of_iterations=50,
                       tolerance_constant=1e-4,
                       TV_penalty=Regularizer.TotalVariationPenalty.isotropic)

    fistaRecon = FISTAReconstructor(proj_geom,
                                vol_geom,
                                Sino3D ,
                                weights=Weights3D,
                                device=astradevice,
                                #regularizer = regul,
                                subsets=8)

    print ("Lipschitz Constant {0}".format(fistaRecon.pars['Lipschitz_constant']))
    fistaRecon.setParameter(number_of_iterations = 1)
    fistaRecon.setParameter(Lipschitz_constant = 767893952.0)
    fistaRecon.setParameter(ring_alpha = 21)
    fistaRecon.setParameter(ring_lambda_R_L1 = 0.002)
    #fistaRecon.setParameter(subsets=8)
    
    #lc = fistaRecon.getParameter('Lipschitz_constant')
    #fistaRecon.getParameter('regularizer').setParameter(regularization_parameter=5e6/lc)
    
    fistaRecon.prepareForIteration()
    X = fistaRecon.iterate(numpy.load("X.npy"))
    

# plot
fig = plt.figure()
cols = 3

## add the difference
rd = []
for i in range(1,len(results)):
    rd.append(results[i-1])
    rd.append(results[i])
    rd.append(results[i] - results[i-1])

rows = (lambda x: int(numpy.floor(x/cols) + 1) if x%cols != 0  else int(x/cols)) \
       (len (rd))
for i in range(len (results)):
    a=fig.add_subplot(rows,cols,i+1)
    imgplot = plt.imshow(results[i], vmin=0, vmax=1)
    a.text(0.05, 0.95, "iteration {0}".format(i),
               verticalalignment='top')
##    i = i + 1
##    a=fig.add_subplot(rows,cols,i+1)
##    imgplot = plt.imshow(results[i], vmin=0, vmax=10)
##    a.text(0.05, 0.95, "iteration {0}".format(i),
##               verticalalignment='top')
    
##    a=fig.add_subplot(rows,cols,i+2)
##    imgplot = plt.imshow(results[i]-results[i-1], vmin=0, vmax=10)
##    a.text(0.05, 0.95, "difference {0}-{1}".format(i, i-1),
##               verticalalignment='top')
        
        

plt.show()