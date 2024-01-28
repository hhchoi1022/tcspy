#%%
import time
import numpy as np
import os
import glob
from astropy.io import fits
import re
import numpy as np
from scipy.ndimage import convolve
from photutils.segmentation import detect_threshold, detect_sources
from astropy.stats import sigma_clipped_stats, SigmaClip
from photutils.utils import circular_footprint
from photutils.detection import DAOStarFinder
from astropy.nddata import Cutout2D
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from astropy.io import fits
from astropy.modeling import models, fitting
from astropy.stats import sigma_clipped_stats
from photutils import DAOStarFinder, aperture_photometry, CircularAperture
from photutils.detection import find_peaks
#%%
file_key = '/data2/Autofocus/Test_samples/231207/7DT01/*.fits'
files = sorted(glob.glob(file_key))
#%%
file = files[4]
#%%
def crop_image(data, 
               center_x : int,
               center_y : int,
               crop_size : int):
    x_start = max(0, center_x - crop_size // 2)
    x_end = min(data.shape[1], center_x + crop_size // 2)
    y_start = max(0, center_y - crop_size // 2)
    y_end = min(data.shape[0], center_y + crop_size // 2)
    data_cropped = data[y_start:y_end, x_start:x_end]
    return data_cropped
#%% Visualization of the cropped image
crop_size = 5000
data = fits.getdata(file)
data_mean = np.mean(data)
data_std = np.std(data)
data_cropped = crop_image(data, data.shape[1]//2, data.shape[0]//2, crop_size)
data_c_mean = np.mean(data_cropped)
data_c_std = np.std(data_cropped)
fig, axes = plt.subplots(2, figsize = (30,20))
axes[0].imshow(data, vmin = data_mean-data_std, vmax = data_mean + data_std)
square = patches.Rectangle(((data.shape[1]//2)-crop_size//2, (data.shape[0]//2)-crop_size//2), crop_size, crop_size, linewidth=3, edgecolor='r', facecolor='none')
axes[0].add_patch(square)
axes[1].imshow(data_cropped, vmin = data_mean-data_std, vmax = data_mean + data_std)
#%%
def calc_norm_variance(array):
    mean = np.mean(array)
    variance = np.sum((np.array(array) - mean)**2)
    FM = 1/(array.shape[0]*array.shape[1]) * variance / mean
    return FM
#%%
import cv2
from astropy.stats import sigma_clip
def fparam(data):
        # compute the Laplacian of the image and then return the focus
        # measure, which is simply the variance of the Laplacian
        return cv2.Laplacian(data, cv2.CV_64F).var()
all_FM = []
all_fwhm = []
crop_size = 2000
source_size = 30
focusposlist = []
all_fwhm_error = []
for file in files:
    
    data = np.array(fits.getdata(file), dtype = float)
    hdr = fits.getheader(file)
    data_cropped = crop_image(data, data.shape[1]//2, data.shape[0]//2, crop_size)
    mean, median, std = sigma_clipped_stats(data_cropped, sigma=3.0)
    data_cropped -= median
    threshold = 30 * std
    fwhm_x_all = []
    fwhm_y_all = []
    from astropy.convolution import convolve
    from photutils.segmentation import make_2dgaussian_kernel
    kernel = make_2dgaussian_kernel(3.0, size=5)  # FWHM = 3.0
    convolved_data = convolve(data_cropped, kernel)
    segment_map = detect_sources(convolved_data, threshold, npixels=10)
    focusposlist.append(hdr['FOCUSPOS'])
    FM = 0
    for bbox in segment_map.bbox:
        source_segment  = crop_image(data_cropped, round(bbox.center[1]), round(bbox.center[0]), crop_size = np.max(bbox.shape)+10)
        convolved_source = convolve(source_segment, kernel)
        #plt.imshow(source_segment, vmax = 30, vmin = 0)
        #plt.show()
        FM += calc_norm_variance(source_segment)
        ##############
        #gauss_init = models.Gaussian2D(amplitude=np.max(source_segment),
        #                                x_mean=(np.max(bbox.shape)+10)//2, y_mean=(np.max(bbox.shape)+10)//2)
        #fitter = fitting.LevMarLSQFitter()
        #x, y = np.meshgrid(np.arange(0, len(source_segment[0,:]), 1), np.arange(0, len(source_segment[:,0]), 1))
        #gauss_fit = fitter(gauss_init, x,y, source_segment)
        #fwhm_x = 2 * np.sqrt(2 * np.log(2)) * gauss_fit.x_stddev.value
        #fwhm_y = 2 * np.sqrt(2 * np.log(2)) * gauss_fit.y_stddev.value
        #fwhm_x_all.append(fwhm_x)
        #fwhm_y_all.append(fwhm_y)
        # Project onto 1D arrays for x and y directions
        projection_x = np.sum(source_segment, axis=0)  # Sum along the y-axis
        projection_y = np.sum(source_segment, axis=1)  # Sum along the x-axis
        # Fit Gaussian to the projections
        def gaussian_fit(data, axis_values):
            g_init = models.Gaussian1D(amplitude=data.max(), mean=axis_values[np.argmax(data)], stddev=1.0)
            fit_p = fitting.LevMarLSQFitter()
            gaussian_fit = fit_p(g_init, axis_values, data)
            return gaussian_fit
        x = np.linspace(-5, 5, len(projection_x))
        y = np.linspace(-5, 5, len(projection_y))
        fit_x = gaussian_fit(projection_x, x)
        fit_y = gaussian_fit(projection_y, y)
        fwhm_x = 2 * np.sqrt(2 * np.log(2)) * fit_x.stddev.value
        fwhm_y = 2 * np.sqrt(2 * np.log(2)) * fit_y.stddev.value
        fwhm_x_all.append(fwhm_x)
        fwhm_y_all.append(fwhm_y)
        
        
        # 여기에 Gaussian fitting (2D or 1D) 추가하기 with error
        ##############
    all_FM.append(FM)
    fwhm_x_all_clipped = sigma_clip(fwhm_x_all, sigma_lower = 3, sigma_upper = 5, maxiters = 3, cenfunc = 'median', stdfunc = 'std', masked = False)
    fwhm_y_all_clipped = sigma_clip(fwhm_y_all, sigma_lower = 3, sigma_upper = 5, maxiters = 3, cenfunc = 'median', stdfunc = 'std', masked = False)

    fwhm_mean = (np.mean(fwhm_x_all_clipped) + np.mean(fwhm_y_all_clipped))/2
    
    all_fwhm.append(fwhm_mean)
    all_fwhm_error.append(np.sqrt(np.std(fwhm_x_all_clipped)**2 + np.std(fwhm_y_all_clipped)**2))
    
#%%
plt.imshow(convolved_data, vmin = data_c_mean-data_c_std, vmax = data_c_mean + data_c_std)
plt.colorbar()
#%%
plt.imshow(data_cropped, vmin = data_c_mean-data_c_std, vmax = data_c_mean + data_c_std)
plt.colorbar()
#%%
fig, ax1 = plt.subplots()
ax2 = ax1.twinx()
# Plot the first scatter plot on the left y-axis (ax1)
ax1.scatter(focusposlist, all_FM, color='blue', label='Focus Meature (FM)')
ax1.set_xlabel('X-axis')
ax1.set_ylabel('Y-axis 1', color='blue')
ax1.tick_params('y', colors='blue')
# Plot the second scatter plot on the right y-axis (ax2)
ax2.scatter(focusposlist, all_fwhm, facecolor = 'none', edgecolor ='red', label='FWHM')
ax2.errorbar(focusposlist, all_fwhm, all_fwhm_error, fmt = 'none', ecolor ='k')
ax2.set_ylim(0, 30)
ax2.set_ylabel('Y-axis 2', color='red')
ax2.tick_params('y', colors='red')

# Display the legend for both scatter plots
ax1.legend(loc='upper left')
ax2.legend(loc='upper right')

# %%
plt.plot(fwhm_y_all)
# %%
focusposlist[22]
# %%
all_FM[22]
# %%
