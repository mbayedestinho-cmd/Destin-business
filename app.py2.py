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
    .hero { background: linear-gradient(rgba(0,0,0,0.65), rgba(0,0,0,0.65)), url('https://source.unsplash.com/random/1600x900/?luxury-fashion'); 
             background-size: cover; padding: 140px 20px; text-align: center; color: white; border-radius: 20px; margin-bottom: 50px; }
    .product-card { background: white; border-radius: 16px; padding: 16px; box-shadow: 0 4px 25px rgba(0,0,0,0.06); transition: 0.3s; }
    .product-card:hover { transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
    .product-image { border-radius: 12px; height: 360px; object-fit: cover; width: 100%; }
    .price { color: #b58328; font-weight: 700; font-size: 1.4rem; }
    </style>
""", unsafe_allow_html=True)

# ==================== CONFIG ====================
NUMERO_WHATSAPP = "23408167043143"
MOT_DE_PASSE_ADMIN = "Luxe2026"
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbykGuq78OzBGqHT8C82NLehEeLtcKVkTkFhDa5l_Z8k8i0mX_EL2Fmnl57N6SLLvMRa5w/exec" # ←←← Remplace par ton URL

st.markdown('<div class="hero"><h1 class="main-title">COLLECTION LUXE<br>N\'DJAMENA</h1></div>', unsafe_allow_html=True)

# Chargement données
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

# ====================== INTERFACE CLIENT ======================
st.subheader("Notre Collection")

col1, col2, col3 = st.columns([3,2,2])
with col1:
    search = st.text_input("🔍 Rechercher", "")
with col2:
    max_price = st.slider("Prix maximum", 0, 500000, 300000, 10000)
with col3:
    couleurs = ["Toutes"] + sorted(df['couleurs'].dropna().astype(str).unique()) if not df.empty else ["Toutes"]
    couleur_filter = st.selectbox("Couleur", couleurs)

# Filtrage
df_filtered = df.copy()
if search:
    df_filtered = df_filtered[df_filtered['nom'].astype(str).str.contains(search, case=False, na=False)]
if couleur_filter != "Toutes":
    df_filtered = df_filtered[df_filtered['couleurs'].astype(str).str.contains(couleur_filter, case=False, na=False)]
df_filtered = df_filtered[pd.to_numeric(df_filtered['prix'], errors='coerce') <= max_price]

# Affichage produits
if not df_filtered.empty:
    cols = st.columns(3)
    for idx, row in df_filtered.reset_index().iterrows():
        with cols[idx % 3]:
            prix_str = f"{int(float(row['prix'])):,} FCFA".replace(",", " ")
            st.markdown(f"""
                <div class="product-card">
                    <img class="product-image" src="{row['image']}">
                    <h3>{row['nom']}</h3>
                    <div class="price">{prix_str}</div>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Voir détails"):
                st.image(row['image'], use_column_width=True)
                st.subheader(row['nom'])
                st.write(f"**Prix :** {prix_str}")
                st.write(f"**Tailles :** {row.get('tailles', 'Unique')}")
                st.write(f"**Couleurs :** {row.get('couleurs', '—')}")
                
                msg = f"Bonjour, je souhaite commander {row['nom']} - {prix_str}"
                wa_url = f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}"
                st.link_button("💬 Commander sur WhatsApp", wa_url, use_container_width=True, type="primary")
else:
    st.info("Aucun article trouvé.")

# ====================== ADMIN ======================
with st.sidebar:
    st.header("⚙️ Administration")
    password = st.text_input("Mot de passe admin", type="password")
    
    if password == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé")
        
        # Ajout
        st.subheader("➕ Ajouter un article")
        with st.form("add_form", clear_on_submit=True):
            nom = st.text_input("Nom de l'article")
            prix = st.number_input("Prix (FCFA)", min_value=0)
            uploaded_file = st.file_uploader("Photo", type=["jpg","png","jpeg"])
            tailles = st.text_input("Tailles", "Unique")
            couleurs = st.text_input("Couleurs", "Unique")
            stock = st.number_input("Stock", min_value=1, value=1)
            
            if st.form_submit_button("Ajouter au catalogue"):
                if nom and prix and uploaded_file:
                    with st.spinner("Enregistrement..."):
                        try:
                            b64 = base64.b64encode(uploaded_file.read()).decode()
                            res_img = requests.post("https://api.imgbb.com/1/upload", data={"key": st.secrets.get("IMGBB_API_KEY", "70be83b276ba6ccbf03b71597dfc2a5d"), "image": b64})
                            img_url = res_img.json()["data"]["url"]
                            
                            payload = {"action": "ajout_article", "nom": nom, "prix": prix, "image": img_url, "tailles": tailles, "couleurs": couleurs, "stock": stock}
                            requests.post(URL_PASSERELLE, json=payload)
                            st.success("Article ajouté avec succès !")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
        
        # Liste + Suppression
        st.subheader("📋 Catalogue complet")
        if not df_admin.empty:
            st.dataframe(df_admin, use_container_width=True)
            
            article_suppr = st.selectbox("Supprimer un article", df_admin['nom'].dropna().astype(str).unique())
            if st.button("🗑️ Supprimer", type="primary"):
                try:
                    requests.post(URL_PASSERELLE, json={"action": "suppression_article", "nom": article_suppr})
                    st.success("Article supprimé")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(e)
    elif password:
        st.error("Mot de passe incorrect")

st.caption("Collection Luxe N'Djamena © 2026")
