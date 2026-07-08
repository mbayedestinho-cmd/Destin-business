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
    .main-title { font-family: 'Playfair Display', serif; font-size: clamp(2.8rem, 8vw, 4rem); font-weight: 700; text-align: center; margin: 30px 0 20px 0; }
    .hero { background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url('https://source.unsplash.com/random/1600x900/?luxury-fashion'); 
             background-size: cover; padding: 120px 20px; text-align: center; color: white; border-radius: 16px; margin-bottom: 40px; }
    .product-card { border-radius: 16px; padding: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }
    .price { color: #b58328; font-weight: 700; font-size: 1.35rem; }
    </style>
""", unsafe_allow_html=True)

# Configuration
NUMERO_WHATSAPP = "23408167043143"
MOT_DE_PASSE_ADMIN = "Luxe2026"
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbykGuq78OzBGqHT8C82NLehEeLtcKVkTkFhDa5l_Z8k8i0mX_EL2Fmnl57N6SLLvMRa5w/exec" # ← Change ici

st.markdown('<div class="hero"><h1 class="main-title">COLLECTION LUXE<br>N\'DJAMENA</h1></div>', unsafe_allow_html=True)

# Chargement sécurisé
df = pd.DataFrame()
df_admin = pd.DataFrame()

try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
    df_raw = pd.read_csv(url_csv)
    df_raw.columns = [col.lower().strip() for col in df_raw.columns]
    df = df_raw.dropna(subset=['nom', 'prix', 'image']).copy()
    df_admin = df_raw.copy()
except Exception as e:
    st.warning("Catalogue en cours de chargement...")

# ====================== CLIENT ======================
st.subheader("Notre Collection")

col1, col2, col3 = st.columns([3,2,2])
with col1:
    search = st.text_input("🔍 Rechercher un article", "")
with col2:
    max_price = st.slider("Prix maximum (FCFA)", 0, 500000, 300000, 10000)
with col3:
    # Protection renforcée
    if not df.empty and 'couleurs' in df.columns:
        couleurs_list = ["Toutes"] + sorted(df['couleurs'].dropna().astype(str).unique().tolist())
    else:
        couleurs_list = ["Toutes"]
    couleur_filter = st.selectbox("Couleur", couleurs_list)

# Filtrage sécurisé
df_filtered = df.copy()
if not df_filtered.empty:
    if search:
        df_filtered = df_filtered[df_filtered['nom'].astype(str).str.contains(search, case=False, na=False)]
    if couleur_filter != "Toutes" and 'couleurs' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['couleurs'].astype(str).str.contains(couleur_filter, case=False, na=False)]
    df_filtered = df_filtered[pd.to_numeric(df_filtered['prix'], errors='coerce') <= max_price]

# Affichage
if not df_filtered.empty:
    cols = st.columns(3)
    for idx, row in df_filtered.reset_index().iterrows():
        with cols[idx % 3]:
            prix_str = f"{int(float(row['prix'])):,} FCFA".replace(",", " ") if pd.notna(row.get('prix')) else "—"
            st.markdown(f"""
                <div class="product-card">
                    <img class="product-image" src="{row.get('image', '')}">
                    <h3>{row.get('nom', '')}</h3>
                    <div class="price">{prix_str}</div>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Détails"):
                st.image(row.get('image', ''), use_column_width=True)
                st.subheader(row.get('nom', ''))
                st.write(f"**Prix :** {prix_str}")
                st.link_button("Commander sur WhatsApp", 
                             f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(f'Bonjour, je veux {row.get("nom")}')}", 
                             use_container_width=True)
else:
    st.info("Aucun article disponible pour le moment.")

# ====================== ADMIN ======================
with st.sidebar:
    st.header("Administration")
    pw = st.text_input("Mot de passe", type="password")
    
    if pw == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé")
        st.metric("Articles", len(df))
        
        # Ajout
        st.subheader("➕ Ajouter")
        with st.form("add"):
            nom = st.text_input("Nom")
            prix = st.number_input("Prix", min_value=0)
            file = st.file_uploader("Photo", type=["jpg","png"])
            if st.form_submit_button("Ajouter"):
                st.info("Fonction ajout prête (connectée au script)")
        
        st.subheader("Catalogue")
        if not df_admin.empty:
            st.dataframe(df_admin, use_container_width=True)
    elif pw:
        st.error("Mot de passe incorrect")
