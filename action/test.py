#%%
from tcspy.action.level1 import * 
from threading import Event
from tcspy.devices import SingleTelescope
abort_action = Event()
from tcspy.devices.camera import mainCamera
#%%
telescope1 = SingleTelescope(1)
telescope2 = SingleTelescope(2)
telescope3 = SingleTelescope(3)
telescope = SingleTelescope(1)
#cam1 = mainCamera(1)
cam2 = mainCamera(2)
cam3 = mainCamera(3)
cam5 = mainCamera(5)
def return_image(cam):
    
    start = time.time()
    a = cam.device.ImageArray
    print(cam.unitnum,  time.time() -start)
    return a
#%%
from threading import Thread
import time
kwargs2 = dict(cam = cam2)
kwargs3 = dict(cam = cam3)
kwargs5 = dict(cam = cam5)
a = Thread(target  =return_image, kwargs = kwargs2)
b = Thread(target  =return_image, kwargs = kwargs3)
c = Thread(target  =return_image, kwargs = kwargs5)
#%%
a.start()
b.start()
c.start()
a.join()
#%%
import requests
import threading
def make_request(url):
    response = requests.get(url)
    print(f"Response from {url}: {response.status_code}")
# List of URLs to make requests to
urls = [
    "https://www.example.com",
    "https://www.google.com",
    "https://www.wikipedia.org",
    "https://www.python.org"
]

# Create and start threads for each URL
threads = []
for url in urls:
    thread = threading.Thread(target=make_request, args=(url,))
    thread.start()
    threads.append(thread)
# Wait for all threads to finish
#%%
import time
from concurrent.futures import ThreadPoolExecutor

# Define the function to retrieve an image
def return_image(cam):
    start = time.time()
    a = cam.device.ImageArray
    print(cam.unitnum, time.time() - start)
    return a

# Create mainCamera instances
cam2 = mainCamera(2)
cam3 = mainCamera(3)
cam5 = mainCamera(5)
#%%
# Create a ThreadPoolExecutor with 3 threads
with ThreadPoolExecutor(max_workers=10) as executor:
    # Submit the return_image function with arguments to the executor
    futures = [executor.submit(return_image, cam) for cam in [cam2, cam3, cam5]]

    # Wait for all tasks to complete
    for future in futures:
        future.result()

#%%
from threading import Thread
import time

kwargs = dict(abort_action = Event(), exptime = 5, imgtype = 'Dark', binning = 1, is_light = False, gain =0)
#a = Thread(target  =cam1.exposure, kwargs = kwargs).start()
a = Thread(target  =cam2.exposure, kwargs = kwargs).start()
a = Thread(target  =cam3.exposure, kwargs = kwargs).start()
a = Thread(target  =cam5.exposure, kwargs = kwargs).start()

#%%


#%%
from tcspy.action import MultiAction
array_telescope= [telescope1, telescope2, telescope3]
kwargs = dict(frame_number = 1, exptime = 1, filter_ = 'r', imgtype = 'DARK')
array_kwargs = []
for i in range(3):
    array_kwargs.append(kwargs)

m = MultiAction(array_telescope = array_telescope, array_kwargs= array_kwargs, function = Exposure, abort_action = abort_action)
#%%
m.run()
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