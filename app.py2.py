import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time

st.set_page_config(page_title="Collection Luxe N'Djamena", page_icon="✨", layout="wide")

# CSS (simplifié)
st.markdown("""
    <style>
    .main-title { font-family: 'Playfair Display', serif; font-size: clamp(2.8rem, 8vw, 4rem); font-weight: 700; text-align: center; }
    .product-card { border-radius: 16px; padding: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }
    .price { color: #b58328; font-weight: 700; font-size: 1.35rem; }
    </style>
""", unsafe_allow_html=True)

NUMERO_WHATSAPP = "23408167043143"
MOT_DE_PASSE_ADMIN = "Luxe2026"
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbwAtKtO_g5HWgeUe0XwSnWLgJuMMLrz6BXfmTDF5iQEVW8qjrZDos67S7VW8RBH-oco/exec"

st.title("Collection Luxe N'Djamena")

# Chargement catalogue
try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
    df_raw = pd.read_csv(url)
    df_raw.columns = [col.lower().strip() for col in df_raw.columns]
    df = df_raw.dropna(subset=['nom','prix','image']).copy()
    df_admin = df_raw.copy()
except:
    df = pd.DataFrame()
    df_admin = pd.DataFrame()

# ====================== CLIENT ======================
# (Filtres + affichage produits avec expander - code précédent)

# ====================== ADMIN ======================
with st.sidebar:
    st.header("Administration")
    pw = st.text_input("Mot de passe", type="password")
    
    if pw == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé")
        
        # === AJOUT ===
        st.subheader("➕ Ajouter")
        with st.form("add"):
            nom = st.text_input("Nom")
            prix = st.number_input("Prix", min_value=0)
            file = st.file_uploader("Photo", type=["jpg","png","jpeg"])
            tailles = st.text_input("Tailles", "Unique")
            couleurs = st.text_input("Couleurs", "Unique")
            stock = st.number_input("Stock", 1)
            if st.form_submit_button("Ajouter"):
                if file and nom:
                    with st.spinner("Ajout en cours..."):
                        try:
                            b64 = base64.b64encode(file.read()).decode()
                            res = requests.post("https://api.imgbb.com/1/upload", 
                                              data={"key": st.secrets.get("IMGBB_API_KEY", "70be83b276ba6ccbf03b71597dfc2a5d"), "image": b64})
                            img_url = res.json()["data"]["url"]
                            
                            payload = {
                                "action": "ajout_article",
                                "nom": nom,
                                "prix": prix,
                                "image": img_url,
                                "tailles": tailles,
                                "couleurs": couleurs,
                                "stock": stock
                            }
                            r = requests.post(URL_PASSERELLE, json=payload, timeout=15)
                            st.success("Ajouté avec succès !" if r.status_code == 200 else "Erreur serveur")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
        
        # === SUPPRESSION ===
        st.subheader("🗑️ Supprimer")
        if not df_admin.empty:
            nom_suppr = st.selectbox("Article à supprimer", df_admin['nom'].dropna().astype(str).unique())
            if st.button("Supprimer", type="primary"):
                try:
                    r = requests.post(URL_PASSERELLE, json={"action": "suppression_article", "nom": nom_suppr})
                    st.success("Supprimé !") if r.status_code == 200 else st.error("Échec")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(e)
        
        # Liste
        st.subheader("📋 Catalogue complet")
        st.dataframe(df_admin, use_container_width=True)
        
    elif pw:
        st.error("Mot de passe incorrect")
