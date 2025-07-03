#%%
from tcspy.interfaces import *
from tcspy.devices import SingleTelescope
from tcspy.utils import Timeout
import time

class TelescopeStatus(Interface):
    
    def __init__(self, 
                 singletelescope : SingleTelescope):
        self.telescope = singletelescope
        self.tel_name = self.telescope.name
        self.mount_type = self.telescope.mount_type
        self.focus_type = self.telescope.focus_type
    
    @property
    def dict(self):
        status = dict()
        status['camera'] = self.camera
        status['mount'] = self.mount
        status['filterwheel'] = self.filterwheel
        status['focuser'] = self.focuser
        status['dome'] = self.dome
        status['safetymonitor'] = self.safetymonitor
        status['weather'] = self.weather
        return status
    
    @property
    def camera(self):
        cam = self.telescope.camera.device
        from multiprocessing.pool import ThreadPool
        def call_with_timeout(func, timeout=5):
            pool = ThreadPool(processes=1)
            async_result = pool.apply_async(func)
            try:
                return async_result.get(timeout)
            except Exception:
                return 'disconnected'
        
        def get_state():
            return cam.CameraState
        
        status = 'disconnected'
        try:

            state = call_with_timeout(get_state, timeout=5)
            if isinstance(state, int):
                status = 'idle' if state == 0 else 'busy'  # 0 = cameraIdle
            else:
                # fallback: try to use .name safely
                try:
                    if state.name == 'cameraIdle':
                        status = 'idle'
                    else:
                        status = 'busy'
                except:
                    status = 'idle'
        except Exception as e:
            pass
        return status

    @property
    def mount(self):
        """return mount status

        Returns:
            status : str = telescope's status [disconnected, idle, Parked, busy, Tracking]
        """
        status = 'disconnected'
        try:
            mount = self.telescope.mount
            # Alpaca device
            if self.telescope.mount_type.lower() == 'alpaca':
                if mount.device.Connected:
                    status = 'idle'
                    if mount.device.AtHome:
                        status = 'idle'
                    if mount.device.AtPark:
                        status = 'idle'
                    if mount.device.Slewing:
                        status = 'busy'
                    if mount.device.Tracking:
                        status = 'idle'
            # PWI4 device
            else:
                mount_status = mount.device.status()
                if mount_status.mount.is_connected:
                    status = 'idle'
                if (mount_status.mount.axis0.is_enabled == False) & (mount_status.mount.axis2.is_enabled == False):
                    status = 'idle'
                if mount_status.mount.is_slewing:
                    status = 'busy'
                if mount_status.mount.is_tracking:
                    status = 'idle'
        except:
            pass
        return status

    @property
    def filterwheel(self):
        """return filterwheel status

        Returns:
            status : str = filterwheel's status [disconnected, idle]
        """
        status = 'disconnected'
        try:
            #if self.telescope.filterwheel.device.Connected:
            status = 'idle'
        except:
            pass
        return status

    @property
    def focuser(self):
        """return focuser status

        Returns:
            status : str = focuser's status [disconnected, idle]
        """
        status = 'disconnected'
        try:
            focuser = self.telescope.focuser
            # Alpaca device
            if self.telescope.focus_type.lower() == 'alpaca':
                if focuser.device.Connected:
                    status = 'idle'
                if focuser.device.IsMoving:
                    status = 'busy'
            # PWI4 device
            else:
                focuser_status = focuser.device.status()
                if focuser_status.focuser.is_connected:
                    status = 'idle'
                if focuser_status.focuser.is_enabled == False:
                    status = 'parked'
                if focuser_status.focuser.is_moving:
                    status = 'busy'
        except:
            pass
        return status

    @property
    def dome(self):
        """return dome status

        Returns:
            status : str = dome's status [disconnected]
        """
        status = 'disconnected'
        return status
    
    @property
    def safetymonitor(self):
        """return safetymonitor status

        Returns:
            status : str = safetymonitor's status [disconnected, safe, unsafe]
        """

        status = 'disconnected'

        @Timeout(3, 'Timeout error when updating status of SafetyMonitor device')
        def update_status(status):
            status = 'disconnected'
            try:
                device_status = self.telescope.safetymonitor.get_status()
                if device_status['is_connected']:
                    status = 'unsafe'
                    if device_status['is_safe']:
                        status = 'safe'
            except:
                pass
            return status
        try:
            status = update_status(status)
        except:
            pass
        return status

    @property
    def weather(self):
        """return weather status

        Returns:
            status : str = weather's status [disconnected, safe, unsafe]
        """
        status = 'disconnected'
        
        @Timeout(3, 'Timeout error when updating status of Weather device')
        def update_status(status):
            status = 'disconnected'
            try:
                device_status = self.telescope.weather.get_status()
                if device_status['is_connected']:
                    status = 'unsafe'
                    if device_status['is_safe']:
                        status = 'safe'
            except:
                pass
            return status
        try:
            status = update_status(status)
        except:
            pass    
        
        return status

# %%
if __name__ == '__main__':
    for unitnum in [2,4,5,7,8,9,10,11,12,13,14,15,16]:
        t = TelescopeStatus(SingleTelescope(unitnum))
        print(t.camera)
    

# %%
