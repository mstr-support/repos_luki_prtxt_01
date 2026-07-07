import streamlit as st
import streamlit.components.v1 as components

from openai import OpenAI
from datetime import datetime
import pandas as pd
from io import BytesIO
import re
import json

# for selling point config
from azure.storage.blob import BlobClient


#helper functions
# add helper functions if needed


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

#
# Prompt definitions

# input prompt -> can be dynamic in the future with a text box
inpt_prmt = (
	"Du bist ein erfahrener Werbetexter mit Spezialisierung auf Schuhe."
    "Du erhältst Textvorlagen sowie strukturierte Produktattribute."
    "Verwende die Leistenbeschreibung und die Modellbeschreibung als zentrale Grundlage."
	"Der erste Satz muss Produktname und Produkttyp enthalten."
    "Produktname + Produkttyp immer mit Artikel (zB Der Sneaker XXX, die Hausschuhe YYY)."
    "Füge manchmal auch das Geschlecht zum Produkttyp, zB Herrensneaker, Damenschuh."
	"Ergänze nur befüllte, relevante Attribute; es dürfen keine Inhalte erfunden werden."
    "Wenn vorhanden, erwähne die Laufsohleneigenschaften und die Aspekte der Nachhaltigkeit."
	"Schreibe in flüssigem, natürlichem Deutsch ohne Aufzählungen."
    "Achte auf eine natürliche, menschlich klingende Sprache."
    "Vermeide Aufzählungen, Wortwiederholungen, übermäßig werbliche Floskeln und direkte persönliche Ansprache."
    "Halte die Textlänge zwischen 500-550 Zeichen, erwähne nie das Wort Leisten."
    "Beachte korrekte Rechtschreibung und flüssigen Satzbau. Leistenname immer in Großbuchstaben."
)

# Prompt for product text review
inpt_prmt_review = (
    "Verbessere im folgenden Text Rechtschreib- und Grammatikfehler."
    "Verkürze den Text auf circa 450 Zeichen"
    "Ersetze Wortwiederholungen, ohne den Inhalt zu verändern."
    "Füge am Ende einen kurzen werbehaften Abschlusssatz hinzu, siehe Beispieltext."
    "Gib ausschließlich den überarbeiteten Text zurück, ohne zusätzliche Erklärungen oder Kommentare."
    "Hier ein Beispieltext: Ganz schön raffiniert, bewegt man sich mit der Sandale MOVE durch den Sommer. "
    "Dezente Schmuckelemente an den Riemenenden, in Kombination mit dem naturgemilltem Nappaleder sorgen bei "
    "dem legero Schuh für einen feinen und modernen Look. Die besonders weiche, flexible und superleichte PU-Sohle "
    "mit dem markanten Profil macht MOVE so luftig und flexibel. Damit stellt sich das Sommergefühl ganz leicht ein. "      
)

# Prompt for SEO optimization

# prompt for step 1

inpt_prmt_seo_1 = (
    "Aufgabe: Du erhälst einen Produkttext, der für ein Modell komplett gleich ist."
    "Erzeuge auf Basis der zusätzlichen Informationen einen Text für eine einzelne Artikelvariante."
)

# prompt for step 2

inpt_prmt_seo_2 = (
    "Aufgabe: Vergleiche einen Ausgangstext mit einem oder mehreren zu prüfenden Produkttexten. "
    "Überarbeite jeden Prüfling so, dass er sprachlich korrekt, verkaufsstark und eigenständig formuliert ist. "
    "Regeln: Prüfe jeden Text auf identische oder zu nah übernommene Formulierungen aus dem Ausgangstext. "
    "Prüfe zusätzlich, ob sich die Prüflinge untereinander zu ähnlich klingen. "
    "Inhalte dürfen ähnlich sein, Formulierungen nicht. "
    "Formuliere gleiche Satzanfänge, Schlusssätze, Nutzenargumente und Standardphrasen abwechslungsreich um. "
    "Erhalte alle sachlichen Produktinformationen des jeweiligen Textes. "
    "Behalte die SEO- und GEO-Optimierung der Texte bei. "
    "Erfinde keine neuen Eigenschaften. "
    "Korrigiere Grammatik, Rechtschreibung und Zeichensetzung wenn notwendig. "
    "Jeder finale Text soll mindestens 550 Zeichen inklusive Leerzeichen haben. "
    "Gib ausschließlich die überarbeiteten Texte als JSON zurück. Keine Analyse. Keine Erklärungen. "
    "Format: {\"1\": \"text prüfling 1\", \"2\": \"text prüfling 2\", ...}"
)


#
# columns, of the Excel file
#
tab1_required_columns = [
    "Marke", "Gruppe", "Saison", "Modellnr", "Leistenbeschreibung", "Modellbeschreibung",
    "Produkttext", 
    "Geschlecht", "Produkttyp OS", "Verschluss",
    "Schuhweite", "Membrane", "Laufsohle",
    "Absatzart", "Form Schuhspitze", "Nachhaltigkeit", "Barfussschuh",
    "Wechselfußbett", "Decksohle", "Futtermaterial", "Futter Detail", "Zertifikate",
    "Leuchtendes Motiv", "Non-marking Sohle", "Wasserbeständig", "Made in Europe",
    ]


# requires columns for SEO Optimization have to be the same
# as the output file of product text generation
tab2_required_columns = [    
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
    {"attr1": "Barfußschuh",       "attr2": None},
    {"attr1": "Zertifikate",       "attr2": None},
    {"attr1": "Leuchtendes Motiv",  "attr2": None},
    {"attr1": "Wasserbeständig",   "attr2": None},
    {"attr1": "Nachhaltigkeit",    "attr2": None},
    {"attr1": "Membrane",          "attr2": None},
    {"attr1": "Wechselfußbett",    "attr2": "Decksohle"},
    {"attr1": "Futtermaterial",    "attr2": None},
    {"attr1": "Schuhweite",        "attr2": None},
    {"attr1": "Non-marking Sohle", "attr2": None},
    {"attr1": "Made in Europe",    "attr2": None},
    {"attr1": "Laufsohle",          "attr2": None},
    {"attr1": "Absatzart",          "attr2": None},
    {"attr1": "Verschluss",          "attr2": None}
]

#
# fixed replacement for speficif values

#Funktion für Geschlecht
def fnct_gesl(marke: str, geschlecht: str) -> str:
    if pd.isna(geschlecht):
        return geschlecht
    if str(marke).strip().lower() == "superfit":
        g = str(geschlecht).strip().lower()
        if g == "weiblich":
            return "Mädchen"
        elif g == "männlich":
            return "Junge"
    return geschlecht

#Funktion für Produkttyp
def fnct_ptyp(text: str) -> str:
    if pd.isna(text):
        return text
    text = str(text).strip()
    if "sneaker" in text.lower():
        return "Sneaker"
    if text.lower() == "ancle boot":
        return "Stiefelette"
    return text

#Funktion Verschluss
def fnct_vrsl(text: str) -> str:
    if pd.isna(text):
        return text
    text = str(text).strip().lower()
    # Ausschließen bestimmter Begriffe
    if "schlupfschuh" in text or "kein verschluss" in text or "offen" in text:
        return ""
    # Immer '/' durch 'zusätzlich' ersetzen
    if "/" in text:
        text = text.replace("/", " zusätzlich ")
    # Ersten Buchstaben groß für konsistente Formatierung
    return text.capitalize()

#Funktion Profil Laufsohle
def fnct_pfls(text: str) -> str:
    if pd.isna(text):
        return None
    text = str(text).strip().lower()
    if text == "stark ausgeprägtes profil":
        return "Stark ausgeprägtes Profil"
    return None

#Funktion laufsohleneigenschaft erzeugen
def fnct_lfso(saison: str, laufsohle: str, marke: str) -> str:
    if pd.isna(laufsohle):
        return laufsohle
    # Sommersaison
    if str(saison).strip().upper().startswith("FS"):

        #Marke unterscheiden
        if str(marke).strip().upper().startswith("SUPERFIT"):

            # Laufsohle unterscheiden
            if str(laufsohle).strip().upper().startswith("PU"):
                return "Leicht, rutschhemmend, flexibel: die PU-Laufsohle"
            
            elif str(laufsohle).strip().upper().startswith("TPU"):
                return "Leicht, rutschhemmend, flexibel: die TPU-Laufsohle"

            elif str(laufsohle).strip().upper().startswith("TPR"):
                return "rutschhemmend, flexibel"
            
            elif str(laufsohle).strip().upper().startswith("GUMMI"):
                return "Dämpft jeden Schritt: die Sohle aus Gummi"
            
            elif str(laufsohle).strip().upper().startswith("PVC"):
                return "nicht abfärbend, flexibel, leicht"
            
            elif str(laufsohle).strip().upper().startswith("NATURLATEX"):
                return "aus nachwachsendem Rohstoff, flexibel, natürliche Abrollbewegung"
            
            elif str(laufsohle).strip().upper().startswith("EVA"):
                return "Leicht, flexibel und dämpfend: die Sohle aus EVA"
            
            elif str(laufsohle).strip().upper().startswith("PHYLON"):
                return "sehr leicht, flexibel, hoher Tragekomfort"
            
            else:
                return ""
            
        elif str(marke).strip().upper().startswith("LEGERO"):

            # Laufsohle unterscheiden
            if str(laufsohle).strip().upper().startswith("PU"):
                return "flexibel, leicht, hoher Tragekomfort"
            
            elif str(laufsohle).strip().upper().startswith("TPU"):
                return "optimaler Grip, rutschhemmend, abriebfest"
            
            else:
                return ""

        elif str(marke).strip().upper().startswith("THINK"):

            # Laufsohle unterscheiden
            if str(laufsohle).strip().upper().startswith("PU"):
                return "leicht, stoßabsorbierend, dämpfend"
            
            elif str(laufsohle).strip().upper().startswith("TPU"):
                return "elastisch, abriebfest, stabil"
            
            elif str(laufsohle).strip().upper().startswith("GUMMI"):
                return "flexibel, abriebfest, rutschhemmend"
            
            elif str(laufsohle).strip().upper().startswith("NATURLATEX"):
                return "dämpfend, flexibel, aus nachwachsendem Rohstoff"
            
            elif str(laufsohle).strip().upper().startswith("EVA"):
                return "flexibel, dämpfend, leicht"
            
            elif str(laufsohle).strip().upper().startswith("BLOWTECH"):
                return "dämpfend, leicht, rutschhemmend"
            
            elif str(laufsohle).strip().upper().startswith("LIGHT GUM"):
                return "dämpfend, leicht, rutschhemmend"

            else:
                return ""

        else:
            return ""
    
    # Wintersaison
    elif str(saison).strip().upper().startswith("HW"):

        #Marke unterscheiden
        if str(marke).strip().upper().startswith("SUPERFIT"):

            # Laufsohle unterscheiden
            if str(laufsohle).strip().upper().startswith("PU"):
                return "isolierend, rutschhemmend, hoher Tragekomfort"
            
            elif str(laufsohle).strip().upper().startswith("TPU"):
                return "optimaler Grip, rutschhemmend, abriebfest, kälte-und witterungsbeständig"

            elif str(laufsohle).strip().upper().startswith("TPR"):
                return "rutschhemmend, flexibel"
            
            elif str(laufsohle).strip().upper().startswith("GUMMI"):
                return "abriebfest, rutschhemmend, flexibel"
            
            elif str(laufsohle).strip().upper().startswith("PVC"):
                return "nicht abfärbend, flexibel, leicht"
            
            elif str(laufsohle).strip().upper().startswith("NATURLATEX"):
                return "aus nachwachsendem Rohstoff, flexibel, natürliche Abrollbewegung"
            
            elif str(laufsohle).strip().upper().startswith("EVA"):
                return "sehr leicht, Flexibilität auch bei Kälte, hoher Tragekomfort"
            
            elif str(laufsohle).strip().upper().startswith("PHYLON"):
                return "sehr leicht, Flexibilität auch bei Kälte, hoher Tragekomfort"
            
            else:
                return ""
            
        elif str(marke).strip().upper().startswith("LEGERO"):

            # Laufsohle unterscheiden
            if str(laufsohle).strip().upper().startswith("PU"):
                return "flexibel, leicht, hoher Tragekomfort, rutschhemmend"
            
            elif str(laufsohle).strip().upper().startswith("TPU"):
                return "optimaler Grip, rutschhemmend, abriebfest, kälte-und witterungsbeständig"
            
            else:
                return ""

        elif str(marke).strip().upper().startswith("THINK"):

            # Laufsohle unterscheiden
            if str(laufsohle).strip().upper().startswith("PU"):
                return "leicht, stoßabsorbierend, dämpfend"
            
            elif str(laufsohle).strip().upper().startswith("TPU"):
                return "elastisch, abriebfest, stabil"
            
            elif str(laufsohle).strip().upper().startswith("GUMMI"):
                return "flexibel, abriebfest, rutschhemmend"
            
            elif str(laufsohle).strip().upper().startswith("NATURLATEX"):
                return "dämpfend, flexibel, aus nachwachsendem Rohstoff"
            
            elif str(laufsohle).strip().upper().startswith("EVA"):
                return "flexibel, dämpfend, leicht"
            
            elif str(laufsohle).strip().upper().startswith("BLOWTECH"):
                return "dämpfend, leicht, rutschhemmend"
            
            elif str(laufsohle).strip().upper().startswith("LIGHT GUM"):
                return "dämpfend, leicht, rutschhemmend"

            else:
                ## Leersting, wenn keine Auswahl zutrifft
                return ""

        else:
            ## Leersting, wenn keine Auswahl zutrifft
            return ""
        
    else:
        ## Leersting, wenn keine Auswahl zutrifft
        return ""


#Funktion Wechselfußbett
def fnct_wfub(wert: str) -> str:
    return "Einlegesohle wechselbar" if wert.lower() == "ja" else "nicht erwähnen"

#Funktion Produkttext
def fnct_ptxt(text: str) -> str:

    # Gore-Tex nur ersetzen, wenn es noch nicht korrekt ist
    if "gore-tex®" not in text.lower():
        text = re.sub(r"gore[\s-]?tex", "GORE-TEX®", text, flags=re.IGNORECASE)

    # Diese Anpassungen immer durchführen
    text = text.replace("Außenzip", "Außenzipp")
    text = text.replace("Damen-Schuh", "Damenschuh")

    return text


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

    # load Selling point Excel file if not yet done    
    if "tab3_df" not in st.session_state:
        try:
            tab3_df = pd.read_excel(st.secrets["AZURE_BLOB_URL"], engine="openpyxl")
            st.session_state.tab3_df = tab3_df
        except Exception as e:
            st.error(f"Fehler beim Laden der Datei: {e}")
            st.stop()

    #
    # general filters
    #

    # filter selling point data only for relevant rows
    df_sp = st.session_state.tab3_df[st.session_state.tab3_df["Relevant"].astype(str).str.strip().str.upper() == "J"].copy()

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
        return str(df_sp_filtered.iloc[0]["Selling Point Text"]).strip()
    else:
        return wert1_str


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

        # Testausgabe
        st.write("Aktuelle Sellingpiont Menge:",len(results))
        st.write("attr1:",attr1)
        st.write("val1_str:",val1_str)
        st.write("attr2:",attr1)
        st.write("val2_str:",val1_str)
        st.write("sp_text:",sp_text)


        # check if selling point text 
        if sp_text and sp_text != val1_str:            

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

tab1, tab2, tab3 = st.tabs(["Produkttexte", "SEO-Optimierung","Selling Points Config"])


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


# check session variables for SOE , whether a generation was already done
if "tab2_generation_done" not in st.session_state:
    st.session_state.tab2_generation_done = False
if "tab2_df_output_data" not in st.session_state:
    st.session_state.tab2_df_output_data = None
if "tab2_imported_file_name" not in st.session_state:
    st.session_state.tab2_imported_file_name = None


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
    tab1_uploaded_file = st.file_uploader("Excel Datei mit Produkttexten auswählen", accept_multiple_files=False, type=["xlsx", "xls", "csv"])

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

            
            
            # loop
            with st.spinner("Produkttexte werden generiert...", show_time=True):

                for rows_indx in tab1_df_org_data.index:
                            
                    #st.write(rows_indx)

                    inpt_vatr = ", ".join(
                        f"{col}: {val}"
                        for col, val in {

                            # base values are taken or changed
                            "Produktname": tab1_df_org_data.loc[rows_indx, "Gruppe"],
                            "Leistenbeschreibung": tab1_df_org_data.loc[rows_indx, "Leistenbeschreibung"],                             
                            "Modellbeschreibung": tab1_df_org_data.loc[rows_indx, "Modellbeschreibung"],     
                            "Produkttyp": fnct_ptyp(tab1_df_org_data.loc[rows_indx, "Produkttyp OS"]),                            
                            "Geschlecht": fnct_gesl(tab1_df_org_data.loc[rows_indx, "Marke"], tab1_df_org_data.loc[rows_indx, "Geschlecht"]),
                            "Verschluss": fnct_vrsl(tab1_df_org_data.loc[rows_indx, "Verschluss"]),
                            "Laufsohleneigenschaften": fnct_lfso(tab1_df_org_data.loc[rows_indx, "Saison"], tab1_df_org_data.loc[rows_indx, "Laufsohle"], tab1_df_org_data.loc[rows_indx, "Marke"]),
                            #"Profil Laufsohle": fnct_pfls(dafr_inpt.loc[rows_indx, "Profil Laufsohle"]),

                            "Nachhaltigkeit": tab1_df_org_data.loc[rows_indx, "Nachhaltigkeit"],
                            "Membrane": tab1_df_org_data.loc[rows_indx, "Membrane"],
                            "Futtermaterial": tab1_df_org_data.loc[rows_indx, "Futtermaterial"],                        
                            "Schuhweite": tab1_df_org_data.loc[rows_indx, "Schuhweite"],   
                            "Einlegesohle": fnct_wfub(tab1_df_org_data.loc[rows_indx, "Wechselfußbett"])
                            
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

                    final_prompt = f"""
                    {inpt_prmt}                
                    Attribute:
                    {inpt_vatr}
                    """

                    st.write(final_prompt)

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
                    text_output = fnct_ptxt(text_output)

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

            
            tab1_df_output_data = pd.DataFrame(list_output_data, columns=[
                "Modell", "Saison", "Marke", "Gruppe", "Produkttyp",                    
                "Selling Point 1", "Selling Point 2", "Selling Point 3",
                "Selling Point 4", "Selling Point 5",
                "Produkttext", "Response_ID", "Created_UTC", "Model",
                "Prompt_Tokens", "Completion_Tokens"
            ])
            


            # review the gernerated product 
            with st.spinner("Produkttexte werden nachbearbeitet...", show_time=True):

                # empty lists to store information of second loop
                reviewed_texts = []
                review_response_ids = []
                review_created_utc = []
                review_models = []
                review_prompt_tokens = []
                review_completion_tokens = []

                # loop over every generated row
                for idx in tab1_df_output_data.index:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
                    original_text = tab1_df_output_data.loc[idx, "Produkttext"]

                    review_prompt = f"""
                    {inpt_prmt_review}

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
                    reviewed_text = fnct_ptxt(reviewed_text)

                    # add results to lists
                    reviewed_texts.append(reviewed_text)
                    review_response_ids.append(review_response.id)
                    review_created_utc.append(datetime.fromtimestamp(review_response.created).strftime("%d.%m.%Y %H:%M:%S"))
                    review_models.append(review_response.model)
                    review_prompt_tokens.append(review_response.usage.prompt_tokens)
                    review_completion_tokens.append(review_response.usage.completion_tokens)

                    


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

        
        if tab1_df_output_data is not None:

            # write output
            st.success("Produkttexte erfolgreich generiert.")
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
# 2nd Tab for SEO Optimization of Product text
#
#


with tab2:

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
        if "tab2_seo_prompt_1" not in st.session_state:
            st.session_state.tab2_seo_prompt_1 = inpt_prmt_seo_1

        st.session_state.tab2_seo_prompt_1 = st.text_area(
                                                        "Prompt",
                                                        value=st.session_state.tab2_seo_prompt_1,
                                                        height=200,
                                                        key="tab2_prompt_input_1"
                                                    )
        
    with st.expander("Prompt für die Diversifizierung der Texte für die unterschiedlichen Varianten pro Modell"):

        # of not yet existing, take default prompt text
        if "tab2_seo_prompt_2" not in st.session_state:
            st.session_state.tab2_seo_prompt_2 = inpt_prmt_seo_2

        st.session_state.tab2_seo_prompt_2 = st.text_area(
                                                        "Prompt",
                                                        value=st.session_state.tab2_seo_prompt_2,
                                                        height=200,
                                                        key="tab2_prompt_input_2"
                                                    )

    # upoad butte for Excel file
    tab2_uploaded_file = st.file_uploader("Excel Datei mit generierten Produkttexten auswählen", accept_multiple_files=False, type=["xlsx", "xls", "csv"])

    # empty data frame for data
    tab2_df_org_data = None
    tab2_df_output_data = None

    if tab2_uploaded_file:
        st.markdown(f"**Dateiname:** `{tab2_uploaded_file.name}`")

        # check if the file is still the same like in the session state
        # -> file is always transformed to data frame of the code
        if st.session_state.tab1_imported_file_name != tab2_uploaded_file.name:
            # file name changed -> new generation
            st.session_state.tab1_generation_done = False

        try:
            # CSV einlesen
            if tab2_uploaded_file.name.lower().endswith(".csv"):
                tab2_df_org_data = pd.read_csv(tab2_uploaded_file)
                st.success("CSV erfolgreich geladen.")

            # Read always first sheet of Excelfile
            else:
                tab2_df_org_data = pd.read_excel(tab2_uploaded_file, sheet_name=0, engine="openpyxl")
                st.success("Excel (erstes Tabellenblatt) erfolgreich geladen.")

            st.session_state.tab2_imported_file_name = tab2_uploaded_file.name       

        except Exception as e:
            st.error(f"Fehler beim Einlesen: {e}")

    else:
        st.info("Bitte eine Datei hochladen.")

    
    # LEG-262
    # Load automatically Excel file with 


    if tab2_df_org_data is not None:

        # check required columns for input data
        tab2_col_error = False
        for col in tab2_required_columns:
            if col not in tab2_df_org_data.columns:
                st.error("Folgende Spalte fehlt in der Excel-Datei: " + col)
                tab2_col_error = True

        if len(tab2_df_org_data) == 0:
            st.error("Die hochgeladene Datei enthält keine Datensätze.")
            tab2_col_error = True
      


        # LEG-262
        # Excel file with Artikelvarianten is loaded from Blob and 
        try:
            tab2_df_artv = load_artv_data()
        except Exception as e:
            st.error(f"Fehler beim Laden der Variantendaten aus dem Blob: {e}")
            tab2_col_error = True

        # check required columns for Artikelvarianten
        if "Artikelvariante" not in tab2_df_artv.columns:
            st.error("Spalte 'Artikelmodell' fehlt in den Variantendaten aus dem Blob.")
            tab2_col_error = True

        if tab2_col_error:
            st.stop()

        # get join criteria:
        # sample for model - 
        # sample for Artikelvarioante - 
        tab2_df_artv["Artikelvariante"] = tab2_df_artv["Artikelvariante"].astype(str).str.strip()
        tab2_df_artv["Modell_Join"] = tab2_df_artv["Artikelvariante"].str.rsplit("-", n=1).str[0]


        tab2_df_org_data = tab2_df_org_data.merge(
            tab2_df_artv,
            how="inner",
            left_on="Modell",
            right_on="Modell_Join"
        )

        if len(tab2_df_org_data) == 0:
            st.error("Keine passenden Variantendaten gefunden (Join über Modell/Artikelvariante leer).")
            st.stop()

        st.info(f"{len(tab2_df_org_data)} Artikelvarianten nach Verknüpfung mit Blob-Daten.")
        
        # output for test
        #st.dataframe(tab2_df_artv)

       

        # show data frame
        st.dataframe(tab2_df_org_data)


        if st.session_state.tab2_generation_done:
            tab2_df_output_data = st.session_state.tab2_df_output_data
        
       

        if st.button("SEO-Texte generieren", key="seo_generate_button"):

            client = OpenAI(api_key=st.secrets["OPAI_KEYS"])
            tab2_output_rows = []


            #
            # step 1: generate SEO text per Artikelvariante
            #

            with st.spinner("SEO-Optimierung läuft pro Artikelvariante...", show_time=True):
                for idx in tab2_df_org_data.index:
                    original_text = str(tab2_df_org_data.loc[idx, "Produkttext"]).strip()
                    # add with LEG-259
                    farbe = str(tab2_df_org_data.loc[idx, "Farbe_Suche1"]).strip()
                    matart = str(tab2_df_org_data.loc[idx, "MatArt_Obermaterial"]).strip()

                    variant_input = (
                        f"Produkttext: {original_text}\n"
                        f"Farbe: {farbe}\n"
                        f"Materialart Obermaterial: {matart}"
                    )

                    seo_prompt = f"{st.session_state.tab2_seo_prompt_1}\n\nInput:\n{variant_input}"

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
                    seo_text = fnct_ptxt(seo_text)

                    #st.write(seo_text)                    

                    tab2_output_rows.append({
                        "Modell":           tab2_df_org_data.loc[idx, "Modell"],
                        "Saison":           tab2_df_org_data.loc[idx, "Saison"],       # neu
                        "Marke":            tab2_df_org_data.loc[idx, "Marke"],        # neu
                        "Gruppe":           tab2_df_org_data.loc[idx, "Gruppe"],       # neu
                        "Produkttyp":       tab2_df_org_data.loc[idx, "Produkttyp"],   # neu
                        "Produkttext":      original_text,
                        "Produkttext_SEO":  seo_text,
                        "Response_ID":      seo_response.id,
                        "Created_UTC": datetime.fromtimestamp(seo_response.created).strftime("%d.%m.%Y %H:%M:%S"),
                        "Model": seo_response.model,
                        "Prompt_Tokens": seo_response.usage.prompt_tokens,
                        "Completion_Tokens": seo_response.usage.completion_tokens
                    })

            tab2_df_output_data = pd.DataFrame(tab2_output_rows)


            #
            # step 2: create more divers model text
            #

            with st.spinner("SEO Optimieriung läuft pro Modell", show_time=True):

                # loop over model combinations
                for modell, gruppe in tab2_df_output_data.groupby("Modell", sort=False):

                    # only re-check text, if there are minimum
                    # 2 article variants per model
                    if len(gruppe) < 2:
                        continue

                    indices  = gruppe.index.tolist()                   

                    # get all produkttexte in a list
                    prueflinge = {str(i+1): tab2_df_output_data.loc[idx, "Produkttext"]
                                    for i, idx in enumerate(indices[0:])}                   
                    

                    # join single artikelvariante produkttexte to one text for the prompt
                    pruefling_block = "\n\n".join(
                        f"Prüfling {k}:\n{v}" for k, v in prueflinge.items()
                    )
                

                    # create prompt
                    div_prompt = (
                        f"{st.session_state.tab2_seo_prompt_2}\n\n"                        
                        f"{pruefling_block}"
                    )

                    div_response = client.chat.completions.create(
                        model=gpts_modl,
                        messages=[
                            {"role": "system", "content": "Du überarbeitest Produkttexte sorgfältig auf Deutsch."},
                            {"role": "user",   "content": div_prompt}
                        ],
                        temperature=0.7
                    )

                    #st.write(div_response)

                    # the response contains a JSON with a list of all
                    # the adapted Produkttexte                    
                    raw    = div_response.choices[0].message.content
                    clean  = re.sub(r"```json|```", "", raw).strip()
                    parsed = json.loads(clean)

                    
                    # write back adapted Produkttexte to
                    # output data
                    for i, idx in enumerate(indices[0:]):
                        key = str(i + 1)
                        if key in parsed:

                            # write back new Produkttext
                            tab2_df_output_data.loc[idx, "Produkttext_SEO"] = fnct_ptxt(parsed[key])

                            # prompt tokens get devided by the number of Artikelvariante per Modell
                            tab2_df_output_data.loc[idx, "Prompt_Tokens"]      += div_response.usage.prompt_tokens     // len(prueflinge)
                            tab2_df_output_data.loc[idx, "Completion_Tokens"]  += div_response.usage.completion_tokens // len(prueflinge)

                            # update length 
                            tab2_df_output_data.loc[idx, "Länge()"] = len(parsed[key])
                    

            st.session_state.tab2_df_output_data = tab2_df_output_data
            st.session_state.seo_done = True


        if tab2_df_output_data is not None:
            st.success("SEO-optimierte Produkttexte erfolgreich generiert.")
            st.dataframe(tab2_df_output_data)

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                tab2_df_output_data.to_excel(writer, index=False, sheet_name="Seite1")
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
# 3rd Tab for Selling Point Config
#
#

with tab3:

    with st.expander("Information"):
        st.markdown("""
            <p>Hier kannst du die Selling Points Konfiguration direkt bearbeiten und speichern.</p>
            </p> <p>                                     
            Viel Spaß!</p> <p> </p>
            Robert
            <p> </p>
        """, unsafe_allow_html=True)

    # reload counter -> need to reset the content of the data editor, when pressing reload
    if "tab3_reload_counter" not in st.session_state:
        st.session_state.tab3_reload_counter = 0

    # load excel if not yet done
    if "tab3_df" not in st.session_state:
        try:
            tab3_df = pd.read_excel(st.secrets["AZURE_BLOB_URL"], engine="openpyxl")
            st.session_state.tab3_df = tab3_df
        except Exception as e:
            st.error(f"Fehler beim Laden der Datei: {e}")
            st.stop()

    # Button to manually reload the file
    if st.button("🔄 Neu laden", key="tab3_reload"):
        try:
            # increase reload counter
            st.session_state.tab3_reload_counter += 1

            # reload excel file
            tab3_df = pd.read_excel(st.secrets["AZURE_BLOB_URL"], engine="openpyxl")
            st.session_state.tab3_df = tab3_df
            st.success("Datei neu geladen.")

        except Exception as e:
            st.error(f"Fehler beim Laden: {e}")

    # Data Editor - has seperate data frame, which has to be saved
    tab3_edited_df = st.data_editor(
        st.session_state.tab3_df,
        use_container_width=True,
        num_rows="dynamic",
        # reload counter is part of the key, to regenerate data editor
        key=f"tab3_editor_{st.session_state.tab3_reload_counter}"
    )


    # Save button
    if st.button("💾 Speichern", key="tab3_save"):
        try:
            # tranform data frame to Excel byte stream
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                tab3_edited_df.to_excel(writer, index=False, sheet_name="Seite1")
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
            st.session_state.tab3_df = tab3_edited_df
            st.success("Datei erfolgreich gespeichert.")

        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")