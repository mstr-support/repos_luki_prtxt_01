import streamlit as st
import pandas as pd
import datetime as dt
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import hashlib



# make any grid with a function
def make_grid(cols,rows):
    grid = [0]*cols
    for i in range(cols):
        with st.container():
            grid[i] = st.columns(rows)
    return grid



#
# cache DB connection to Snowflake
#


def get_connection_hash():

    # Concatenate the variables as a string
    concatenated_string = f"""
                            {st.session_state.snowflake_user}
                            {st.session_state.snowflake_password}
                            {st.session_state.snowflake_account}
                            {st.session_state.snowflake_warehouse}
                            {st.session_state.snowflake_database}
                            {st.session_state.snowflake_schema}
                            {st.session_state.snowflake_role}
                            """

    # Hash the concatenated string
    hashed_value = hashlib.sha256(concatenated_string.encode()).hexdigest()

    return hashed_value


@st.cache_resource(ttl=dt.timedelta(hours=1)) #refreshes the cached db connection after 1 hour to prevend expired auth token error
def get_db_connection(connection_hash):

    
    try:
        conn = snowflake.connector.connect(
            user=st.session_state.snowflake_user,
            password=st.session_state.snowflake_password,
            account=st.session_state.snowflake_account,
            warehouse=st.session_state.snowflake_warehouse,
            database=st.session_state.snowflake_database,
            schema=st.session_state.snowflake_schema,
            role=st.session_state.snowflake_role
            )    

        return conn
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None

#
# Check if a connection is set
#

def check_db_connection():
    # only continue if sesssion state contains the connection information
    if "snowflake_account" not in st.session_state or \
            "snowflake_user" not in st.session_state or \
            "snowflake_password" not in st.session_state or \
            "snowflake_database" not in st.session_state or \
            "snowflake_schema" not in st.session_state or \
            "snowflake_role" not in st.session_state:
        st.error("No connection information. Please save Snowflake connection information first.")
        st.stop()

    if st.session_state.snowflake_account == "" or \
            st.session_state.snowflake_user == "" or \
            st.session_state.snowflake_password == "" or \
            st.session_state.snowflake_database == "" or \
            st.session_state.snowflake_schema == "" or \
            st.session_state.snowflake_role == "":
        st.error("No connection information. Please save Snowflake connection information first.")
        st.stop()


#
# Get and save stage configuration
#



# get configured stage schema
def get_stage_config():
    try:
        conn = get_db_connection(st.session_state.connection_hash)
        
        # Your SQL query
        query = "SELECT stage_schema, LOAD_TYPE, TAGS FROM LOAD_CONFIG order by stage_schema"

        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)
        
        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None
        

# write stage config back to the database
def push_stage_config(df_stage_config):
    try:
        conn = get_db_connection(st.session_state.connection_hash)         

        # truncate table
        conn.cursor().execute("truncate table LOAD_CONFIG")

        # import data frame in empty table
        success, nchunks, nrows, _ = write_pandas(conn=conn, 
                                                df =  df_stage_config,
                                                table_name = 'LOAD_CONFIG'
                                                )
                
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None



#
# Get and save Hub load configuration
#


# get configured stage schema
def get_hub_load_config():
    try:
        conn = get_db_connection(st.session_state.connection_hash)         

        #
        # Hub Alias or Hub name is queried. -> needed for hierarchical links

        # Your SQL query
        query = """SELECT 
                stage_schema,
                stage_table,
                HUB_SCHEMA,
                hub_name,
                HUB_ALIAS,
                BK_SOURCE_COLUMN_LIST,
                SLICE_SRC_COLUMN_LIST,
                TAGS
            FROM 
                HUB_LOAD
            ORDER BY 1,2,4,5"""

        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)
       

        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None


# write stage config back to the database
def push_hub_load_config(df_hub_config):
    try:
        conn = get_db_connection(st.session_state.connection_hash)           

        # truncate table
        conn.cursor().execute("truncate table HUB_LOAD")

        # import data frame in empty table
        success, nchunks, nrows, _ = write_pandas(conn=conn, 
                                                df =  df_hub_config,
                                                table_name = 'HUB_LOAD'
                                                )
       
        
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None


#
# Get and save Sat load configuration
#


def get_sat_load_config():
    try:
        conn = get_db_connection(st.session_state.connection_hash)          

        # Your SQL query
        query = """SELECT 
                    stage_schema,
                    stage_table,
                    sat_schema,
                    SAT_NAME,
                    REFERENCED_OBJECT_NAME,
                    DELTA_HASH_SRC_COLUMN_LIST,
                    TAGS
                FROM 
                    SATELLITE_LOAD
                ORDER BY 1,2,4"""

        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)
       

        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None
    


# write stage config back to the database
def push_sat_load_config(df_sat_config):
    try:
        conn = get_db_connection(st.session_state.connection_hash)          

        # truncate table
        conn.cursor().execute("truncate table SATELLITE_LOAD")

        # import data frame in empty table
        success, nchunks, nrows, _ = write_pandas(conn=conn, 
                                                df =  df_sat_config,
                                                table_name = 'SATELLITE_LOAD'
                                                )
        
        
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None



#
# Get and save link load configuration
#

def get_link_load_config():
    try:
        conn = get_db_connection(st.session_state.connection_hash)        

        # Your SQL query
        query = """SELECT 
                    STAGE_SCHEMA,
                    stage_table,
                    link_schema,
                    LINK_NAME,
                    L_COLUMN_NAME,
                    REFERENCED_HUB_NAME_1,
                    REFERENCED_HUB_NAME_2,
                    TAGS
                FROM 
                    LINK_LOAD
                ORDER BY 1,2,4"""

        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)


        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None




# write stage config back to the database
def push_link_load_config(df_link_config):
    try:
        conn = get_db_connection(st.session_state.connection_hash)          

        # truncate table
        conn.cursor().execute("truncate table LINK_LOAD")

        # import data frame in empty table
        success, nchunks, nrows, _ = write_pandas(conn=conn, 
                                                df =  df_link_config,
                                                table_name = 'LINK_LOAD'
                                                )
        
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None



#
# Get and save transactional link load configuration
#

def get_t_link_def_config():
    try:
        conn = get_db_connection(st.session_state.connection_hash)

        # Your SQL query
        query = """SELECT 
                    STAGE_SCHEMA,
                    STAGE_TABLE,
                    LINK_SCHEMA,
                    LINK_NAME,
                    L_COLUMN_NAME,
                    TAGS
                FROM 
                    TRANS_LINK_DEF
                ORDER BY 1,2"""

        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)

        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None


# write transactional link config back to the database
def push_t_link_def_config(df_t_link_config):
    try:
        conn = get_db_connection(st.session_state.connection_hash)

        # truncate table
        conn.cursor().execute("truncate table TRANS_LINK_DEF")

        # import data frame in empty table
        success, nchunks, nrows, _ = write_pandas(conn=conn,
                                                  df=df_t_link_config,
                                                  table_name='TRANS_LINK_DEF'
                                                  )

    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None

def get_t_link_col_config():
    try:
        conn = get_db_connection(st.session_state.connection_hash)

        # Your SQL query
        query = """SELECT 
                    LINK_SCHEMA,
                    LINK_NAME,
                    SRC_COLUMN_NAME,
                    SRC_COLUMN_TYPE,
                    REFERENCED_HUB_NAME
                FROM 
                    TRANS_LINK_COLUMNS
                ORDER BY 1,2,4"""

        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)

        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None


# write transactional link config back to the database
def push_t_link_col_config(df_t_link_col_config):
    try:
        conn = get_db_connection(st.session_state.connection_hash)

        # truncate table
        conn.cursor().execute("truncate table TRANS_LINK_COLUMNS")

        # import data frame in empty table
        success, nchunks, nrows, _ = write_pandas(conn=conn,
                                                  df=df_t_link_col_config,
                                                  table_name='TRANS_LINK_COLUMNS'
                                                  )

    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None

def get_br_load_config():
    
    try:
        conn = get_db_connection(st.session_state.connection_hash)        

        # Your SQL query
        query = """SELECT 
                    *
                FROM 
                    BUSINESS_RULES
                ORDER BY 1,2,4"""

        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)


        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None



# write stage config back to the database
def push_br_load_config(df_br_config):
    try:
        conn = get_db_connection(st.session_state.connection_hash)          

        # truncate table
        conn.cursor().execute("truncate table BUSINESS_RULES")

        # import data frame in empty table
        success, nchunks, nrows, _ = write_pandas(conn=conn, 
                                                df =  df_br_config,
                                                table_name = 'BUSINESS_RULES'
                                                )
        
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None


#
# Get and save tag configuration
#

def get_tag_config():
    try:
        conn = get_db_connection(st.session_state.connection_hash)        

        # Your SQL query
        query = """SELECT 
                        TAG, 
                        TAG_DESC
                    FROM 
                        TAG_CONFIG
                    ORDER BY 1"""

        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)


        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None





# write stage config back to the database
def push_tag_config(df_tag_config):
    try:
        conn = get_db_connection(st.session_state.connection_hash)          

        # truncate table
        conn.cursor().execute("truncate table TAG_CONFIG")

        # import data frame in empty table
        success, nchunks, nrows, _ = write_pandas(conn=conn, 
                                                df =  df_tag_config,
                                                table_name = 'TAG_CONFIG'
                                                )
        
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None






#
# other helping functions to get meta information from the database
#




# get all available schemas in 
def get_all_db_schema():
    try:
        conn = get_db_connection(st.session_state.connection_hash)         

        # Your SQL query
        query = "SELECT schema_name FROM INFORMATION_SCHEMA.SCHEMATA"

        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)

        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None


# get table for a given schema
def get_tables_by_schema(schema_name):

    try:
        conn = get_db_connection(st.session_state.connection_hash)           

        # Your SQL query
        query = """SELECT 
                    table_name
                FROM 
                    INFORMATION_SCHEMA."TABLES"
                WHERE
                    --exlude stage-views
                    table_name not like 'VW_%' and
                    table_schema = '""" + schema_name + """'
                ORDER BY 1"""

        
        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)


        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None
    


# get columns from a given table
def get_columns_by_table(schema_name, table_name):

    try:
        conn = get_db_connection(st.session_state.connection_hash)        

        # Your SQL query
        query = """SELECT 
                    COLUMN_NAME
                FROM 
                    INFORMATION_SCHEMA."COLUMNS"
                WHERE 
                    table_schema = '""" + schema_name + """'
                    AND table_name =  '""" + table_name + """'
                ORDER BY 1"""

        
        # Execute the query and fetch results into a DataFrame
        df = pd.read_sql_query(query, conn)

        
        return df
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return None
