mport streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time

# Configuration globale
st.set_page_config(page_title="Collection Luxe N'Djamena", layout="wide")

# CSS
st.markdown("""<style>.product-card { border: 1px solid #f0f0f0; border-radius: 12px; padding: 16px; text-align: center; }</style>""", unsafe_allow_html=True)

# Liens et Identifiants
NUMERO_WHATSAPP = "23408167043143"  
MOT_DE_PASSE_ADMIN = "Luxe2026"  
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbwAtKtO_g5HWgeUe0XwSnWLgJuMMLrz6BXfmTDF5iQEVW8qjrZDos67S7VW8RBH-oco/exec"

st.title("COLLECTION LUXE N'DJAMENA")

# --- CHARGEMENT DU CATALOGUE ---
try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
    df_raw = pd.read_csv(url_csv)
    df_raw.columns = [col.lower().strip() for col in df_raw.columns]
   
    # Nettoyage robuste pour éviter les 'nan'
    df_vitrine = df_raw.dropna(subset=['nom', 'prix'])
    df_vitrine = df_vitrine[df_vitrine['nom'].astype(str).str.strip() != ""]
    df_admin = df_raw.dropna(subset=['nom'])
except Exception as e:
    st.error(f"⚠️ Liaison Google Sheets : {e}")
    df_vitrine = pd.DataFrame()

# --- ESPACE DE GESTION ---
with st.sidebar:
    password_input = st.text_input("Clé d'accès admin", type="password")
    if password_input == MOT_DE_PASSE_ADMIN:
        
        # AJOUT
        with st.form("form_ajout", clear_on_submit=True):
            nom = st.text_input("Nom :")
            prix = st.number_input("Prix :", step=5000)
            uploaded_file = st.file_uploader("Photo :", type=["png", "jpg"])
            if st.form_submit_button("🚀 Ajouter"):
                img_bytes = uploaded_file.read()
                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                res_img = requests.post("https://api.imgbb.com/1/upload", data={"key": "70be83b276ba6ccbf03b71597dfc2a5d", "image": base64_image})
                img_url = res_img.json()["data"]["url"]
                requests.post(URL_PASSERELLE, json={"action": "ajout", "nom": nom, "prix": prix, "image": img_url})
                st.rerun()

        # SUPPRESSION CORRIGÉE
        st.markdown("### 🗑️ Supprimer un article")
        noms_dispos = [str(n).strip() for n in df_admin['nom'].unique() if str(n).strip() != ""]
        if noms_dispos:
            article_a_supprimer = st.selectbox("Sélectionnez l'article :", noms_dispos)
            if st.button("🔴 Supprimer définitivement"):
                res = requests.post(URL_PASSERELLE, json={"action": "suppression_article", "nom": article_a_supprimer})
                if res.status_code == 200 and res.json().get("status") == "success":
                    st.success("Article supprimé !")
                    st.rerun()
                else:
                    st.error("Erreur suppression.")
