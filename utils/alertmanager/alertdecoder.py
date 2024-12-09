
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
        for key in gw_table.keys():
            noramlized_key = self._normalize_required_keys(key)
            if noramlized_key:
                formatted_tbl[noramlized_key] = gw_table[key]
            else:
                print('The key is not found in the key variants: ', key)

                            
        formatted_tbl['objname'] = ['T%.5d'%int(objname) if not str(objname).startswith('T') else objname for objname in formatted_tbl['objname']]
        formatted_tbl['objtype'] = 'GECKO'
        formatted_tbl['note'] = gw_table['obj'] # Tile observation -> objname is stored in "Note"
        formatted_tbl['is_ToO'] = [1 if confidence <= 0.95 else 0 for confidence in gw_table['confidence']]
        self.is_decoded = True
        self.formatted_data = formatted_tbl
    
    def decode_brokermail(self, mail_str, match_to_tiles = True):
        # Read the alert data from the attachment
        mail_dict = dict(mail_str)
        # If Attachment is not present, read the body
        if len(mail_dict['Attachments']) > 0:
            try:
                alert_dict = json.load(open(mail_dict['Attachments'][0]))
                self.filepath = mail_dict['Attachments'][0]
            except:
                raise ValueError(f'Error reading the alert data')
        else:
            try:
                alert_dict = self._parse_mail_string(mail_dict['Body']) 
                self.filepath = None
            except:
                raise ValueError(f'Error reading the alert data')
        self.alert_data = alert_dict
        self.alert_type = 'mail_broker'
        
        # Set/Modify the columns to the standard format
        formatted_dict = dict()
        for key, value in self.config.items():
            formatted_dict[key] = value
            
        # Update values from alert_data if the key exists
        for key in alert_dict.keys():
            normalized_key = self._normalize_required_keys(key)
            if normalized_key:
                formatted_dict[normalized_key] = alert_dict[key]
            else:
                print('The key is not found in the key variants: ', key)
        
        # Match the RA, Dec to the RIS tiles
        if match_to_tiles:
            tile_info = self._match_RIS_tile(formatted_dict['RA'], formatted_dict['De'])
            if len(tile_info) == 0:
                raise ValueError(f'No matching tile found for RA = {formatted_dict["RA"]}, Dec = {formatted_dict["De"]}')
            objname = formatted_dict['objname']
            formatted_dict['objname'] = tile_info['id'][0]
            formatted_dict['RA'] = tile_info['ra'][0]
            formatted_dict['De'] = tile_info['dec'][0]
            formatted_dict['note'] = objname
        
        # If the value of the dict is list, convert it to comma-separated string
        for key, value in formatted_dict.items():
            if isinstance(value, list):
                formatted_dict[key] = ','.join(value).replace(" ", "")
                
        # if space in the value, remove it
        for key, value in formatted_dict.items():
            if isinstance(value, str):
                formatted_dict[key] = value.replace(" ", "")
                
        # If is_ToO is not defined, set it to 0
        if str(formatted_dict['is_ToO']).upper() == 'TRUE':
            formatted_dict['is_ToO'] = 1
        else:
            formatted_dict['is_ToO'] = 0

        # Convert the dict to astropy.Table
        formatted_tbl = Table()
        for key, value in formatted_dict.items():
            formatted_tbl[key] = [value]
        self.is_decoded = True
        self.formatted_data = formatted_tbl
    
    def decode_usermail(self, mail_str, match_to_tiles = True):
        # Read the alert data from the attachment
        mail_dict = dict(mail_str)
        mail_body = mail_dict['Body']

        self.alert_type = 'mail_user'
        alert_dict_normalized = self._parse_mail_string(mail_body)

        # Set/Modify the columns to the standard format
        formatted_dict = dict()
        for key, value in self.config.items():
            formatted_dict[key] = value

        # Match the RA, Dec to the RIS tiles
        if match_to_tiles:
            tile_info = self._match_RIS_tile(alert_dict_normalized['RA'], alert_dict_normalized['De'])
            if len(tile_info) == 0:
                raise ValueError(f'No matching tile found for RA = {alert_dict_normalized["RA"]}, Dec = {alert_dict_normalized["De"]}')
            objname = alert_dict_normalized['objname']
            alert_dict_normalized['objname'] = tile_info['id'][0]
            alert_dict_normalized['RA'] = tile_info['ra'][0]
            alert_dict_normalized['De'] = tile_info['dec'][0]
            alert_dict_normalized['note'] = objname
        
        # If number of exposure is not defined, divide the total exposure time by the default single exposure time (60s)
        if 'count' not in alert_dict_normalized.keys():
            alert_dict_normalized['count'] = int(alert_dict_normalized['exptime']) // self.config['exptime']
            
        # If the value of the dict is list, convert it to comma-separated string
        for key, value in alert_dict_normalized.items():
            if isinstance(value, list):
                alert_dict_normalized[key] = ','.join(value)
                
        # if space in the value, remove it
        for key, value in formatted_dict.items():
            if isinstance(value, str):
                formatted_dict[key] = value.replace(" ", "")
            
        # Update values of formatted_dict from alert_dict if the key exists
        for key in alert_dict_normalized.keys():
            formatted_dict[key] = alert_dict_normalized[key]
        
        # If is_ToO is not defined, set it to 0
        if str(formatted_dict['is_ToO']).upper() == 'TRUE':
            formatted_dict['is_ToO'] = 1
        else:
            formatted_dict['is_ToO'] = 0
        
        # Convert the dict to astropy.Table
        formatted_tbl = Table()
        for key, value in formatted_dict.items():
            formatted_tbl[key] = [value]
        
        self.is_decoded = True
        self.formatted_data = formatted_tbl

    # Read the alert data from the body
    def _parse_mail_string(self, mail_string):
        # Initialize the dictionary
        parsed_dict = {}

        # Process the string line by line
        for line in mail_string.splitlines():
            # Normalize the key and clean up the value
            key, value = self._check_required_keys_in_string(line)

            if not key:
                continue
            
            # Add to the dictionary
            normalized_key = self._normalize_required_keys(key)
            if not noramlized_key:
                raise ValueError(f'Key {key} is not found in the key variants')
            parsed_dict[normalized_key] = value

        return parsed_dict
    
    def _check_required_keys_in_string(self, line_string: str):
        """
        Check if the line contains any required keys and return the canonical key if a match is found.
        :param line_string: str, the input line to check
        :return: str, canonical key and value if a match is found; None and None otherwise
        """
        # Iterate through the dictionary to find a match
        for canonical_key, variants in self.required_key_variants.items():
            # Create a regex pattern for each variant followed by ':' or '=' or a space
            pattern = r'^\s*(' + '|'.join(re.escape(variant) for variant in variants) + r')\s*[:= ]\s*(.+)$'
            
            # Search for the pattern in the line string
            match = re.search(pattern, line_string.lower())
            if match:
                # Extract the matched key variant and the value
                key_variant = match.group(1)  # The matched key (variant)
                value = match.group(2).strip()  # The value after ':' or '=' or space
                return key_variant, value
        
        # If no match is found, return None
        return None, None
    
    def _normalize_required_keys(self, key: str):

        # Iterate through the dictionary to find a match
        for canonical_key, variants in self.required_key_variants.items():
            if key.lower() in variants:
                print(canonical_key)
                return canonical_key
        return None
    
    @property
    def required_key_variants(self):
        # Define key variants
        required_key_variants_lower = {
            'objname': ['target', 'object', 'objname', 'id'],
            'RA': ['ra', 'r.a.', 'right ascension'],
            'De': ['de', 'dec', 'dec.', 'declination'],
            'exptime': ['exptime', 'exposure', 'exposuretime', 'exposure time', 'singleframeexposure'],
            'count': ['count', 'imagecount', 'numbercount', 'image count', 'number count'],
            'obsmode': ['obsmode', 'observationmode', 'mode'],
            'binning': ['binning'],
            'gain': ['gain'],
            'priority': ['priority', 'rank'],
            'weight': ['weight'],
            'objtype': ['objtype', 'objecttype'],
            'specmode': ['specmode', 'spectralmode', 'spectral mode'],
            'filter': ['filter', 'filters', 'selectedfilters'],
            'ntelescopes': ['ntelescopes', 'ntelescope', 'numberoftelescopes', 'number of telescopes', 'selectedtelnumber'],
            'obs_starttime': ['obsstarttime', 'starttime', 'start time', 'obs_starttime'],
            'is_ToO': ['is_too', 'is too', 'abortobservation'],
            'comments': ['comment', 'comments']
        }
        return required_key_variants_lower