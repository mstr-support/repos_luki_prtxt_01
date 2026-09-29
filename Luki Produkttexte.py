import streamlit as st
import streamlit.components.v1 as components

from openai import OpenAI
from datetime import datetime
import pandas as pd
from io import BytesIO
import re
import json
import time

# for selling point config
from azure.storage.blob import BlobClient


#helper functions
# add helper functions if needed
import helper.luki_prtxt_fcts as fcts
import helper.luki_prtxt_prompts as prompts
import helper.luki_prtxt_helper as helper


st.set_page_config(
         layout="wide",
         page_title="[LUKI] Produkttexte",
         page_icon="images/legero_klein.png",
         initial_sidebar_state ="expanded"
               )


#
# variable declaration
#

# model select -> can be dynamic in the future with a dropbox
#gpts_modl = "gpt-5.4-mini"
gpts_modl = "gpt-5.4"
gpts_modl_transl = "gpt-6-luna"   # SAT-6 - model forr translation




#
# columns, of the Excel file
#

tab1_required_columns = [
    "Marke", "Gruppe", "Saison", "Modellnr", "Leistenbeschreibung", "Modellbeschreibung",
    "Produkttext", 
    "Geschlecht", "Produkttyp OS", "Verschluss",
    "Schuhweite", "Membrane", "Laufsohle",
    "Absatzart", "Form Schuhspitze", "Nachhaltigkeit",
    "Wechselfußbett", "Decksohle", "Futtermaterial", "Zertifikate",
    "Besonderheiten",
    ]

# requires columns for product text translation
# as the output file of product text generation
tab2_required_columns = [    
    "Modell", "Saison", "Marke", "Gruppe", "Produkttyp",    
    "Produkttext", "Response_ID", "Created_UTC", "Model",
    "Prompt_Tokens", "Completion_Tokens",
    # Leg-280
    "Selling Point 1", "Selling Point 2", "Selling Point 3",
    "Selling Point 4", "Selling Point 5",    
    ]



# requires columns for SEO Optimization have to be the same
# as the output file of product text generation
tab3_required_columns = [    
    "Modell", "Saison", "Marke", "Gruppe", "Produkttyp",    
    "Produkttext", "Response_ID", "Created_UTC", "Model",
    "Prompt_Tokens", "Completion_Tokens",
    # Leg-280
    "Selling Point 1", "Selling Point 2", "Selling Point 3",
    "Selling Point 4", "Selling Point 5",    
    ]


#
# priority for selling points config
# defines which attributes need to be checked for selling points, order defines the priority
#

selling_point_checks = [
    {"attr1": "Zertifikate",       "attr2": None},
    {"attr1": "Nachhaltigkeit",    "attr2": None},
    {"attr1": "Membrane",          "attr2": None},
    {"attr1": "Wechselfußbett",    "attr2": "Decksohle"},
    {"attr1": "Futtermaterial",    "attr2": None},
    {"attr1": "Schuhweite",        "attr2": None},
    {"attr1": "Laufsohle",          "attr2": None},
    {"attr1": "Absatzart",          "attr2": None},
    {"attr1": "Verschluss",          "attr2": None}
]

# which SP config column is used for selling point lookup
SP_TEXT_COL = "Selling Point Text (DE)"



#
# selling point functions - both functions are needed to
# determin selling point texts for all configered attributes
#

# single function to determin a selling point text for a single attribute combination
def fnct_selling_point(
    attribut1: str,
    wert1: str,    
    marke: str = None,
    attribut2: str = None,
    wert2: str = None
):
    
    # Testausgabe    
    #st.write("attr1:",attribut1)
    #st.write("val1_str:",wert1)
    #st.write("attr2:",attribut2)
    #st.write("val2_str:",wert2)
    

    # load Selling point Excel file if not yet done    
    if "tab5_df" not in st.session_state:
        try:
            tab5_df = pd.read_excel(st.secrets["AZURE_BLOB_URL"], engine="openpyxl")
            st.session_state.tab5_df = tab5_df
        except Exception as e:
            st.error(f"Fehler beim Laden der Datei: {e}")
            st.stop()

    #
    # general filters
    #
   

    # filter selling point data only for relevant rows
    df_sp = st.session_state.tab5_df[st.session_state.tab5_df["Relevant"].astype(str).str.strip().str.upper() == "J"].copy()
   

    # filter for Marke
    marke_str = str(marke).strip().upper()

    df_sp = df_sp[
        df_sp["Marke"].astype(str).str.strip().str.upper().isin(["ALLE", marke_str])
    ]


    #
    # differ between different lookups
    # 1 -> map only Attribute 1
    # 2 -> map Attribute 1 and Attribute 2
    #

    if attribut2 is None:

        wert1_str = str(wert1).strip()

        # simple lookup via attribute 1
        df_sp_filtered = df_sp[
            (df_sp["Attribut 1"].astype(str).str.strip() == attribut1) &
            (df_sp["Wert 1"].astype(str).str.strip().str.lower() == wert1_str.lower())
        ]       


    else:

        wert1_str = str(wert1).strip()
        wert2_str = str(wert2).strip() if pd.notna(wert2) else ""

        # lookup for both attribute (e.g. for Wechselfußbet)
        df_sp_filtered = df_sp[
            (df_sp["Attribut 1"].astype(str).str.strip() == attribut1) &
            (df_sp["Wert 1"].astype(str).str.strip().str.lower() == wert1_str.lower()) &
            (df_sp["Attribut 2"].astype(str).str.strip() == attribut2) &
            (df_sp["Wert 2"].astype(str).str.strip().str.lower() == wert2_str.lower())
        ]


    # return first selling point text of filtered dataframe (if there's data)
    if len(df_sp_filtered) > 0:
        return str(df_sp_filtered.iloc[0][SP_TEXT_COL]).strip()
    else:
        return None


# Function to loop over selling point config
def fnct_selling_points(row: pd.Series, marke: str) -> dict:
    results = []


    # loop over config
    for check in selling_point_checks:
        if len(results) >= 5:
            # if already 5 selling points reached, stop
            break
        
        # get attributes based on config
        attr1 = check["attr1"]
        attr2 = check["attr2"]

        if attr1 not in row.index:
            continue

        val1 = row[attr1]

        if pd.isna(val1) or str(val1).strip() in ["", "nan"]:
            continue

        val1_str = str(val1).strip()
        val2     = row[attr2] if (attr2 and attr2 in row.index) else None
        val2_str = str(val2).strip()

        # call selling point logic for attribute combination
        sp_text = fnct_selling_point(
            attribut1=attr1,
            wert1=val1_str,
            marke=marke,
            attribut2=attr2,
            wert2=val2
        )

     
        # check if selling point text exists
        # if sp_text and sp_text != val1_str: -> was changed with LEG-260           
        # LEG-260 'ja' and 'nein' explizit filtered
        if sp_text:            

            # LEG-260
            # Wenn Wechselfußbett = "Ja", dann Nachhaltigkeits-Selling-Points,
            # die die Decksohle erwähnen, ignorieren
            wfb = row["Wechselfußbett"] if "Wechselfußbett" in row.index else None
            if (
                attr1 == "Nachhaltigkeit"
                and pd.notna(wfb)
                and str(wfb).strip().lower() == "ja"
                and "decksohle" in sp_text.lower()
            ):
                continue

            results.append(sp_text)
                
 
    while len(results) < 5:
        # at empty text, if no 5 selling points exist
        results.append("")

    return {f"Selling Point {i+1}": results[i] for i in range(5)}


#
# functions to load 

@st.cache_data(ttl=86400)  # TTL so that the data is forced to reload, when data is updated daily
def load_artv_data():
    return pd.read_excel(st.secrets["AZURE_BLOB_URL_ARTV"], engine="openpyxl")



# build config for authenticator
# -> not needed here



# 
# side bar configuration
#



#
# tab definition
#


st.title("[LUKI] Produkttexte")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Produkttexte", "Produkttexte-Übersetzungen",
                                        "SEO-Optimierung", "SEO-Übersetzungen",
                                        "Selling Points Config"])


#
# content
#

# session variables are needed for both tabs

# check session variables for product , whether a generation was already done
if "tab1_generation_done" not in st.session_state:
    st.session_state.tab1_generation_done = False
if "tab1_df_output_data" not in st.session_state:
    st.session_state.tab1_df_output_data = None
if "tab1_imported_file_name" not in st.session_state:
    st.session_state.tab1_imported_file_name = None
if "tab1_timing" not in st.session_state:
    st.session_state.tab1_timing = None


# check session variables for translation of product texts
if "tab2_generation_done" not in st.session_state:
    st.session_state.tab2_generation_done = False
if "tab2_df_output_data" not in st.session_state:
    st.session_state.tab2_df_output_data = None
if "tab2_imported_file_name" not in st.session_state:
    st.session_state.tab2_imported_file_name = None
if "tab2_timing" not in st.session_state:
    st.session_state.tab2_timing = None


# check session variables for SOE , whether a generation was already done
if "tab3_generation_done" not in st.session_state:
    st.session_state.tab3_generation_done = False
if "tab3_df_output_data" not in st.session_state:
    st.session_state.tab3_df_output_data = None
if "tab3_imported_file_name" not in st.session_state:
    st.session_state.tab3_imported_file_name = None
if "tab3_timing" not in st.session_state:
    st.session_state.tab3_timing = None


# logo on page right
#col1, col2 = st.columns([4, 1])  # links mehr Platz, rechts kleiner
#with col2:
#    st.image("images/logo_large_leg.png", width=200)





####
# 
# 1st tab for product text generation
#
#

with tab1:

    with st.expander("Information"):
                

                st.markdown("""
                    <p>
                    Willkommen in der App zur automatischen Erstellung von Produkttexten. Diese wurde im Rahmen des LUKI-Projektes erstellt und generiert automatisch Texte für Modelle. 
                    Unter "Upload File" kannst du die zu verarbeitenden Modelle hochladen, das Excel muss dem Format des IPIM-Exportes "ipim_datenfeed" entsprechen. Die Verarbeitung in der App dauert einige Sekunden bis Minuten.
                    </p> <p>                 
                    Bitte lade während der Testphase nicht mehr als 50 Modelle auf einmal hoch. 
                    </p> <p>
                    Viel Spaß!</p> <p> </p>
                    Robert
                    <p> </p>
                    """, unsafe_allow_html=True)
                

    # upoad butte for Excel file
    tab1_uploaded_file = st.file_uploader("Hier IPIM-Datenfeed uploaden. Datei muss auf Modellebene sein", accept_multiple_files=False, type=["xlsx", "xls", "csv"])

    # empty data frame for data
    tab1_df_org_data = None
    tab1_df_output_data = None

    if tab1_uploaded_file:
        st.markdown(f"**Dateiname:** `{tab1_uploaded_file.name}`")

        # check if the file is still the same like in the session state
        # -> file is always transformed to data frame of the code
        if st.session_state.tab1_imported_file_name != tab1_uploaded_file.name:
            # file name changed -> new generation
            st.session_state.tab1_generation_done = False

        try:
            # CSV einlesen
            if tab1_uploaded_file.name.lower().endswith(".csv"):
                tab1_df_org_data = pd.read_csv(tab1_uploaded_file)
                st.success("CSV erfolgreich geladen.")

            # Read always first sheet of Excelfile
            else:
                tab1_df_org_data = pd.read_excel(tab1_uploaded_file, sheet_name=0, engine="openpyxl")
                st.success("Excel (erstes Tabellenblatt) erfolgreich geladen.")

            st.session_state.tab1_imported_file_name = tab1_uploaded_file.name

            # records with already existing Produkttext are filtered
            tab1_df_org_data = tab1_df_org_data[tab1_df_org_data["Produkttext"].isna()]

            # reset index after drop of rows
            tab1_df_org_data = tab1_df_org_data.reset_index(drop=True)

        except Exception as e:
            st.error(f"Fehler beim Einlesen: {e}")

    else:
        st.info("Bitte eine Datei hochladen.")


    #
    # site will just continue if data was read from Excel
    #

    if tab1_df_org_data is not None:

        # check for errors
        col_error = False

        for col in tab1_required_columns:
            if col not in tab1_df_org_data.columns:
                st.error("Folgende Spalte fehlt in der Excel-Datei: " + col)
                col_error = True


        # check for duplicate Modellnr entries
        if "Modellnr" in tab1_df_org_data.columns:
            if tab1_df_org_data["Modellnr"].duplicated().any():
                st.error("Modelle nicht eindeutig, bitte Datei prüfen")
                col_error = True


        # check if still data in dataframe after filterung for empty Produkttexte
        if len(tab1_df_org_data) == 0:
            st.error("Alle Produkttexte in hochgeladener Datei bereits befüllt.")
            col_error = True

        # stop generation if a error in the data was recognized
        if col_error == True:
            st.stop()




        st.dataframe(tab1_df_org_data)

        # check if generation was already done before and
        # take data from last execution
        if st.session_state.tab1_generation_done == True:
            tab1_df_output_data = st.session_state.tab1_df_output_data
        

        # button to start generation of produkttexte
        if st.button("Produkttexte generieren"):

            # initialisierung
            client = OpenAI(api_key=st.secrets["OPAI_KEYS"])
            rows_indx = 0
            list_output_data = []

            # Zeitmessung: Ergebnisse pro Schritt werden hier gesammelt
            tab1_timing_records = []

            
            
            # loop
            tab1_step1_start = time.perf_counter()
            tab1_step1_total = len(tab1_df_org_data.index)
            tab1_step1_progress = st.empty()
            with st.spinner("Produkttexte werden generiert...", show_time=True):

                for tab1_step1_i, rows_indx in enumerate(tab1_df_org_data.index, start=1):

                    tab1_step1_progress.text(f"Produkttexte generieren: {tab1_step1_i} von {tab1_step1_total}")
                            
                    #st.write(rows_indx)

                    inpt_vatr = ", ".join(
                        f"{col}: {val}"
                        for col, val in {

                            # base values are taken or changed
                            "Produktname": tab1_df_org_data.loc[rows_indx, "Gruppe"],
                            "Leistenbeschreibung": tab1_df_org_data.loc[rows_indx, "Leistenbeschreibung"],                             
                            "Modellbeschreibung": tab1_df_org_data.loc[rows_indx, "Modellbeschreibung"],     
                            "Produkttyp": fcts.fnct_ptyp(tab1_df_org_data.loc[rows_indx, "Produkttyp OS"]),                            
                            "Geschlecht": fcts.fnct_gesl(tab1_df_org_data.loc[rows_indx, "Marke"], tab1_df_org_data.loc[rows_indx, "Geschlecht"]),
                            "Verschluss": fcts.fnct_vrsl(tab1_df_org_data.loc[rows_indx, "Verschluss"]),
                            "Laufsohleneigenschaften": fcts.fnct_lfso(tab1_df_org_data.loc[rows_indx, "Saison"], tab1_df_org_data.loc[rows_indx, "Laufsohle"], tab1_df_org_data.loc[rows_indx, "Marke"]),
                            #"Profil Laufsohle": fnct_pfls(dafr_inpt.loc[rows_indx, "Profil Laufsohle"]),

                            "Nachhaltigkeit": tab1_df_org_data.loc[rows_indx, "Nachhaltigkeit"],
                            "Membrane": tab1_df_org_data.loc[rows_indx, "Membrane"],
                            "Futtermaterial": tab1_df_org_data.loc[rows_indx, "Futtermaterial"],                        
                            "Schuhweite": tab1_df_org_data.loc[rows_indx, "Schuhweite"],   
                            "Einlegesohle": fcts.fnct_wfub(tab1_df_org_data.loc[rows_indx, "Wechselfußbett"]),
                            "Besonderheiten": tab1_df_org_data.loc[rows_indx, "Besonderheiten"]
                            
                            # Logic from Leg-258 zurückgebaut - muss raus, wenn das so passt
                            # info aus selling point config lookup wird nicht mehr in die Spalte
                            # sonder in selling point spalte geschrieben.
                            #"Nachhaltigkeit": fnct_selling_point(
                            #    'Nachhaltigkeit',
                            #    tab1_df_org_data.loc[rows_indx, "Nachhaltigkeit"],
                            #    tab1_df_org_data.loc[rows_indx, "Marke"]
                            #    ),
                            #"Membrane": fnct_selling_point(
                            #    'Membrane',
                            #    tab1_df_org_data.loc[rows_indx, "Membrane"],
                            #    tab1_df_org_data.loc[rows_indx, "Marke"]
                            #    ),                            
                            #"Futtermaterial": fnct_selling_point( 
                            #    'Futtermaterial',
                            #    tab1_df_org_data.loc[rows_indx, "Futtermaterial"],
                            #    tab1_df_org_data.loc[rows_indx, "Marke"]
                            #    ),                     
                            #"Schuhweite": fnct_selling_point(
                            #   'Schuheweite', 
                            #    tab1_df_org_data.loc[rows_indx, "Schuhweite"],   
                            #    tab1_df_org_data.loc[rows_indx, "Marke"]
                            #),
                            # Alte Logik für Einlegesohle
                            # "Einlegesohle": fnct_wfub(tab1_df_org_data.loc[rows_indx, "Wechselfußbett"])     
                            #"Einlegesohle": fnct_selling_point(
                            #    "Wechselfußbett",
                            #    tab1_df_org_data.loc[rows_indx, "Wechselfußbett"],                                
                            #    tab1_df_org_data.loc[rows_indx, "Marke"],
                            #    "Decksohle",                       
                            #    tab1_df_org_data.loc[rows_indx, "Decksohle"]
                            #)                                                                       
                        }.items()
                        if pd.notna(val) and str(val).strip() != ""
                    )

                    # get Marke to differ between Kids and normal shoes
                    marke = str(tab1_df_org_data.loc[rows_indx, "Marke"]).strip().upper()
                    
                    # choose input prompt based on Marke
                    if marke.startswith("SUPERFIT"):
                        active_prompt = prompts.inpt_prmt_kids
                    else:
                        active_prompt = prompts.inpt_prmt

                    final_prompt = f"""
                    {active_prompt}                
                    Attribute:
                    {inpt_vatr}
                    """

                    #st.write(final_prompt)

                    response = client.chat.completions.create(
                        model=gpts_modl,
                        messages=[
                            {"role": "system", "content": "Du bist ein erfahrener Werbetexter für Schuhe."},
                            {"role": "user", "content": final_prompt}
                        ],
                        temperature=0.5

                        # tokens not needed for 5.2 model
                        #max_tokens=1200
                    )

                    #print(f"\n--- Zeile {rows_indx + 1} ---")
                    #print(response.choices[0].message.content)
                    text_output = response.choices[0].message.content  

                    # Gore Tex in Ergebnis anpassen
                    text_output = fcts.fnct_ptxt(text_output)

                    modl = tab1_df_org_data["Modellnr"].iloc[rows_indx]
                    
                    # added with LEG-258
                    saison      = tab1_df_org_data["Saison"].iloc[rows_indx]
                    marke       = tab1_df_org_data["Marke"].iloc[rows_indx]
                    gruppe      = tab1_df_org_data["Gruppe"].iloc[rows_indx]                    
                    produkttyp  = tab1_df_org_data["Produkttyp OS"].iloc[rows_indx]

                                      
                    # get selling point texts
                    selling_points = fnct_selling_points(
                                            row=tab1_df_org_data.loc[rows_indx],
                                            marke=tab1_df_org_data.loc[rows_indx, "Marke"]
                                            )
                    
                    
                   
                    list_output_data.append({
                        "Modell": modl,
                        # LEG-258
                        "Saison": saison,
                        "Marke": marke, 
                        "Gruppe": gruppe,
                        "Produkttyp": produkttyp,                        
                        ##
                        "Produkttext": text_output,
                        ## Leg-260
                        "Selling Point 1":   selling_points["Selling Point 1"],
                        "Selling Point 2":   selling_points["Selling Point 2"],
                        "Selling Point 3":   selling_points["Selling Point 3"],
                        "Selling Point 4":   selling_points["Selling Point 4"],
                        "Selling Point 5":   selling_points["Selling Point 5"],
                        #
                        "Response_ID": response.id,
                        "Created_UTC": datetime.fromtimestamp(response.created).strftime("%d.%m.%Y %H:%M:%S"),
                        "Model": response.model,
                        "Prompt_Tokens": response.usage.prompt_tokens,
                        "Completion_Tokens": response.usage.completion_tokens
                    })

                    print(rows_indx, datetime.fromtimestamp(response.created).strftime("%d.%m.%Y %H:%M:%S"))
                    rows_indx += 1

            tab1_step1_elapsed = time.perf_counter() - tab1_step1_start
            tab1_step1_count = len(list_output_data)
            tab1_timing_records.append({
                "Schritt": "1. Produkttexte generieren",
                "Anzahl": tab1_step1_count,
                "Gesamtzeit (s)": round(tab1_step1_elapsed, 2),
                "Ø Zeit/Element (s)": round(tab1_step1_elapsed / tab1_step1_count, 2) if tab1_step1_count else 0,
            })

            
            tab1_df_output_data = pd.DataFrame(list_output_data, columns=[
                "Modell", "Saison", "Marke", "Gruppe", "Produkttyp",                    
                "Selling Point 1", "Selling Point 2", "Selling Point 3",
                "Selling Point 4", "Selling Point 5",
                "Produkttext", "Response_ID", "Created_UTC", "Model",
                "Prompt_Tokens", "Completion_Tokens"
            ])
            


            # review the gernerated product 
            tab1_step2_start = time.perf_counter()
            tab1_step2_total = len(tab1_df_output_data.index)
            tab1_step2_progress = st.empty()
            with st.spinner("Produkttexte werden nachbearbeitet...", show_time=True):

                # empty lists to store information of second loop
                reviewed_texts = []
                review_response_ids = []
                review_created_utc = []
                review_models = []
                review_prompt_tokens = []
                review_completion_tokens = []

                # loop over every generated row
                for tab1_step2_i, idx in enumerate(tab1_df_output_data.index, start=1):

                    tab1_step2_progress.text(f"Produkttexte nachbearbeiten: {tab1_step2_i} von {tab1_step2_total}")

                    original_text = tab1_df_output_data.loc[idx, "Produkttext"]

                    review_prompt = f"""
                    {prompts.inpt_prmt_review}

                    Text:
                    {original_text}
                    """

                    review_response = client.chat.completions.create(
                        model=gpts_modl,
                        messages=[
                            {"role": "system", "content": "Du überarbeitest Produkttexte sorgfältig und in natürlichem Deutsch."},
                            {"role": "user", "content": review_prompt}
                        ],
                        temperature=0.7
                    )

                    # Gore Tex in Ergebnis anpassen
                    reviewed_text = review_response.choices[0].message.content
                    reviewed_text = fcts.fnct_ptxt(reviewed_text)

                    # add results to lists
                    reviewed_texts.append(reviewed_text)
                    review_response_ids.append(review_response.id)
                    review_created_utc.append(datetime.fromtimestamp(review_response.created).strftime("%d.%m.%Y %H:%M:%S"))
                    review_models.append(review_response.model)
                    review_prompt_tokens.append(review_response.usage.prompt_tokens)
                    review_completion_tokens.append(review_response.usage.completion_tokens)

                    

            tab1_step2_elapsed = time.perf_counter() - tab1_step2_start
            tab1_step2_count = len(reviewed_texts)
            tab1_timing_records.append({
                "Schritt": "2. Produkttexte nachbearbeiten",
                "Anzahl": tab1_step2_count,
                "Gesamtzeit (s)": round(tab1_step2_elapsed, 2),
                "Ø Zeit/Element (s)": round(tab1_step2_elapsed / tab1_step2_count, 2) if tab1_step2_count else 0,
            })

            # LEG-256 final consolidation if review round
            # only result text of review is taken
            # used tokens are summed up

            tab1_df_output_data["Produkttext"] = reviewed_texts
            # LEG-258 Länge des Produkttextes eingefügt
            tab1_df_output_data["Länge()"] = tab1_df_output_data["Produkttext"].str.len()
            tab1_df_output_data["Response_ID"] = review_response_ids
            tab1_df_output_data["Created_UTC"] = review_created_utc
            tab1_df_output_data["Model"] = review_models
            
            tab1_df_output_data["Prompt_Tokens"] = (
                tab1_df_output_data["Prompt_Tokens"] + pd.Series(review_prompt_tokens)
            )
            tab1_df_output_data["Completion_Tokens"] = (
                tab1_df_output_data["Completion_Tokens"] + pd.Series(review_completion_tokens)
            )

            # save current result in session state
            st.session_state.tab1_df_output_data = tab1_df_output_data
            st.session_state.tab1_generation_done = True
            st.session_state.tab1_timing = tab1_timing_records

        
        if tab1_df_output_data is not None:

            # write output
            st.success("Produkttexte erfolgreich generiert.")

            # Zeitmessung anzeigen
            if st.session_state.tab1_timing:
                tab1_timing_df = pd.DataFrame(st.session_state.tab1_timing)
                if not tab1_timing_df.empty and "Gesamtzeit (s)" in tab1_timing_df.columns:
                    st.markdown("**Zeitmessung**")
                    gesamt_zeit = tab1_timing_df["Gesamtzeit (s)"].sum()
                    st.dataframe(tab1_timing_df, hide_index=True)
                    st.caption(f"Gesamtdauer aller Schritte: {round(gesamt_zeit, 2)} Sekunden")

            st.dataframe(tab1_df_output_data.drop('Produkttext',axis=1))

            # prepare Excel Download
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                tab1_df_output_data.to_excel(writer, index=False, sheet_name="Seite1")
            buffer.seek(0)

            # create timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"Produkttexte_{timestamp}.xlsx"

            # Download button
            st.download_button(
                label="Als Excel herunterladen",
                data=buffer,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )




####
# 
# 2nd Tab for product text translation - SAT6
#
#


with tab2:

    with st.expander("Information"):
                

        st.markdown("""
            <p>
            Hier kannst du die englischen Übersetzungen für die Produkttexte erstellern. 
            Lade dazu die im ersten Reiter erstellte Datei hoch.
            """, unsafe_allow_html=True)

    # Upload Produkttext file from 1st tab
    tab2_uploaded_file = st.file_uploader(
        "Datei aus dem Reiter „Produkttexte“ hochladen",
        accept_multiple_files=False,
        type=["xlsx", "xls", "csv"],
        key="tab2_uploader"
    )

    tab2_df_org_data = None
    tab2_df_output_data = None

    if tab2_uploaded_file:
        st.markdown(f"**Dateiname:** `{tab2_uploaded_file.name}`")

        # new file -> discard old results
        if st.session_state.tab2_imported_file_name != tab2_uploaded_file.name:
            st.session_state.tab2_generation_done = False
            st.session_state.tab2_df_output_data = None
            st.session_state.tab2_timing = None

        try:
            if tab2_uploaded_file.name.lower().endswith(".csv"):
                tab2_df_org_data = pd.read_csv(tab2_uploaded_file)
                st.success("CSV erfolgreich geladen.")
            else:
                tab2_df_org_data = pd.read_excel(tab2_uploaded_file, sheet_name=0, engine="openpyxl")
                st.success("Excel (erstes Tabellenblatt) erfolgreich geladen.")

            st.session_state.tab2_imported_file_name = tab2_uploaded_file.name

        except Exception as e:
            st.error(f"Fehler beim Einlesen: {e}")
    else:
        st.info("Bitte eine Datei hochladen.")


    # check if Excel file was readd
    if tab2_df_org_data is not None:

        # all required columns exist?
        tab2_col_error = False
        for col in tab2_required_columns:
            if col not in tab2_df_org_data.columns:
                st.error("Folgende Spalte fehlt in der Excel-Datei: " + col)
                tab2_col_error = True

        # there's data in the file
        if len(tab2_df_org_data) == 0:
            st.error("Die hochgeladene Datei enthält keine Datensätze.")
            tab2_col_error = True


        if not tab2_col_error:

            st.dataframe(tab2_df_org_data)

            if st.session_state.tab2_generation_done:
                tab2_df_output_data = st.session_state.tab2_df_output_data

            if st.button("Übersetzungen generieren", key="tab2_translate_button"):

                client = OpenAI(api_key=st.secrets["OPAI_KEYS"])
                tab2_output_rows = []

                tab2_step1_start = time.perf_counter()
                tab2_step1_total = len(tab2_df_org_data.index)
                tab2_step1_progress = st.empty()

                with st.spinner("Produkttexte werden übersetzt...", show_time=True):
                    for tab2_step1_i, idx in enumerate(tab2_df_org_data.index, start=1):

                        tab2_step1_progress.text(f"Übersetzen: {tab2_step1_i} von {tab2_step1_total}")

                        row = tab2_df_org_data.loc[idx]

                        # collect German texts, empty ones are not translated
                        de_texts = {
                            col: ("" if pd.isna(row[col]) else str(row[col]).strip())
                            for col in tab2_required_columns
                        }
                        payload = {k: v for k, v in de_texts.items() if v}

                        en_texts = {col: "" for col in tab2_required_columns}
                        resp_id = created = model = None
                        prompt_tokens = completion_tokens = None

                        if payload:
                            try:
                                transl_prompt = (
                                    f"{prompts.inpt_prmt_translation}\n\n"
                                    "Gib ausschließlich ein JSON-Objekt mit exakt denselben Schlüsseln "
                                    "wie im Input zurück, die Werte sind die englischen Übersetzungen. "
                                    "Keine Erklärungen.\n\n"
                                    f"Input:\n{json.dumps(payload, ensure_ascii=False)}"
                                )

                                response = client.chat.completions.create(
                                    model=gpts_modl_transl,
                                    messages=[
                                        {"role": "system", "content": "Du übersetzt Produkttexte für Schuhe sorgfältig ins Englische."},
                                        {"role": "user", "content": transl_prompt}
                                    ],
                                    response_format={"type": "json_object"}
                                )

                                raw = response.choices[0].message.content
                                parsed = json.loads(re.sub(r"```json|```", "", raw).strip())

                                for col in payload:
                                    if col in parsed:
                                        en_texts[col] = str(parsed[col]).strip()

                                resp_id           = response.id
                                created           = datetime.fromtimestamp(response.created).strftime("%d.%m.%Y %H:%M:%S")
                                model             = response.model
                                prompt_tokens     = response.usage.prompt_tokens
                                completion_tokens = response.usage.completion_tokens

                            except Exception as e:
                                st.error({"Modell": row["Modell"], "Fehler": str(e)})

                        # output row: first 5 columns, DE/EN pairs, then metadata of the new call
                        out = {}
                        for col in ["Modell", "Saison", "Marke", "Gruppe", "Produkttyp"]:
                            out[col] = row[col]

                        for col in tab2_required_columns:
                            out[f"{col} (DE)"] = de_texts[col]
                            out[f"{col} (EN)"] = en_texts[col]

                        out["Response_ID"]       = resp_id
                        out["Created_UTC"]       = created
                        out["Model"]             = model
                        out["Prompt_Tokens"]     = prompt_tokens
                        out["Completion_Tokens"] = completion_tokens
                        out["Länge()"]           = len(en_texts["Produkttext"])

                        tab2_output_rows.append(out)

                tab2_step1_elapsed = time.perf_counter() - tab2_step1_start
                tab2_step1_count = len(tab2_output_rows)

                tab2_df_output_data = pd.DataFrame(tab2_output_rows)

                st.session_state.tab2_df_output_data = tab2_df_output_data
                st.session_state.tab2_timing = [{
                    "Schritt": "1. Produkttexte übersetzen",
                    "Anzahl": tab2_step1_count,
                    "Gesamtzeit (s)": round(tab2_step1_elapsed, 2),
                    "Ø Zeit/Element (s)": round(tab2_step1_elapsed / tab2_step1_count, 2) if tab2_step1_count else 0,
                }]
                st.session_state.tab2_generation_done = True

            if tab2_df_output_data is not None:
                st.success("Übersetzungen erfolgreich generiert.")

                if st.session_state.tab2_timing:
                    tab2_timing_df = pd.DataFrame(st.session_state.tab2_timing)
                    st.markdown("**Zeitmessung**")
                    st.dataframe(tab2_timing_df, hide_index=True)
                    st.caption(f"Gesamtdauer: {round(tab2_timing_df['Gesamtzeit (s)'].sum(), 2)} Sekunden")

                st.dataframe(tab2_df_output_data)

                st.download_button(
                    label="Als Excel herunterladen",
                    data=helper.fnct_to_excel_bytes(tab2_df_output_data),
                    file_name=f"Produkttexte_translated_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="tab2_download_button"
                )


                #
                # section 2: IPIM import files (from the currently generated data)
                #
                st.divider()
                st.subheader("IPIM-Import-Dateien erstellen")
                st.markdown(
                    "Wenn du mit den Übersetzungen zufrieden bist, lade die Datei hier hoch, "
                    "damit die entsprechenden Importdateien für IPIM erstellt werden."
                )

                # column mapping per language: column in output -> column in IPIM file
                ipim_cols_de = {
                    "Saison": "Saison", "Marke": "Marke", "Gruppe": "Gruppe",
                    "Modell": "Modellnummer", "Produkttext (DE)": "Haupttext DE",
                    **{f"Selling Point {i} (DE)": f"Selling Point {i}" for i in range(1, 6)},
                }
                ipim_cols_en = {
                    "Saison": "Saison", "Marke": "Marke", "Gruppe": "Gruppe",
                    "Modell": "Modellnummer", "Produkttext (EN)": "Haupttext EN",
                    **{f"Selling Point {i} (EN)": f"Selling Point {i}" for i in range(1, 6)},
                }

                # only needed columns, in the defined order
                df_ipim_de = tab2_df_output_data[list(ipim_cols_de)].rename(columns=ipim_cols_de)
                df_ipim_en = tab2_df_output_data[list(ipim_cols_en)].rename(columns=ipim_cols_en)

                col_de, col_en = st.columns(2)
                with col_de:
                    st.download_button(
                        label="Produkttexte_IPIM_Upload_DE herunterladen",
                        data=helper.fnct_to_excel_bytes(df_ipim_de),
                        file_name="Produkttexte_IPIM_Upload_DE.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="tab2_ipim_download_de"
                    )
                with col_en:
                    st.download_button(
                        label="Produkttexte_IPIM_Upload_EN herunterladen",
                        data=helper.fnct_to_excel_bytes(df_ipim_en),
                        file_name="Produkttexte_IPIM_Upload_EN.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="tab2_ipim_download_en"
                    )




####
# 
# 3rd Tab for SEO Optimization of Product text
#
#


with tab3:

    with st.expander("Information"):
                

        st.markdown("""
            <p>
            In diesem Reiter können bereits erstellte und manuell geprüfte Produkttexte SEO-optimiert werden.
            Bitte lade die Output-Datei aus der Produkttexterstellung hoch.
            """, unsafe_allow_html=True)
                

    #
    # LEG-259 prompt text
    #  -> is saved in the session state and can be adapted
    with st.expander("Prompt für die SEO-Textgenerierung"):

        # of not yet existing, take default prompt text
        if "tab3_seo_prompt_1" not in st.session_state:
            st.session_state.tab3_seo_prompt_1 = prompts.inpt_prmt_seo_1

        st.session_state.tab3_seo_prompt_1 = st.text_area(
                                                        "Prompt",
                                                        value=st.session_state.tab3_seo_prompt_1,
                                                        height=200,
                                                        key="tab3_prompt_input_1"
                                                    )
        
    with st.expander("Prompt für die Diversifizierung der Texte für die unterschiedlichen Varianten pro Modell"):

        # of not yet existing, take default prompt text
        if "tab3_seo_prompt_2" not in st.session_state:
            st.session_state.tab3_seo_prompt_2 = prompts.inpt_prmt_seo_2

        st.session_state.tab3_seo_prompt_2 = st.text_area(
                                                        "Prompt",
                                                        value=st.session_state.tab3_seo_prompt_2,
                                                        height=200,
                                                        key="tab3_prompt_input_2"
                                                    )

    # upoad butte for Excel file
    tab3_uploaded_file = st.file_uploader("Excel Datei mit generierten Produkttexten auswählen", accept_multiple_files=False, type=["xlsx", "xls", "csv"])

    # empty data frame for data
    tab3_df_org_data = None
    tab3_df_output_data = None

    if tab3_uploaded_file:
        st.markdown(f"**Dateiname:** `{tab3_uploaded_file.name}`")

        # check if the file is still the same like in the session state
        # -> file is always transformed to data frame of the code
        if st.session_state.tab3_imported_file_name != tab3_uploaded_file.name:
            # file name changed -> new generation, alte Ergebnisse verwerfen
            st.session_state.tab3_generation_done = False
            st.session_state.tab3_df_output_data = None
            st.session_state.tab3_timing = None

        try:
            # CSV einlesen
            if tab3_uploaded_file.name.lower().endswith(".csv"):
                tab3_df_org_data = pd.read_csv(tab3_uploaded_file)
                st.success("CSV erfolgreich geladen.")

            # Read always first sheet of Excelfile
            else:
                tab3_df_org_data = pd.read_excel(tab3_uploaded_file, sheet_name=0, engine="openpyxl")
                st.success("Excel (erstes Tabellenblatt) erfolgreich geladen.")

            st.session_state.tab3_imported_file_name = tab3_uploaded_file.name       

        except Exception as e:
            st.error(f"Fehler beim Einlesen: {e}")

    else:
        st.info("Bitte eine Datei hochladen.")

    
    # LEG-262
    # Load automatically Excel file with 


    if tab3_df_org_data is not None:

        # check required columns for input data
        tab3_col_error = False
        for col in tab3_required_columns:
            if col not in tab3_df_org_data.columns:
                st.error("Folgende Spalte fehlt in der Excel-Datei: " + col)
                tab3_col_error = True

        if len(tab3_df_org_data) == 0:
            st.error("Die hochgeladene Datei enthält keine Datensätze.")
            tab3_col_error = True
      


        # LEG-262
        # Excel file with Artikelvarianten is loaded from Blob and 
        tab3_df_artv = None
        try:
            tab3_df_artv = load_artv_data()
        except Exception as e:
            st.error(f"Fehler beim Laden der Variantendaten aus dem Blob: {e}")
            tab3_col_error = True

        # Spaltenprüfung nur, wenn das Laden geklappt hat
        if tab3_df_artv is not None and "Artikelvariante" not in tab3_df_artv.columns:
            st.error("Spalte 'Artikelvariante' fehlt in den Variantendaten aus dem Blob.")
            tab3_col_error = True

        if tab3_col_error:
            st.stop()

        # get join criteria:
        # sample for model - 
        # sample for Artikelvarioante - 
        tab3_df_artv["Artikelvariante"] = tab3_df_artv["Artikelvariante"].astype(str).str.strip()
        tab3_df_artv["Modell_Join"] = tab3_df_artv["Artikelvariante"].str.rsplit("-", n=1).str[0]


        tab3_df_org_data = tab3_df_org_data.merge(
            tab3_df_artv,
            how="inner",
            left_on="Modell",
            right_on="Modell_Join"
        )

        if len(tab3_df_org_data) == 0:
            st.error("Keine passenden Variantendaten gefunden (Join über Modell/Artikelvariante leer).")
            st.stop()

        st.info(f"{len(tab3_df_org_data)} Artikelvarianten nach Verknüpfung mit Blob-Daten.")
        
        # output for test
        #st.dataframe(tab3_df_artv)

       

        # show data frame
        st.dataframe(tab3_df_org_data)

        
        if st.session_state.tab3_generation_done:
            tab3_df_output_data = st.session_state.tab3_df_output_data
        
        if "cnt_loop_1" in st.session_state:
                        st.write('final loop 1',st.session_state.cnt_loop_1)
        
        if "cnt_loop_2" in st.session_state:
            st.write('final loop 2',st.session_state.cnt_loop_2)

        if st.button("SEO-Texte generieren", key="seo_generate_button"):

            cnt_loop_1 = 0
            cnt_loop_2 = 0                        

            client = OpenAI(api_key=st.secrets["OPAI_KEYS"])
            tab3_output_rows = []

            # Zeitmessung: Ergebnisse pro Schritt werden hier gesammelt
            tab3_timing_records = []


            #
            # step 1: generate SEO text per Artikelvariante
            #

            tab3_step1_start = time.perf_counter()
            tab3_step1_total = len(tab3_df_org_data.index)
            tab3_step1_progress = st.empty()
            with st.spinner("SEO-Optimierung läuft pro Artikelvariante...", show_time=True):
                for tab3_step1_i, idx in enumerate(tab3_df_org_data.index, start=1):

                    cnt_loop_1 = cnt_loop_1 + 1
                    st.session_state.cnt_loop_1 = cnt_loop_1

                    
                    tab3_step1_progress.text(f"SEO-Text pro Artikelvariante: {tab3_step1_i} von {tab3_step1_total}")

                    original_text = str(tab3_df_org_data.loc[idx, "Produkttext"]).strip()
                    # add with LEG-259
                    farbe = str(tab3_df_org_data.loc[idx, "Farbe_Suche1"]).strip()
                    matart = str(tab3_df_org_data.loc[idx, "MatArt_Obermaterial"]).strip()

                    variant_input = (
                        f"Produkttext: {original_text}\n"
                        f"Farbe: {farbe}\n"
                        f"Materialart Obermaterial: {matart}"
                    )

                    seo_prompt = f"{st.session_state.tab3_seo_prompt_1}\n\nInput:\n{variant_input}"

                    seo_response = client.chat.completions.create(
                        model=gpts_modl,
                        messages=[
                            {"role": "system", "content": "Du bist ein erfahrener SEO-Texter für Produkttexte."},
                            {"role": "user", "content": seo_prompt}
                        ],
                        temperature=0.5
                    )

                    #st.write(seo_response)

                    seo_text = seo_response.choices[0].message.content
                    seo_text = fcts.fnct_ptxt(seo_text)

                    #st.write(seo_text)                    

                    tab3_output_rows.append({
                        "Modell":           tab3_df_org_data.loc[idx, "Modell"],
                        "Saison":           tab3_df_org_data.loc[idx, "Saison"],       # neu
                        "Marke":            tab3_df_org_data.loc[idx, "Marke"],        # neu
                        "Gruppe":           tab3_df_org_data.loc[idx, "Gruppe"],       # neu
                        "Produkttyp":       tab3_df_org_data.loc[idx, "Produkttyp"],   # neu
                        #LEG-263: provide Artikelvariante, Farbe and Material, so that ChatGPT
                        # can add a sentence, that there are other variants of the article
                        "Artikelvariante":     tab3_df_org_data.loc[idx, "Artikelvariante"],
                        "Farbe_Suche1":        tab3_df_org_data.loc[idx, "Farbe_Suche1"],
                        "MatArt_Obermaterial": tab3_df_org_data.loc[idx, "MatArt_Obermaterial"],
                        "Produkttext":      original_text,
                        "Produkttext_SEO":  seo_text,
                        "Response_ID":      seo_response.id,
                        "Created_UTC": datetime.fromtimestamp(seo_response.created).strftime("%d.%m.%Y %H:%M:%S"),
                        "Model": seo_response.model,
                        "Prompt_Tokens": seo_response.usage.prompt_tokens,
                        "Completion_Tokens": seo_response.usage.completion_tokens
                    })

            tab3_step1_elapsed = time.perf_counter() - tab3_step1_start
            tab3_step1_count = len(tab3_output_rows)
            tab3_timing_records.append({
                "Schritt": "1. SEO-Text pro Artikelvariante",
                "Anzahl": tab3_step1_count,
                "Gesamtzeit (s)": round(tab3_step1_elapsed, 2),
                "Ø Zeit/Element (s)": round(tab3_step1_elapsed / tab3_step1_count, 2) if tab3_step1_count else 0,
            })

            tab3_df_output_data = pd.DataFrame(tab3_output_rows)


            #
            # step 2: create more divers model text
            #

            tab3_step2_start = time.perf_counter()
            tab3_step2_count = 0
            tab3_step2_total = (tab3_df_output_data.groupby("Modell", sort=False).size() >= 2).sum()
            tab3_step2_progress = st.empty()
            with st.spinner("SEO Optimieriung läuft pro Modell", show_time=True):

                # loop over model combinations
                for modell, gruppe in tab3_df_output_data.groupby("Modell", sort=False):

                    cnt_loop_2 = cnt_loop_2 + 1
                    st.session_state.cnt_loop_2 = cnt_loop_2
                    
                    # only re-check text, if there are minimum
                    # 2 article variants per model
                    if len(gruppe) < 2:
                        continue

                    tab3_step2_count += 1
                    tab3_step2_progress.text(f"Diversifizierung pro Modell: {tab3_step2_count} von {tab3_step2_total}")

                    indices  = gruppe.index.tolist()                   

                    # get all produkttexte in a list
                    prueflinge = {str(i+1): tab3_df_output_data.loc[idx, "Produkttext_SEO"]                                  
                                    for i, idx in enumerate(indices[0:])}                   
                    

                    # join single artikelvariante produkttexte to one text for the prompt
                    # LEG-263 - pass Farbe, Material for text of other variants
                    pruefling_block = "\n\n".join(
                        f"Prüfling {str(i+1)}:\n"
                        f"Farbe: {str(tab3_df_output_data.loc[idx, 'Farbe_Suche1']).strip()}\n"
                        f"Material: {str(tab3_df_output_data.loc[idx, 'MatArt_Obermaterial']).strip()}\n"
                        f"Text: {tab3_df_output_data.loc[idx, 'Produkttext_SEO']}"
                        for i, idx in enumerate(indices[0:])
                    )

                    # create prompt
                    div_prompt = (
                        f"{st.session_state.tab3_seo_prompt_2}\n\n"                        
                        f"{pruefling_block}"
                    )

                    #st.write(div_prompt)

                    div_response = client.chat.completions.create(
                        model=gpts_modl,
                        messages=[
                            {"role": "system", "content": "Du überarbeitest Produkttexte sorgfältig auf Deutsch."},
                            {"role": "user",   "content": div_prompt}
                        ],
                        temperature=0.7,
                        response_format={"type": "json_object"}
                    )

                    #st.write(div_response)

                    # the response contains a JSON with a list of all
                    # the adapted Produkttexte                    
                    raw    = div_response.choices[0].message.content
                    clean  = re.sub(r"```json|```", "", raw).strip()


                    try:
                        parsed = json.loads(clean)

                        if not isinstance(parsed, dict):
                            raise ValueError("Antwort ist kein JSON-Objekt")

                        # write back adapted Produkttexte to
                        # output data
                        for i, idx in enumerate(indices[0:]):
                            key = str(i + 1)
                            if key in parsed:
    
                                # write back new Produkttext
                                tab3_df_output_data.loc[idx, "Produkttext_SEO"] = fcts.fnct_ptxt(parsed[key])
    
                                # prompt tokens get devided by the number of Artikelvariante per Modell
                                tab3_df_output_data.loc[idx, "Prompt_Tokens"]      += div_response.usage.prompt_tokens     // len(prueflinge)
                                tab3_df_output_data.loc[idx, "Completion_Tokens"]  += div_response.usage.completion_tokens // len(prueflinge)
    
                                # update length 
                                tab3_df_output_data.loc[idx, "Länge()"] = len(parsed[key])


                    except Exception as e:
                        st.error({"Modell": modell, "Fehler": str(e)})                                    
                    

            tab3_step2_elapsed = time.perf_counter() - tab3_step2_start
            tab3_timing_records.append({
                "Schritt": "2. Diversifizierung pro Modell",
                "Anzahl": tab3_step2_count,
                "Gesamtzeit (s)": round(tab3_step2_elapsed, 2),
                "Ø Zeit/Element (s)": round(tab3_step2_elapsed / tab3_step2_count, 2) if tab3_step2_count else 0,
            })

            st.session_state.tab3_df_output_data = tab3_df_output_data
            st.session_state.tab3_timing = tab3_timing_records
            st.session_state.tab3_generation_done = True


        if tab3_df_output_data is not None:
            st.success("SEO-optimierte Produkttexte erfolgreich generiert.")

            # Zeitmessung anzeigen
            if st.session_state.tab3_timing:
                tab3_timing_df = pd.DataFrame(st.session_state.tab3_timing)
                if not tab3_timing_df.empty and "Gesamtzeit (s)" in tab3_timing_df.columns:
                    st.markdown("**Zeitmessung**")
                    gesamt_zeit = tab3_timing_df["Gesamtzeit (s)"].sum()
                    st.dataframe(tab3_timing_df, hide_index=True)
                    st.caption(f"Gesamtdauer aller Schritte: {round(gesamt_zeit, 2)} Sekunden")

            st.dataframe(tab3_df_output_data)

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                tab3_df_output_data.to_excel(writer, index=False, sheet_name="Seite1")
            buffer.seek(0)

            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"Produkttexte_SEO_{timestamp}.xlsx"

            st.download_button(
                label="Als Excel herunterladen",
                data=buffer,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="seo_download_button"
            )




####
# 
# 4th Tab for SEO text translation - SAT6
#
#


with tab4:

    with st.expander("Information"):
                

        st.markdown("""
            <p>
            Hier kannst du die englischen Übersetzungen für die SEO-Texte erstellen. 
            Lade dazu die im vorigen Reiter erstellte Datei hoch.
            """, unsafe_allow_html=True)






####
# 
# 5th Tab for Selling Point Config
#
#

with tab5:

    with st.expander("Information"):
        st.markdown("""
            <p>Hier kannst du die Selling Points Konfiguration direkt bearbeiten und speichern.</p>
            </p> <p>                                     
            Viel Spaß!</p> <p> </p>
            Robert
            <p> </p>
        """, unsafe_allow_html=True)

    # reload counter -> need to reset the content of the data editor, when pressing reload
    if "tab5_reload_counter" not in st.session_state:
        st.session_state.tab5_reload_counter = 0

    # load excel if not yet done
    if "tab5_df" not in st.session_state:
        try:
            tab5_df = pd.read_excel(st.secrets["AZURE_BLOB_URL"], engine="openpyxl")
            st.session_state.tab5_df = tab5_df
        except Exception as e:
            st.error(f"Fehler beim Laden der Datei: {e}")
            st.stop()

    # Button to manually reload the file
    if st.button("🔄 Neu laden", key="tab5_reload"):
        try:
            # increase reload counter
            st.session_state.tab5_reload_counter += 1

            # reload excel file
            tab5_df = pd.read_excel(st.secrets["AZURE_BLOB_URL"], engine="openpyxl")
            st.session_state.tab5_df = tab5_df
            st.success("Datei neu geladen.")

        except Exception as e:
            st.error(f"Fehler beim Laden: {e}")

    # Data Editor - has seperate data frame, which has to be saved
    tab5_edited_df = st.data_editor(
        st.session_state.tab5_df,
        use_container_width=True,
        num_rows="dynamic",
        # reload counter is part of the key, to regenerate data editor
        key=f"tab5_editor_{st.session_state.tab5_reload_counter}"
    )


    # Save button
    if st.button("💾 Speichern", key="tab5_save"):
        try:
            # tranform data frame to Excel byte stream
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                tab5_edited_df.to_excel(writer, index=False, sheet_name="Seite1")
            buffer.seek(0)

            print('getting SAS token')

            # get sas Token
            sas_token = st.secrets["AZURE_SAS_TOKEN"]
            azure_blob_url = st.secrets["AZURE_BLOB_URL"]
            blob_url_with_sas = f"{azure_blob_url}{sas_token}"

            # write byte stream to blob storage            
            blob_client = BlobClient.from_blob_url(blob_url_with_sas)
            blob_client.upload_blob(buffer, overwrite=True)

            # update session state
            st.session_state.tab5_df = tab5_edited_df
            st.success("Datei erfolgreich gespeichert.")

        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")