#%%
from tcspy.devices import IntegratedDevice
from tcspy.utils.target import mainTarget
from tcspy.devices.integrateddevice import IntegratedDevice
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.action.level1.slewRADec import SlewRADec
from tcspy.action.level1.slewAltAz import SlewAltAz
from tcspy.action.level2.exposure import Exposure
#%%
class SingleObservation(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
        
    def abort(self):
        tel = self.IntDevice.tel
        tel.abort()
        self.IntDevice.update_status()
    
    def run(self, 
            exptime : float,
            count : int = 1,
            filter_ : str = None,
            imgtype : str = 'Light',
            binning : int = 1,
            ra : float = None,
            dec : float = None,
            alt : float = None,
            az : float = None,
            target_name : str = None,
            target : mainTarget = None,
            ):
        
        exposure = Exposure(Integrated_device = self.IntDevice)
        
        if not target:
            target = mainTarget(unitnum = self.IntDevice.unitnum, observer = self.IntDevice.obs, target_ra = ra, target_dec = dec, target_alt = alt, target_az = az, target_name = target_name)
        
        if target.status['coordtype'] == None:
            pass
        elif target.status['coordtype'] == 'radec':
            slew = SlewRADec(Integrated_device = self.IntDevice)
            slew.run(ra = target.status['ra'], dec = target.status['dec'])
        elif target.status['coordtype'] == 'altaz':
            slew = SlewAltAz(Integrated_device = self.IntDevice)
            slew.run(alt = target.status['alt'], az = target.status['az'])
        else:
            raise 
        
        for frame_number in range(count):
            exposure.run(frame_number = frame_number,
                         exptime = exptime,
                         filter_ = filter_,
                         imgtype = imgtype,
                         binning = binning,
                         target_name = target_name,
                         target = target
                         )