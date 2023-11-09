
from abc import ABCMeta, abstractclassmethod

class Interface_Abort(metaclass=ABCMeta):
    __module__ = 'tcspy.interfaces'
    
    @abstractclassmethod
    def abort(self):
        pass

__all__ = ['Interface_Abort']