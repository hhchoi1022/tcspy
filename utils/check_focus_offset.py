#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 14 09:28:44 2023

@author: hhchoi10222
"""

#%%
from astropy.io import fits
import glob, os
from astropy.time import Time
import datetime
import numpy as np
from astropy.table import Table
from astropy.table import vstack
#%%
def match_table(tbl1, tbl2, key, tolerance = 0.01):
    from astropy.table import hstack
    '''
    parameters
    ----------
    {two tables} to combine with the difference of the {key} smaller than the {tolerance}
    
    returns 
    -------
    1. combined table
    2. phase

    notes 
    -----
    Combined table have both columns of original tables. 
    They are horizontally combined in the order of tbl1, tbl2
    -----
    '''
    
    matched_tbl = Table()
    for obs in tbl1:
        ol_idx = (np.abs(obs[key] - tbl2[key]) < tolerance)
        if True in ol_idx:
            closest_idx = np.argmin(np.abs(obs[key]-tbl2[key]))
            compare_tbl = tbl2[closest_idx]
            compare_tbl = hstack([obs, compare_tbl])#join(obs, compare_tbl, keys = 'observatory', join_type = 'outer')
            matched_tbl = vstack([matched_tbl, compare_tbl])

    return matched_tbl

#%%
name_telescope = input('Input telescope')
imkey = f'/large_data/obsdata/{name_telescope}/*/LIGHT*.fits'
focusval_key = 'FOCUSPOS'
obsdate_key = 'DATE-LOC'
neglect_date = True
filter_key = 'FILTER'
base_filter_offset = input('Input base filter')

# Data query
imagelist = glob.glob(imkey)
all_obsdate = []
all_focusval = []
all_filter = []
all_obsdatetime = []
all_obshour = []
imlist = []
for image in imagelist:
    image_hdr = fits.getheader(image)
    obsdate = Time(image_hdr[obsdate_key])
    if obsdate.datetime.hour > 12:
        obshour = datetime.datetime(year = 2023, month = 1, day = 14, hour = obsdate.datetime.hour, minute = obsdate.datetime.minute)
    else:
        obshour = datetime.datetime(year = 2023, month = 1, day = 15, hour = obsdate.datetime.hour, minute = obsdate.datetime.minute)
    #obshour = np.round((obsdate.datetime.hour + (obsdate.datetime.minute)/60),3)
    try:
        focusval = image_hdr[focusval_key]
        imlist.append(image)
        filter_ = image_hdr[filter_key]
        all_obsdate.append(obsdate)
        all_obsdatetime.append(obsdate)
        all_obshour.append(obshour)
        all_focusval.append(focusval)
        all_filter.append(filter_)

    except:
        focusval = None
tbl = Table()
tbl['image'] = imlist
tbl['obsdate'] = all_obsdatetime
tbl['obshour'] = all_obshour
tbl['focus'] = all_focusval
tbl['filter'] = all_filter
tbl.sort('obsdate')
first_obsdate = tbl['obsdate'][0]
tbl['obsdate_relative'] = (tbl['obsdate'] - first_obsdate).value
duration_obs = tbl['obsdate_relative'][-1]
# %% Binning table
tbl_binning = Table()
previous_focus = None
for row in tbl:
    current_focus = row['focus']
    if current_focus != previous_focus:
        tbl_binning = vstack([tbl_binning, row], join_type = 'outer')
    previous_focus = current_focus
# %%
import matplotlib.pyplot as plt
tbl_filters = tbl_binning.group_by('filter')
tbl_filter_dict = dict()
all_filters = tbl_filters.groups.keys['filter']
#all_filters = ['u','g','r','i','z','m400','m425','m650','m675']
for i, filter_ in enumerate(list(tbl_filters.groups.keys['filter'])):
    tbl_filter_dict[filter_] = tbl_filters.groups[i]
#%%
colorset = ['red','peru','darkorange','green','deeppink','teal','navy','blueviolet','dodgerblue', 'blue', 'black']
filter_color = dict()
for i, filter_ in enumerate(all_filters):
    filter_color[filter_] = colorset[i]
#%% Show focus change over all obsdate
plt.figure(dpi = 300, figsize = (7, 4))
for filter_ in all_filters:
    data = tbl_filter_dict[filter_]
    plt.scatter(data['obsdate_relative'],data['focus'], c = filter_color[filter_], label = filter_, s = 20)
plt.xlabel(f'days - {first_obsdate}')
plt.legend(loc = 1, ncol = 2)
plt.xticks(rotation = 45)

#%% Visualize
from astropy.stats import sigma_clip
plt.figure(dpi = 300, figsize = (6,4))
offset_dict = dict()
focusdiffmean_all = []
focusdiffstd_all = []
for filter_ in all_filters:
    tbls = match_table(tbl_filter_dict[filter_], tbl_filter_dict[base_filter_offset], key = 'obsdate', tolerance = 0.1)
    if len(tbls)>0:
        tbls['focusdiff'] = tbls['focus_1']-tbls['focus_2']
        sigma_clip_mask = sigma_clip(tbls['focusdiff'], sigma_lower =2, sigma_upper=2, masked = True).mask
        tbl_clipped = tbls[~sigma_clip_mask]
        focusdiff_mean = int(np.mean(tbl_clipped['focusdiff']))
        focusdiff_std = int(np.std(tbl_clipped['focusdiff']))
        #plt.scatter(Time(tbls['obsdate_1']).datetime,tbls["focusdiff"], c = filter_color[filter_])
        plt.scatter(tbl_clipped['obsdate_relative_1'],tbl_clipped["focusdiff"], c = filter_color[filter_])
        plt.axhline(focusdiff_mean, c = filter_color[filter_], linestyle = '--')
        plt.fill_between((-3, duration_obs+3), focusdiff_mean-focusdiff_std , focusdiff_mean+focusdiff_std, color = filter_color[filter_], alpha = 0.3)
        plt.text(duration_obs+2.2, focusdiff_mean -0.2*focusdiff_std, s = rf'{filter_} : {focusdiff_mean}$\pm${focusdiff_std}', color = filter_color[filter_])
        focusdiffmean_all.append(focusdiff_mean)
        focusdiffstd_all.append(focusdiff_std)
    else:
        focusdiffmean_all.append(None)
        focusdiffstd_all.append(None)
plt.title(f'Focus offset of {name_telescope}')
plt.xticks(rotation = 45)
plt.xlim(-2, duration_obs +2)
plt.xlabel(f'Days since {first_obsdate}')
plt.ylabel('Offset to r filter')
plt.savefig(f'OFFSET_{name_telescope}.png')
#%% Write results
for filter_ in all_filters:
    focus_tbl = tbl_filter_dict[filter_]
    focus_tbl.write(f'FOCUS_{name_telescope}_{filter_}.ascii', format = 'ascii.fixed_width', overwrite = True)
offset_tbl = Table()
offset_tbl['filter'] = all_filters
offset_tbl['offset'] = focusdiffmean_all
offset_tbl['error'] =focusdiffstd_all
offset_tbl.write(f'OFFSET_{name_telescope}_{filter_}.ascii', format = 'ascii.fixed_width', overwrite = True)
#%%
