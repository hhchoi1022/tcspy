#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice

class DeviceStatus(Interface):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IDevice = Integrated_device
        self.tel_type = self.IDevice.tel_type
    
    @property
    def dict(self):
        status = dict()
        status['camera'] = self.camera
        status['telescope'] = self.telescope
        status['filterwheel'] = self.filterwheel
        status['focuser'] = self.focuser
        status['dome'] = self.dome
        status['safetymonitor'] = self.safetymonitor
        status['weather'] = self.weather
        return status
    
    @property
    def camera(self):
        """return camera status

        Returns:
            status : str = camera's status [disconnected, idle, busy]
        """
        status = 'disconnected'
        try:
            if self.IDevice.camera.device.Connected:
                status = 'idle'
                if self.IDevice.camera.device.CamsState.name == 'cameraIdle':
                    status = 'idle'
                else:
                    status = 'busy'    
        except:
            pass
        return status

    @property
    def telescope(self):
        """return telescope status

        Returns:
            status : str = telescope's status [disconnected, idle, Parked, busy, Tracking]
        """
        status = 'disconnected'
        try:
            telescope = self.IDevice.telescope
            # Alpaca device
            if self.IDevice.tel_type.lower() == 'alpaca':
                if telescope.device.Connected:
                    status = 'idle'
                    if telescope.device.AtHome:
                        status = 'idle'
                    if telescope.device.AtPark:
                        status = 'parked'
                    if telescope.device.Slewing:
                        status = 'busy'
                    if telescope.device.Tracking:
                        status = 'tracking'
            # PWI4 device
            else:
                telescope_status = telescope.device.status()
                if telescope_status.mount.is_connected:
                    status = 'idle'
                if (telescope_status.mount.axis0.is_enabled == False) & (telescope_status.mount.axis2.is_enabled == False):
                    status = 'parked'
                if telescope_status.mount.is_slewing:
                    status = 'busy'
                if telescope_status.mount.is_tracking:
                    status = 'tracking'
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
            if self.IDevice.filterwheel.device.Connected:
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
            if self.IDevice.focuser.device.Connected:
                status = 'idle'
            if self.IDevice.focuser.device.IsMoving:
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
        try:
            if self.IDevice.safetymonitor.device.Connected:
                status = 'unsafe'
                if self.IDevice.safetymonitor.device.IsSafe:
                    status = 'safe'
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
        try:
            if self.IDevice.weather.device.Connected:
                status = 'unsafe'
                if self.IDevice.weather.is_safe():
                    status = 'safe'
        except:
            pass
        return status