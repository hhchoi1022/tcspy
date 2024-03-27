#%%
from tcspy.action.level1 import * 
from threading import Event
from tcspy.devices import SingleTelescope
abort_action = Event()

#%%
telescope = SingleTelescope(21)
#%%
ChangeFilter(telescope, abort_action= abort_action).run('g')
telescope.filterwheel.get_status()
# %%
ChangeFocus(telescope, abort_action).run(300, True)
telescope.focuser.get_status()
# %%
Cool(telescope, abort_action).run(10, 1)
telescope.camera.get_status()
# %%
E = Exposure(telescope, abort_action)
E.run(frame_number = 1, exptime = 1, filter_ = 'g', imgtype = 'BIAS')
E.run(frame_number = 1, exptime = 1, filter_ = 'r', imgtype = 'DARK')
E.run(frame_number = 1, exptime = 1, filter_ = 'i', imgtype ='Light', binning = 1, name = 'ABC', objtype = None, obsmode = 'Single')
# %%
FansOn(telescope, abort_action).run()
# %%
FansOff(telescope, abort_action).run()
# %%
Park(telescope, abort_action).run()
telescope.mount.get_status()

# %%
SlewAltAz(telescope, abort_action).run(alt = 40, az = 180)
telescope.mount.get_status()
# %%
SlewRADec(telescope, abort_action).run(ra = 300, dec = -22)
# %%
TrackingOff(telescope, abort_action).run()
# %%
TrackingOn(telescope, abort_action).run()
# %%
from tcspy.action.level2 import * 
# %%
AutoFocus(telescope, abort_action).run(filter_ = 'g', use_offset = True)

# %%
telescope.filterwheel.get_status()
# %%
SingleObservation(telescope, abort_action).run(10, 1, 'i', ra =300, dec = -22, autofocus_before_start = True)
# %%
telescope1 = SingleTelescope(1)
telescope2 = SingleTelescope(2)
telescope3 = SingleTelescope(3)
telescope_array = [telescope1, telescope2, telescope3]
# %%
from tcspy.devices import TelescopeStatus
TelescopeStatus(telescope1).dict
TelescopeStatus(telescope2).dict
#TelescopeStatus(telescope3).dict
# %%
from tcspy.action.level3 import * 
#%%
SpecObservation()