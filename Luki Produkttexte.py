import streamlit as st
import streamlit.components.v1 as components

from openai import OpenAI
from datetime import datetime
import pandas as pd
from io import BytesIO
import re

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

# input prompt -> can be dynamic in the future with a text box
inpt_prmt = (
	"Du bist ein erfahrener Werbetexter mit Spezialisierung auf Schuhe."
    "Du erhältst Textvorlagen sowie strukturierte Produktattribute."
    "Verwende die Leistenbeschreibung und die Modellbeschreibung als zentrale Grundlage."
	"Der erste Satz muss Produktname und Produkttyp enthalten."
    "Produktname + Produkttyp immer mit Artikel (zB Der Sneaker XXX, die Hausschuhe YYY)"
    "Füge manchmal auch das Geschlecht zum Produkttyp, zB Herrensneaker, Damenschuh"
	"Ergänze nur befüllte, relevante Attribute; es dürfen keine Inhalte erfunden werden."
    "Wenn vorhanden, erwähne die Laufsohleneigenschaften und die Aspekte der Nachhaltigkeit."
	"Schreibe in flüssigem, natürlichem Deutsch ohne Aufzählungen."
    "Achte auf eine natürliche, menschlich klingende Sprache."
    "Vermeide Aufzählungen, Wortwiederholungen, übermäßig werbliche Floskeln und direkte persönliche Ansprache."
    "Halte die Textlänge zwischen 500-550 Zeichen, erwähne nie das Wort Leisten."
    "Beachte korrekte Rechtschreibung und flüssigen Satzbau. Leistenname immer in Großbuchstaben"
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
inpt_prmt_seo = (
    "Du bist ein SEO-Texter.\n\n"
    "Aufgabe:\n"
    "SEO-optimiere den folgenden Produkttext.\n\n"
    "Anforderungen:\n"
    "- Verwende relevante Keywords natürlich im Text (z. B. Sneaker, Herren, bequem, Leder, wasserdicht, etc.)\n"
    "- Vermeide Keyword-Stuffing\n"
    "- Schreibe klar, strukturiert und verkaufsorientiert\n"
    "- Länge des Inputes ungefähr beibehalten\n"
    "- Ein zusammenhängender Absatz (kein Bullet-Format)\n\n"
    "Stil:\n"
    "- Sachlich, modern, hochwertig\n"
    "- Keine Wiederholungen\n"
    "- Aktive Sprache\n\n"
    "Output:\n"
    "Nur den optimierten Text zurückgeben.\n\n"
    "Input:\n"
    "{{PRODUCT_TEXT}}"
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
    "Leuchtendes Motiv", "Non-marking Sohle", "Wasserbeständig", "Made in Europe"
]

tab2_required_columns = [
    "Modell", "Produkttext", "Response_ID", "Created_UTC", "Model", "Prompt_Tokens", "Completion_Tokens"
]



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


# Funktion für Selling Point Text Ersetzung
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
                            "Produktname": tab1_df_org_data.loc[rows_indx, "Gruppe"],
                            "Leistenbeschreibung": tab1_df_org_data.loc[rows_indx, "Leistenbeschreibung"],                             
                            "Modellbeschreibung": tab1_df_org_data.loc[rows_indx, "Modellbeschreibung"],     
                            "Produkttyp": fnct_ptyp(tab1_df_org_data.loc[rows_indx, "Produkttyp OS"]),                            
                            "Geschlecht": fnct_gesl(tab1_df_org_data.loc[rows_indx, "Marke"], tab1_df_org_data.loc[rows_indx, "Geschlecht"]),
                            "Verschluss": fnct_vrsl(tab1_df_org_data.loc[rows_indx, "Verschluss"]),
                            "Laufsohleneigenschaften": fnct_lfso(tab1_df_org_data.loc[rows_indx, "Saison"], tab1_df_org_data.loc[rows_indx, "Laufsohle"], tab1_df_org_data.loc[rows_indx, "Marke"]),
                            #"Profil Laufsohle": fnct_pfls(dafr_inpt.loc[rows_indx, "Profil Laufsohle"]),
                            "Nachhaltigkeit": fnct_selling_point(
                                'Nachhaltigkeit',
                                tab1_df_org_data.loc[rows_indx, "Nachhaltigkeit"],
                                tab1_df_org_data.loc[rows_indx, "Marke"]
                                ),
                            "Membrane": fnct_selling_point(
                                'Membrane',
                                tab1_df_org_data.loc[rows_indx, "Membrane"],
                                tab1_df_org_data.loc[rows_indx, "Marke"]
                                ),                            
                            "Futtermaterial": fnct_selling_point( 
                                'Futtermaterial',
                                tab1_df_org_data.loc[rows_indx, "Futtermaterial"],
                                tab1_df_org_data.loc[rows_indx, "Marke"]
                                ),                     
                            "Schuhweite": fnct_selling_point(
                                tab1_df_org_data.loc[rows_indx, "Schuhweite"],   
                                tab1_df_org_data.loc[rows_indx, "Marke"]
                            ),
                            # Alte Logik für Einlegesohle
                            # "Einlegesohle": fnct_wfub(tab1_df_org_data.loc[rows_indx, "Wechselfußbett"])     
                            "Einlegesohle": fnct_selling_point(
                                "Wechselfußbett",
                                tab1_df_org_data.loc[rows_indx, "Wechselfußbett"],                                
                                tab1_df_org_data.loc[rows_indx, "Marke"],
                                "Decksohle",                       
                                tab1_df_org_data.loc[rows_indx, "Decksohle"]
                            )                                           
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
                    list_output_data.append({
                        "Modell": modl,
                        "Produkttext": text_output,
                        "Response_ID": response.id,
                        "Created_UTC": datetime.fromtimestamp(response.created).strftime("%d.%m.%Y %H:%M:%S"),
                        "Model": response.model,
                        "Prompt_Tokens": response.usage.prompt_tokens,
                        "Completion_Tokens": response.usage.completion_tokens
                    })
                    print(rows_indx, datetime.fromtimestamp(response.created).strftime("%d.%m.%Y %H:%M:%S"))
                    rows_indx += 1

            # transform list to dataframe for Excel export
            tab1_df_output_data =  pd.DataFrame(list_output_data, columns=["Modell", "Produkttext", "Response_ID", "Created_UTC", "Model", "Prompt_Tokens", "Completion_Tokens"])
            

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
                    </p> <p>                                     
                    Viel Spaß!</p> <p> </p>
                    Robert
                    <p> </p>
                    """, unsafe_allow_html=True)
                

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


    if tab2_df_org_data is not None:
        

        tab2_col_error = False
        for col in tab2_required_columns:
            if col not in tab2_df_org_data.columns:
                st.error("Folgende Spalte fehlt in der Excel-Datei: " + col)
                tab2_col_error = True

        if len(tab2_df_org_data) == 0:
            st.error("Die hochgeladene Datei enthält keine Datensätze.")
            tab2_col_error = True

        if tab2_col_error:
            st.stop()

        st.dataframe(tab2_df_org_data)

        if st.session_state.tab2_generation_done:
            tab2_df_output_data = st.session_state.tab2_df_output_data

        if st.button("SEO-Texte generieren", key="seo_generate_button"):

            client = OpenAI(api_key=st.secrets["OPAI_KEYS"])
            tab2_output_rows = []

            with st.spinner("SEO-Optimierung läuft...", show_time=True):
                for idx in tab2_df_org_data.index:
                    original_text = str(tab2_df_org_data.loc[idx, "Produkttext"]).strip()

                    seo_prompt = inpt_prmt_seo.replace("{{PRODUCT_TEXT}}", original_text)

                    seo_response = client.chat.completions.create(
                        model=gpts_modl,
                        messages=[
                            {"role": "system", "content": "Du bist ein erfahrener SEO-Texter für Produkttexte."},
                            {"role": "user", "content": seo_prompt}
                        ],
                        temperature=0.5
                    )

                    seo_text = seo_response.choices[0].message.content
                    seo_text = fnct_ptxt(seo_text)

                    # add Tokens to already used tokens 
                    original_prompt_tokens = tab2_df_org_data.loc[idx, "Prompt_Tokens"]
                    original_completion_tokens = tab2_df_org_data.loc[idx, "Completion_Tokens"]

                    if pd.isna(original_prompt_tokens):
                        original_prompt_tokens = 0
                    if pd.isna(original_completion_tokens):
                        original_completion_tokens = 0

                    tab2_output_rows.append({
                        "Modell": tab2_df_org_data.loc[idx, "Modell"],
                        "Produkttext": seo_text,
                        "Response_ID": seo_response.id,
                        "Created_UTC": datetime.fromtimestamp(seo_response.created).strftime("%d.%m.%Y %H:%M:%S"),
                        "Model": seo_response.model,
                        "Prompt_Tokens": int(original_prompt_tokens) + seo_response.usage.prompt_tokens,
                        "Completion_Tokens": int(original_completion_tokens) + seo_response.usage.completion_tokens
                    })

            tab2_df_output_data = pd.DataFrame(
                tab2_output_rows,
                columns=[
                    "Modell",
                    "Produkttext",
                    "Response_ID",
                    "Created_UTC",
                    "Model",
                    "Prompt_Tokens",
                    "Completion_Tokens"
                ]
            )

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