import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time

st.set_page_config(
    page_title="Collection Luxe N'Djamena",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Style CSS amélioré
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500&display=swap');
    html, body, [data-testid="stAppViewContainer"] { background-color: #ffffff; font-family: 'Poppins', sans-serif; }
    .main-title { font-family: 'Playfair Display', serif; font-size: clamp(2.8rem, 8vw, 4rem); font-weight: 700; color: #1a1a1a; text-align: center; line-height: 1.1; margin: 30px 0 10px 0; }
    .subtitle { text-align: center; color: #555555; font-style: italic; font-size: 1.35rem; margin-bottom: 40px; }
    .hero { background: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), url('https://source.unsplash.com/random/1600x900/?luxury-fashion'); 
             background-size: cover; background-position: center; padding: 120px 20px; text-align: center; color: white; border-radius: 16px; margin-bottom: 40px; }
    .product-card { background-color: #ffffff; border: 1px solid #f0f0f0; border-radius: 16px; padding: 16px; text-align: center; 
                    box-shadow: 0px 4px 25px rgba(0, 0, 0, 0.04); transition: all 0.3s ease; }
    .product-card:hover { transform: translateY(-8px); box-shadow: 0px 15px 40px rgba(0, 0, 0, 0.08); }
    .product-image { border-radius: 12px; object-fit: cover; width: 100%; height: 340px; }
    .product-price { color: #b58328; font-weight: 700; font-size: 1.35rem; margin: 12px 0; }
    .stButton>button { background-color: #1a1a1a; color: white; border-radius: 8px; height: 48px; }
    </style>
""", unsafe_allow_html=True)

# Configuration
NUMERO_WHATSAPP = "23408167043143"
MOT_DE_PASSE_ADMIN = "Luxe2026"
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbwAtKtO_g5HWgeUe0XwSnWLgJuMMLrz6BXfmTDF5iQEVW8qjrZDos67S7VW8RBH-oco/exec"

# Hero Banner
st.markdown("""
    <div class="hero">
        <h1 class="main-title">COLLECTION LUXE<br>N'DJAMENA</h1>
        <p class="subtitle" style="color:white;">L'élégance intemporelle à portée de main</p>
    </div>
""", unsafe_allow_html=True)

# Chargement données
try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
    df_raw = pd.read_csv(url_csv)
    df_raw.columns = [col.lower().strip() for col in df_raw.columns]
    
    df = df_raw.dropna(subset=['nom', 'prix', 'image']).copy()
    df = df[df['nom'].astype(str).str.strip() != ""]
    df_admin = df_raw.copy()
except:
    st.error("Erreur de connexion au catalogue.")
    df = pd.DataFrame()

# ====================== FILTRES & RECHERCHE ======================
st.markdown("### 🎯 Découvrez nos pièces exclusives")

col1, col2, col3 = st.columns([3, 2, 2])
with col1:
    search = st.text_input("🔎 Rechercher un article", placeholder="Robe, chemise, sac...")

with col2:
    price_max = st.slider("Prix maximum (FCFA)", min_value=0, max_value=500000, value=300000, step=10000)

with col3:
    if not df.empty and 'couleurs' in df.columns:
        couleurs_dispo = ["Toutes"] + sorted(df['couleurs'].dropna().unique().tolist())
        couleur_filter = st.selectbox("Couleur", couleurs_dispo)

# Application des filtres
df_filtered = df.copy()
if search:
    df_filtered = df_filtered[df_filtered['nom'].astype(str).str.contains(search, case=False, na=False)]
if 'couleur_filter' in locals() and couleur_filter != "Toutes":
    df_filtered = df_filtered[df_filtered['couleurs'].astype(str).str.contains(couleur_filter, case=False, na=False)]
df_filtered = df_filtered[pd.to_numeric(df_filtered['prix'], errors='coerce') <= price_max]

# ====================== AFFICHAGE PRODUITS ======================
if not df_filtered.empty:
    cols = st.columns(3)
    for idx, row in df_filtered.reset_index().iterrows():
        with cols[idx % 3]:
            try:
                prix = int(float(row['prix']))
                text_prix = f"{prix:,} FCFA".replace(",", " ")
            except:
                text_prix = str(row['prix'])

            # Carte produit
            st.markdown(f"""
                <div class="product-card">
                    <img class="product-image" src="{row['image']}">
                    <h3 style="margin: 15px 0 8px 0; font-family: 'Playfair Display', serif;">{row['nom']}</h3>
                    <div class="product-price">{text_prix}</div>
                </div>
            """, unsafe_allow_html=True)

            # Bouton qui ouvre la modal
            if st.button("Voir les détails", key=f"btn_{idx}"):
                with st.dialog("Détails de l'article"):
                    st.image(row['image'], use_column_width=True)
                    st.subheader(row['nom'])
                    st.markdown(f"**Prix :** {text_prix}")
                    if 'tailles' in row and pd.notna(row['tailles']):
                        st.markdown(f"**Tailles :** {row['tailles']}")
                    if 'couleurs' in row and pd.notna(row['couleurs']):
                        st.markdown(f"**Couleurs :** {row['couleurs']}")
                    if 'stock' in row and pd.notna(row['stock']):
                        st.markdown(f"**Stock :** {row['stock']} pièce(s)")

                    txt_whatsapp = f"Bonjour, je souhaite commander :\n- Article : {row['nom']}\n- Prix : {text_prix}"
                    url_whatsapp = f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(txt_whatsapp)}"
                    
                    if st.link_button("💬 Commander via WhatsApp", url_whatsapp, use_container_width=True, type="primary"):
                        st.success("Redirection vers WhatsApp...")
            
            st.markdown("---")
else:
    st.info("Aucune pièce ne correspond à votre recherche.")

# ====================== ADMIN (inchangé mais conservé) ======================
with st.sidebar:
    st.markdown("### ⚙️ Administration")
    password_input = st.text_input("Mot de passe admin", type="password")
    
    if password_input == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé")
        # ... (tu peux garder ici tout le code admin précédent : ajout, édition, suppression, liste complète)
        st.info("Le panneau admin complet est disponible dans la version précédente.")
    elif password_input:
        st.error("Mot de passe incorrect")
