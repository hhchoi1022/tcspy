
#%%
import mysql.connector
from astropy.table import Table
import uuid
import mysql
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
        self.set_db(db_name = db_name)
    
    # DB
    def create_db(self,
                  db_name : str):
        self.exec(f"CREATE DATABASE {db_name}")
        #print(f"DATABASE {db_name} CREATED")
    
    def remove_db(self,
                  db_name : str):
        self.exec(f"REMOVE DATABASE {db_name}")
        #print(f"DATABASE {db_name} REMOVED")
    
    def set_db(self,
               db_name : str):
        self.db_name = db_name
        self.connector = mysql.connector.connect(
        host= self.host_user,
        user=self.id_user,
        password=self.pwd_user,
        database = self.db_name
        )
        self.cursor = self.connector.cursor()
        self.exec = self.cursor.execute
    
    def show_db(self):
        self.exec(f"SHOW DATABASES")
        for db_name in self.cursor:
            pass
            print(db_name[0])
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
            print(tbl_name[0])
    
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
        values = self.get_data(tbl_name = tbl_name, select_key = 'id,idx')
        id_values = values['id']
        idx_values = values['idx']
        if update_all:
            indices = idx_values
        else:
            indices = [index for value, index in zip(id_values, idx_values) if value == '' or value is None]
        uuidlist = [uuid.uuid4().hex for i in range(len(indices))]
        for id_, index in zip(uuidlist, indices):
            self.update_data(tbl_name = tbl_name, update_value = id_, update_key = 'id', id_value = index, id_key='idx')


# %%
