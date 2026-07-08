import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time

st.set_page_config(page_title="Collection Luxe N'Djamena", page_icon="✨", layout="wide")

# CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500&display=swap');
    .main-title { font-family: 'Playfair Display', serif; font-size: clamp(2.8rem, 8vw, 4.2rem); font-weight: 700; text-align: center; margin: 30px 0 20px 0; }
    .hero { background: linear-gradient(rgba(0,0,0,0.65), rgba(0,0,0,0.65)), url('https://source.unsplash.com/random/1600x900/?luxury-fashion'); 
             background-size: cover; padding: 130px 20px; text-align: center; color: white; border-radius: 20px; margin-bottom: 40px; }
    .product-card { background: white; border-radius: 16px; padding: 16px; box-shadow: 0 4px 25px rgba(0,0,0,0.06); transition: 0.3s; }
    .product-card:hover { transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
    .price { color: #b58328; font-weight: 700; font-size: 1.4rem; }
    </style>
""", unsafe_allow_html=True)

# Configuration
NUMERO_WHATSAPP = "23408167043143"
MOT_DE_PASSE_ADMIN = "Luxe2026"
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbykGuq78OzBGqHT8C82NLehEeLtcKVkTkFhDa5l_Z8k8i0mX_EL2Fmnl57N6SLLvMRa5w/exec" # ← Remplace par ton URL
IMGBB_API_KEY = "945cbd1bd1a39645a2d3d04ffb7630ea"

st.markdown('<div class="hero"><h1 class="main-title">COLLECTION LUXE<br>N\'DJAMENA</h1></div>', unsafe_allow_html=True)

if 'cart' not in st.session_state:
    st.session_state.cart = []

# Chargement
try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
    df_raw = pd.read_csv(url_csv)
    df_raw.columns = [col.lower().strip() for col in df_raw.columns]
    df = df_raw.dropna(subset=['nom', 'prix', 'image']).copy()
    df_admin = df_raw.copy()
except:
    df = pd.DataFrame()
    df_admin = pd.DataFrame()

# ====================== CLIENT + PANIER ======================
# (Garde le code client et panier du dernier code qui fonctionne)

st.subheader("Notre Collection")
# ... (insère le code client ici)

with st.sidebar:
    st.header("🛍️ Mon Panier")
    # ... (code panier identique)

    # ====================== ADMIN ======================
    st.markdown("---")
    st.header("⚙️ Administration")
    password = st.text_input("Mot de passe admin", type="password")
    
    if password == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé")
        
        # AJOUT
        st.subheader("➕ Ajouter")
        with st.form("add_form", clear_on_submit=True):
            nom = st.text_input("Nom")
            prix = st.number_input("Prix", min_value=0)
            uploaded = st.file_uploader("Photo", type=["jpg","png","jpeg"])
            tailles = st.text_input("Tailles", "Unique")
            couleurs = st.text_input("Couleurs", "Unique")
            stock = st.number_input("Stock", min_value=1, value=1)
            
            if st.form_submit_button("Ajouter"):
                if nom and uploaded:
                    with st.spinner("Ajout..."):
                        try:
                            b64 = base64.b64encode(uploaded.read()).decode()
                            res_img = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": b64})
                            img_url = res_img.json()["data"]["url"]
                            
                            payload = {"action": "ajout_article", "nom": nom, "prix": prix, "image": img_url, "tailles": tailles, "couleurs": couleurs, "stock": stock}
                            requests.post(URL_PASSERELLE, json=payload)
                            st.success("Ajouté !")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
        
        # LISTE
        st.subheader("📋 Articles existants")
        if not df_admin.empty:
            st.dataframe(df_admin, use_container_width=True)
        
        # MODIFICATION
        st.subheader("✏️ Modifier un article")
        if not df_admin.empty:
            article_to_edit = st.selectbox("Choisir l'article à modifier", df_admin['nom'].dropna().astype(str).unique())
            
            art = df_admin[df_admin['nom'].astype(str) == article_to_edit].iloc[0]
            with st.form("edit_form"):
                new_nom = st.text_input("Nom", art['nom'])
                new_prix = st.number_input("Prix", value=int(float(art['prix'])))
                new_tailles = st.text_input("Tailles", art.get('tailles', 'Unique'))
                new_couleurs = st.text_input("Couleurs", art.get('couleurs', 'Unique'))
                new_stock = st.number_input("Stock", value=int(art.get('stock', 1)))
                new_image = st.file_uploader("Nouvelle photo (optionnel)")
                
                if st.form_submit_button("Enregistrer modifications"):
                    with st.spinner("Mise à jour..."):
                        try:
                            img_url = art['image']
                            if new_image:
                                b64 = base64.b64encode(new_image.read()).decode()
                                res = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": b64})
                                img_url = res.json()["data"]["url"]
                            
                            payload = {
                                "action": "modification_article",
                                "ancien_nom": article_to_edit,
                                "nom": new_nom,
                                "prix": new_prix,
                                "image": img_url,
                                "tailles": new_tailles,
                                "couleurs": new_couleurs,
                                "stock": new_stock
                            }
                            r = requests.post(URL_PASSERELLE, json=payload)
                            st.success("Modifié avec succès !")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
        
        # SUPPRESSION
        st.subheader("🗑️ Supprimer")
        if not df_admin.empty:
            article = st.selectbox("Article à supprimer", df_admin['nom'].dropna().astype(str).unique(), key="suppr")
            if st.button("Supprimer", type="primary"):
                try:
                    requests.post(URL_PASSERELLE, json={"action": "suppression_article", "nom": article})
                    st.success("Supprimé !")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(e)
        
    elif password:
        st.error("Mot de passe incorrect")

st.caption("Collection Luxe N'Djamena © 2026")
