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
file_key = '/data2/Autofocus/Test_samples/240112/7DT01/*.fits'
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
def fparam(data):
        # compute the Laplacian of the image and then return the focus
        # measure, which is simply the variance of the Laplacian
        return cv2.Laplacian(data, cv2.CV_64F).var()
all_FM = []
crop_size = 2000
source_size = 30
focusposlist = []
for file in files:
    
    data = np.array(fits.getdata(file), dtype = float)
    hdr = fits.getheader(file)
    data_cropped = crop_image(data, data.shape[1]//2, data.shape[0]//2, crop_size)
    mean, median, std = sigma_clipped_stats(data_cropped, sigma=3.0)
    data_cropped -= median
    threshold = 30 * std
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
        # 여기에 Gaussian fitting (2D or 1D) 추가하기 with error
        ##############
    all_FM.append(FM)
#%%
plt.imshow(convolved_data, vmin = data_c_mean-data_c_std, vmax = data_c_mean + data_c_std)
plt.colorbar()
#%%
plt.imshow(data_cropped, vmin = data_c_mean-data_c_std, vmax = data_c_mean + data_c_std)
plt.colorbar()
#%%
position = (source['xcentroid'], source['ycentroid'])
gauss_init = models.Gaussian2D(amplitude=source['peak'],
                                x_mean=10, y_mean=10)
fit_data = crop_image(crop_data, int(position[0]), int(position[1]), 20)
fitter = fitting.LevMarLSQFitter()
gauss_fit = fitter(gauss_init, x,y, fit_data)
    # Extract FWHM
fwhm = gauss_fit.x_stddev

