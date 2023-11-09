
from abc import ABCMeta, abstractclassmethod
from .Abort import Interface_Abort

class Interface_Exposure(Interface_Abort, metaclass=ABCMeta):
    __module__ = 'tcspy.interfaces'
    
    @abstractclassmethod
    def exposure(self):
        pass

__all__ = ['Interface_Exposure']