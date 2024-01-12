#%%
import time
import numpy as np
import os
import glob
from astropy.io import fits
import re
import numpy as np
from scipy.ndimage import convolve
#%%
dir_key = '/home/hhchoi1022/Desktop/data2/Autofocus/Test_samples/FocusTest*'
folder_list = glob.glob(dir_key)
#%%
tel_list =  [re.findall('(7DT\d\d)',folder)[0] for folder in folder_list]
folder_dict = dict()
for tel, folder in zip(tel_list, folder_list):
    folder_dict[tel] = dict()
    folder_dict[tel]['folder'] = folder
    filelist = glob.glob(folder + '/*.fits')
    folder_dict[tel]['files'] = sorted(filelist)
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
# %%
