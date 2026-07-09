import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time

st.set_page_config(page_title="Collection Luxe N'Djamena", page_icon="✨", layout="wide")

# ====================== CSS ======================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500&display=swap');
    .main-title {font-family: 'Playfair Display', serif; font-size: clamp(2.8rem, 8vw, 4.2rem); font-weight: 700; text-align: center; margin: 30px 0 20px 0; color: #fff;}
    .hero {background: linear-gradient(rgba(0,0,0,0.65), rgba(0,0,0,0.65)), url('https://source.unsplash.com/random/1600x900/?luxury-fashion,african'); background-size: cover; background-position: center; padding: 130px 20px; text-align: center; color: white; border-radius: 20px; margin-bottom: 40px;}
    .product-card {background: white; border-radius: 16px; padding: 16px; box-shadow: 0 4px 25px rgba(0,0,0,0.06); transition: 0.3s; height: 100%;}
    .product-card:hover {transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.1);}
    .price {color: #b58328; font-weight: 700; font-size: 1.4rem;}
    </style>
""", unsafe_allow_html=True)

# ====================== CONFIG ======================
NUMERO_WHATSAPP = st.secrets.get("NUMERO_WHATSAPP")
MOT_DE_PASSE_ADMIN = st.secrets.get("ADMIN_PASSWORD")
URL_PASSERELLE = st.secrets.get("URL_PASSERELLE_WEB")
ID_SHEET = st.secrets.get("ID_DU_SHEET", "").strip()
IMGBB_API_KEY = st.secrets.get("IMGBB_API_KEY")

st.markdown('<div class="hero"><h1 class="main-title">COLLECTION LUXE<br>N\'DJAMENA</h1></div>', unsafe_allow_html=True)

if 'cart' not in st.session_state:
    st.session_state.cart = []

# ====================== CHARGEMENT DONNÉES (CORRIGÉ) ======================
@st.cache_data(ttl=120)
def load_data(sheet_name="Catalogue"):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/gviz/tq?tqx=out:csv&sheet={sheet_name}&nocache={int(time.time())}"
        df = pd.read_csv(url)
        df.columns = [col.lower().strip() for col in df.columns]
        # Ligne corrigée :
        return df.loc[:, \~df.columns.str.contains('^unnamed', case=False)]
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return pd.DataFrame()

df_catalogue = load_data("Catalogue")
df_commandes = load_data("Commandes")

# ====================== CATALOGUE ======================
st.subheader("Notre Collection")
col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
with col1: search = st.text_input("🔍 Rechercher", "")
with col2: max_price = st.slider("Prix max (FCFA)", 0, 500000, 300000, 10000)
with col3: 
    cats = ["Toutes"] + sorted(df_catalogue.get('categorie', pd.Series()).dropna().astype(str).unique())
    cat_filter = st.selectbox("Catégorie", cats)
with col4:
    couleurs = ["Toutes"] + sorted(df_catalogue.get('couleurs', pd.Series()).dropna().astype(str).unique())
    couleur_filter = st.selectbox("Couleur", couleurs)

df_f = df_catalogue.copy()
if search: df_f = df_f[df_f['nom'].astype(str).str.contains(search, case=False, na=False)]
if cat_filter != "Toutes": df_f = df_f[df_f.get('categorie','').astype(str).str.contains(cat_filter, case=False, na=False)]
if couleur_filter != "Toutes": df_f = df_f[df_f.get('couleurs','').astype(str).str.contains(couleur_filter, case=False, na=False)]

if not df_f.empty:
    df_f['prix_numeric'] = pd.to_numeric(df_f.get('prix'), errors='coerce')
    df_f = df_f[df_f['prix_numeric'] <= max_price]

if not df_f.empty:
    cols = st.columns(3)
    for idx, row in df_f.reset_index(drop=True).iterrows():
        with cols[idx % 3]:
            prix = int(float(row.get('prix_numeric', row.get('prix', 0))))
            st.markdown(f"""
                <div class="product-card">
                    <img src="{row['image']}" style="width:100%; border-radius:12px; margin-bottom:10px; aspect-ratio:1/1; object-fit:cover;">
                    <h3>{row['nom']}</h3>
                    <div class="price">{prix:,} FCFA</div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("🛒 Ajouter au panier", key=f"add_{idx}"):
                existing = next((item for item in st.session_state.cart if item['nom'] == row['nom']), None)
                if existing:
                    existing['quantite'] += 1
                else:
                    st.session_state.cart.append({"nom": row['nom'], "prix": prix, "image": row['image'], "quantite": 1})
                st.success("✅ Ajouté !")
                st.rerun()
else:
    st.info("Aucun article trouvé.")

# ====================== PANIER ======================
with st.sidebar:
    st.header("🛍️ Mon Panier")
    if st.session_state.cart:
        total = sum(item['prix'] * item.get('quantite', 1) for item in st.session_state.cart)
        st.write(f"**Total : {total:,} FCFA**".replace(",", " "))

        for i, item in enumerate(st.session_state.cart):
            c1, c2, c3 = st.columns([5, 2, 1])
            with c1: st.write(f"{item['nom']} × {item.get('quantite', 1)}")
            with c2:
                q = st.number_input("Qté", min_value=1, value=item.get('quantite', 1), key=f"q{i}")
                if q != item.get('quantite', 1):
                    item['quantite'] = q
                    st.rerun()
            with c3:
                if st.button("🗑️", key=f"del{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📱 WhatsApp", type="secondary"):
                msg = "Bonjour, voici ma commande :\n\n"
                for item in st.session_state.cart:
                    msg += f"- {item['nom']} × {item.get('quantite',1)} = {item['prix']*item.get('quantite',1):,} FCFA\n".replace(",", " ")
                msg += f"\n**Total : {total:,} FCFA**".replace(",", " ")
                st.link_button("Ouvrir WhatsApp", f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}")

        with col2:
            if st.button("✅ Enregistrer + Telegram", type="primary"):
                with st.spinner("Enregistrement..."):
                    payload = {
                        "action": "nouvelle_commande",
                        "password": MOT_DE_PASSE_ADMIN,
                        "client_nom": "Client Site Web",
                        "articles": st.session_state.cart,
                        "total": total
                    }
                    try:
                        r = requests.post(URL_PASSERELLE, json=payload, timeout=15)
                        if r.status_code == 200:
                            st.success("✅ Commande enregistrée ! Notification Telegram envoyée.")
                            st.session_state.cart = []
                            st.rerun()
                    except:
                        st.error("Erreur lors de l'enregistrement")
    else:
        st.info("Votre panier est vide.")

    # ====================== ADMINISTRATION ======================
    st.markdown("---")
    st.header("⚙️ Administration")
    password = st.text_input("Mot de passe admin", type="password")

    if password == MOT_DE_PASSE_ADMIN:
        st.success("✅ Accès autorisé")
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer"])

        with tab1:
            st.subheader("Ajouter un article")
            with st.form("add_form", clear_on_submit=True):
                nom = st.text_input("Nom de l'article*")
                prix = st.number_input("Prix (FCFA)", min_value=0)
                uploaded = st.file_uploader("Photo*", type=["jpg", "png", "jpeg"])
                tailles = st.text_input("Tailles", "Unique")
                couleurs = st.text_input("Couleurs", "")
                categorie = st.text_input("Catégorie", "Vêtements")
                stock = st.number_input("Stock", min_value=0, value=10)
                
                if st.form_submit_button("Ajouter au catalogue"):
                    if nom and uploaded:
                        with st.spinner("Ajout en cours..."):
                            try:
                                b64 = base64.b64encode(uploaded.getvalue()).decode()
                                res = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": b64})
                                img_url = res.json()["data"]["url"]
                                
                                payload = {
                                    "action": "ajout_article",
                                    "password": MOT_DE_PASSE_ADMIN,
                                    "nom": nom, "prix": prix, "image": img_url,
                                    "tailles": tailles, "couleurs": couleurs,
                                    "categorie": categorie, "stock": stock
                                }
                                r = requests.post(URL_PASSERELLE, json=payload, timeout=20)
                                if r.status_code == 200:
                                    st.success("✅ Article ajouté !")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Erreur : {e}")

        with tab2:
            st.subheader("Modifier un article")
            if not df_catalogue.empty:
                noms = df_catalogue['nom'].dropna().astype(str).unique()
                article_to_edit = st.selectbox("Choisir l'article", noms)
                if article_to_edit:
                    art = df_catalogue[df_catalogue['nom'].astype(str) == article_to_edit].iloc[0]
                    with st.form("edit_form"):
                        new_nom = st.text_input("Nouveau nom", art['nom'])
                        new_prix = st.number_input("Nouveau prix", value=int(float(art.get('prix', 0))))
                        new_tailles = st.text_input("Tailles", art.get('tailles', 'Unique'))
                        new_couleurs = st.text_input("Couleurs", art.get('couleurs', ''))
                        new_categorie = st.text_input("Catégorie", art.get('categorie', 'Vêtements'))
                        new_stock = st.number_input("Stock", value=int(art.get('stock', 0)))
                        new_image = st.file_uploader("Nouvelle photo (optionnel)", type=["jpg","png","jpeg"])
                        
                        if st.form_submit_button("Enregistrer les modifications"):
                            with st.spinner("Mise à jour..."):
                                try:
                                    img_url = art.get('image')
                                    if new_image is not None:
                                        b64 = base64.b64encode(new_image.getvalue()).decode()
                                        res = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": b64})
                                        img_url = res.json()["data"]["url"]
                                    
                                    payload = {
                                        "action": "modification_article",
                                        "password": MOT_DE_PASSE_ADMIN,
                                        "ancien_nom": article_to_edit,
                                        "nom": new_nom,
                                        "prix": new_prix,
                                        "image": img_url,
                                        "tailles": new_tailles,
                                        "couleurs": new_couleurs,
                                        "categorie": new_categorie,
                                        "stock": new_stock
                                    }
                                    r = requests.post(URL_PASSERELLE, json=payload, timeout=20)
                                    if r.status_code == 200:
                                        st.success("✅ Article modifié !")
                                        time.sleep(1)
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur : {e}")

        with tab3:
            st.subheader("Supprimer un article")
            if not df_catalogue.empty:
                article_suppr = st.selectbox("Choisir l'article à supprimer", df_catalogue['nom'].dropna().astype(str).unique())
                if st.button("🗑️ Supprimer définitivement", type="primary"):
                    try:
                        payload = {
                            "action": "suppression_article",
                            "password": MOT_DE_PASSE_ADMIN,
                            "nom": article_suppr
                        }
                        r = requests.post(URL_PASSERELLE, json=payload)
                        if r.status_code == 200:
                            st.success("Article supprimé !")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
    elif password:
        st.error("Mot de passe incorrect")

st.caption("Collection Luxe N'Djamena © 2026")
