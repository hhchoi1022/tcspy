
# Table management operator
#%%
def SQL_Create_table(tblname : str = 'DB_Target'):
    sql_command = f""" CREATE TABLE {tblname}(
        id int(8) ZEROFILL NOT NULL AUTO_INCREMENT,
        name varchar(20) DEFAULT NULL,
        ra_hms varchar(20) DEFAULT NULL,
        dec_dms varchar(20) DEFAULT NULL,
        ra_hour varchar(20) DEFAULT NULL,
        dec_deg varchar(20) DEFAULT NULL,
        status varchar(20) DEFAULT NULL,
        telescope varchar(20) DEFAULT NULL,
        priority varchar(20) DEFAULT NULL,
        mode varchar(20) DEFAULT NULL,
        project varchar(20) DEFAULT NULL,
        note varchar(20) DEFAULT NULL,
        PRIMARY KEY(id)
        );
    """
    return sql_command

def SQL_Delete_table(tblname : str = 'DB_Target'):
    return f" DROP TABLE {tblname}; "

# Data management operator

def SQL_Insert_data(data : dict,
                    tblname :str = 'DB_Target'
                    ):
    import numpy as np
    keys = list(data.keys())
    keys_comma_separated = ', '.join(keys)
    all_values = np.array(list(data.values()))
    if all_values.ndim == 1:
        all_values = np.array([all_values]).T
    all_values = all_values.T
    all_values_comma_separated = ''
    for values in all_values:
        values_comma_separated = '('+', '.join(["'"+value+"'" for value in values]) +'),'
        all_values_comma_separated +=  values_comma_separated
    sql_command = f"""
    INSERT INTO {tblname}({keys_comma_separated})
    VALUES {all_values_comma_separated[:-1]};
    """
    return sql_command

def SQL_Update_data(data : dict,
                    tblname :str = 'DB_Target'
                    ):
    import numpy as np
    data = data.copy()
    if isinstance(data['id'], int):
        id = data['id']
        del data['id']
        set_command = ''
        for key, value in data.items():
            set_command += f"{key} = '{value}',"
        sql_command = f"""
            UPDATE {tblname} SET {set_command[:-1]} WHERE id = {id};
            """
        return sql_command
    ids = data['id']
    del data['id']
    keys = list(data.keys())
    all_values = np.array(list(data.values())).T
    all_sql_command = ''
    for id, values in zip(ids, all_values):
        set_command = ''
        for key, value in zip(keys, values):
            set_command += f"{key} = '{value}',"
        sql_command = f"""
            UPDATE {tblname} SET {set_command[:-1]} WHERE id = {id};
            """
        all_sql_command += sql_command
    return all_sql_command

def SQL_Reset_data(key : str,
                   value : str,
                   tblname : str = 'DB_Target'):
    sql_command = f"""
        UPDATE {tblname} SET {key} ='{value}';
        """
    return sql_command
    

#%%

#%%