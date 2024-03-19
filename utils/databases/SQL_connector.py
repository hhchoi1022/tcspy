
#%%
import mysql.connector
from astropy.table import Table
import uuid
import mysql
import numpy as np
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
        self.connect()
    
    def __repr__(self):
        txt = f"MySQL(DB = {self.db_name}, Address = {self.id_user}@{self.host_user})"
        return txt
    
    
    def connect(self):
        self.connector = mysql.connector.connect(
        host= self.host_user,
        user=self.id_user,
        password=self.pwd_user,
        database = self.db_name
        )
        self.cursor = self.connector.cursor()
        self.exec = self.cursor.execute
        self.connected = True
        
    def disconnect(self):
        self.connector.close()
        self.connected = False
    
    # DB operator
    
    @property
    def databases(self):
        self.exec(f"SHOW DATABASES")
        return [db_name[0] for db_name in self.cursor]
    
    def change_db(self,
                  db_name : str):
        self.db_name = db_name
        self.connect()
        
    def create_db(self,
                  db_name : str):
        self.exec(f"CREATE DATABASE {db_name}")
        #print(f"DATABASE {db_name} CREATED")
    
    def remove_db(self,
                  db_name : str):
        self.exec(f"REMOVE DATABASE {db_name}")
        #print(f"DATABASE {db_name} REMOVED")
    
    # Table operator

    @property
    def tables(self):
        self.exec(f"SHOW TABLES")
        return [tbl_name[0] for tbl_name in self.cursor]
        
    def remove_tbl(self,
                   tbl_name : str):
        self.exec(f"REMOVE TABLE {tbl_name} ")
        #print(f"TABLE {tbl_name} REMOVED")
    
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
    
    def get_column_data_types(self, 
                              tbl_name: str):
        sql_query = f"SHOW COLUMNS FROM {tbl_name}"
        self.cursor.execute(sql_query)
        column_info = self.cursor.fetchall()
        column_data_types = {col[0]: col[1] for col in column_info}
        return column_data_types
    
    def insert_rows(self,
                    tbl_name : str,
                    data : Table):
        data_str = data.copy()
        for colname in data_str.columns:
            data_str[colname] = data_str[colname].astype(str)
        data_str.remove_column('idx')

        common_colnames = [col for col in data_str.colnames if col in self.get_colnames(tbl_name)]
        placeholders = ', '.join(['%s'] * len(common_colnames))
        sql_command = f"INSERT INTO {tbl_name} ({', '.join(common_colnames)}) VALUES ({placeholders})"
        values = [tuple(row[col] if row[col] != 'None' else None for col in common_colnames) for row in data_str]
        self.cursor.executemany(sql_command, values)
        self.connector.commit()
    
    def update_row(self,
                   tbl_name : str,
                   update_value : list or str,
                   update_key : list or str,
                   id_value : str,
                   id_key : str = 'id'
                   ):
        
        if isinstance(update_value,str):
            update_command = f"{update_key} = '{update_value}'"
        elif isinstance(update_value, (list, np.ndarray)):
            update_command_list = []
            for i in range(len(update_value)):
                value = update_value[i]
                key = update_key [i]
                command_single = f"{key} = '{value}'"
                update_command_list.append(command_single)
            update_command = ','.join(update_command_list)
        else:
            print(f'Input type ({type(update_value)}) is not supported')
        sql_command = f"UPDATE {tbl_name} SET {update_command} WHERE {id_key} = '{id_value}'"
        self.exec(sql_command)
        self.connector.commit()
    
    def get_data(self,
                 tbl_name : str,
                 select_key : str,
                 where_value : str = None,
                 where_key : str = 'id',
                 out_format : str = 'Table' # Table or dict
                 ):
        keys = select_key.split(',')
        if select_key == '*':
            keys = self.get_colnames(tbl_name = tbl_name)
        len_key = len(keys)
        sql_command = f"SELECT {select_key} FROM {tbl_name}"
        if where_value != None:
            sql_command = f"SELECT {select_key} FROM {tbl_name} WHERE {where_key} = '{where_value}'"
        self.exec(sql_command)
        output = self.cursor.fetchall()
        if out_format.lower() == 'table':
            result = Table()
        else:
            result = dict()
        if len_key == 1:
            result[keys[0]] = [out[0] for out in output]
        else:
            for i, key in enumerate(keys):
                result[key] = [out[i] for out in output]
        return result

    def set_data_id(self,
                    tbl_name : str,
                    update_all : bool = False):
        values_all = self.get_data(tbl_name = tbl_name, select_key = 'id,idx')
        values_to_update = values_all
        if not update_all:
            rows_to_update = [any(row[name] is None for name in ['id']) for row in values_all]
            values_to_update =  values_all[rows_to_update]
        uuidlist = [uuid.uuid4().hex for i in range(len(values_to_update))]
        
        for id_, index in zip(uuidlist, values_to_update['idx']):
            self.update_row(tbl_name = tbl_name, update_value = id_, update_key = 'id', id_value = index, id_key='idx')


# %%
S = SQL_Connector()

#%%
S.databases
# %%
