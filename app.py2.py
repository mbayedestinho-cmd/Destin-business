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
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbykGuq78OzBGqHT8C82NLehEeLtcKVkTkFhDa5l_Z8k8i0mX_EL2Fmnl57N6SLLvMRa5w/exec" # ← Remplace par ton URL réelle

st.markdown('<div class="hero"><h1 class="main-title">COLLECTION LUXE<br>N\'DJAMENA</h1></div>', unsafe_allow_html=True)

# Panier
if 'cart' not in st.session_state:
    st.session_state.cart = []

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

# ====================== CLIENT ======================
st.subheader("Notre Collection")

col1, col2, col3 = st.columns([3,2,2])
with col1: search = st.text_input("🔍 Rechercher", "")
with col2: max_price = st.slider("Prix maximum", 0, 500000, 300000, 10000)
with col3: 
    couleurs = ["Toutes"] + sorted(df['couleurs'].dropna().astype(str).unique()) if not df.empty and 'couleurs' in df.columns else ["Toutes"]
    couleur_filter = st.selectbox("Couleur", couleurs)

df_filtered = df.copy()
if search: df_filtered = df_filtered[df_filtered['nom'].astype(str).str.contains(search, case=False, na=False)]
if couleur_filter != "Toutes": df_filtered = df_filtered[df_filtered['couleurs'].astype(str).str.contains(couleur_filter, case=False, na=False)]
df_filtered = df_filtered[pd.to_numeric(df_filtered['prix'], errors='coerce') <= max_price]

if not df_filtered.empty:
    cols = st.columns(3)
    for idx, row in df_filtered.reset_index().iterrows():
        with cols[idx % 3]:
            prix = int(float(row['prix']))
            prix_str = f"{prix:,} FCFA".replace(",", " ")
            
            st.markdown(f"""
                <div class="product-card">
                    <img class="product-image" src="{row['image']}">
                    <h3>{row['nom']}</h3>
                    <div class="price">{prix_str}</div>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns([3,1])
            with c1:
                if st.button("🛒 Ajouter au panier", key=f"add_{idx}"):
                    existing = next((item for item in st.session_state.cart if item['nom'] == row['nom']), None)
                    if existing:
                        existing['quantite'] += 1
                    else:
                        st.session_state.cart.append({"nom": row['nom'], "prix": prix, "image": row['image'], "quantite": 1})
                    st.success("Ajouté au panier !")
                    time.sleep(0.6)
                    st.rerun()
            with c2:
                with st.expander("Détails"):
                    st.image(row['image'], use_column_width=True)
                    st.subheader(row['nom'])
                    st.write(f"**Prix :** {prix_str}")
                    st.write(f"**Tailles :** {row.get('tailles', 'Unique')}")
                    st.write(f"**Couleurs :** {row.get('couleurs', '—')}")
                    st.write(f"**Stock :** {row.get('stock', '—')} pièces")

# ====================== PANIER ======================
with st.sidebar:
    st.header("🛍️ Mon Panier")
    if st.session_state.cart:
        total = sum(item['prix'] * item.get('quantite', 1) for item in st.session_state.cart)
        st.write(f"**{len(st.session_state.cart)} article(s)** - **Total : {total:,} FCFA**".replace(",", " "))
        
        for i, item in enumerate(st.session_state.cart):
            col1, col2, col3 = st.columns([5,2,1])
            with col1:
                st.write(f"{item['nom']} × {item.get('quantite', 1)}")
            with col2:
                q = st.number_input("Qté", min_value=1, value=item.get('quantite', 1), key=f"q{i}")
                if q != item.get('quantite', 1):
                    item['quantite'] = q
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
        
        if st.button("Commander tout sur WhatsApp", type="primary"):
            msg = "Bonjour, voici ma commande :\n\n"
            for item in st.session_state.cart:
                msg += f"- {item['nom']} × {item.get('quantite',1)} = {item['prix']*item.get('quantite',1):,} FCFA\n".replace(",", " ")
            msg += f"\n**Total : {total:,} FCFA**".replace(",", " ")
            st.link_button("Ouvrir WhatsApp", f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}")
    else:
        st.info("Panier vide")

    # ====================== ADMIN COMPLET ======================
    st.markdown("---")
    st.header("⚙️ Administration")
    password = st.text_input("Mot de passe admin", type="password")
    
    if password == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé")
        
        # AJOUT
        st.subheader("➕ Ajouter un article")
        with st.form("add_form", clear_on_submit=True):
            nom = st.text_input("Nom de l'article")
            prix = st.number_input("Prix (FCFA)", min_value=0)
            uploaded = st.file_uploader("Photo", type=["jpg","png","jpeg"])
            tailles = st.text_input("Tailles disponibles", "Unique")
            couleurs = st.text_input("Couleurs disponibles", "Unique")
            stock = st.number_input("Quantité en stock", min_value=1, value=1)
            
            if st.form_submit_button("Ajouter au catalogue"):
                if nom and uploaded:
                    with st.spinner("Ajout en cours..."):
                        try:
                            b64 = base64.b64encode(uploaded.read()).decode()
                            res_img = requests.post("https://api.imgbb.com/1/upload", 
                                                  data={"key": st.secrets.get("IMGBB_API_KEY", "70be83b276ba6ccbf03b71597dfc2a5d"), "image": b64})
                            img_url = res_img.json()["data"]["url"]
                            
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
                            if r.status_code == 200:
                                st.success("✅ Article ajouté avec succès !")
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error("Erreur lors de l'ajout")
                        except Exception as e:
                            st.error(f"Erreur : {e}")
        
        # LISTE + MODIFICATION + SUPPRESSION
        st.subheader("📋 Articles existants")
        if not df_admin.empty:
            st.dataframe(df_admin[['nom', 'prix', 'tailles', 'couleurs', 'stock']], use_container_width=True)
            
            article = st.selectbox("Sélectionner un article", df_admin['nom'].dropna().astype(str).unique())
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Supprimer", type="primary"):
                    try:
                        r = requests.post(URL_PASSERELLE, json={"action": "suppression_article", "nom": article})
                        st.success("Article supprimé !")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(e)
            with col2:
                st.info("Modification complète disponible dans la prochaine version")
        else:
            st.info("Aucun article pour le moment")
            
    elif password:
        st.error("Mot de passe incorrect")

st.caption("Collection Luxe N'Djamena © 2026")
