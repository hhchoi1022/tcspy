#%%
from tcspy.action.level1 import * 
from threading import Event
from tcspy.action import MultiAction

abort_action = Event()
from tcspy.devices.camera import mainCamera
from tcspy.action import MultiAction
from threading import Thread

def return_image(cam):
    #cam.device.StartExposure(1, False)
    a = cam.device.ImageArray
    return a

#%%

#%%

unitnumlist = [1,2,3,5,6,7,8,9,10,11]
camlist = dict()
for unitnum in unitnumlist:
    camlist[unitnum] = mainCamera(unitnum)
#%%
for unitnum in unitnumlist:
    Thread(target = return_image, kwargs = dict(cam = camlist[unitnum])).start()
#%%
from multiprocessing import Process
import concurrent.futures

def return_image(cam):
    # Assuming cam.device.StartExposure(1, False) is called here
    a = cam.device.ImageArray
    return a

unitnumlist = [1,2,3,5,6,7,8,9,10,11]
camlist = dict()

# Creating instances of mainCamera
for unitnum in unitnumlist:
    camlist[unitnum] = mainCamera(unitnum)

# Starting processes for each camera
processes = []
for unitnum in unitnumlist:
    p = Process(target=return_image, kwargs={'cam': camlist[unitnum]})
    p.start()
    processes.append(p)

# Wait for all processes to finish
for p in processes:
    p.join()


#%%

from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=30) as executor:
    executor.map(return_image, camlist)

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
#%%
from multiprocessing import Process

def return_image(cam):
    # Assuming cam.device.StartExposure(1, False) is called here
    a = cam.device.ImageArray
    return a

unitnumlist = [1,2,3,5,6,7,8,9,10,11]
camlist = dict()


#%%
# Starting processes for each camera
processes = []
for unitnum in unitnumlist:
    e = Exposure(singletelescope= telescope_array[unitnum], abort_action = Event())
    p = Process(target=e.run, kwargs=dict(frame_number = 1, exptime = 5, filter_ = 'g', imgtype = 'DARK'))
    p.start()
    processes.append(p)

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
SingleObservation(telescope, abort_action).run()
# %%
singleobs_kwargs = dict(exptime = 10, count = 5, filter_ = 'r,i', ra =300, dec = -22, autofocus_before_start = True)
#%%
from tcspy.devices import SingleTelescope
from tcspy.action.level2 import * 
telescope_array = dict()

for unitnum in [1,2,3,5,6,7,8,9,10,11]:
    telescope_array[unitnum] = SingleTelescope(unitnum)
#%%
m = MultiAction(array_telescope = telescope_array.values(), array_kwargs = dict(frame_number = 1, exptime = 5, filter_ = 'g', imgtype = 'DARK'), function= Exposure, abort_action= abort_action)
#%%
m.run()
# %%
processes = []
for unitnum in unitnumlist:
    e = SingleObservation(singletelescope= telescope_array[unitnum], abort_action = Event())
    p = Process(target=e.run, kwargs=singleobs_kwargs)
    p.start()
    processes.append(p)
# %%
for process in processes:
    process.terminate()
# %%
Thread(target = e.run, kwargs = singleobs_kwargs).start()
# %%
e = SingleObservation(singletelescope= telescope_array[unitnum], abort_action = Event())
p = Process(target=e.run, kwargs=singleobs_kwargs).start()

# %%
