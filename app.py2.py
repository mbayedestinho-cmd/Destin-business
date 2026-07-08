mport streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time

# Configuration globale
st.set_page_config(
    page_title="Collection Luxe N'Djamena",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Style CSS épuré haute couture
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500&display=swap');
    html, body, [data-testid="stAppViewContainer"] { background-color: #ffffff; font-family: 'Poppins', sans-serif; }
    .main-title { font-family: 'Playfair Display', serif !important; font-size: 3rem !important; font-weight: 700 !important; color: #1a1a1a !important; text-align: center !important; }
    .product-card { background-color: #ffffff; border: 1px solid #f0f0f0; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.02); margin-bottom: 10px; }
    .product-image { border-radius: 8px; object-fit: cover; width: 100%; height: 320px; }
    .product-price { color: #b58328; font-weight: 600; font-size: 1.25rem; margin: 8px 0; }
    </style>
""", unsafe_allow_html=True)

# Identifiants (Assurez-vous qu'ils sont bien configurés dans vos secrets)
NUMERO_WHATSAPP = "23408167043143"  
MOT_DE_PASSE_ADMIN = "Luxe2026"  
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbwAtKtO_g5HWgeUe0XwSnWLgJuMMLrz6BXfmTDF5iQEVW8qjrZDos67S7VW8RBH-oco/exec"

st.markdown('<h1 class="main-title">COLLECTION LUXE N\'DJAMENA</h1>', unsafe_allow_html=True)

# --- CHARGEMENT ET NETTOYAGE DU CATALOGUE ---
try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
    df_raw = pd.read_csv(url_csv)
    df_raw.columns = [col.lower().strip() for col in df_raw.columns]
   
    # Nettoyage strict pour éviter les erreurs d'affichage 'nan'
    df_vitrine = df_raw.dropna(subset=['nom', 'prix'])
    df_vitrine = df_vitrine[df_vitrine['nom'].astype(str).str.strip() != ""]
    df_admin = df_raw.dropna(subset=['nom'])
except Exception as e:
    st.error(f"⚠️ Liaison Google Sheets : {e}")
    df_vitrine = pd.DataFrame()

# --- AFFICHAGE CLIENT ---
if not df_vitrine.empty:
    cols = st.columns(3)
    for index, row in df_vitrine.reset_index().iterrows():
        with cols[index % 3]:
            st.markdown(f"""
                <div class="product-card">
                    <img class="product-image" src="{row['image']}">
                    <h3>{row['nom']}</h3>
                    <div class="product-price">{int(float(row['prix'])):,} FCFA</div>
                </div>
            """, unsafe_allow_html=True)
            st.link_button("💬 Commander sur WhatsApp", url=f"https://wa.me/{NUMERO_WHATSAPP}", use_container_width=True)

# --- ESPACE ADMIN (SUPPRESSION CORRIGÉE) ---
with st.sidebar:
    if st.text_input("Clé d'accès admin", type="password") == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé")
        
        # Section Suppression
        st.markdown("### 🗑️ Supprimer un article")
        noms_dispos = [str(n).strip() for n in df_admin['nom'].unique() if str(n).strip() != ""]
        if noms_dispos:
            article_a_supprimer = st.selectbox("Sélectionnez l'article :", noms_dispos)
            if st.button("🔴 Supprimer définitivement"):
                with st.spinner("Retrait des serveurs..."):
                    res = requests.post(URL_PASSERELLE, json={"action": "suppression_article", "nom": article_a_supprimer})
                    if res.status_code == 200 and res.json().get("status") == "success":
                        st.success("Article supprimé !")
                        st.rerun()
                    else:
                        st.error("Erreur de suppression.")
