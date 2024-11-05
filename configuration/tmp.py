
#%%
import json


#%%
original_data = dict()
filename = 'devicestatus.data'
for tel_num in range(20):
    tel_name = '7DT%.2d'%(tel_num+1)
    original_data[tel_name] = dict()
    original_data[tel_name]['Mount'] = dict()
    original_data[tel_name]['Focuser'] = dict()
    original_data[tel_name]['Filterwheel'] = dict()
    original_data[tel_name]['Camera'] = dict()
    original_data[tel_name]['Mount']['is_active'] = True
    original_data[tel_name]['Focuser']['is_active'] = True
    original_data[tel_name]['Filterwheel']['is_active'] = True
    original_data[tel_name]['Camera']['is_active'] = True
    original_data[tel_name]['Mount']['name'] = tel_name
    original_data[tel_name]['Focuser']['name'] = tel_name
    original_data[tel_name]['Filterwheel']['name'] = tel_name
    original_data[tel_name]['Camera']['name'] = tel_name
    original_data[tel_name]['Mount']['status'] = 'active'
    original_data[tel_name]['Focuser']['status'] = 'active'
    original_data[tel_name]['Filterwheel']['status'] = 'active'
    original_data[tel_name]['Camera']['status'] = 'active'
    
#%%
with open(filename, 'w') as f:
    json.dump(original_data, f, indent = 4)
# %%
with open(filename, 'r') as f:
    data = json.load(f) 
# %%
from astropy.time import Time
for tel_num in range(20):
    tel_name = '7DT%.2d'%(tel_num+1)
    for device_name in ['Mount', 'Focuser', 'Filterwheel', 'Camera']:
        data[tel_name][device_name]['timestamp'] = Time.now().isot[:10]
        data[tel_name][device_name]['description'] = ''
        data[tel_name][device_name]['reported_by'] = 'HyeonhoChoi'

    
# %%
with open(filename, 'w') as f:
    json.dump(data, f, indent = 4)
# %%
