#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice

class DeviceCondition(Interface):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
    
    @property
    def camera(self):
        """return camera condition

        Returns:
            condition : str = camera's condition [disconnected, idle, busy]
        """
        condition = 'disconnected'
        try:
            if self.IntDevice.cam.device.Connected:
                condition = 'idle'
                if self.IntDevice.cam.device.CamsState.name == 'cameraIdle':
                    condition = 'idle'
                else:
                    condition = 'busy'    
        except:
            pass
        return condition

    @property
    def telescope(self):
        """return telescope condition

        Returns:
            condition : str = telescope's condition [disconnected, idle, Parked, busy, Tracking]
        """
        condition = 'disconnected'
        try:
            if self.IntDevice.tel.device.Connected:
                condition = 'idle'
                if self.IntDevice.device.tel.device.AtHome:
                    condition = 'idle'
                if self.IntDevice.device.tel.device.AtPark:
                    condition = 'parked'
                if self.c.IntDevice.tel.device.Slewing:
                    condition = 'busy'
                if self.IntDevice.tel.device.Tracking:
                    condition = 'tracking'
        except:
            pass
        return condition

    @property
    def filterwheel(self):
        """return filterwheel condition

        Returns:
            condition : str = filterwheel's condition [disconnected, idle]
        """
        condition = 'disconnected'
        try:
            if self.IntDevice.filt.device.Connected:
                condition = 'idle'
                condition = self.filt.condition
        except:
            pass
        return condition

    @property
    def focuser(self):
        """return focuser condition

        Returns:
            condition : str = focuser's condition [disconnected, idle]
        """
        condition = 'disconnected'
        try:
            if self.IntDevice.focus.device.Connected:
                condition = 'idle'
                condition = self.filt.condition
        except:
            pass
        return condition

    @property
    def dome(self):
        """return dome condition

        Returns:
            condition : str = dome's condition [disconnected]
        """
        condition = 'disconnected'
        return condition
    
    @property
    def safetymonitor(self):
        """return safetymonitor condition

        Returns:
            condition : str = safetymonitor's condition [disconnected, safe, unsafe]
        """
        condition = 'disconnected'
        try:
            if self.IntDevice.safe.device.Connected:
                condition = 'unsafe'
                if self.IntDevice.safe.device.IsSafe:
                    condition = 'safe'
        except:
            pass
        return condition

    @property
    def weather(self):
        """return weather condition

        Returns:
            condition : str = weather's condition [disconnected, safe, unsafe]
        """
        condition = 'disconnected'
        try:
            if self.IntDevice.weat.device.Connected:
                condition = 'unsafe'
                if self.IntDevice.weat.is_safe():
                    condition = 'safe'
        except:
            pass
        return condition