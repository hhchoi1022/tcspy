#%%
from tcspy.pilot import singleObservation
from tcspy.pilot import StartUp
import sys
#%%
unitnum = int(sys.argv[1])
alt = 40
az = 310
target_name = 'test'

startup = StartUp(unitnum=unitnum)
devices = startup.devices
observer = startup.observer
obs = singleObservation(unitnum=unitnum, **devices, observer = observer )
image = obs.slew_exposure(target_alt = alt, target_az = az, exptime = 5, binning = 1, target_name = 'test', filter = 'g')
image.save('{}.fits'.format(target_name))
# %%
