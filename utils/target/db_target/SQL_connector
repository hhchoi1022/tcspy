
#%%
import mysql.connector
from astropy.table import Table
#%%

class SQL_Connector:
    
    def __init__(self,
                 id_user: str = 'hhchoi',
                 pwd_user : str = 'lksdf1020',
                 host_user : str = 'localhost',
                 db_name : str = 'target'
                 ):
        self.id_user = id_user
        self.pwd_user = pwd_user
        self.host_user = host_user
        self.db_name = db_name
        self.connector = mysql.connector.connect(
        host= self.host_user,
        user=self.id_user,
        password=self.pwd_user,
        database = self.db_name
        )
        self.cursor = self.connector.cursor()
        self.exec = self.cursor.execute
    
    # DB
    def create_db(self,
                  db_name : str):
        self.exec(f"CREATE DATABASE {db_name}")
        #print(f"DATABASE {db_name} CREATED")
    
    def remove_db(self,
                  db_name : str):
        self.exec(f"REMOVE DATABASE {db_name}")
        #print(f"DATABASE {db_name} REMOVED")
    
    def show_db(self):
        self.exec(f"SHOW DATABASES")
        for db_name in self.cursor:
            pass
            #print(db_name)
    # Table 
    def create_tbl(self,
                   tbl_name : str):
        self.exec(f"CREATE TABLE {tbl_name} ")
        #print(f"TABLE {tbl_name} CREATED")

    def remove_tbl(self,
                   tbl_name : str):
        self.exec(f"REMOVE TABLE {tbl_name} ")
        #print(f"TABLE {tbl_name} REMOVED")
    
    def show_tbl(self):
        self.exec(f"SHOW TABLES")
        for tbl_name in self.cursor:
            print(tbl_name)
    
    def initialize_tbl(self,
                       tbl_name : str):
        self.exec(f"TRUNCATE TABLE {tbl_name}")
        #print(f"TABLE {tbl_name} INITIALIZED")
    
    # functions
    def execute(self,
                command : str):
        self.exec(command)
        print(f"{command} EXECUTED")
        
    def get_colnames(self,
                     tbl_name : str):
        self.exec(f"SHOW COLUMNS FROM {tbl_name};")
        column_names = [column[0] for column in self.cursor.fetchall()]
        return column_names
    
    def insert_data(self,
                    tbl_name : str,
                    data : Table
                    ):
        colnames = data.colnames
        colnames_string = ', '.join(colnames)
        dtype_list = ['%s'] * len(colnames)
        dtype_str =  ', '.join(dtype_list)
        
        sql_command = f"INSERT INTO {tbl_name} ({colnames_string}) VALUES ({dtype_str}) "

        values = data.to_pandas().to_numpy()
        list_values = [tuple(row) for row in values.tolist()]
        self.cursor.executemany(sql_command, list_values)
        self.connector.commit()
        #print(self.cursor.rowcount, "was inserted.")
    
    def update_data(self,
                    tbl_name : str,
                    update_value : str,
                    update_key : str,
                    id_value : str,
                    id_key : str = 'id'
                    ):
        sql_command = f"UPDATE {tbl_name} SET {update_key} = '{update_value}' WHERE {id_key} = '{id_value}'"
        self.exec(sql_command)
        self.connector.commit()
        #print(self.cursor.rowcount, "record(s) affected")
    
    def select_data(self,
                    tbl_name : str,
                    select_key : str,
                    where_value : str = None,
                    where_key : str = 'id'
                    ):
        keys = select_key.split(',')
        len_key = len(keys)
        sql_command = f"SELECT {select_key} FROM {tbl_name}"
        if where_value != None:
            sql_command = f"SELECT {select_key} FROM {tbl_name} WHERE {where_key} = '{where_value}'"
        self.exec(sql_command)
        output = self.cursor.fetchall()
        result = dict()
        if len_key == 1:
            result[keys[0]] = [out[0] for out in output]
        else:
            for i, key in enumerate(keys):
                result[key] = [out[i] for out in output]
        return result

    def set_data_id(self,
                    tbl_name : str):
        values = sql.select_data(tbl_name = tbl_name, select_key = 'id,idx')
        id_values = values['id']
        idx_values = values['idx']
        indices = [index for value, index in zip(id_values, idx_values) if value == '' or value is None]
        uuidlist = [uuid.uuid4().hex for i in range(len(indices))]
        for id_, index in zip(uuidlist, indices):
            self.update_data(tbl_name = tbl_name, update_value = id_, update_key = 'id', id_value = index, id_key='idx')
        
            


        
        
        
            
            
            
            
            
        
    
        
    
# %%
sql = SQL_Connector(db_name = 'target')
# %% 
from astropy.io import ascii
import uuid
#%% RIS
tbl = ascii.read('./sky-grid and tiling/7-DT/displaycenter.txt')
tbl.rename_column('id', 'objname')
tbl.rename_column('ra', 'RA')
tbl.rename_column('dec', 'De')
str_tile = tbl['objname']
objnames = []
for tilenum in str_tile:
    objname = 'Tile_' + str(tilenum).zfill(5)
    objnames.append(objname)
tbl['objname'] = objnames
#%%
sql.initialize_tbl(tbl_name = 'RIS')
#%%
sql.insert_data(tbl_name = 'RIS', data = tbl)
# %% Update data
sql.update_data(tbl_name = 'RIS', update_value = 'observed', update_key='obs_status', id_value = id_)
observed_num = sql.select_data(tbl_name = 'RIS', select_key= 'obs_number', where_value = id_)['obs_number'][0]
sql.update_data(tbl_name = 'RIS', update_value = observed_num+1, update_key='obs_number', id_value = id_)
# %% Select data
id_data = sql.select_data(tbl_name = 'Daily', select_key = 'id')['id']
# %% Set ID
sql.set_data_id('Daily')
# %%
