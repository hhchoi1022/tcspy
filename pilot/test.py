

#%%
from tcspy.utils.to_skycoord import to_SkyCoord

from alpaca.camera import Camera
from alpaca.focuser import Focuser
from alpaca.filterwheel import FilterWheel
from alpaca.telescope import Telescope

from tcspy.pilot.startup import StartUp
from tcspy.utils import mainLogger
from tcspy.utils.target import mainTarget
from tcspy.configuration import mainConfig
from tcspy.devices.camera import mainCamera
from tcspy.devices.focuser import mainFocuser
from tcspy.devices.telescope import mainTelescope_Alpaca
from tcspy.devices.filterwheel import mainFilterwheel
from tcspy.devices.observer import mainObserver

from tcspy.pilot.singleobservation import singleObservation
#%% Setting devices
startup = StartUp()
startup.run()
devices = startup.devices
observer = startup.observer
#%%
obs = singleObservation(**devices, observer = observer)
#%%
ra = '10:43:57.7'
dec = '+11:42:14.1'
target_name = 'M95'
coord_radec = to_SkyCoord(ra, dec)
ra_hour ,dec_deg = coord_radec.ra.hour, coord_radec.dec.deg
alt = 60
az = 170
#%%
obs.slew_exposure(target_alt = alt, target_az = az, exptime = 10, binning = 1, target_name = target_name)
obs.slew_exposure(target = coordinate_radec, exptime = 10, counts = 1, filter = 'w425')
# %%
