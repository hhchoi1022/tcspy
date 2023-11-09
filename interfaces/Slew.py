
from abc import ABCMeta, abstractclassmethod
from .Abort import Interface_Abort

class Interface_Slew(Interface_Abort, metaclass=ABCMeta):
    __module__ = 'tcspy.interfaces'
    
    @abstractclassmethod
    def slew_RADec(self):
        pass
    
    @abstractclassmethod
    def slew_AltAz(self):
        pass
    
    
__all__ = ['Interface_Slew']