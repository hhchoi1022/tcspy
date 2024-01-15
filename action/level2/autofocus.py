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





#%%
file_key = '/Users/hhchoi1022/code/FocusTest_240112_7DT01/*.fits'
files = glob.glob(file_key)
#%%
file = files[3]


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
#%%
mean, median, std = sigma_clipped_stats(data_cropped, sigma=3.0)
daofind = DAOStarFinder(fwhm=4, threshold=20 * std)
sources = daofind(data_cropped - median)
#%%
'''sources['snr'] = sources['peak'] / std
saturation_mask = sources['peak'] < saturation_level

# Step 4: Combine SNR and Saturation Checks
valid_sources_mask = sources['snr'] > your_snr_threshold  # Adjust your_snr_threshold as needed
valid_sources_mask &= saturation_mask
valid_sources = sources[valid_sources_mask]'''
#%%
from scipy import optimize, ndimage
center = (sources[30]['xcentroid'], sources[30]['ycentroid'])

# Create a Cutout2D object to extract the rectangular patch
cutout = Cutout2D(data_cropped, center, size=(20, 20), mode='partial', fill_value=np.nan)
data_c_mean = np.mean(cutout.data)
data_c_std = np.std(cutout.data)
plt.imshow(cutout.data, vmin = data_mean-data_std, vmax = data_mean + data_std)
#%%
#data_cropped = cutout.data
def _window_function(arr, border=0):

    """
    Creates a sine window function of the same size as some 1-D array "arr".
    Optionally, a zero border at the edges is added by "scrunching" the window.
    """
    ndata = len(arr)
    nwind = ndata - 2 * border

    w = np.zeros(ndata)
    for i in range(nwind):
        w[i + border] = np.sin(np.pi * (i + 1.) / (nwind + 1.))
    return w
def _fit_correlation(correl):
    from lmfit.models import GaussianModel

    # create Gaussian model
    model = GaussianModel()

    # initial guess
    x = np.arange(len(correl))
    pars = model.guess(correl, x=x)
    pars['sigma'].value = 20.

    # fit
    return model.fit(correl, pars, x=x)

def _clean(data, backsub=True, xbad=None, ybad=None):
    """
    Removes global slopes and fills up bad rows (ybad) or columns (xbad).
    """
    (ny, nx) = data.shape

    # REMOVE BAD COLUMNS AND ROWS
    if xbad is not None:
        x1 = xbad - 1
        if x1 < 0:
            x1 = 1
        x2 = x1 + 2
        if x2 >= nx:
            x2 = nx - 1
            x1 = x2 - 2
        for j in range(ny):
            data[j][xbad] = 0.5 * (data[j][x1] + data[j][x2])
    if ybad is not None:
        y1 = ybad - 1
        if y1 < 0:
            y1 = 1
        y2 = y1 + 2
        if y2 >= ny:
            y2 = ny - 1
            y1 = y2 - 2
        for i in range(nx):
            data[ybad][i] = 0.5 * (data[y1][i] + data[y2][i])

    # REMOVE GLOBAL SLOPES
    if backsub:
        xsl = np.median(data, axis=0)
        ysl = np.median(data, axis=1).reshape((ny, 1))
        xsl -= np.mean(xsl)
        ysl -= np.mean(ysl)
        xslope = np.tile(xsl, (ny, 1))
        yslope = np.tile(ysl, (1, nx))
        return data - xslope - yslope
    else:
        return data

def _analyse_image(data, backsub=True, xbad=None, ybad=None):
    # clean data
    data = _clean(data, backsub=backsub, xbad=xbad, ybad=ybad)

    # get projections
    xproj = np.mean(data, axis=0)  # PROJECTIONS
    yproj = np.mean(data, axis=1)
    nx = len(xproj)
    ny = len(yproj)

    # remove background gradient
    xclean = xproj - ndimage.uniform_filter1d(xproj, nx // 10)
    yclean = yproj - ndimage.uniform_filter1d(yproj, ny // 10)

    # get window functions
    xwind = _window_function(xclean, border=3)
    ywind = _window_function(yclean, border=3)

    # calculate correlation functions
    xavg = np.average(xclean)
    yavg = np.average(yclean)
    x = xwind * (xclean - xavg) / xavg
    y = ywind * (yclean - yavg) / yavg
    xcorr = np.correlate(x, x, mode='same')
    ycorr = np.correlate(y, y, mode='same')

    # filter out the peak (e.g. cosmics, ...)
    # imx = np.argmax(xcorr)
    # xcorr[imx] = 0.5 * (xcorr[imx - 1] + xcorr[imx + 1])
    # imx = np.argmax(ycorr)
    # ycorr[imx] = 0.5 * (ycorr[imx - 1] + ycorr[imx + 1])

    # fit cc functions to get fwhm
    xfit = _fit_correlation(xcorr)
    yfit = _fit_correlation(ycorr)

    # log it
    print('Found x=%.1f+-%.1f and y=%.1f+-%.1f.'%(xfit.params['fwhm'].value, xfit.params['fwhm'].stderr,yfit.params['fwhm'].value, yfit.params['fwhm'].stderr))


#%%

_analyse_image(data = data_cropped)
#%%

yfit.params

#%%
xfit.params
#%%
plt.plot(xcorr)
#%%
import cv2
def fparam(data):
        # compute the Laplacian of the image and then return the focus
        # measure, which is simply the variance of the Laplacian
        return cv2.Laplacian(data, cv2.CV_64F).var()
focus_files = folder_dict['7DT01']['files']
test_files = [focus_files[i] for i in [5,10,15,20,25,30,35]]
test_files = focus_files
sum_lap_subsequent = []
for focus_file in test_files:
    #focus_file = focus_files[0]    
    data = fits.getdata(focus_file)
    """
    start = time.perf_counter()
    sigma_clip = SigmaClip(sigma=50.0, maxiters=1)
    threshold = detect_threshold(data, nsigma=10, sigma_clip=sigma_clip)
    segment_img = detect_sources(data, threshold, npixels=10)
    sources = [segment_img.bbox[i].center for i in range(len(segment_img.bbox)) if (segment_img.bbox[i].center[0] > 300) &  (segment_img.bbox[i].center[0] < 6388-300) &  (segment_img.bbox[i].center[1] > 300) &  (segment_img.bbox[i].center[1] < 9576-300) ]
    patch_size = 100  # Set your desired patch size


    for source in sources[:10]:
        center = (source[1], source[0])
        
        # Create a Cutout2D object to extract the rectangular patch
        cutout = Cutout2D(data, center, size=(patch_size, patch_size), mode='partial', fill_value=np.nan)

        # Display the patch
        plt.imshow(cutout.data, origin='lower', cmap='viridis', interpolation='nearest', label = fparam(cutout.data))
        plt.title(fparam(cutout.data))
        plt.show()

    print(time.perf_counter() - start)
    """
    array_shape = data.shape
    tile_size = 1500
    tiles_per_side = 2
    # Calculate the center region
    center_start_row = (array_shape[0] - tile_size * tiles_per_side) // 2
    center_start_col = (array_shape[1] - tile_size * tiles_per_side) // 2

    # Initialize an empty list to store tiles
    tiles = []

    # Iterate through rows and columns to extract tiles
    for i in range(tiles_per_side):
        for j in range(tiles_per_side):
            start_row = center_start_row + i * tile_size
            start_col = center_start_col + j * tile_size
            tile = data[start_row:start_row + tile_size, start_col:start_col + tile_size]
            tiles.append(tile)

    # Display one of the tiles (for demonstration purposes)
    sum_lap = 0
    sum_lap_list = []
    for tile in tiles:
        sum_lap_list.append(fparam(tile))
        #sum_lap += fparam(tile)
    #plt.plot(sum_lap_list)
    sum_lap_list = np.array(sum_lap_list)
    indices_of_largest = np.argpartition(sum_lap_list, -3)[-3:]
    sum_lap_subsequent.append(np.sum(sum_lap_list[indices_of_largest]))
    
#%%
def calc_norm_variance(array):
    
    mean = np.mean(array)
    variance = np.sum((np.array(array) - mean)**2)
    FM = 1/(array.shape[0]*array.shape[1]) * variance / mean
    return FM
#%%
test_files = [focus_files[i] for i in [5,10,15,20,25,30,35]]
all_FM = []
for file in test_files:
    data = fits.getdata(file)
    all_FM.append((calc_norm_variance(data)))
#%%
plt.plot(all_FM)
#%%
plt.plot(sum_lap_subsequent)
#%%

#%%

#%%

#%%
for source in sources:
    center = (source['xcentroid'], source['ycentroid'])
    
    # Create a Cutout2D object to extract the rectangular patch
    cutout = Cutout2D(data, center, size=(patch_size, patch_size), mode='partial', fill_value=np.nan)

    # Display the patch
    plt.imshow(cutout.data, origin='lower', cmap='viridis', interpolation='nearest')
    plt.title('Source Patch')
    plt.show()
#footprint = circular_footprint(radius=10)
#mask = segment_img.make_source_mask(footprint=footprint)

#mean, median, std = sigma_clipped_stats(data, sigma=3.0, mask=mask)
#%%
data
#%%
i = 20
for tel, info in folder_dict.items():
    image = '/home/hhchoi1022/Desktop/data2/Autofocus/Test_samples/LIGHT_FOCUS7588__UDS_2023-11-05_01-51-44_m400_60.00s_0667.fits'
    #image = info['files'][i]
    data = fits.getdata(image)
    (ny, nx) = data.shape
    xsl = np.median(data, axis=0)
    ysl = np.median(data, axis=1).reshape((ny, 1))
    xsl -= np.mean(xsl)
    ysl -= np.mean(ysl)
    xslope = np.tile(xsl, (ny, 1))
    yslope = np.tile(ysl, (1, nx))
    sub_data = data-xslope-yslope
    # imshow scaling 
    data_mean = np.mean(data)
    data_std = np.std(data)
    sub_mean = np.mean(sub_data)
    sub_std = np.std(sub_data)
    bkg_mean = np.mean(xslope+yslope)
    bkg_std = np.std(xslope+yslope)


    import matplotlib.pyplot as plt
    f, axs = plt.subplots(2, 2, sharey=True, figsize=(25,25))
    plt.title(tel)
    axs[0,0].imshow(data, vmin = data_mean - data_std/2, vmax = data_mean+data_std/2)
    axs[0,1].imshow(sub_data,  vmin = sub_mean-sub_std/2, vmax = sub_mean+sub_std/2)
    axs[1,0].imshow(xslope+yslope,  vmin = bkg_mean-bkg_std/2, vmax = bkg_mean+bkg_std/2)
    axs[1,1].imshow(xslope, vmin = bkg_mean-bkg_std/2, vmax = bkg_mean+bkg_std/2)
    plt.show()



#%%
from photutils.background import Background2D, MedianBackground
sigma_clip = SigmaClip(sigma=3.0)
bkg_estimator = MedianBackground()
bkg = Background2D(data, (50, 50), filter_size=(3, 3),
                   sigma_clip=sigma_clip, bkg_estimator=bkg_estimator)
#%%
# %%
import numpy as np

def estimate_background_polynomial(image, degree=2):
    rows, cols = np.indices(image.shape)
    params = np.polyfit(cols.flatten(), image.flatten(), degree)
    background = np.polyval(params, cols)
    return background.reshape(image.shape)
#%%
bkg = estimate_background_polynomial(data)
import matplotlib.pyplot as plt
#%%

f, axes = plt.subplots(2,1, figsize = (25,25))
axes[0].imshow(bkg, vmin = 510, vmax = 520)
axes[1].imshow(data, vmin = 510, vmax = 520)

#%%
data
#%%

saturation_level = 3000
your_snr_threshold = 20

# Step 1: Read FITS file
hdulist = fits.open(focus_files[0])
data = hdulist[0].data
#%%
crop_data = crop_image(data, data.shape[1]//2, data.shape[0]//2, 3000)

plt.imshow(crop_data, vmin = 515, vmax = 540)
#%%
plt.imshow(data, vmin = 515, vmax = 540)

#%%
# Step 2: Source Detection
mean, median, std = sigma_clipped_stats(crop_data, sigma=3.0)
daofind = DAOStarFinder(fwhm=4, threshold=20 * std)
sources = daofind(crop_data - median)
#%%
# Step 3: Calculate SNR and Check Saturation
sources['snr'] = sources['peak'] / std
saturation_mask = sources['peak'] < saturation_level

# Step 4: Combine SNR and Saturation Checks
valid_sources_mask = sources['snr'] > your_snr_threshold  # Adjust your_snr_threshold as needed
valid_sources_mask &= saturation_mask
valid_sources = sources[valid_sources_mask]
#%%
# Step 5: Sort by SNR
valid_sources.sort('snr', reverse = True)

# Step 6: Select Top 30 Valid Sources
top_30_valid_sources = valid_sources[:30]

# Step 7: Calculate FWHM
fwhm_values = []
#%%
x, y = np.meshgrid(np.arange(0, 20, 1), np.arange(0, 20, 1))
from photutils.aperture import ApertureStats
#%%
for source in top_30_valid_sources:
    position = (source['xcentroid'], source['ycentroid'])
    gauss_init = models.Gaussian2D(amplitude=source['peak'],
                                   x_mean=10, y_mean=10)
    fit_data = crop_image(crop_data, int(position[0]), int(position[1]), 20)
    fitter = fitting.LevMarLSQFitter()
    gauss_fit = fitter(gauss_init, x,y, fit_data)
        # Extract FWHM
    fwhm = gauss_fit.x_stddev
#%%