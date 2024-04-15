#%%
from tcspy.action.level1 import * 
from threading import Event
from tcspy.devices import SingleTelescope
abort_action = Event()
from tcspy.devices.camera import mainCamera
from tcspy.action import MultiAction

#%%



def return_image(cam):
    a = cam.device.ImageArra
    return a
#%%
from threading import Thread

unitnumlist = [1,2,3,5,6,7,8,9,10,11]
for unitnum in unitnumlist:
    Thread(target = return_image, kwargs = dict(cam = mainCamera(unitnum))).start()
#%%
a1.start()
a2.start()
a3.start()
a5.start()
a6.start()
a7.start()
a8.start()
a9.start()
a10.start()
a11.start()

#%%


#%%
telescope1 = SingleTelescope(1)
telescope2 = SingleTelescope(2)
telescope3 = SingleTelescope(3)
telescope5 = SingleTelescope(5)
telescope6 = SingleTelescope(6)
telescope7 = SingleTelescope(7)
telescope8 = SingleTelescope(8)
telescope9 = SingleTelescope(9)
array_telescope= [ telescope1, telescope2, telescope3]#, telescope5, telescope6, telescope7, telescope8, telescope9]
kwargs = dict(frame_number = 1, exptime = 1, filter_ = 'r', imgtype = 'DARK')
array_kwargs = []
for i in range(1):
    array_kwargs.append(kwargs)
#%%
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = Exposure, abort_action = abort_action)
m.run()
#%%
from tcspy.devices import MultiTelescopes
mtel = MultiTelescopes(SingleTelescope_list= array_telescope)
#%%
#%%
ChangeFilter(telescope, abort_action= abort_action).run('m425')
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
from tcspy.action.level2 import * 
telescope_array = []
SingleObs_list = []

for unitnum in [1,2,3,5,6,7,8,9,10,11]:
    tel = SingleTelescope(unitnum)
    SingleObs_list.append(SingleObservation(tel, Event()))
#%%

kwargs = dict( exptime = 10, count = 1, filter_ = 'i', alt =60, az = 300, autofocus_before_start = False)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=100) as executor:
    # Submit the return_image function with arguments to the executor
    futures = [executor.submit(SingleObs.run, **kwargs) for SingleObs in SingleObs_list]

    # Wait for all tasks to complete
    for future in futures:
        future.result()
#m = MultiAction(array_telescope= telescope_array, array_kwargs = kwargs, function = SingleObservation, abort_action= Event())
#%%
SingleObservation()
#%%
m.run()
# %%
from tcspy.devices import TelescopeStatus
TelescopeStatus(telescope1).dict
TelescopeStatus(telescope2).dict
#TelescopeStatus(telescope3).dict
# %%
from tcspy.action.level3 import * 
#%%
SpecObservation()