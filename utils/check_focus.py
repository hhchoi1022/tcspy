

#%%
import os, glob
from astropy.io import ascii
import matplotlib.pyplot as plt
from datetime import datetime
from astropy.time import Time
#%%
filelist = glob.glob('/home/hhchoi1022/tmp/*.ascii')
# %%
for file_ in filelist:
    data = ascii.read(file_, format = 'fixed_width')

    filter_ = data[0]["filter"]
    #plt.figure()
    plt.title(f'{filter_}')
    plt.scatter(Time(data['obsdate']).to_datetime(), data['focus'], label = filter_, s = 10)
    plt.xticks(rotation = 45)
    plt.ylim(7200,7800)
    plt.xlim(datetime(year= 2023, month = 10, day = 20),datetime(year= 2023, month = 11, day = 30))
plt.legend()


# %%
