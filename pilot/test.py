

#%%
from tcspy.utils.to_skycoord import to_SkyCoord
from tcspy.pilot.startup import StartUp
from tcspy.utils.target import mainTarget
from tcspy.pilot.singleobservation import singleObservation
#%% Startup
startup = StartUp()
startup.run()
devices = startup.devices
observer = startup.observer
#%% Setting Target
ra = '17:37:36'
dec = '-03:14:59'
target_name = 'M14'
coord_radec = to_SkyCoord(ra, dec)
ra_hour ,dec_deg = coord_radec.ra.hour, coord_radec.dec.deg
alt = 60
az = 170
target = mainTarget(observer = observer, target_ra = ra_hour, target_dec = dec_deg, target_name = target_name)
target.staralt()
#%% Observation
obs = singleObservation(**devices, observer = observer)
image = obs.slew_exposure(target_ra = ra_hour, target_dec = dec_deg, exptime = 120, binning = 1, target_name = target_name)
image.show()
image.save('{}_1.fits'.format(target_name))
devices['telescope'].park()

