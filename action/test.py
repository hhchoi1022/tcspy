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
from tcspy.devices import SingleTelescope
telescope1 = SingleTelescope(1)
telescope2 = SingleTelescope(2)
telescope3 = SingleTelescope(3)
telescope5 = SingleTelescope(5)
telescope6 = SingleTelescope(6)
telescope7 = SingleTelescope(7)
telescope8 = SingleTelescope(8)
telescope9 = SingleTelescope(9)
telescope10 = SingleTelescope(10)
telescope11= SingleTelescope(11)

array_telescope= [ telescope1, telescope2, telescope3, telescope5, telescope6, telescope7, telescope8, telescope9, telescope10, telescope11]

#%% Exposure
kwargs = dict(frame_number = 1, exptime = 5, filter_ = 'r', imgtype = 'DARK')
array_kwargs = []
for i in range(1):
    array_kwargs.append(kwargs)
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = Exposure, abort_action = abort_action)
m.run()
#%% Connect
kwargs = dict()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = Connect, abort_action = abort_action)
m.run()
# %% ChangeFilter
kwargs = dict(filter_ = 'r')
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = ChangeFilter, abort_action = abort_action)
m.run()
# %% SLew
kwargs = dict(ra = 300, dec=  -20)
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = SlewRADec, abort_action = abort_action)
m.run()
# %%
