
#%%
from astropy.io import ascii
from astropy.table import Table
#from tcspy.utils.databases.tiles import Tiles
#from tcspy.utils.connector import GoogleSheetConnector
#%%

class AlertDecoder:
    
    def __init__(self):
        self.filepath = None
        self.formatted_data = None
        self.alert_data = None
        self.alert_type = None
        self.is_decoded = False
        self.config = self._default_config
        #self.tiles = Tiles()
    
    def __repr__(self):
        txt = (f'ALERT (type = {self.alert_type}, decoded = {self.is_decoded}, path = {self.filepath})')
        return txt   
    
    @property
    def _default_config(self):
        default_config = dict()
        default_config['exptime'] = 100
        default_config['count'] = 3
        default_config['obsmode'] = 'Spec'
        default_config['filter'] = 'g'
        default_config['specmode'] = 'specall'
        default_config['ntelescope'] = 10
        default_config['priority'] = 50
        default_config['weight'] = 1
        default_config['binning'] = 1
        default_config['gain'] = 1
        default_config['objtype'] = 'Request'
        default_config['is_ToO'] = 0
        return default_config
    
    def decode_gwalert(self, file_path : str):
        """
        Decodes a GW alert file and returns the alert data as an astropy.Table.
        
        Parameters:
        - file_path: str, path to the alert file
        
        Returns:
        - alert_data: astropy.Table containing the alert data
        """
        # Read the alert data from the file
        try:
            gw_table = ascii.read(file_path)
        except:
            raise ValueError(f'Error reading the alert file at {file_path}')
        self.filepath = file_path
        self.alert_data = gw_table
        self.alert_type = 'GW'
        format_colnamelist = ['id', 'ra', 'dec', 'obj', 'rank']
        # Check if the alert data contains the required columns
        if not all(col in gw_table.colnames for col in format_colnamelist):
            raise ValueError('Alert data does not contain the required columns.')
        # Set/Modify the columns to the standard format
        formatted_tbl = Table()
        for key, value in self.config.items():
            formatted_tbl[key] = [value] * len(gw_table)
        formatted_tbl['objname'] = ['T%.5d'%id_ for id_ in gw_table['id']]
        formatted_tbl['RA'] = gw_table['ra']
        formatted_tbl['De'] = gw_table['dec']
        formatted_tbl['obj'] = gw_table['obj']
        formatted_tbl['priority'] = gw_table['rank']
        formatted_tbl['note'] = gw_table['obj']
        formatted_tbl['objtype'] = 'GECKO'
        self.is_decoded = True
        self.formatted_data = formatted_tbl
    
    def decode_mailalert(self, mail_str):
        pass
    
