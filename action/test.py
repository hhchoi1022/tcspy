#%%
from tcspy.action.level1 import * 
from multiprocessing import Event
from tcspy.devices import SingleTelescope

abort_action = Event()
from tcspy.devices.camera import mainCamera
from tcspy.action import MultiAction
from threading import Thread

#%%
"""
telescope1 = SingleTelescope(1)
telescope2 = SingleTelescope(2)
telescope3 = SingleTelescope(3)
telescope5 = SingleTelescope(5)
telescope6 = SingleTelescope(6)
telescope7 = SingleTelescope(7)
telescope8 = SingleTelescope(8)
telescope9 = SingleTelescope(9)
"""
#%%
telescope21 = SingleTelescope(21)
array_telescope= [ telescope21]#telescope1, telescope2, telescope3]#, telescope5, telescope6, telescope7, telescope8, telescope9]
#%%
#%%
kwargs = dict(filter_ = 'g')
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = ChangeFilter, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
#%%
kwargs = dict(position = 30000)
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = ChangeFocus, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
# %%
kwargs = dict()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = Connect, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
#%%
kwargs = dict(settemperature = -20)
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = Cool, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
# %%
kwargs = dict(frame_number = 1, exptime = 1, filter_ = 'i', imgtype ='Light', binning = 1, name = 'ABC', objtype = None, obsmode = 'Single')
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = Exposure, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])

# %%
kwargs = dict()
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = FansOn, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])# %%
# %%
kwargs = dict()
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = FansOff, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
# %%

kwargs = dict(alt = 40, az = 180)
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = SlewAltAz, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
# %%
kwargs = dict(ra = 150, dec = -40)
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = SlewRADec, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
# %%
kwargs = dict()
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = TrackingOff, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
#%%
kwargs = dict()
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = TrackingOn, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
#%%
kwargs = dict()
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = Unpark, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
#%%
kwargs = dict(settemperature = 10)
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = Warm, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])

#%%
from tcspy.action.level2 import * 
# %%
kwargs = dict(filter_ = 'r', use_offset = False)
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = AutoFocus, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
#%%
kwargs = dict(exptime = 10, count = 1, filter_ = 'i', ra =180, dec = -22, autofocus_before_start = True)
abort_action = Event()
m = MultiAction(array_telescope = array_telescope, array_kwargs= kwargs, function = SingleObservation, abort_action = abort_action)
m.run()
dict(m.shared_memory['7DT21'])
#%%
from tcspy.action.level2 import * 
telescope_array = []
SingleObs_list = []

for unitnum in [1,2,3,5,6,7,8,9,10,11]:
    tel = SingleTelescope(unitnum)
    SingleObs_list.append(SingleObservation(tel, Event()))
#%%

kwargs = dict( exptime = 1, count = 1, filter_ = 'i', alt =60, az = 300, autofocus_before_start = False)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=11) as executor:
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








#%%
import requests
import time
from astropy.time import Time
from threading import Thread

def request_imagearray(cam):
    client_trans_id = 1
    client_id = 1
    attribute = 'imagearray'

    url = f"{cam.device.base_url}/{attribute}"
    hdrs = {'accept' : 'application/imagebytes'}
    # Make Host: header safe for IPv6
    if(cam.device.address.startswith('[') and cam.device.address.startswith('[::1]')):
        hdrs['Host'] = f'{cam.device.address.split("%")[0]}]'
    pdata = {
            "ClientTransactionID": f"{client_trans_id}",
            "ClientID": f"{client_id}" 
            }         

    print('START:',Time.now(), cam.device.address)
    start = time.time()
    print("%s/%s" % (cam.device.base_url, attribute))
    response = requests.get("%s/%s" % (cam.device.base_url, attribute), params=pdata, headers=hdrs, verify = False)

    print('consumed time:', time.time() - start, cam.device.address)
# %%

unitnumlist = [1,2,3,5,6,7,8,9,10,11]
camlist = []
for unitnum in unitnumlist:
    #camlist.append(mainCamera(unitnum))
    Thread(target = request_imagearray, kwargs = dict(cam = mainCamera(unitnum))).start()
#%%

cam1 = mainCamera(1)
cam2 = mainCamera(2)
cam3 = mainCamera(3)
# %%
Thread(target = request_imagearray, kwargs = dict(cam = cam1)).start()
Thread(target = request_imagearray, kwargs = dict(cam = cam2)).start()
Thread(target = request_imagearray, kwargs = dict(cam = cam3)).start()
# %%
