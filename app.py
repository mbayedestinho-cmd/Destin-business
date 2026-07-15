import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time
import uuid
import re
import unicodedata

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
NUMERO_WHATSAPP = re.sub(r"\D", "", NUMERO_WHATSAPP_RAW)

MOT_DE_PASSE_ADMIN = st.secrets.get("ADMIN_PASSWORD", "")
URL_PASSERELLE = st.secrets.get("URL_PASSERELLE_WEB", "")
ID_SHEET = st.secrets.get("ID_DU_SHEET", "").strip()
IMGBB_API_KEY = st.secrets.get("IMGBB_API_KEY", "")

if not all([NUMERO_WHATSAPP, URL_PASSERELLE, ID_SHEET, MOT_DE_PASSE_ADMIN, IMGBB_API_KEY]):
    st.error("⚠️ Configuration incomplète dans les secrets Streamlit.")
    st.stop()

st.markdown('<div class="hero"><h1 class="main-title">COLLECTION LUXE<br>N\'DJAMENA</h1></div>', unsafe_allow_html=True)

# ====================== SESSION STATE ======================
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'refresh_token' not in st.session_state:
    st.session_state.refresh_token = 0
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False

# ====================== HELPERS ======================
def format_fcfa(n):
    return f"{int(n):,} FCFA".replace(",", " ")

def normalize_col(col):
    """Met en minuscule, retire les espaces et supprime les accents d'un nom de colonne."""
    col = str(col).lower().strip()
    col = ''.join(c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn')
    return col

def get_unique_values(df, col):
    """Retourne la liste des valeurs uniques d'une colonne, sans planter si elle est absente."""
    if df.empty or col not in df.columns:
        return ["Toutes"]
    return ["Toutes"] + sorted(df[col].dropna().astype(str).unique())

def upload_image_to_imgbb(file_bytes):
    try:
        b64 = base64.b64encode(file_bytes).decode()
        res = requests.post("https://api.imgbb.com/1/upload",
                           data={"key": IMGBB_API_KEY, "image": b64}, timeout=25)
        if res.status_code != 200:
            return None, "Erreur upload ImgBB"
        return res.json()["data"]["url"], None
    except Exception as e:
        return None, str(e)

def call_passerelle(payload, timeout=20):
    try:
        r = requests.post(URL_PASSERELLE, json=payload, timeout=timeout)
        if r.status_code != 200:
            return None, f"Erreur serveur ({r.status_code})"
        return r.json(), None
    except Exception as e:
        return None, str(e)

# ====================== CHARGEMENT DONNÉES ======================
# ⚠️ FIX : le paramètre ne doit PAS commencer par "_" (Streamlit ignore les
# paramètres préfixés par underscore dans le calcul de la clé de cache, donc
# faire varier refresh_token n'invalidait jamais le cache). En complément,
# on appelle explicitement load_data.clear() après chaque mutation réussie.
@st.cache_data(ttl=90, show_spinner=False)
def load_data(sheet_id, refresh_token=0):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Catalogue"
        df = pd.read_csv(url)
        df.columns = [normalize_col(col) for col in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^unnamed', case=False)]
        df = df.dropna(subset=['nom', 'prix'])
        df['prix_numeric'] = pd.to_numeric(df['prix'], errors='coerce').fillna(0)
        df['stock'] = pd.to_numeric(df.get('stock', 0), errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return pd.DataFrame()

df_catalogue = load_data(ID_SHEET, st.session_state.refresh_token)

# ====================== FILTRES ======================
st.subheader("Notre Collection")
col1, col2, col3, col4, col5 = st.columns([2.5, 1.8, 1.5, 1.5, 1.5])

with col1:
    search = st.text_input("🔍 Rechercher par nom", "")
with col2:
    min_price, max_price = st.slider("Fourchette de prix (FCFA)", 0, 500000, (0, 300000), 10000)

cats = get_unique_values(df_catalogue, 'categorie')
tailles_list = get_unique_values(df_catalogue, 'tailles')

with col3:
    cat_filter = st.selectbox("Catégorie", cats)
with col4:
    taille_filter = st.selectbox("Taille", tailles_list)
with col5:
    sort_option = st.selectbox("Trier par", ["Pertinence", "Prix croissant", "Prix décroissant"])

# ====================== FILTRAGE ======================
df_f = df_catalogue.copy()
if not df_f.empty:
    if search:
        df_f = df_f[df_f['nom'].astype(str).str.contains(search, case=False, na=False)]
    if cat_filter != "Toutes" and 'categorie' in df_f.columns:
        df_f = df_f[df_f['categorie'].astype(str).str.contains(cat_filter, case=False, na=False)]
    if taille_filter != "Toutes" and 'tailles' in df_f.columns:
        df_f = df_f[df_f['tailles'].astype(str).str.contains(taille_filter, case=False, na=False)]

    df_f = df_f[(df_f['prix_numeric'] >= min_price) & (df_f['prix_numeric'] <= max_price)]

    if sort_option == "Prix croissant":
        df_f = df_f.sort_values('prix_numeric')
    elif sort_option == "Prix décroissant":
        df_f = df_f.sort_values('prix_numeric', ascending=False)

st.caption(f"**{len(df_f)} article(s)** trouvé(s)")

# ====================== AFFICHAGE PRODUITS ======================
if not df_f.empty:
    cols = st.columns(3)
    for idx, row in df_f.iterrows():
        with cols[idx % 3]:
            prix = int(row['prix_numeric'])
            stock = int(row['stock'])
            en_rupture = stock <= 0

            st.markdown(f"""
                <div class="product-card">
                    <a href="{row.get('image', '')}" target="_blank">
                        <img src="{row.get('image', '')}" style="width:100%; border-radius:12px; aspect-ratio:1/1; object-fit:cover;"
                             onerror="this.src='https://placehold.co/300x300?text=Image+non+disponible';">
                    </a>
                    <h3>{row['nom']}</h3>
                    <div class="price">{format_fcfa(prix)}</div>
                    <div class="{'stock-low' if stock < 5 else 'stock'}">Stock : {stock} pièce(s)</div>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🛒 Ajouter au panier" if not en_rupture else "❌ Rupture de stock",
                        key=f"add_{idx}_{row.get('nom')}", disabled=en_rupture):
                existing = next((item for item in st.session_state.cart if item['nom'] == row['nom']), None)
                if existing:
                    existing['quantite'] += 1
                else:
                    st.session_state.cart.append({
                        "id": str(uuid.uuid4()),
                        "nom": row['nom'],
                        "prix": prix,
                        "image": row.get('image', ''),
                        "quantite": 1
                    })
                st.toast(f"✅ {row['nom']} ajouté au panier !", icon="🛍️")
                st.rerun()
else:
    st.info("Aucun article ne correspond à vos critères.")

# ====================== PANIER ======================
with st.sidebar:
    st.header("🛍️ Mon Panier")
    if st.session_state.cart:
        total = sum(item['prix'] * item['quantite'] for item in st.session_state.cart)
        st.success(f"**Total : {format_fcfa(total)}**")

        for item in st.session_state.cart[:]:
            c1, c2, c3 = st.columns([5, 2, 1])
            with c1: st.write(item['nom'])
            with c2:
                item['quantite'] = st.number_input("Qté", min_value=1, value=item['quantite'], key=f"q_{item['id']}")
            with c3:
                if st.button("🗑️", key=f"del_{item['id']}"):
                    st.session_state.cart = [i for i in st.session_state.cart if i['id'] != item['id']]
                    st.rerun()

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            msg = "Bonjour, voici ma commande :\n\n" + "\n".join(
                [f"- {item['nom']} × {item['quantite']} = {format_fcfa(item['prix']*item['quantite'])} FCFA"
                 for item in st.session_state.cart]
            ) + f"\n\nTotal : {format_fcfa(total)} FCFA"
            st.link_button("📱 WhatsApp", f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}", use_container_width=True)

        with col_b:
            if st.button("✅ Valider Commande", type="primary", use_container_width=True):
                with st.spinner("Enregistrement..."):
                    payload = {
                        "action": "nouvelle_commande",
                        "password": MOT_DE_PASSE_ADMIN,
                        "client_nom": "Client Site Web",
                        "articles": st.session_state.cart,
                        "total": total
                    }
                    reponse, err = call_passerelle(payload)
                    if err or not reponse or reponse.get("status") != "success":
                        st.error(f"❌ Erreur lors de l'enregistrement : {err or (reponse or {}).get('message', 'réponse invalide')}")
                    else:
                        st.success("✅ Commande enregistrée avec succès !")
                        st.session_state.cart = []
                        time.sleep(3)
                        st.rerun()
    else:
        st.info("Votre panier est vide.")

    # ====================== ADMINISTRATION AVANCÉE ======================
    st.markdown("---")
    st.header("⚙️ Administration")
    pwd = st.text_input("Mot de passe admin", type="password", key="admin_input")

    if pwd:
        if pwd == MOT_DE_PASSE_ADMIN:
            st.session_state.admin_logged_in = True
        else:
            st.error("❌ Mot de passe incorrect")
            st.session_state.admin_logged_in = False

    if st.session_state.admin_logged_in:
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer"])

        with tab1:  # DASHBOARD
            st.subheader("📊 Tableau de Bord")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Articles totaux", len(df_catalogue))
            with col2:
                low_stock = len(df_catalogue[df_catalogue['stock'] < 5]) if not df_catalogue.empty else 0
                st.metric("Stock faible (< 5)", low_stock)

            with col3:
                stats_payload = {"action": "get_stats", "password": MOT_DE_PASSE_ADMIN}
                stats, _ = call_passerelle(stats_payload)
                total_sales = stats.get("total_sales", 0) if stats else 0
                st.metric("CA Total", format_fcfa(total_sales))

            with col4:
                orders_count = stats.get("orders_count", 0) if stats else 0
                st.metric("Commandes", orders_count)

            st.markdown("---")
            st.subheader("📋 Dernières Commandes")
            orders_payload = {"action": "get_orders", "password": MOT_DE_PASSE_ADMIN, "limit": 15}
            orders_data, err = call_passerelle(orders_payload)

            if orders_data and orders_data.get("status") == "success":
                orders_list = orders_data.get("orders", [])
                if orders_list:
                    orders_df = pd.DataFrame(orders_list)
                    orders_df['date'] = pd.to_datetime(orders_df['date']).dt.strftime("%d/%m/%Y %H:%M")
                    orders_df['total'] = orders_df['total'].apply(format_fcfa)
                    st.dataframe(orders_df[['date', 'client', 'total', 'articles_count']],
                               use_container_width=True, hide_index=True)

                    csv = orders_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Exporter en CSV", csv, "commandes.csv", "text/csv")
                else:
                    st.info("Aucune commande enregistrée.")
            else:
                st.warning("Impossible de charger les commandes.")

            st.subheader("⚠️ Alertes Stock")
            if not df_catalogue.empty:
                alerts = df_catalogue[df_catalogue['stock'] < 10].copy()
                if not alerts.empty:
                    st.dataframe(alerts[['nom', 'stock', 'prix']].sort_values('stock'),
                               use_container_width=True)
                else:
                    st.success("✅ Aucun stock critique")

        # ====================== AJOUTER ======================
        with tab2:
            st.subheader("➕ Ajouter un article")
            with st.form("add_form", clear_on_submit=True):
                nom = st.text_input("Nom de l'article *")
                prix = st.number_input("Prix (FCFA)", min_value=0, step=1000)
                uploaded = st.file_uploader("Photo *", type=["jpg", "png", "jpeg"])
                tailles = st.text_input("Tailles", "Unique")
                couleurs = st.text_input("Couleurs", "")
                categorie = st.text_input("Catégorie", "Vêtements")
                stock = st.number_input("Stock initial", min_value=0, value=10)

                if st.form_submit_button("Ajouter au catalogue"):
                    if not nom or not uploaded:
                        st.warning("Nom et photo sont obligatoires.")
                    else:
                        with st.spinner("Upload + enregistrement..."):
                            img_url, err = upload_image_to_imgbb(uploaded.getvalue())
                            if err:
                                st.error(err)
                            else:
                                payload = {
                                    "action": "ajout_article",
                                    "password": MOT_DE_PASSE_ADMIN,
                                    "nom": nom, "prix": prix, "image": img_url,
                                    "tailles": tailles, "couleurs": couleurs,
                                    "categorie": categorie, "stock": stock
                                }
                                reponse, err = call_passerelle(payload)
                                if err or not reponse or reponse.get("status") != "success":
                                    st.error(f"❌ Erreur : {err or (reponse or {}).get('message', 'réponse invalide')}")
                                else:
                                    st.success("✅ Article ajouté !")
                                    load_data.clear()  # 🔧 FIX cache
                                    st.session_state.refresh_token += 1
                                    time.sleep(1.5)
                                    st.rerun()

        # ====================== MODIFIER ======================
        with tab3:
            st.subheader("✏️ Modifier un article")
            if not df_catalogue.empty:
                noms = df_catalogue['nom'].dropna().astype(str).unique().tolist()
                article_to_edit = st.selectbox("Article à modifier", noms, key="select_edit")

                # Récupère la ligne actuelle de l'article sélectionné
                row_edit = df_catalogue[df_catalogue['nom'].astype(str) == article_to_edit].iloc[0]

                with st.form("edit_form"):
                    col_img1, col_img2 = st.columns([1, 2])
                    with col_img1:
                        st.image(row_edit.get('image', ''), width=120, caption="Photo actuelle")
                    with col_img2:
                        nouvelle_photo = st.file_uploader(
                            "Remplacer la photo (optionnel)", type=["jpg", "png", "jpeg"], key="edit_photo"
                        )

                    nouveau_nom = st.text_input("Nom de l'article", value=str(row_edit.get('nom', '')))
                    nouveau_prix = st.number_input(
                        "Prix (FCFA)", min_value=0, step=1000,
                        value=int(row_edit.get('prix_numeric', 0))
                    )
                    nouvelles_tailles = st.text_input(
                        "Tailles", value=str(row_edit.get('tailles', '') or '')
                    )
                    nouvelles_couleurs = st.text_input(
                        "Couleurs", value=str(row_edit.get('couleurs', '') or '')
                    )
                    nouvelle_categorie = st.text_input(
                        "Catégorie", value=str(row_edit.get('categorie', '') or '')
                    )
                    nouveau_stock = st.number_input(
                        "Stock", min_value=0, value=int(row_edit.get('stock', 0))
                    )

                    if st.form_submit_button("💾 Enregistrer les modifications"):
                        with st.spinner("Mise à jour en cours..."):
                            image_url = row_edit.get('image', '')
                            if nouvelle_photo is not None:
                                image_url, err = upload_image_to_imgbb(nouvelle_photo.getvalue())
                                if err:
                                    st.error(f"Erreur upload photo : {err}")
                                    st.stop()

                            payload = {
                                "action": "modification_article",
                                "password": MOT_DE_PASSE_ADMIN,
                                "ancien_nom": article_to_edit,
                                "nom": nouveau_nom,
                                "prix": nouveau_prix,
                                "image": image_url,
                                "tailles": nouvelles_tailles,
                                "couleurs": nouvelles_couleurs,
                                "categorie": nouvelle_categorie,
                                "stock": nouveau_stock
                            }
                            reponse, err = call_passerelle(payload)
                            if err or not reponse or reponse.get("status") != "success":
                                st.error(f"❌ Erreur lors de la mise à jour : {err or (reponse or {}).get('message', 'réponse invalide')}")
                            else:
                                st.success("✅ Article mis à jour !")
                                load_data.clear()  # 🔧 FIX cache
                                st.session_state.refresh_token += 1
                                time.sleep(1.5)
                                st.rerun()
            else:
                st.info("Aucun article disponible.")

        # ====================== SUPPRIMER ======================
        with tab4:
            st.subheader("🗑️ Supprimer un article")
            if not df_catalogue.empty:
                article_suppr = st.selectbox(
                    "Article à supprimer",
                    df_catalogue['nom'].dropna().astype(str).unique(),
                    key="select_delete"
                )

                row_suppr = df_catalogue[df_catalogue['nom'].astype(str) == article_suppr].iloc[0]
                col_prev1, col_prev2 = st.columns([1, 2])
                with col_prev1:
                    st.image(row_suppr.get('image', ''), width=120)
                with col_prev2:
                    st.write(f"**{article_suppr}**")
                    st.write(f"Prix : {format_fcfa(row_suppr.get('prix_numeric', 0))}")
                    st.write(f"Stock : {int(row_suppr.get('stock', 0))} pièce(s)")

                st.warning("⚠️ Cette action est irréversible.")

                # Réinitialise la confirmation si l'utilisateur change d'article
                if st.session_state.get("last_delete_target") != article_suppr:
                    st.session_state.confirm_delete = False
                    st.session_state.last_delete_target = article_suppr

                if not st.session_state.confirm_delete:
                    if st.button("🗑️ Supprimer cet article", type="primary", use_container_width=True):
                        st.session_state.confirm_delete = True
                        st.rerun()
                else:
                    st.error(f"Confirmer la suppression définitive de **{article_suppr}** ?")
                    col_conf1, col_conf2 = st.columns(2)
                    with col_conf1:
                        if st.button("✅ Oui, supprimer", type="primary", use_container_width=True):
                            with st.spinner("Suppression en cours..."):
                                payload = {
                                    "action": "suppression_article",
                                    "password": MOT_DE_PASSE_ADMIN,
                                    "nom": article_suppr
                                }
                                reponse, err = call_passerelle(payload)
                                if err or not reponse or reponse.get("status") != "success":
                                    st.error(f"❌ Erreur lors de la suppression : {err or (reponse or {}).get('message', '')}")
                                else:
                                    st.success("✅ Article supprimé !")
                                    load_data.clear()  # 🔧 FIX cache
                                    st.session_state.refresh_token += 1
                                    st.session_state.confirm_delete = False
                                    time.sleep(1.5)
                                    st.rerun()
                    with col_conf2:
                        if st.button("❌ Annuler", use_container_width=True):
                            st.session_state.confirm_delete = False
                            st.rerun()
            else:
                st.info("Aucun article disponible.")
