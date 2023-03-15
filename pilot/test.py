

#%%
from tcspy.utils.to_skycoord import to_SkyCoord
from tcspy.pilot.startup import StartUp
from tcspy.utils.target import mainTarget
from tcspy.pilot.singleobservation import singleObservation
#%%
startup = StartUp(unitnum=4)
devices = startup.run()
observer = startup.observer
#%% Setting Target
ra = '3:37:36'
dec = '32:14:59'
target_name = 'M15'
coord_radec = to_SkyCoord(ra, dec)
ra_hour ,dec_deg = coord_radec.ra.hour, coord_radec.dec.deg
alt = 60
az = 170
target = mainTarget(observer = observer, target_ra = ra_hour, target_dec = dec_deg, target_name = target_name)
target.staralt()
#%% Observation
obs = singleObservation(**devices, observer = observer)
image = obs.slew_exposure(target_ra = ra_hour, target_dec = dec_deg, exptime = 15, binning = 1, target_name = target_name, filter = 'g')
image.show()
image.save('{}.fits'.format(target_name))
#devices['telescope'].park()
#%%




#%%
from alpaca.telescope import Telescope
from alpaca.camera import Camera
from tcspy.devices.camera import mainCamera
from tcspy.devices.telescope import mainTelescope_Alpaca
from tcspy.configuration import mainConfig
from tcspy.devices.observer import mainObserver
T1 = Telescope('192.168.0.5:11111',0)
T2 = Telescope('192.168.0.4:11111',0)
config = mainConfig().config
Tel1 = mainTelescope_Alpaca(T1, observer = mainObserver(**config) )
Tel2 = mainTelescope_Alpaca(T2, observer = mainObserver(**config) )
#%%
Tel1.slew_altaz(alt = 40, az = 270)
Tel2.slew_altaz(alt = 40, az = 270)
# %%
Tel1.park()
Tel2.park()
# %%
T1.SlewToAltAzAsync(320, 30)
T2.SlewToAltAzAsync(320, 30)
#%% Camera
C1 = Camera('192.168.0.5:11111',0)
C2 = Camera('192.168.0.4:11111',0)
Cam1 = mainCamera(C1)
Cam2 = mainCamera(C2)
img1, stat1 = Cam1.take_bias()
img2, stat2 = Cam2.take_bias()
# %%

