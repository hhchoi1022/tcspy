#%%
from tcspy.action.level1 import * 
from threading import Event

abort_action = Event()
from tcspy.devices.camera import mainCamera
from tcspy.action import MultiAction
from threading import Thread

#%%



def return_image(cam):
    #cam.device.StartExposure(1, False)
    a = cam.device.ImageArray
    return a
#%%

unitnumlist = [1,2,3]
camlist = dict()
for unitnum in unitnumlist:
    camlist[unitnum] = mainCamera(unitnum)
#%%
for unitnum in unitnumlist:
    Thread(target = return_image, kwargs = dict(cam = camlist[unitnum])).start()

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
