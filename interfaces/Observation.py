
from abc import ABCMeta, abstractclassmethod
from .Slew import Interface_Slew
from .Filterchange import Interface_Filterchange
from .Exposure import Interface_Exposure
from .Abort import Interface_Abort

class Interface_Observation(Interface_Slew,
                            Interface_Exposure,
                            Interface_Filterchange,
                            Interface_Abort,
                            metaclass = ABCMeta):
    __module__ = 'tcspy.interfaces'
    
    @abstractclassmethod
    def save(self):
        pass
    
__all__ = ['Interface_Observation']