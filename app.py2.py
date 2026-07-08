import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time

st.set_page_config(page_title="Collection Luxe N'Djamena", page_icon="✨", layout="wide")

# ==================== CSS ====================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500&display=swap');
    .main-title { font-family: 'Playfair Display', serif; font-size: clamp(2.8rem, 8vw, 4.2rem); font-weight: 700; text-align: center; margin: 30px 0 15px 0; }
    .hero { background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url('https://source.unsplash.com/random/1600x900/?luxury-fashion,africa'); 
             background-size: cover; padding: 130px 20px; text-align: center; color: white; border-radius: 16px; margin-bottom: 40px; }
    .product-card { background: white; border-radius: 16px; padding: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); transition: 0.3s; }
    .product-card:hover { transform: translateY(-6px); box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
    .product-image { border-radius: 12px; height: 340px; object-fit: cover; width: 100%; }
    .price { color: #b58328; font-weight: 700; font-size: 1.35rem; }
    </style>
""", unsafe_allow_html=True)

# Configuration
NUMERO_WHATSAPP = "23408167043143"  
MOT_DE_PASSE_ADMIN = "Luxe2026"  
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbwAtKtO_g5HWgeUe0XwSnWLgJuMMLrz6BXfmTDF5iQEVW8qjrZDos67S7VW8RBH-oco/exec"

st.markdown('<div class="hero"><h1 class="main-title">COLLECTION LUXE<br>N\'DJAMENA</h1></div>', unsafe_allow_html=True)

# Chargement données
try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
    df_raw = pd.read_csv(url_csv)
    df_raw.columns = [col.lower().strip() for col in df_raw.columns]
    df = df_raw.dropna(subset=['nom', 'prix', 'image']).copy()
except Exception as e:
    st.error("Erreur de chargement du catalogue")
    df = pd.DataFrame()

# Filtres
col1, col2, col3 = st.columns([3,2,2])
with col1:
    search = st.text_input("🔍 Rechercher un article", "")
with col2:
    max_price = st.slider("Prix maximum", 0, 500000, 300000, 10000)
with col3:
    if not df.empty:
        couleurs = ["Toutes"] + sorted(df['couleurs'].dropna().astype(str).unique().tolist())
        couleur_filter = st.selectbox("Couleur", couleurs)

# Application filtres
df_filtered = df.copy()
if search:
    df_filtered = df_filtered[df_filtered['nom'].astype(str).str.contains(search, case=False, na=False)]
if 'couleur_filter' in locals() and couleur_filter != "Toutes":
    df_filtered = df_filtered[df_filtered['couleurs'].astype(str).str.contains(couleur_filter, case=False, na=False)]
df_filtered = df_filtered[pd.to_numeric(df_filtered['prix'], errors='coerce') <= max_price]

# ====================== AFFICHAGE PRODUITS ======================
if not df_filtered.empty:
    cols = st.columns(3)
    for idx, row in df_filtered.reset_index().iterrows():
        with cols[idx % 3]:
            try:
                prix = int(float(row['prix']))
                prix_str = f"{prix:,} FCFA".replace(",", " ")
            except:
                prix_str = row['prix']

            st.markdown(f"""
                <div class="product-card">
                    <img class="product-image" src="{row['image']}">
                    <h3 style="margin:12px 0 8px 0;">{row['nom']}</h3>
                    <div class="price">{prix_str}</div>
                </div>
            """, unsafe_allow_html=True)

            # Détails avec expander (plus stable que dialog)
            with st.expander("Voir détails & commander"):
                st.image(row['image'], use_column_width=True)
                st.subheader(row['nom'])
                st.write(f"**Prix :** {prix_str}")
                st.write(f"**Tailles :** {row.get('tailles', 'Unique')}")
                st.write(f"**Couleurs :** {row.get('couleurs', 'Unique')}")
                
                whatsapp_msg = f"Bonjour, je souhaite commander {row['nom']} au prix de {prix_str}"
                whatsapp_url = f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(whatsapp_msg)}"
                
                st.link_button("💬 Commander sur WhatsApp", whatsapp_url, use_container_width=True, type="primary")
else:
    st.info("Aucun article ne correspond à vos critères.")

# ====================== PANNEAU ADMIN COMPLET ======================
with st.sidebar:
    st.markdown("### ⚙️ Administration")
    password = st.text_input("Mot de passe admin", type="password")
    
    if password == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé ✅")
        
        st.metric("Nombre d'articles", len(df))
        
        # Ici tu peux remettre tout le code admin complet (ajout, modification, suppression, liste)
        # Pour l'instant, je mets un rappel :
        st.info("Le panneau admin complet (Ajout / Modification / Suppression) est dans la version précédente que je t’ai envoyée.")
        st.caption("Copie-colle la partie admin de la version précédente ici si tu veux.")
        
    elif password != "":
        st.error("Mot de passe incorrect")

st.caption("Collection Luxe N'Djamena • 2026")
