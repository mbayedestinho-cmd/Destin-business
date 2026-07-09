
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
    .stock {font-size: 0.9rem; color: #28a745; font-weight: 500;}
    .stock-low {color: #dc3545; font-weight: 500;}
    </style>
""", unsafe_allow_html=True)

# ====================== CONFIG ======================
NUMERO_WHATSAPP = st.secrets.get("NUMERO_WHATSAPP", "")
MOT_DE_PASSE_ADMIN = st.secrets.get("ADMIN_PASSWORD", "")
URL_PASSERELLE = st.secrets.get("URL_PASSERELLE_WEB", "")
ID_SHEET = st.secrets.get("ID_DU_SHEET", "")
if ID_SHEET: 
    ID_SHEET = ID_SHEET.strip()
IMGBB_API_KEY = st.secrets.get("IMGBB_API_KEY", "")

st.markdown('<div class="hero"><h1 class="main-title">COLLECTION LUXE<br>N\'DJAMENA</h1></div>', unsafe_allow_html=True)

if 'cart' not in st.session_state:
    st.session_state.cart = []

# ====================== CHARGEMENT DONNÉES ======================
@st.cache_data(ttl=120)
def load_data(sheet_id, sheet_name="Catalogue"):
    if not sheet_id:
        return pd.DataFrame()
    try:
        # L'URL est simplifiée, ttl=120 gère déjà le rafraîchissement
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        df = pd.read_csv(url)
        df.columns = [col.lower().strip() for col in df.columns]
        # Nettoyage des colonnes fantômes et des lignes vides
        df = df.loc[:, ~df.columns.str.contains('^unnamed', case=False)]
        df = df.dropna(subset=['nom', 'prix'])
        return df
    except Exception as e:
        st.error(f"Erreur de chargement des données : {e}")
        return pd.DataFrame()

df_catalogue = load_data(ID_SHEET, "Catalogue")

# ====================== FILTRES ======================
st.subheader("Notre Collection")

col1, col2, col3, col4, col5 = st.columns([2.5, 1.8, 1.5, 1.5, 1.5])

with col1: 
    search = st.text_input("🔍 Rechercher par nom", "")
with col2: 
    min_price, max_price = st.slider("Fourchette de prix (FCFA)", 0, 500000, (0, 300000), 10000)

cats = ["Toutes"]
tailles_list = ["Toutes"]
if not df_catalogue.empty:
    if 'categorie' in df_catalogue.columns:
        cats += sorted(df_catalogue['categorie'].dropna().astype(str).unique())
    if 'tailles' in df_catalogue.columns:
        tailles_list += sorted(df_catalogue['tailles'].dropna().astype(str).unique())

with col3: 
    cat_filter = st.selectbox("Catégorie", cats)
with col4:
    taille_filter = st.selectbox("Taille", tailles_list)
with col5:
    sort_option = st.selectbox("Trier par", ["Pertinence", "Prix croissant", "Prix décroissant"])

# ====================== APPLICATION DES FILTRES ======================
df_f = df_catalogue.copy()

if not df_f.empty:
    if search:
        df_f = df_f[df_f['nom'].astype(str).str.contains(search, case=False, na=False)]
    if cat_filter != "Toutes" and 'categorie' in df_f.columns:
        df_f = df_f[df_f['categorie'].astype(str).str.contains(cat_filter, case=False, na=False)]
    if taille_filter != "Toutes" and 'tailles' in df_f.columns:
        df_f = df_f[df_f['tailles'].astype(str).str.contains(taille_filter, case=False, na=False)]

    # Conversion stricte des prix pour le tri
    df_f['prix_numeric'] = pd.to_numeric(df_f['prix'], errors='coerce').fillna(0)
    df_f = df_f[(df_f['prix_numeric'] >= min_price) & (df_f['prix_numeric'] <= max_price)]

    if sort_option == "Prix croissant":
        df_f = df_f.sort_values('prix_numeric')
    elif sort_option == "Prix décroissant":
        df_f = df_f.sort_values('prix_numeric', ascending=False)

# ====================== AFFICHAGE PRODUITS ======================
if not df_f.empty:
    cols = st.columns(3)
    for idx, row in df_f.reset_index(drop=True).iterrows():
        with cols[idx % 3]:
            prix = int(row['prix_numeric'])
            image_url = str(row.get('image', ''))
            stock = int(pd.to_numeric(row.get('stock', 0), errors='coerce'))
            stock_class = "stock-low" if stock < 5 else "stock"
            nom_article = str(row.get('nom', 'Article'))
            
            st.markdown(f"""
                <div class="product-card">
                    <a href="{image_url}" target="_blank">
                        <img src="{image_url}" style="width:100%; border-radius:12px; margin-bottom:10px; aspect-ratio:1/1; object-fit:cover;" 
                             onerror="this.src='https://via.placeholder.com/300x300?text=Image+non+disponible';">
                    </a>
                    <h3>{nom_article}</h3>
                    <div class="price">{prix:,} FCFA</div>
                    <div class="{stock_class}">Stock : {stock} pièce(s)</div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("🛒 Ajouter au panier", key=f"add_{idx}_{hash(nom_article)}"):
                existing = next((item for item in st.session_state.cart if item['nom'] == nom_article), None)
                if existing:
                    existing['quantite'] += 1
                else:
                    st.session_state.cart.append({
                        "nom": nom_article, 
                        "prix": prix, 
                        "image": image_url, 
                        "quantite": 1
                    })
                st.toast(f"✅ {nom_article} ajouté au panier !", icon="🛍️")
else:
    st.info("Aucun article ne correspond à vos critères ou le catalogue est vide.")

# ====================== PANIER ======================
with st.sidebar:
    st.header("🛍️ Mon Panier")
    if st.session_state.cart:
        total = sum(item['prix'] * item['quantite'] for item in st.session_state.cart)
        st.success(f"**Total : {total:,} FCFA**".replace(",", " "))

        for i, item in enumerate(st.session_state.cart.copy()):
            c1, c2, c3 = st.columns([5, 2, 1])
            with c1: 
                st.write(f"{item['nom']}")
            with c2:
                # Retrait du st.rerun() inutile, Streamlit gère le state tout seul
                new_q = st.number_input("Qté", min_value=1, value=item['quantite'], key=f"q_{i}")
                st.session_state.cart[i]['quantite'] = new_q
            with c3:
                # Ajout de padding pour aligner la corbeille avec l'input
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            msg = "Bonjour, voici ma commande :\n\n"
            for item in st.session_state.cart:
                msg += f"- {item['nom']} × {item['quantite']} = {item['prix'] * item['quantite']:,} FCFA\n"
            msg += f"\n**Total : {total:,} FCFA**"
            st.link_button("📱 WhatsApp", f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}", use_container_width=True)

        with col2:
            if st.button("✅ Valider", type="primary", use_container_width=True):
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
                            st.success("✅ Commande enregistrée !")
                            st.session_state.cart = []
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Erreur serveur.")
                    except Exception as e:
                        st.error(f"Erreur réseau : {e}")
    else:
        st.info("Votre panier est vide.")

    # ====================== ADMINISTRATION ======================
    st.markdown("---")
    st.header("⚙️ Administration")
    password = st.text_input("Mot de passe admin", type="password")

    if password == MOT_DE_PASSE_ADMIN and MOT_DE_PASSE_ADMIN != "":
        st.success("✅ Accès autorisé")
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer"])

        with tab1:
            st.subheader("Ajouter un article")
            with st.form("add_form", clear_on_submit=True):
                nom = st.text_input("Nom de l'article*")
                prix = st.number_input("Prix (FCFA)", min_value=0, step=1000)
                uploaded = st.file_uploader("Photo*", type=["jpg", "png", "jpeg"])
                tailles = st.text_input("Tailles", "Unique")
                couleurs = st.text_input("Couleurs", "")
                categorie = st.text_input("Catégorie", "Vêtements")
                stock = st.number_input("Stock", min_value=0, value=10)
                
                if st.form_submit_button("Ajouter au catalogue"):
                    if nom and uploaded and IMGBB_API_KEY:
                        with st.spinner("Upload + enregistrement..."):
                            try:
                                b64 = base64.b64encode(uploaded.getvalue()).decode()
                                res = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": b64})
                                if res.status_code == 200 and "data" in res.json():
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
                                        st.success("✅ Article ajouté avec succès !")
                                        time.sleep(1.5)
                                        st.cache_data.clear() # Force le rafraîchissement des données
                                        st.rerun()
                                    else:
                                        st.error(f"Erreur API Google : {r.text}")
                                else:
                                    st.error("Échec de l'upload de l'image (Vérifiez la clé ImgBB).")
                            except Exception as e:
                                st.error(f"Erreur technique : {e}")
                    else:
                        st.warning("Veuillez remplir le nom et ajouter une photo.")

        with tab2:
            st.subheader("Modifier un article")
            if not df_catalogue.empty:
                noms = df_catalogue['nom'].dropna().astype(str).unique().tolist()
                article_to_edit = st.selectbox("Choisir l'article à modifier", noms)
                
                if article_to_edit:
                    art = df_catalogue[df_catalogue['nom'].astype(str) == article_to_edit].iloc[0]
                    with st.form("edit_form"):
                        new_nom = st.text_input("Nouveau nom", art.get('nom', ''))
                        new_prix = st.number_input("Nouveau prix", value=int(pd.to_numeric(art.get('prix', 0), errors='coerce')))
                        new_tailles = st.text_input("Tailles", art.get('tailles', 'Unique'))
                        new_couleurs = st.text_input("Couleurs", art.get('couleurs', ''))
                        new_categorie = st.text_input("Catégorie", art.get('categorie', 'Vêtements'))
                        new_stock = st.number_input("Stock", value=int(pd.to_numeric(art.get('stock', 0), errors='coerce')))
                        new_image = st.file_uploader("Nouvelle photo (optionnel)", type=["jpg","png","jpeg"])
                        
                        if st.form_submit_button("Enregistrer les modifications"):
                            with st.spinner("Mise à jour..."):
                                try:
                                    img_url = str(art.get('image', ''))
                                    if new_image is not None:
                                        b64 = base64.b64encode(new_image.getvalue()).decode()
                                        res = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": b64})
                                        if "data" in res.json():
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
                                        st.success("✅ Article modifié avec succès !")
                                        time.sleep(1.5)
                                        st.cache_data.clear()
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur : {e}")

        with tab3:
            st.subheader("Supprimer un article")
            if not df_catalogue.empty:
                article_suppr = st.selectbox("Choisir l'article à supprimer", df_catalogue['nom'].dropna().astype(str).unique())
                
                # Correction du système de case à cocher (placée AVANT le bouton)
                confirm = st.checkbox("Je confirme la suppression définitive de cet article")
                
                # Le bouton est désactivé tant que la case n'est pas cochée
                if st.button("🗑️ Supprimer définitivement", type="primary", disabled=not confirm):
                    with st.spinner("Suppression en cours..."):
                        try:
                            payload = {
                                "action": "suppression_article",
                                "password": MOT_DE_PASSE_ADMIN,
                                "nom": article_suppr
                            }
                            r = requests.post(URL_PASSERELLE, json=payload, timeout=15)
                            if r.status_code == 200:
                                st.success("✅ Article supprimé avec succès !")
                                time.sleep(1.5)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("Erreur du serveur lors de la suppression.")
                        except Exception as e:
                            st.error(f"Erreur : {e}")

    elif password != "":
        st.error("❌ Mot de passe incorrect")

st.caption("Collection Luxe N'Djamena © 2026")
