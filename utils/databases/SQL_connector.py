
#%%
import mysql.connector
from astropy.table import Table
import uuid
import mysql
import numpy as np
import time


class SQL_Connector:
    """
    A class to establish and operate a connection to a MySQL database.

    Parameters
    ----------
    id_user : str
        The user id to connect to the MySQL database.
    pwd_user : str
        The password for the given user id.
    host_user : str
        The host address for the MySQL database.
    db_name : str
        The name of the MySQL database to connect to.

    Attributes
    ----------
    connector : mysql.connector.connect
        The MySQL connector object to perform database operations.
    cursor : mysql.connector.cursor
        The MySQL cursor object to execute SQL commands.
    connected : bool
        The connection status flag.

    Methods
    -------
    connect()
        Establish a connection to the MySQL database and set the cursor.
    disconnect()
        Disconnect from the MySQL database and update the connection status flag to False.
    databases
        Lists all the databases in the MySQL connection.
    change_db(db_name)
        Change the current database to the given one and reestablish the connection.
    create_db(db_name)
        Create a new database in the MySQL connection.
    remove_db(db_name)
        Remove the specified database from the MySQL connection.
    tables
        Lists all the tables in the current database.
    remove_tbl(tbl_name)
        Remove the specified table from the current database.
    initialize_tbl(tbl_name)
        Reset the specified table in the current database.
    execute(command)
        Execute the given SQL command on the current database.
    get_colnames(tbl_name)
        Returns the column names from the specified table.
    get_column_data_types(tbl_name)
        Returns the data types for every column in the specified table.
    insert_rows(tbl_name, data)
        Insert the provided data into the specified table.
    update_row(tbl_name, update_value, update_key, id_value, id_key)
        Update a row in the specified table in the current database based on the provided criteria.
    get_data(tbl_name, select_key, where_value, where_key, out_format)
        Fetch the requested data from the specified table in the current database.
    set_data_id(tbl_name, update_all)
        Generate unique ids for all data entries in the specified table in the current database.
    """
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
        """
        Establish a connection to the MySQL database and set the cursor.
        """
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
        """
        Disconnect from the MySQL database and update the connection status flag to False.
        """
        self.connector.close()
        self.connected = False
    
    # DB operator
    
    @property
    def databases(self):
        """
        Lists all the databases in the MySQL connection.

        Returns
        -------
        list
            A list containing the names of all databases.
        """
        self.connect()
        self.exec(f"SHOW DATABASES")
        return [db_name[0] for db_name in self.cursor]
    
    def change_db(self,
                  db_name : str):
        """
        Change the current database to the given one and reestablish the connection.

        Parameters
        ----------
        db_name : str
            The name of the database to switch to.
        """
        self.db_name = db_name
        self.connect()
        
    def create_db(self,
                  db_name : str):
        """
        Create a new database in the MySQL connection.

        Parameters
        ----------
        db_name : str
            The name of the database to be created.
        """
        self.exec(f"CREATE DATABASE {db_name}")
        #print(f"DATABASE {db_name} CREATED")
    
    def remove_db(self,
                  db_name : str):
        """
        Remove the specified database from the MySQL connection.

        Parameters
        ----------
        db_name : str
            The name of the database to be removed.
        """
        self.exec(f"REMOVE DATABASE {db_name}")
        #print(f"DATABASE {db_name} REMOVED")
    
    # Table operator
    @property
    def tables(self):
        """
        Lists all the tables in the current database.

        Returns
        -------
        list
            A list containing the names of all tables in the current database.
        """
        self.exec(f"SHOW TABLES")
        return [tbl_name[0] for tbl_name in self.cursor]
        
    def remove_tbl(self,
                   tbl_name : str):
        """
        Remove the specified table from the current database.

        Parameters
        ----------
        tbl_name : str
            The name of the table to be removed.
        """
        self.exec(f"REMOVE TABLE {tbl_name} ")
        #print(f"TABLE {tbl_name} REMOVED")
        
    def get_colnames(self,
                     tbl_name : str):
        """
        Returns the column names from the specified table.

        Parameters
        ----------
        tbl_name : str
            The name of the table to get the column names from.

        Returns
        -------
        list
            A list of column names in the specified table.
        """
        self.exec(f"SHOW COLUMNS FROM {tbl_name};")
        column_names = [column[0] for column in self.cursor.fetchall()]
        return column_names
    
    def get_column_data_types(self, 
                              tbl_name: str):
        """
        Returns the data types for every column in the specified table.

        Parameters
        ----------
        tbl_name : str
            The name of the table to get the column data types from.

        Returns
        -------
        dict
            A dictionary of column names and their corresponding data types.
        """
        sql_query = f"SHOW COLUMNS FROM {tbl_name}"
        self.cursor.execute(sql_query)
        column_info = self.cursor.fetchall()
        column_data_types = {col[0]: col[1] for col in column_info}
        return column_data_types
    
    def insert_rows(self,
                    tbl_name : str,
                    data : Table):
        """
        Insert the provided data into the specified table.

        Parameters
        ----------
        tbl_name : str
            The name of the table to insert the data into.
        data : astropy.table.Table
            The Table object containing the data to be inserted into the table.

        Raises
        ------
        mysql.connector.Error
            If an error occurred during the insertion operation.
        
        
        data_str = data.copy()
        for colname in data_str.columns:
            data_str[colname] = data_str[colname].astype(str)
        if 'idx' in data_str.keys():
            data_str.remove_column('idx')

        common_colnames = [col for col in data_str.colnames if col in self.get_colnames(tbl_name)]
        placeholders = ', '.join(['%s'] * len(common_colnames))
        sql_command = f"INSERT INTO {tbl_name} ({', '.join(common_colnames)}) VALUES ({placeholders})"
        values = [tuple(row[col] if row[col] != ('None' and '') else None for col in common_colnames) for row in data_str]
        self.cursor.executemany(sql_command, values)
        self.connector.commit()
        
        """

        data_str = data.copy()
        for colname in data_str.columns:
            data_str[colname] = data_str[colname].astype(str)
        if 'idx' in data_str.keys():
            data_str.remove_column('idx')

        common_colnames = [col for col in data_str.colnames if col in self.get_colnames(tbl_name)]
        placeholders = ', '.join(['%s'] * len(common_colnames))
        sql_command = f"INSERT INTO {tbl_name} ({', '.join(common_colnames)}) VALUES ({placeholders})"
        values = [tuple(row[col] if row[col] != ('None' and '') else None for col in common_colnames) for row in data_str]
        
        insertion_results = []
        for value in values:
            try:
                self.cursor.execute(sql_command, value)
                self.connector.commit()
                insertion_results.append(True)
            except:
                insertion_results.append(False)
        return insertion_results
    
    def update_row(self,
                   tbl_name : str,
                   update_value : list or str,
                   update_key : list or str,
                   id_value : str,
                   id_key : str = 'id'
                   ):
        """
        Update a row in the specified table in the current database based on the provided criteria.

        Parameters
        ----------
        tbl_name : str
            The name of the table with the row to be updated.
        update_value : list or str
            The value or values to be updated.
        update_key : list or str
            The column name or names to be updated.
        id_value : str
            The id value of the row to be updated.
        id_key : str, optional
            The name of the column that identifies the row to be updated.

        Raises
        ------
        mysql.connector.Error
            If an error occurred during the update operation.
        """
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
            update_value = str(update_value)
            update_command = f"{update_key} = '{update_value}'"
        sql_command = f"UPDATE {tbl_name} SET {update_command} WHERE {id_key} = '{id_value}'"
        self.exec(sql_command)
        self.connector.commit()
    
    def get_data(self,
                 tbl_name : str,
                 select_key : str = '*',
                 where_value : str = None,
                 where_key : str = 'id',
                 out_format : str = 'Table' # Table or dict
                 ):
        """
        Fetch the requested data from the specified table in the current database.

        Parameters
        ----------
        tbl_name : str
            The name of the table to fetch data from.
        select_key : str
            The column names to be included in the fetched data.
        where_value : str, optional
            The condition value for fetching the data.
        where_key : str, optional
            The condition column for fetching the data.
        out_format : str, optional
            The format of the fetched data.

        Returns
        -------
        astropy.table.Table or dict
            The fetched data in the requested format.

        Raises
        ------
        mysql.connector.Error
            If an error occurred during the fetch operation.
        """
        self.connect()
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
        """
        Generate unique ids for all data entries in the specified table in the current database.

        Parameters
        ----------
        tbl_name : str
            The name of the table to set data ids.
        update_all : bool, optional
            A flag indicating whether to update all data ids.

        Raises
        ------
        mysql.connector.Error
            If an error occurred during the id setting operation.
        """
        self.connect()
        values_all = self.get_data(tbl_name = tbl_name, select_key = 'id,idx')
        values_to_update = values_all
        if not update_all:
            rows_to_update = [any(row[name] in (None, '') for name in ['id']) for row in values_all]
            values_to_update =  values_all[rows_to_update]
        uuidlist = [uuid.uuid4().hex for i in range(len(values_to_update))]
        
        for id_, index in zip(uuidlist, values_to_update['idx']):
            self.update_row(tbl_name = tbl_name, update_value = id_, update_key = 'id', id_value = index, id_key='idx')



# %%
