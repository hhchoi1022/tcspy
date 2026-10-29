


#%%
from astropy.time import Time

from tcspy.utils.databases import *
from tcspy.configuration import mainConfig
#%%

class DB(mainConfig):
    """
    A class used to handle actions with the database.

    Parameters
    ----------
    utctime : Time
        Representing the current time.

    Attributes
    ----------
    Dynamic : DB_Dynamic
        An instance of the DB_Dynamic class updated at utctime.
    RIS : DB_Survey
        An instance of the DB_Survey class updated at utcdate.
    IMS : DB_Survey
        An instance of the DB_Survey class updated at utcdate.

    Methods
    -------
    update_Dynamic(utctime)
        Returns an instance of DB_Dynamic updated at utctime.
    update_RIS(utcdate)
        Returns an instance of DB_Survey updated at utcdate.
    update_IMS(utcdate)
        Returns an instance of DB_Survey updated at utcdate.
    """
    
    def __init__(self,
                 utctime = Time.now()):
        super().__init__()
        self.Dynamic = self.update_Dynamic(utctime = utctime)
        self.RIS = self.update_RIS()
        self.IMS = self.update_IMS()
        
    
    def update_Dynamic(self, utctime):
        """
        Returns an instance of DB_Dynamic updated at utctime.

        Parameters
        ----------
        utctime : Time
            Representing the current time.

        Returns
        -------
        DB_Dynamic
            An instance of the DB_Dynamic class updated at utctime.
        """
        Dynamic = DB_Dynamic(utctime = utctime, tbl_name = 'Dynamic')
        return Dynamic

    def update_RIS(self):
        """
        Returns an instance of DB_Survey updated at utcdate.

        Parameters
        ----------
        utcdate : Time
            Representing the current time.

        Returns
        -------
        DB_Survey
            An instance of the DB_Survey class updated at utcdate.
        """
        return DB_Survey(tbl_name = 'RIS')
    
    def update_IMS(self):
        """
        Returns an instance of DB_Survey updated at utcdate.

        Parameters
        ----------
        utcdate : Time
            Representing the current time.

        Returns
        -------
        DB_Survey
            An instance of the DB_Survey class updated at utcdate.
        """
        return DB_Survey(tbl_name = 'IMS')
# %%