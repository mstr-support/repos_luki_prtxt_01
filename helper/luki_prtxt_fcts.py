import streamlit as st
import pandas as pd
import re

########
# 
# Functions needed for manipulating, checking, changing the Produkttext and SEO Text
#
########


# ####
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
