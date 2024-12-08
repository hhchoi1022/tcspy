
#%%
from astropy.io import ascii
from astropy.table import Table
from GSconnector import GoogleSheetConnector
from gmailconnector import GmailConnector
import json
from tcspy.utils.databases.tiles import Tiles
#from tcspy.utils.connector import GoogleSheetConnector
#%%

class Alert:
    
    def __init__(self):
        self.filepath = None
        self.formatted_data = None
        self.alert_data = None
        self.alert_type = None
        self.is_decoded = False
        self.config = self._default_config
        self.tiles = None
    
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
    
    def _match_RIS_tile(self, ra, dec):
        if not self.tiles:
            self.tiles = Tiles(tile_path = None)
        tile, _ = self.tiles.find_overlapping_tiles([ra], [dec], visualize = False)
        return tile
    
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
        
        # Set/Modify the columns to the standard format
        formatted_tbl = Table()
        for key, value in self.config.items():
            formatted_tbl[key] = [value] * len(self.alert_data)
        # Update values from alert_data if the key exists
        columns_match = {
            'objname': 'id',
            'RA': 'ra',
            'De': 'dec',
            'exptime': 'exptime',
            'count': 'count',
            'obsmode': 'obsmode',
            'specmode': 'specmode',
            'filter': 'filter',
            'ntelescopes': 'ntelescopes',
            'gain': 'gain',
            'priority': 'rank',
            'note': 'obj',
        }            
        for key, value in columns_match.items():
            if value in self.alert_data.keys():
                formatted_tbl[key] = self.alert_data[value]
                
        formatted_tbl['objname'] = ['T%.5d'%int(objname) if str(objname) !=6 else objname for objname in formatted_tbl['objname']]
        formatted_tbl['objtype'] = 'GECKO'
        self.is_decoded = True
        self.formatted_data = formatted_tbl
    
    def decode_ToOalert_mailbroker(self, mail_str, match_to_tiles = True):
        # Read the alert data from the attachment
        mail_dict = dict(mail_str)
        # If Attachment is not present, read the body
        if 'Attachments' in mail_dict.keys():
            try:
                self.filepath = mail_dict['Attachments'][0]
                self.alert_data = json.load(open(mail_dict['Attachments'][0]))
            except:
                raise ValueError(f'Error reading the alert data')
        else:
            try:
                self.alert_data = read_mail_body(mail_dict['Body'])  # TODO: Implement read_mail_body
            except:
                raise ValueError(f'Error reading the alert data')
        self.alert_type = 'mail_broker'
        
        # Set/Modify the columns to the standard format
        formatted_dict = dict()
        for key, value in self.config.items():
            formatted_dict[key] = value
        # Update values from alert_data if the key exists
        columns_match = {
            'objname': 'target',
            'RA': 'ra',
            'De': 'dec',
            'exptime': 'singleFrameExposure',
            'count': 'imageCount',
            'obsmode': 'observationMode',
            'specmode': 'specmode',
            'filter': 'selectedFilters',
            'ntelescopes': 'selectedTelNumber',
            'gain': 'gain',
            'priority': 'priority',
            'obs_starttime': 'obsStartTime',
        }            
        for key, value in columns_match.items():
            if value in self.alert_data.keys():
                formatted_dict[key] = self.alert_data[value]
        
        # Match the RA, Dec to the RIS tiles
        if match_to_tiles:
            tile_info = self._match_RIS_tile(formatted_dict['RA'], formatted_dict['De'])
            objname = formatted_dict['objname']
            # Update values from alert_data if the key exists
            columns_match = {
                'objname': 'id',
                'RA': 'ra',
                'De': 'dec'
            }            
            for key, value in columns_match.items():
                if value in tile_info.keys():
                    formatted_dict[key] = tile_info[value][0]
            # Note become the target name 
            formatted_dict['note'] = objname
        
        # If the value of the dict is list, convert it to comma-separated string
        for key, value in formatted_dict.items():
            if isinstance(value, list):
                formatted_dict[key] = ','.join(value)

        # Convert the dict to astropy.Table
        formatted_tbl = Table()
        for key, value in formatted_dict.items():
            formatted_tbl[key] = [value]
        self.is_decoded = True
        self.formatted_data = formatted_tbl
    
    def decode_ToOalert_mailuser(self, mail_str, match_to_tiles = True):
        # Read the alert data from the attachment
        mail_dict = dict(mail_str)
        mail_body = mail_dict['Body']
        # Read the alert data from the body
        def parse_mail_string(mail_string):
            # Define key variants
            required_key_variants_lower = {
                'objname': ['target', 'object', 'objname'],
                'RA': ['ra', 'r.a.', 'right ascension'],
                'De': ['dec', 'dec.', 'declination'],
                'exptime': ['exptime', 'exposure', 'exposuretime', 'exposure time'],
                'count': ['count', 'imagecount', 'numbercount', 'image count', 'number count'],
                'filter_': ['filter', 'filters'],
                'specmode': ['specmode', 'spectralmode', 'spectral mode'],
                'obsmode': ['obsmode', 'observationmode', 'mode'],
                'ntelescopes': ['ntelescopes', 'ntelescope', 'numberoftelescopes', 'number of telescopes'],
                'binning': ['binning'],
                'gain': ['gain'],
                'priority': ['priority'],
                'weight': ['weight'],
                'objtype': ['objtype', 'objecttype'],
                'obs_starttime': ['obsstarttime', 'starttime', 'start time', 'obs_starttime'],
                'is_ToO': ['is_too', 'is too'],
                'comments': ['comment', 'comments']
            }

            def check_and_normalize_required_keys(line_string, required_key_variants_lower):
                """
                Check if the line contains any required keys and return the canonical key if a match is found.
                :param line_string: str, the input line to check
                :param required_key_variants_lower: dict, dictionary of canonical keys to their variants
                :return: str, canonical key if a match is found; None otherwise
                """
                # Iterate through the dictionary to find a match
                for canonical_key, variants in required_key_variants_lower.items():
                    # Create a regex pattern for each variant followed by ':' or '=' or a space
                    #pattern = r'(' + '|'.join(re.escape(variant) for variant in variants) + r')\s*[:= ]\s*(.+)'
                    pattern = r'^\s*(' + '|'.join(re.escape(variant) for variant in variants) + r')\s*[:= ]\s*(.+)$'

                    
                    # Search for the pattern in the line string
                    match = re.search(pattern, line_string.lower())
                    if match:
                        # Extract the matched key variant and the value
                        key_variant = match.group(1)  # The matched key (variant)
                        value = match.group(2).strip()  # The value after ':' or '=' or space
                        print(canonical_key,': ', value)
                        return canonical_key, value
                
                # If no match is found, return None
                return None, None

            # Initialize the dictionary
            parsed_dict = {}

            # Process the string line by line
            for line in mail_body.splitlines():
                # Skip empty lines or lines that don't have delimiters

                # Split the line using possible delimiters
                key, value = check_and_normalize_required_keys(line, required_key_variants_lower)

                # Normalize the key and clean up the value
                if not key:
                    continue

                # Convert numeric values if applicable
                #if re.match(r'^-?\d+(\.\d+)?$', value):  # Float or int
                #    value = float(value) if '.' in value else int(value)
                #elif value.lower() in ['true', 'false']:  # Boolean
                #    value = value.lower() == 'true'

                # Add to the dictionary
                parsed_dict[key] = value

            return parsed_dict
        
        self.alert_type = 'mail_user'
        formatted_dict = parse_mail_string(mail_body)

        # Match the RA, Dec to the RIS tiles
        if match_to_tiles:
            tile_info = self._match_RIS_tile(formatted_dict['RA'], formatted_dict['De'])
            if len(tile_info) == 0:
                raise ValueError(f'No matching tile found for RA = {formatted_dict["RA"]}, Dec = {formatted_dict["De"]}')
            objname = formatted_dict['objname']
            # Update values from alert_data if the key exists
            columns_match = {
                'objname': 'id',
                'RA': 'ra',
                'De': 'dec'
            }            
            for key, value in columns_match.items():
                if value in tile_info.keys():
                    formatted_dict[key] = tile_info[value][0]
            # Note become the target name 
            formatted_dict['note'] = objname
        
        formatted_tbl = Table()
        for key, value in formatted_dict.items():
            formatted_tbl[key] = [value]
        self.is_decoded = True
        self.formatted_data = formatted_tbl


# %%
if __name__ == '__main__':
    Gmail = GmailConnector('7dt.observation.alert@gmail.com')
    Gmail.login()
    maillist = Gmail.readmail()
    mail_str = maillist[-1]
    B = Alert()
# %%
B.decode_gwalert('/Users/hhchoi1022/code/GECKO/S240925n/SkyGridCatalog_7DT_90.csv')
# %%
B
# %%
B.formatted_data
# %%
B.decode_ToOalert_mailbroker(mail_str)
# %%
B
# %%
