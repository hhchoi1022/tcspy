from abc import ABCMeta, abstractclassmethod

class Interface_Abortable(metaclass=ABCMeta):
    __module__ = 'tcspy.interfaces'
    
    @abstractclassmethod
    def abort(self):
        pass

__all__ = ['Interface_Abortable']