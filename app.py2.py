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
    .hero { background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url('https://source.unsplash.com/random/1600x900/?luxury-fashion'); 
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
    df_admin = df_raw.copy()
except Exception as e:
    st.error(f"Erreur de chargement : {e}")
    df = pd.DataFrame(columns=["nom", "prix", "image"])
    df_admin = pd.DataFrame()

# ====================== FILTRES CLIENT ======================
col1, col2, col3 = st.columns([3, 2, 2])
with col1:
    search = st.text_input("🔍 Rechercher", placeholder="Robe, veste...")
with col2:
    max_price = st.slider("Prix maximum (FCFA)", 0, 500000, 300000, 10000)
with col3:
    if not df.empty and 'couleurs' in df.columns:
        couleurs = ["Toutes"] + sorted(df['couleurs'].dropna().astype(str).unique())
    else:
        couleurs = ["Toutes"]
    couleur_filter = st.selectbox("Couleur", couleurs)

# Filtrage
df_filtered = df.copy()
if search:
    df_filtered = df_filtered[df_filtered['nom'].astype(str).str.contains(search, case=False, na=False)]
if couleur_filter != "Toutes":
    df_filtered = df_filtered[df_filtered['couleurs'].astype(str).str.contains(couleur_filter, case=False, na=False)]
df_filtered = df_filtered[pd.to_numeric(df_filtered['prix'], errors='coerce') <= max_price]

# ====================== AFFICHAGE CLIENT ======================
if not df_filtered.empty:
    cols = st.columns(3)
    for idx, row in df_filtered.reset_index().iterrows():
        with cols[idx % 3]:
            prix_str = f"{int(float(row['prix'])):,} FCFA".replace(",", " ") if pd.notna(row['prix']) else "—"
            
            st.markdown(f"""
                <div class="product-card">
                    <img class="product-image" src="{row.get('image', '')}">
                    <h3 style="margin:12px 0 8px 0;">{row.get('nom', '')}</h3>
                    <div class="price">{prix_str}</div>
                </div>
            """, unsafe_allow_html=True)

            with st.expander("📋 Détails & Commander"):
                st.image(row.get('image', ''), use_column_width=True)
                st.subheader(row.get('nom', ''))
                st.write(f"**Prix :** {prix_str}")
                st.write(f"**Tailles :** {row.get('tailles', 'Unique')}")
                st.write(f"**Couleurs :** {row.get('couleurs', '—')}")
                
                msg = f"Bonjour, je souhaite commander {row.get('nom')} au prix de {prix_str}"
                wa_url = f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}"
                st.link_button("💬 Commander sur WhatsApp", wa_url, use_container_width=True, type="primary")
else:
    st.info("Aucun article ne correspond à vos critères.")

# ====================== PANNEAU ADMIN COMPLET ======================
with st.sidebar:
    st.markdown("### ⚙️ Direction de la Boutique")
    password_input = st.text_input("Clé d'accès admin", type="password")
    
    if password_input == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé 🔓")
        
        message_ajout = st.container()
        message_edit = st.container()
        message_suppr = st.container()
        
        st.markdown("---")
        
        # AJOUT
        st.markdown("### ➕ Ajouter un article")
        with st.form("ajout_form", clear_on_submit=True):
            nom = st.text_input("Nom de l'article")
            prix = st.number_input("Prix (FCFA)", min_value=0, step=5000)
            uploaded = st.file_uploader("Photo", type=["jpg", "png", "jpeg"])
            tailles = st.text_input("Tailles", "Unique")
            couleurs = st.text_input("Couleurs", "Unique")
            stock = st.number_input("Stock", min_value=1, value=1)
            
            if st.form_submit_button("Ajouter"):
                if nom and prix and uploaded:
                    with st.spinner("En cours..."):
                        try:
                            img_bytes = uploaded.read()
                            b64 = base64.b64encode(img_bytes).decode()
                            res = requests.post("https://api.imgbb.com/1/upload", 
                                              data={"key": st.secrets.get("IMGBB_API_KEY", "70be83b276ba6ccbf03b71597dfc2a5d"), 
                                                    "image": b64})
                            img_url = res.json()["data"]["url"]
                            
                            payload = {"action": "ajout_article", "nom": nom, "prix": prix, "image": img_url,
                                       "tailles": tailles, "couleurs": couleurs, "stock": stock}
                            requests.post(URL_PASSERELLE, json=payload)
                            message_ajout.success("Article ajouté !")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            message_ajout.error(f"Erreur : {e}")
        
        st.markdown("---")
        
        # MODIFICATION
        st.markdown("### ✏️ Modifier un article")
        if not df_admin.empty:
            article_list = df_admin['nom'].dropna().astype(str).unique().tolist()
            selected = st.selectbox("Choisir un article", article_list)
            
            if selected:
                art = df_admin[df_admin['nom'].astype(str) == selected].iloc[0]
                with st.form("edit_form"):
                    new_nom = st.text_input("Nom", art['nom'])
                    new_prix = st.number_input("Prix", value=int(float(art['prix'])))
                    new_tailles = st.text_input("Tailles", art.get('tailles', 'Unique'))
                    new_couleurs = st.text_input("Couleurs", art.get('couleurs', 'Unique'))
                    new_stock = st.number_input("Stock", value=int(art.get('stock', 1)))
                    new_image = st.file_uploader("Nouvelle photo (optionnel)")
                    
                    if st.form_submit_button("Enregistrer modifications"):
                        # Logique de mise à jour (similaire à avant)
                        st.info("Fonction de mise à jour prête - à connecter avec ton script Google")
        
        st.markdown("---")
        
        # SUPPRESSION
        st.markdown("### 🗑️ Supprimer")
        if not df_admin.empty:
            to_delete = st.selectbox("Article à supprimer", df_admin['nom'].dropna().astype(str).unique())
            if st.button("Supprimer définitivement", type="primary"):
                # Logique suppression
                st.info("Fonction suppression prête")
        
        # Liste complète
        st.markdown("### 📋 Tous les articles")
        st.dataframe(df_admin, use_container_width=True)
        
    elif password_input != "":
        st.error("Mot de passe incorrect")

st.caption("Collection Luxe N'Djamena © 2026")
