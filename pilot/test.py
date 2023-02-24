

#%%
from tcspy.utils.to_skycoord import to_SkyCoord

from alpaca.camera import Camera
from alpaca.focuser import Focuser
from alpaca.filterwheel import FilterWheel
from alpaca.telescope import Telescope

from tcspy.pilot.startup import startUp
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
config = mainConfig().config
observer = mainObserver(**config)
cam = mainCamera(Camera('127.0.0.1:32323', 0))
focus = mainFocuser(Focuser('127.0.0.1:32323', 0))
filt = mainFilterwheel(FilterWheel('127.0.0.1:32323', 0))
tel = mainTelescope_Alpaca(Telescope('127.0.0.1:32323', 0), Observer = observer)
#%%
startUp().run()
#%%
obs = singleObservation(camera = cam, telescope= tel, filterwheel = filt, observer = observer)
#%%
ra = '15:35:28'
dec = '-50:39:32'
coordinate_radec = to_SkyCoord(ra, dec)
target = mainTarget(observer= observer, target_ra = coordinate_radec.ra.value, target_dec = coordinate_radec.dec.value, target_name = 'NGC1566')
#%%
obs.slew_exposure(target = coordinate_radec, exptime = 10, counts = 1, filter = 'w425')
# %%
