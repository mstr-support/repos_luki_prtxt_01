import streamlit as st
import streamlit.components.v1 as components

from openai import OpenAI
from datetime import datetime
import pandas as pd
from io import BytesIO


#helper functions
# add helper functions if needed


st.set_page_config(
         layout="wide",
         page_title="Luki Produkttexte",
         page_icon="images/legero_klein.png",
         initial_sidebar_state ="expanded"
               )


#
# variable declaration
#

# model select -> can be dynamic in the future with a dropbox
gpts_modl = "gpt-4.1-mini"

# input prompt -> can be dynamic in the future with a text box
inpt_prmt = (
    "Du bist ein erfahrener Werbetexter für Schuhe. "
    "Formuliere markante Teile der Modellbeschreibung und der Gruppenbeschreibung neu " 
    "um den Charakter des Schuhs hervorzuheben. Erwähne Produktname und Produkttyp im ersten Satz. "     
    "Ergänze den Text um relevante Attribute, damit er informativ, emotional ansprechend wirkt. "
    "Achte auf eine natürliche, menschlich klingende Sprache und eine SEO-optimierte "
    "Formulierung. Vermeide Aufzählungen, Wortwiederholungen und übermäßig werbliche Floskeln. "
    "Halte die Textlänge zwischen 350-400 Zeichen, erwähne nie das Wort Leisten. "
    "Wenn möglich, erwähne die Laufsohleneigenschaften und die Aspekte der Nachhaltigkeit (wenn befüllt) in einem Satz. "
    "Beachte korrekte Rechtschreibung und flüssigen Satzbau. Leistenname immer in Großbuchstaben"
    "Hier ein Beispieltext: Ganz schön raffiniert, bewegt man sich mit der Sandale MOVE durch den Sommer. "
    "Dezente Schmuckelemente an den Riemenenden, in Kombination mit dem naturgemilltem Nappaleder sorgen bei "
    "dem legero Schuh für einen feinen und modernen Look. Die besonders weiche, flexible und superleichte PU-Sohle "
    "mit dem markanten Profil macht MOVE so luftig und flexibel. Damit stellt sich das Sommergefühl ganz leicht ein. "
)


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

#Funktion Laufsohleneigneschaften FS <> rutschhemmend
def fnct_lfso(saison: str, laufsohle: str) -> str:
    if pd.isna(laufsohle):
        return laufsohle
    if str(saison).strip().upper().startswith("FS"):
        return str(laufsohle).replace("rutschhemmend", "").strip()
    return laufsohle


# build config for authenticator
# -> not needed here



# 
# side bar configuration
#



#
# tab definition
#




#
# content
# 

st.title("Luki Produkttexte")


with st.expander("Information"):
            

            st.markdown("""
                  <p>
                  Hier kann etwas Text für eine Erklärung hin
                  
                  </p>
                  """, unsafe_allow_html=True)
            


# upoad butte for Excel file
uploaded_file = st.file_uploader("Excel Datei mit Produkttexten auswählen", accept_multiple_files=False, type=["xlsx", "xls", "csv"])

# empty data frame for data
df_org_data = None

if uploaded_file:
    st.markdown(f"**Dateiname:** `{uploaded_file.name}`")

    try:
        # CSV einlesen
        if uploaded_file.name.lower().endswith(".csv"):
            df_org_data = pd.read_csv(uploaded_file)
            st.success("CSV erfolgreich geladen.")

        # Excel: immer erstes Sheet einlesen
        else:
            df_org_data = pd.read_excel(uploaded_file, sheet_name=0, engine="openpyxl")
            st.success("Excel (erstes Tabellenblatt) erfolgreich geladen.")

    except Exception as e:
        st.error(f"Fehler beim Einlesen: {e}")

else:
    st.info("Bitte eine Datei hochladen.")



#
# site will just continue if data was read from Excel
#

if df_org_data is not None:
    
    st.dataframe(df_org_data)

    # button to start generation of produkttexte
    if st.button("Produkttexte generieren"):

        # initialisierung
        client = OpenAI(api_key=st.secrets["OPAI_KEYS"])
        rows_indx = 0
        df_output_data = []
        
        # loop
        while rows_indx < len(df_org_data):
            inpt_grpb = df_org_data["Gruppenbeschreibung"].iloc[rows_indx]

            inpt_vatr = ", ".join(
                f"{col}: {val}"
                for col, val in {
                    "Produktname": df_org_data.loc[rows_indx, "Gruppe"],
                    "Modellbeschreibung": df_org_data.loc[rows_indx, "Modellbeschreibung"],         
                    "Geschlecht": fnct_gesl(df_org_data.loc[rows_indx, "Marke"], df_org_data.loc[rows_indx, "Geschlecht"]),
                    "Produkttyp": fnct_ptyp(df_org_data.loc[rows_indx, "Produkttyp OS"]),
                    "Verschluss": fnct_vrsl(df_org_data.loc[rows_indx, "Verschluss"]),
                    "Schuhweite": df_org_data.loc[rows_indx, "Schuhweite"],
                    "Laufsohleneigenschaften": fnct_lfso(df_org_data.loc[rows_indx, "Saison"], df_org_data.loc[rows_indx, "Laufsohle Eigenschaften"]),
                    #"Profil Laufsohle": fnct_pfls(dafr_inpt.loc[rows_indx, "Profil Laufsohle"]),
                    "Nachhaltigkeit": df_org_data.loc[rows_indx, "Nachhaltigkeit"]
                }.items()
                if pd.notna(val) and str(val).strip() != ""
            )

            final_prompt = f"""
            {inpt_prmt}
            Gruppenbeschreibung::
            {inpt_grpb}
            Attribute:
            {inpt_vatr}
            """

            response = client.chat.completions.create(
                model=gpts_modl,
                messages=[
                    {"role": "system", "content": "Du bist ein erfahrener Werbetexter für Schuhe."},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )

            #print(f"\n--- Zeile {rows_indx + 1} ---")
            #print(response.choices[0].message.content)
            text_output = response.choices[0].message.content    
            modl = df_org_data["Modellnr"].iloc[rows_indx]
            df_output_data.append({
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


        st.success("Produkttexte erfolgreich generiert.")
        st.dataframe(df_output_data)

        # prepare Excel Download
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_output_data.to_excel(writer, index=False, sheet_name="Sheet1")
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

    
