
# Mount

class ParkingFailedException(Exception):
    pass

class SlewingFailedException(Exception):
    pass

class TrackingFailedException(Exception):
    pass

class MountEnableFailedException(Exception):
    pass

class FindingHomeFailedException(Exception):
    pass


# Camera

class ExposureFailedException(Exception):
    pass

class WarmingFailedException(Exception):
    pass

class CoolingFailedException(Exception):
    pass


# Focuser

class FocusChangeFailedException(Exception):
    pass

# Filterwheel

class FilterChangeFailedException(Exception):
    pass

class FilterRegisterException(Exception):
    pass

# 

class AbortionException(Exception):
    pass

class ConnectionException(Exception):
    pass

class ActionFailedException(Exception):
    pass