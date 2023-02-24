#%%
from tcspy.configuration import mainConfig
#%%

class calibImages(mainConfig):
    def __init__(self,
                 devices,
                 device_names,
                 observer):
        mainConfig.__init__(self)
        self.devices = devices
        self.device_names = device_names
        self.tel, self.cam, self.filt, self.focus = self.devices
        self.observer = observer
    def take_bias(self,
                  counts : int):
        self.cam.take_bias()
    
    
#%%

from startup import startUp
# %%
A = startUp()
A.run()
# %%
B = calibImages(A.devices, A.device_names, A.observer)
# %%
B.tel.is_connected()
# %%
