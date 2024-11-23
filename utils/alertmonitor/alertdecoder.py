

from astropy.table import Table
from tcspy.utils import GoogleSheet


class AlertDecoder:
    
    def __init__(self):
        self.formatted_data = None
        self.alert_data = None
        self.alert_type = None
        self.is_decoded = False
    
    def default_configuration(self):
        
        class configuration:
            pass
        pass
    
    def _decode_gwalert(self, file_path : str):
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
        self.alert_data = gw_table
        self.alert_type = 'GW'
        format_colnamelist = ['#id', 'ra', 'dec', 'obj', 'rank']
        # Check if the alert data contains the required columns
        if not all(col in gw_table.colnames for col in format_colnamelist):
            raise ValueError('Alert data does not contain the required columns.')
        # Rename the columns to the standard format
        formatted_tbl = Table()
        formatted_tbl['objname'] = ['%.5d'%id_ for id_ in gw_table['#id']]
        formatted_tbl['ra'] = gw_table['ra']
        formatted_tbl['dec'] = gw_table['dec']
        formatted_tbl['obj'] = gw_table['obj']
        formatted_tbl['rank'] = gw_table['rank']
        

        
        return alert_data
    
        
    