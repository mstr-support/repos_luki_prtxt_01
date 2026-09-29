import streamlit as st
from azure.storage.blob import BlobClient
import pandas as pd
from io import BytesIO



#######
# Helper Functions for Streamlit development
#
######



# make any grid with a function
def make_grid(cols,rows):
    grid = [0]*cols
    for i in range(cols):
        with st.container():
            grid[i] = st.columns(rows)
    return grid



# Dataframe to Excel File
def fnct_to_excel_bytes(df: pd.DataFrame) -> BytesIO:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Seite1")
    buf.seek(0)
    return buf