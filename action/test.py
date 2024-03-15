#%%
from tcspy.action.level1 import * 
from threading import Event
from tcspy.devices import IntegratedDevice
abort_action = Event()

#%%
IDevice = IntegratedDevice(21)
#%%
ChangeFilter(IDevice, abort_action= abort_action).run('g')
IDevice.filterwheel.get_status()
# %%
ChangeFocus(IDevice, abort_action).run(300, True)
IDevice.focuser.get_status()
# %%
Cool(IDevice, abort_action).run(10, 1)
IDevice.camera.get_status()
# %%
E = Exposure(IDevice, abort_action)
E.run(frame_number = 1, exptime = 1, filter_ = 'g', imgtype = 'BIAS')
E.run(frame_number = 1, exptime = 1, filter_ = 'r', imgtype = 'DARK')
E.run(frame_number = 1, exptime = 1, filter_ = 'i', imgtype ='Light', binning = 1, target_name = 'ABC', objtype = None, obsmode = 'Single')
# %%
FansOn(IDevice, abort_action).run()
# %%
FansOff(IDevice, abort_action).run()
# %%
Park(IDevice, abort_action).run()
IDevice.telescope.get_status()

# %%
SlewAltAz(IDevice, abort_action).run(alt = 40, az = 180)
IDevice.telescope.get_status()
# %%
SlewRADec(IDevice, abort_action).run(ra = 220, dec = -22)
# %%
TrackingOff(IDevice, abort_action).run()
# %%
TrackingOn(IDevice, abort_action).run()
# %%
from tcspy.action.level2 import * 
# %%
AutoFocus(IDevice, abort_action).run(filter_ = 'g', use_offset = True)

# %%
IDevice.filterwheel.get_status()
# %%
SingleObservation(IDevice, abort_action).run(10, 1, 'i', ra =150, dec = -22, autofocus_before_start = True)
# %%
IDevice1 = IntegratedDevice(1)
IDevice2 = IntegratedDevice(2)
IDevice3 = IntegratedDevice(3)
IDevice_array = [IDevice1, IDevice2, IDevice3]
# %%
from tcspy.devices import DeviceStatus
DeviceStatus(IDevice1).dict
DeviceStatus(IDevice2).dict
#DeviceStatus(IDevice3).dict
# %%
from tcspy.action.level3 import * 
#%%
SpecObservation()