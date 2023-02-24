#%%


#%%
from alpaca.telescope import Telescope

from tcspy.utils import mainLogger
from tcspy.configuration import loadConfig
from .devicetelescope import deviceTelescope

#%%
log = mainLogger(__name__).log()
class mainTelescope(deviceTelescope, loadConfig):
    
    def __init__(self):
        loadConfig.__init__(self)
        deviceaddress = self.config['TELESCOPE_HOSTIP']+':'+self.config['TELESCOPE_PORTNUM']
        T = Telescope(deviceaddress, int(self.config['TELESCOPE_DEVICENUM']))
        deviceTelescope.__init__(self, device = T)
        try:
            self.connect()
        except:
            logtxt = 'Connection to the telescope Failed'
            log.warning(logtxt)
            raise ConnectionError(logtxt)