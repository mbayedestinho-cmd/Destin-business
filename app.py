import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time
import uuid
import re

st.set_page_config(page_title="Collection Luxe N'Djamena", page_icon="✨", layout="wide")

# ====================== CSS ======================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500&display=swap');
    .main-title {font-family: 'Playfair Display', serif; font-size: clamp(2.8rem, 8vw, 4.2rem); font-weight: 700; text-align: center; margin: 30px 0 20px 0; color: #fff;}
    .hero {background: linear-gradient(135deg, #1a1a2e 0%, #3a2a1a 45%, #b58328 100%); padding: 130px 20px; text-align: center; color: white; border-radius: 20px; margin-bottom: 40px;}
    .product-card {background: white; border-radius: 16px; padding: 16px; box-shadow: 0 4px 25px rgba(0,0,0,0.06); transition: 0.3s; height: 100%;}
    .product-card:hover {transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.1);}
    .price {color: #b58328; font-weight: 700; font-size: 1.4rem;}
    .stock {font-size: 0.9rem; color: #28a745; font-weight: 500;}
    .stock-low {color: #dc3545; font-weight: 500;}
    </style>
""", unsafe_allow_html=True)

# ====================== CONFIG ======================
NUMERO_WHATSAPP_RAW = st.secrets.get("NUMERO_WHATSAPP", "")
# Fix : wa.me exige uniquement des chiffres (pas de +, espaces, tirets)
NUMERO_WHATSAPP = re.sub(r"\D", "", NUMERO_WHATSAPP_RAW)

MOT_DE_PASSE_ADMIN = st.secrets.get("ADMIN_PASSWORD", "")
URL_PASSERELLE = st.secrets.get("URL_PASSERELLE_WEB", "")
ID_SHEET = st.secrets.get("ID_DU_SHEET", "").strip()
IMGBB_API_KEY = st.secrets.get("IMGBB_API_KEY", "")

# Fix : avertir clairement si la config est incomplète plutôt que planter plus loin
_missing = [name for name, val in [
    ("NUMERO_WHATSAPP", NUMERO_WHATSAPP_RAW),
    ("URL_PASSERELLE_WEB", URL_PASSERELLE),
    ("ID_DU_SHEET", ID_SHEET),
] if not val]
if _missing:
    st.warning(f"⚠️ Configuration incomplète dans les secrets : {', '.join(_missing)}")

st.markdown('<div class="hero"><h1 class="main-title">COLLECTION LUXE<br>N\'DJAMENA</h1></div>', unsafe_allow_html=True)

if 'cart' not in st.session_state:
    st.session_state.cart = []

# ====================== HELPERS ======================
def format_fcfa(n):
    return f"{n:,.0f}".replace(",", " ")


def upload_image_to_imgbb(file_bytes):
    """Upload une image sur ImgBB. Retourne (url, erreur)."""
    if not IMGBB_API_KEY:
        return None, "Clé IMGBB_API_KEY manquante dans les secrets."
    try:
        b64 = base64.b64encode(file_bytes).decode()
        res = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": b64},
            timeout=30,
        )
        if res.status_code != 200:
            return None, f"Échec de l'upload ImgBB (code {res.status_code})."
        data = res.json()
        if "data" not in data or "url" not in data["data"]:
            return None, "Réponse ImgBB inattendue."
        return data["data"]["url"], None
    except requests.exceptions.RequestException as e:
        return None, f"Erreur réseau ImgBB : {e}"
    except Exception as e:
        return None, f"Erreur ImgBB : {e}"


def post_to_passerelle(payload, timeout=20):
    """Envoie une requête à la passerelle Google. Retourne (json_ou_None, erreur)."""
    if not URL_PASSERELLE:
        return None, "URL_PASSERELLE_WEB n'est pas configurée dans les secrets."
    try:
        r = requests.post(URL_PASSERELLE, json=payload, timeout=timeout)
        if r.status_code != 200:
            return None, f"Erreur serveur (code {r.status_code})."
        try:
            return r.json(), None
        except ValueError:
            return None, "Réponse invalide du serveur (pas du JSON)."
    except requests.exceptions.Timeout:
        return None, "Le serveur met trop de temps à répondre."
    except requests.exceptions.RequestException as e:
        return None, f"Erreur réseau : {e}"


# ====================== CHARGEMENT DONNÉES ======================
@st.cache_data(ttl=120)
def load_data(sheet_id, sheet_name="Catalogue"):
    if not sheet_id:
        return pd.DataFrame()
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        df = pd.read_csv(url)
        df.columns = [col.lower().strip() for col in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^unnamed', case=False)]

        # Fix : éviter un KeyError si la feuille n'a pas les bonnes colonnes
        required = {"nom", "prix"}
        missing_cols = required - set(df.columns)
        if missing_cols:
            st.error(f"Colonnes manquantes dans la feuille '{sheet_name}' : {', '.join(missing_cols)}")
            return pd.DataFrame()

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
            image_url = str(row.get('image', '') or '')

            # Sécurisation : évite le crash si le stock est vide ou non numérique
            stock_tmp = pd.to_numeric(row.get('stock', 0), errors='coerce')
            stock = int(stock_tmp) if pd.notna(stock_tmp) else 0

            stock_class = "stock-low" if stock < 5 else "stock"
            nom_article = str(row.get('nom', 'Article'))
            en_rupture = stock <= 0

            st.markdown(f"""
                <div class="product-card">
                    <a href="{image_url}" target="_blank">
                        <img src="{image_url}" style="width:100%; border-radius:12px; margin-bottom:10px; aspect-ratio:1/1; object-fit:cover;"
                             onerror="this.onerror=null;this.src='https://placehold.co/300x300?text=Image+non+disponible';">
                    </a>
                    <h3>{nom_article}</h3>
                    <div class="price">{format_fcfa(prix)} FCFA</div>
                    <div class="{stock_class}">Stock : {stock} pièce(s)</div>
                </div>
            """, unsafe_allow_html=True)

            if st.button(
                "🛒 Ajouter au panier" if not en_rupture else "❌ Rupture de stock",
                key=f"add_{idx}_{nom_article}",
                disabled=en_rupture,
            ):
                existing = next((item for item in st.session_state.cart if item['nom'] == nom_article), None)
                if existing:
                    existing['quantite'] += 1
                else:
                    st.session_state.cart.append({
                        "id": uuid.uuid4().hex, # Fix : id stable pour les widgets du panier
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
        st.success(f"**Total : {format_fcfa(total)} FCFA**")

        item_to_delete = None
        for item in st.session_state.cart:
            # Fix : clé basée sur un id stable, pas sur l'index de la liste
            item_id = item["id"]
            c1, c2, c3 = st.columns([5, 2, 1])
            with c1:
                st.write(f"{item['nom']}")
            with c2:
                new_q = st.number_input("Qté", min_value=1, value=item['quantite'], key=f"q_{item_id}")
                item['quantite'] = new_q
            with c3:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{item_id}"):
                    item_to_delete = item_id

        if item_to_delete:
            st.session_state.cart = [i for i in st.session_state.cart if i["id"] != item_to_delete]
            st.rerun()

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            msg = "Bonjour, voici ma commande :\n\n"
            for item in st.session_state.cart:
                msg += f"- {item['nom']} × {item['quantite']} = {format_fcfa(item['prix'] * item['quantite'])} FCFA\n"
            msg += f"\nTotal : {format_fcfa(total)} FCFA"
            if NUMERO_WHATSAPP:
                st.link_button("📱 WhatsApp", f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}", use_container_width=True)
            else:
                st.button("📱 WhatsApp", disabled=True, use_container_width=True, help="Numéro WhatsApp non configuré")

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
                    reponse_google, err = post_to_passerelle(payload, timeout=15)
                    if err:
                        st.error(f"❌ {err}")
                    elif reponse_google.get("status") == "success":
                        st.success("✅ Commande enregistrée et notification Telegram envoyée !")
                        st.session_state.cart = []
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ Erreur Google : {reponse_google.get('message')}")
    else:
        st.info("Votre panier est vide.")

    # ====================== ADMINISTRATION ======================
    st.markdown("---")
    st.header("⚙️ Administration")
    password = st.text_input("Mot de passe admin", type="password")

    if password and MOT_DE_PASSE_ADMIN and password == MOT_DE_PASSE_ADMIN:
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
                    if not nom or not uploaded:
                        st.warning("Veuillez remplir le nom et ajouter une photo.")
                    elif not IMGBB_API_KEY:
                        st.error("Clé IMGBB_API_KEY manquante dans les secrets.")
                    else:
                        with st.spinner("Upload + enregistrement..."):
                            img_url, err = upload_image_to_imgbb(uploaded.getvalue())
                            if err:
                                st.error(f"❌ {err}")
                            else:
                                payload = {
                                    "action": "ajout_article",
                                    "password": MOT_DE_PASSE_ADMIN,
                                    "nom": nom, "prix": prix, "image": img_url,
                                    "tailles": tailles, "couleurs": couleurs,
                                    "categorie": categorie, "stock": stock
                                }
                                _, err = post_to_passerelle(payload)
                                if err:
                                    st.error(f"❌ {err}")
                                else:
                                    st.success("✅ Article ajouté avec succès !")
                                    time.sleep(1.5)
                                    st.cache_data.clear()
                                    st.rerun()

        with tab2:
            st.subheader("Modifier un article")
            if not df_catalogue.empty:
                noms = df_catalogue['nom'].dropna().astype(str).unique().tolist()
                article_to_edit = st.selectbox("Choisir l'article à modifier", noms)

                if article_to_edit:
                    art = df_catalogue[df_catalogue['nom'].astype(str) == article_to_edit].iloc[0]

                    prix_init_tmp = pd.to_numeric(art.get('prix', 0), errors='coerce')
                    prix_initial = int(prix_init_tmp) if pd.notna(prix_init_tmp) else 0

                    stock_init_tmp = pd.to_numeric(art.get('stock', 0), errors='coerce')
                    stock_initial = int(stock_init_tmp) if pd.notna(stock_init_tmp) else 0

                    with st.form("edit_form"):
                        new_nom = st.text_input("Nouveau nom", art.get('nom', ''))
                        new_prix = st.number_input("Nouveau prix", value=prix_initial)
                        new_tailles = st.text_input("Tailles", art.get('tailles', 'Unique'))
                        new_couleurs = st.text_input("Couleurs", art.get('couleurs', ''))
                        new_categorie = st.text_input("Catégorie", art.get('categorie', 'Vêtements'))
                        new_stock = st.number_input("Stock", value=stock_initial)
                        new_image = st.file_uploader("Nouvelle photo (optionnel)", type=["jpg", "png", "jpeg"])

                        if st.form_submit_button("Enregistrer les modifications"):
                            with st.spinner("Mise à jour..."):
                                img_url = str(art.get('image', '') or '')
                                upload_err = None
                                if new_image is not None:
                                    img_url_new, upload_err = upload_image_to_imgbb(new_image.getvalue())
                                    if not upload_err:
                                        img_url = img_url_new

                                if upload_err:
                                    st.error(f"❌ {upload_err}")
                                else:
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
                                    _, err = post_to_passerelle(payload)
                                    if err:
                                        st.error(f"❌ {err}")
                                    else:
                                        st.success("✅ Article modifié avec succès !")
                                        time.sleep(1.5)
                                        st.cache_data.clear()
                                        st.rerun()
            else:
                st.info("Aucun article dans le catalogue.")

        with tab3:
            st.subheader("Supprimer un article")
            if not df_catalogue.empty:
                article_suppr = st.selectbox("Choisir l'article à supprimer", df_catalogue['nom'].dropna().astype(str).unique())

                confirm = st.checkbox("Je confirme la suppression définitive de cet article")

                if st.button("🗑️ Supprimer définitivement", type="primary", disabled=not confirm):
                    with st.spinner("Suppression en cours..."):
                        payload = {
                            "action": "suppression_article",
                            "password": MOT_DE_PASSE_ADMIN,
                            "nom": article_suppr
                        }
                        _, err = post_to_passerelle(payload)
                        if err:
                            st.error(f"❌ {err}")
                        else:
                            st.success("✅ Article supprimé avec succès !")
                            time.sleep(1.5)
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.info("Aucun article dans le catalogue.")

    elif password:
        st.error("❌ Mot de passe incorrect")

st.caption("Collection Luxe N'Djamena © 2026")
