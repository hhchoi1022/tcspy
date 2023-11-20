
from abc import ABCMeta, abstractclassmethod
from .interface_abortable import Interface_Abortable
from .interface_runnable import Interface_Runnable

class Interface_SlewAltAz(Interface_Abortable, Interface_Runnable, metaclass=ABCMeta):
    __module__ = 'tcspy.interfaces'
    
__all__ = ['Interface_SlewAltAz']