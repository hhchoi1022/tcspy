
from abc import ABCMeta, abstractclassmethod
from .Abort import Interface_Abort

class Interface_Filterchange(Interface_Abort, metaclass=ABCMeta):
    __module__ = 'tcspy.interfaces'
    
    @abstractclassmethod
    def change_filter(self):
        pass

__all__ = ['Interface_Filterchange']