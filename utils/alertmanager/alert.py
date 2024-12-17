
#%%
from astropy.io import ascii
from astropy.table import Table
from astropy.time import Time
import json
import re
import math
import os
from datetime import datetime
import uuid

from tcspy.utils.databases.tiles import Tiles
#%%

class Alert:
    
    def __init__(self):
        self.alert_data = None # raw data of the alert
        self.alert_type = None # mail_broker, mail_user, googlesheet, gw, table
        self.alert_sender = 'Undefined' # sender of the alert
        self.formatted_data = None # formatted data of the alert
        self.is_decoded = False # after decoding the alert data, set it to True
        self.is_inputted = False # after inputting the alert data to the scheduler, set it to True
        self.is_matched_to_tiles = False
        self.tiles = None
    
    def __repr__(self):
        txt = (f'ALERT (type = {self.alert_type}, decoded = {self.is_decoded}, inputted = {self.is_inputted})')
        return txt   
    
    @property
    def default_config(self):
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
        default_config['id'] = uuid.uuid4().hex
        return default_config
    
    def _match_RIS_tile(self, ra : list or str, dec : list or str):
        if not self.tiles:
            self.tiles = Tiles(tile_path = None)
        if not isinstance(ra, list):
            ra = [ra]
        if not isinstance(dec, list):
            dec = [dec]
        tile, matched_indices, _ = self.tiles.find_overlapping_tiles(ra, dec, visualize = False)
        return tile, matched_indices
        
    def decode_gsheet(self, tbl : Table, match_to_tiles : bool = False):
        """
        Decodes a Google Sheet and register the alert data as an astropy.Table.
        
        Parameters:
        - tbl: astropy.Table, the Google Sheet table
        
        """
        self.alert_data = {col: tbl[col].tolist() for col in tbl.colnames}
        self.alert_type = 'googlesheet'
        self.alert_sender = 'Undefined'
        
        # Set/Modify the columns to the standard format
        formatted_tbl = Table()
        for key, value in self.default_config.items():
            formatted_tbl[key] = [value] * len(tbl)
        
        # Update values from alert_data if the key exists
        for key in tbl.keys():
            noramlized_key = self._normalize_required_keys(key)
            if noramlized_key:
                formatted_tbl[noramlized_key] = tbl[key]
            else:
                print('The key is not found in the key variants: ', key)
                
        # Match the RA, Dec to the RIS tiles
        if match_to_tiles:
            self.is_matched_to_tiles = True
            tile_info, matched_indices = self._match_RIS_tile(list(formatted_tbl['RA']), list(formatted_tbl['De']))
            if len(tile_info) == 0:
                raise ValueError(f'No matching tile found for RA = {formatted_tbl["RA"]}, Dec = {formatted_tbl["De"]}')
            # Sort the formatted_tbl by the matched_indices
            formatted_tbl = formatted_tbl[matched_indices]
            objname = formatted_tbl['objname']
            formatted_tbl['objname'] = tile_info['id']
            formatted_tbl['RA'] = tile_info['ra']
            formatted_tbl['De'] = tile_info['dec']
            formatted_tbl['note'] = objname
        
        existing_columns = [col for col in self.required_key_variants.keys() if col in formatted_tbl.colnames]
        self.is_decoded = True
        self.formatted_data = formatted_tbl[existing_columns]

    def decode_tbl(self, tbl : Table, match_to_tiles : bool = False):
        """
        Decodes a Google Sheet and register the alert data as an astropy.Table.
        
        Parameters:
        - tbl: astropy.Table, the Google Sheet table
        
        """
        self.alert_data = {col: tbl[col].tolist() for col in tbl.colnames}
        self.alert_type = 'table'
        self.alert_sender = 'Undefined'
        
        # Set/Modify the columns to the standard format
        formatted_tbl = Table()
        for key, value in self.default_config.items():
            formatted_tbl[key] = [value] * len(tbl)
        
        # Update values from alert_data if the key exists
        for key in tbl.keys():
            noramlized_key = self._normalize_required_keys(key)
            if noramlized_key:
                formatted_tbl[noramlized_key] = tbl[key]
            else:
                print('The key is not found in the key variants: ', key)
                
        # Match the RA, Dec to the RIS tiles
        if match_to_tiles:
            self.is_matched_to_tiles = True
            tile_info, matched_indices = self._match_RIS_tile(list(formatted_tbl['RA']), list(formatted_tbl['De']))
            if len(tile_info) == 0:
                raise ValueError(f'No matching tile found for RA = {formatted_tbl["RA"]}, Dec = {formatted_tbl["De"]}')
            # Sort the formatted_tbl by the matched_indices
            formatted_tbl = formatted_tbl[matched_indices]
            objname = formatted_tbl['objname']
            formatted_tbl['objname'] = tile_info['id']
            formatted_tbl['RA'] = tile_info['ra']
            formatted_tbl['De'] = tile_info['dec']
            formatted_tbl['note'] = objname
        
        existing_columns = [col for col in self.required_key_variants.keys() if col in formatted_tbl.colnames]
        self.is_decoded = True
        self.formatted_data = formatted_tbl[existing_columns]

    def decode_gwalert(self, tbl : Table):
        """
        Decodes a GW alert file and register the alert data as an astropy.Table.
        
        Parameters:
        - tbl: astropy.Table, the GW alert table
        
        """
        # Read the alert data from the file
        self.alert_data = {col: tbl[col].tolist() for col in tbl.colnames}
        self.alert_type = 'gw'
        self.alert_sender = 'GECKO'
        
        # Set/Modify the columns to the standard format
        formatted_tbl = Table()
        for key, value in self.default_config.items():
            formatted_tbl[key] = [value] * len(tbl)
        
        # Update values from alert_data if the key exists         
        for key in tbl.keys():
            noramlized_key = self._normalize_required_keys(key)
            if noramlized_key:
                formatted_tbl[noramlized_key] = tbl[key]
            else:
                print('The key is not found in the key variants: ', key)

                            
        formatted_tbl['objname'] = ['T%.5d'%int(objname) if not str(objname).startswith('T') else objname for objname in formatted_tbl['objname']]
        formatted_tbl['objtype'] = 'GECKO'
        formatted_tbl['note'] = tbl['obj'] # Tile observation -> objname is stored in "Note"
        formatted_tbl['is_ToO'] = [1 if confidence <= 0.95 else 0 for confidence in tbl['confidence']]
        
        existing_columns = [col for col in self.required_key_variants.keys() if col in formatted_tbl.colnames]
        self.is_decoded = True
        self.formatted_data = formatted_tbl[existing_columns]
    
    def decode_mail(self, mail_dict, match_to_tiles = True):
        """
        Decodes a mail alert and register the alert data as an astropy.Table.
        
        Parameters:
        - mail_dict: dict, the mail dictionary
        - match_to_tiles: bool, whether to match the RA, Dec to the RIS tiles
        - alert_type: str, the alert type (broker or user)
        
        """
        # Read the alert data from the attachment
        #date_str = mail_dict['Date']
        #parsed_date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        #self.received_time = Time(parsed_date, format= 'datetime').isot

        # If Attachment is not present, read the body
        alert_dict_normalized = dict()
        if len(mail_dict['Attachments']) > 0:
            try:
                alert_data = json.load(open(mail_dict['Attachments'][0]))
                for key, value in alert_data.items():
                    normalized_key = self._normalize_required_keys(key)
                    if normalized_key:
                        alert_dict_normalized[normalized_key] = value
                    else:
                        print('The key is not found in the key variants: ', key)
                file_path = mail_dict['Attachments'][0]
            except:
                print('Error reading the alert data. Try reading the mail body')
                pass
        if not alert_dict_normalized:
            try:
                alert_dict_normalized = self._parse_mail_string(mail_dict['Body']) 
                file_path = None
            except:
                raise ValueError(f'Error reading the alert data')
        self.alert_data = alert_dict_normalized
        self.alert_type = 'gmail'
        self.alert_sender = mail_dict['From'][1]
        # If the requester is defined, set it as the alert sender, otherwise set it as the mail sender   
        if 'requester' in alert_dict_normalized.keys():
            self.alert_sender = alert_dict_normalized['requester']
        
        # Set/Modify the columns to the standard format
        formatted_dict = dict()
        for key, value in self.default_config.items():
            formatted_dict[key] = value
            
        # Update values from alert_data if the key exists
        for key in alert_dict_normalized.keys():
            formatted_dict[key] = alert_dict_normalized[key]
        
        # Match the RA, Dec to the RIS tiles
        if match_to_tiles:
            self.is_matched_to_tiles = True
            tile_info, matched_indices = self._match_RIS_tile(formatted_dict['RA'], formatted_dict['De'])
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
            
        # If specmode is defined, remove the extension
        if 'specmode' in alert_dict_normalized.keys():
            formatted_dict['specmode'] = alert_dict_normalized['specmode'].split('.')[0]        

        # Convert the dict to astropy.Table
        formatted_tbl = Table()
        for key, value in formatted_dict.items():
            formatted_tbl[key] = [value]
            
        existing_columns = [col for col in self.required_key_variants.keys() if col in formatted_tbl.colnames]
        self.is_decoded = True
        self.formatted_data = formatted_tbl[existing_columns]

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
            if not normalized_key:
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
            pattern = r'(?<!\w)[ \W]*(' + '|'.join(re.escape(variant) for variant in variants) + r')\s*[:= ]\s*(.*)$'
            
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
        # Define key variants, if a word is duplicated in the same variant, posit the word with the highest priority first
        required_key_variants_lower = {
            'requester': ['requester', 'requestor', 'requestinguser', 'requesting user', 'requesting user name'],
            'objname': ['target name', 'target', 'object', 'objname', 'id'],
            'RA': ['right ascension (ra)', 'right ascension (r.a.)', 'ra', 'r.a.'],
            'De': ['de', 'dec', 'dec.', 'declination', 'declination (dec)', 'declination (dec.)'],
            'exptime': ['exptime', 'exposure', 'exposuretime', 'exposure time', 'singleframeexposure', 'single frame exposure'],
            'count': ['count', 'imagecount', 'numbercount', 'image count', 'number count'],
            'obsmode': ['obsmode', 'observationmode', 'mode'],
            'specmode': ['specmode', 'spectralmode', 'spectral mode', 'selectedspecfile'],
            'filter': ['filter', 'filters', 'selectedfilters'],
            'ntelescopes': ['ntelescopes', 'ntelescope', 'numberoftelescopes', 'number of telescopes', 'selectedtelnumber'],
            'binning': ['binning'],
            'gain': ['gain'],
            'priority': ['priority', 'rank'],
            'weight': ['weight'],
            'objtype': ['objtype', 'objecttype'],
            'note': ['note', 'notes'],
            'comments': ['comment', 'comments'],
            'is_ToO': ['is_too', 'is too', 'abortobservation', 'abort current observation'],
            'obs_starttime': ['obsstarttime', 'starttime', 'start time', 'obs_starttime'],
            'id': ['id', 'uuid', 'uniqueid', 'unique id', 'unique identifier']
        }
        # Sort each list in the dictionary by string length (descending order)
        sorted_required_key_variants = {
            key: sorted(variants, key=len, reverse=True)
            for key, variants in required_key_variants_lower.items()
        }
        return sorted_required_key_variants
#%%
if __name__ == '__main__':
    from tcspy.utils.connector import GmailConnector
    G = GmailConnector('7dt.observation.alert@gmail.com')
    #G.login()
    mail_str = G.read_mail()
# %%
if __name__ == '__main__':
    alert = Alert()
    alert.decode_mail(mail_str[0], match_to_tiles = True, alert_type = 'broker')
    print(alert.formatted_data)

# %%
if __name__ == '__main__':
    tbl = ascii.read('/Users/hhchoi1022/code/GECKO/S240925n/SkyGridCatalog_7DT_90.csv')
#%%
