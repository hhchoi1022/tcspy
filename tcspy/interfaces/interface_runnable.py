
from abc import ABCMeta, abstractclassmethod

class Interface_Runnable(metaclass=ABCMeta):
    __module__ = 'tcspy.interfaces'
    
    @abstractclassmethod
    def run(self):
        pass

__all__ = ['Interface_Runnable']