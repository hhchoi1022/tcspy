#!/usr/bin/env python
# coding: utf-8

#%%
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from astropy.table import Table
from astropy.io import ascii
import numpy as np
#%%
class GoogleSheet:
    """
    [History]
    =========
    (23.04.18) Written by Hyeonho Choi
    =========
    
    A class that represents a Google Sheet and provides methods for reading and writing data to it.

    Args
    ====
    spreadsheet_url (str): The URL of the Google Sheet.
    authorize_json_file (str): The path of the JSON file that contains the authorization credentials.
    scope (list): The list of OAuth2 scopes.

    Attributes
    ==========
    doc: The `gspread.models.Spreadsheet` object that represents the Google Sheet.

    Methods
    =======
    get_sheet_data(sheet_name, format_): Returns the data in the specified sheet in the specified format.
    write_sheet_data(sheet_name, data, append): Writes the data to the specified sheet, either by appending or overwriting the existing data.
    """
    
    def __init__(self,
                 spreadsheet_url : str = 'https://docs.google.com/spreadsheets/d/1KaRax8XIg7QnlZqi2XCynRb_zfYFI3zKj0z4o7X7WXg/edit#gid=0',
                 authorize_json_file : str = '../../../configuration/Google_authorize_lmd13bnd.json',
                 scope = [
                 'https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive'
                 ]
                 ):
        """
        Initializes a new instance of the GoogleSheet class.

        Args
        ==== 
        spreadsheet_url (str): The URL of the Google Sheet.
        authorize_json_file (str): The path of the JSON file that contains the authorization credentials.
        scope (list): The list of OAuth2 scopes.
        """
        
        self._url = spreadsheet_url
        self._authfile = authorize_json_file
        self._scope = scope
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self._authfile, self._scope)
        gc = gspread.authorize(credentials)
        self.doc = gc.open_by_url(self._url)
    
    def __repr__(self):
        return f'GoogleSpreadSheet(Sheetlist={self._get_sheet_list()})'
        
    def _get_sheet_list(self):
        sheet_list = [sheet.title for sheet in self.doc.worksheets()]
        return sheet_list
    
    def get_sheet_data(self,
                       sheet_name : str,
                       format_ = 'pandas' # or Table, Dict
                       ):
        """
        Returns the data in the specified sheet in the specified format.

        Args
        ====
        sheet_name (str): The name of the sheet.
        format_ (str): The format of the returned data (pandas, Table, or dict).

        Returns
        =======
        The data in the specified sheet in the specified format.
        """
        
        try:
            worksheet = self.doc.worksheet(sheet_name)
        except:
            raise AttributeError(f'{sheet_name} does not exist. Existing sheets are {self._get_sheet_list()}')
        values = worksheet.get_all_values()
        if len(values) > 0:
            if format_.upper() == 'PANDAS':
                header, rows = values[0], values[1:]
                dataframe = pd.DataFrame(rows, columns = header)
                return dataframe
            elif format_.upper() == 'TABLE':
                header, rows = values[0], values[1:]
                dataframe = pd.DataFrame(rows, columns = header)
                tbl = Table.from_pandas(dataframe)
                return tbl
            elif format_.upper() == 'DICT':
                header, rows = values[0], values[1:]
                dict_value = dict()
                dict_value['header'] = header
                dict_value['value'] = rows
                return dict_value
            else:
                raise AttributeError('Format is not matched(one among ["Pandas","Table","Dict"])')
        else:
            if format_.upper() == 'PANDAS':
                return pd.DataFrame()
            elif format_.upper() == 'TABLE':
                return Table()
            elif format_.upper() == 'DICT':
                return dict()
                
            return values
        
    def write_sheet_data(self,
                         sheet_name : str,
                         data,
                         append : bool = True,
                         clear_header : bool = False):
        """
        Writes the data to the specified sheet, either by appending or overwriting the existing data.

        Args
        ====
        sheet_name (str): The name of the sheet.
        data (pandas.DataFrame, astropy.table.Table, or dict): The data to write to the sheet.
        append (bool): Whether to append the data to the existing data or overwrite it.
        clear_header (bool): Whether to remove the header to the existing header or overwrite it.

        Raises
        ======
        AttributeError: If the format of the data is not one of pandas.DataFrame, astropy.table.Table, or dict.
        """
        
        if isinstance(data, pd.core.frame.DataFrame):
            add_data = data
        elif isinstance(data, Table):
            add_data = data.to_pandas()
        elif isinstance(data, dict):
            header = data['header']
            values = data['value']
            add_data = pd.DataFrame(values, columns = header)
        else:
            raise AttributeError('Format is not matched(one among ["Pandas","Table","Dict"])')
        if not sheet_name in self._get_sheet_list():
            self.doc.add_worksheet(sheet_name, rows = "1000", cols = "26")
        
        if not append:
            worksheet = self.doc.worksheet(sheet_name)
            if clear_header:
                self.clear_sheet(sheet_name = sheet_name, clear_header = True)
            else:
                self.clear_sheet(sheet_name = sheet_name, clear_header = False)
            original_data = self.get_sheet_data(sheet_name, format_ = 'pandas')
            appended_data = pd.concat([original_data, add_data], ignore_index=True, sort=False)
            appended_data = appended_data.replace(np.nan, '', regex=True)
            header_appended = appended_data.columns.values.tolist()
            rows_appended = appended_data.values.tolist()
            worksheet = self.doc.worksheet(sheet_name)
            worksheet.update([header_appended] + rows_appended)
        else:
            original_data = self.get_sheet_data(sheet_name, format_ = 'pandas')
            appended_data = pd.concat([original_data, add_data], ignore_index=True, sort=False)
            appended_data = appended_data.replace(np.nan, '', regex=True)
            header_appended = appended_data.columns.values.tolist()
            rows_appended = appended_data.values.tolist()
            worksheet = self.doc.worksheet(sheet_name)
            worksheet.update([header_appended] + rows_appended)
    
    def clear_sheet(self,
                    sheet_name : str,
                    clear_header : bool = False):
        worksheet = self.doc.worksheet(sheet_name)
        if clear_header:
            worksheet.clear()
        else:
            original_data = self.get_sheet_data(sheet_name, format_ = 'pandas')
            header = original_data.columns.values.tolist()
            worksheet.clear()
            worksheet.update([header])
    
    @property
    def address_sheets(self):
        address_dict = dict()
        address_dict['ccdinfo'] = 'https://docs.google.com/spreadsheets/d/1YkDkxdYxT6o4oGePELgk_MossrQWpFepeVz0NKy794s/edit#gid=0'
        address_dict['allbricqs'] = 'https://docs.google.com/spreadsheets/d/15QmTtXJodcKb238hVV_dPszupOFs2udYUNE-2ibHoQw/edit#gid=0'
        address_dict['targetlist'] = 'https://docs.google.com/spreadsheets/d/1KaRax8XIg7QnlZqi2XCynRb_zfYFI3zKj0z4o7X7WXg/edit#gid=1930204366'   
        address_dict['serverroom'] = 'https://docs.google.com/spreadsheets/d/1tg-k55hgBGZ3GFH7O6uylVBOYLXbsIgyagakYj8nQEw/edit#gid=1609450750' 
        return address_dict
    
#%%
