

#%%
import json
from astropy.time import Time
import os
#%%

class update_focus_offset:
    
    def __init__(self, 
                 unitnum : int,
                 config_path : str = '../configuration/',
                 filtinfo_file : str = 'filtinfo.config',
                 offset_file : str = 'filter.offset'):
        self.unitnum = unitnum
        self.filtinfo_file = config_path + filtinfo_file
        self.filterinfo = self._read_json(self.filtinfo_file)
        self.offset_file = config_path + '7DT%.2d' % self.unitnum + f'/{offset_file}'
        self.is_exist_offset_file = os.path.isfile(self.offset_file)
    
    def _read_json(self, file):
        with open(file, 'r') as f:
            filtinfo_dict = json.load(f)
        return filtinfo_dict

    def _write_json(self, dict, file):
        with open(file, 'w') as f:
           json.dump(dict, f, indent = 4)
    
    def _format_offset(self,
                       list_filters : list,
                       list_offsets : list = None):
        if list_offsets == None:
            list_offsets = [999] * len(list_filters)
        elif len(list_filters) != len(list_offsets):
            raise AttributeError(f'len(list_offsets)[{len(list_filters)}] is not identical to len(list_filters)[{len(list_offsets)}]')
        format_ = dict()
        format_['updated_date'] = Time.now().isot
        for filter_, offset in zip(list_filters, list_offsets):
            format_[filter_] = offset
        return format_

    def update(self,
               list_offsets : list = None):
        filter_info = self.filterinfo['7DT%.2d' % self.unitnum]
        format_offset_file = self._format_offset(list_filters = filter_info, list_offsets = list_offsets)
        self._write_json(dict = format_offset_file, file = self.offset_file)
        print(f'{self.offset_file} is updated')
