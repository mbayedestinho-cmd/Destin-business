import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import json
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

    /* ---- Bannière logo pleine largeur ---- */
    .hero-banner {
        position: relative;
        width: 100%;
        height: 340px;
        border-radius: 24px;
        overflow: hidden;
        margin-bottom: 40px;
        box-shadow: 0 15px 45px rgba(0,0,0,0.35);
    }
    .hero-banner img.hero-bg {
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        object-fit: cover;
        object-position: center 25%;
        filter: brightness(0.9);
    }
    .hero-banner::before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(180deg, rgba(15,10,5,0.15) 0%, rgba(15,10,5,0.55) 65%, rgba(15,10,5,0.92) 100%);
    }
    .hero-banner .hero-content {
        position: absolute;
        bottom: 0; left: 0; right: 0;
        padding: 30px 24px 26px 24px;
        text-align: center;
        z-index: 2;
    }
    .hero-banner .hero-content h1 {
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        font-size: clamp(2.2rem, 6vw, 3.6rem);
        color: #fff;
        margin: 0;
        letter-spacing: 0.5px;
        text-shadow: 0 4px 18px rgba(0,0,0,0.6);
    }
    .hero-banner .hero-content p {
        font-family: 'Poppins', sans-serif;
        font-weight: 300;
        letter-spacing: 3px;
        text-transform: uppercase;
        font-size: 0.8rem;
        color: #e8c98a;
        margin: 8px 0 0 0;
    }
    @media (max-width: 640px) {
        .hero-banner { height: 260px; border-radius: 18px; }
    }
    .product-card {background: white; border-radius: 16px; padding: 16px; box-shadow: 0 4px 25px rgba(0,0,0,0.06); transition: 0.3s; height: 100%; color: #1a1a1a;}
    .product-card h3 {color: #1a1a1a; margin: 12px 0 6px 0;}
    .product-card:hover {transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.1);}
    .price {color: #b58328; font-weight: 700; font-size: 1.4rem;}
    .price-barre {color: #999; font-size: 0.95rem; text-decoration: line-through; margin-right: 8px;}
    .badge-promo {display: inline-block; background: #dc3545; color: white; font-weight: 700; font-size: 0.75rem; padding: 2px 8px; border-radius: 6px; margin-bottom: 4px;}
    .stock {font-size: 0.9rem; color: #28a745; font-weight: 500;}
    .stock-low {color: #dc3545; font-weight: 500;}
    </style>
""", unsafe_allow_html=True)

# ====================== CONFIG ======================
# Seuls les identifiants "techniques" (indispensables pour se connecter à ton
# Google Sheet et à ImgBB) restent dans les secrets Streamlit. Le mot de passe
# admin, le numéro WhatsApp et le nom de la boutique sont maintenant stockés
# dans l'onglet "Config" de ton Google Sheet, et modifiables directement
# depuis l'appli (onglet ⚙️ Paramètres de l'admin).
URL_PASSERELLE = st.secrets.get("URL_PASSERELLE_WEB", "")
ID_SHEET = st.secrets.get("ID_DU_SHEET", "").strip()
IMGBB_API_KEY = st.secrets.get("IMGBB_API_KEY", "")

if not all([URL_PASSERELLE, ID_SHEET, IMGBB_API_KEY]):
    st.error("⚠️ Configuration incomplète dans les secrets Streamlit.")
    st.stop()

# ====================== 🆕 PERSISTANCE DU PANIER ======================
# Objectif : ne plus perdre le panier quand le téléphone met l'onglet en
# veille (fréquent sur mobile — l'appli WhatsApp prend le dessus, puis
# Streamlit redémarre une session "fraîche" au retour), ou en cas de
# rechargement de page. Le panier est encodé dans l'URL (paramètre
# ?panier=...) : tant que l'onglet garde la même adresse, il est restauré
# automatiquement au prochain chargement. Il ne survit pas à la fermeture
# totale du navigateur si l'URL n'a pas été conservée (favori, onglet
# rouvert) — c'est la seule limite de cette approche, qui ne nécessite
# aucune dépendance supplémentaire ni changement côté serveur.
def _encoder_panier(cart):
    try:
        if not cart:
            return ""
        payload = json.dumps(cart, ensure_ascii=False, separators=(",", ":"))
        return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    except Exception:
        return ""

def _decoder_panier(valeur):
    try:
        if not valeur:
            return []
        payload = base64.urlsafe_b64decode(str(valeur).encode("ascii")).decode("utf-8")
        cart = json.loads(payload)
        if isinstance(cart, list):
            return cart
    except Exception:
        pass
    return []

def _synchroniser_panier_url():
    encode = _encoder_panier(st.session_state.cart)
    if encode:
        if st.query_params.get("panier") != encode:
            st.query_params["panier"] = encode
    elif "panier" in st.query_params:
        del st.query_params["panier"]

# ====================== 🆕 PERSISTANCE DE LA WISHLIST ======================
# Même principe que le panier ci-dessus, mais pour les favoris (❤️).
def _encoder_favoris(favoris):
    try:
        if not favoris:
            return ""
        payload = json.dumps(favoris, ensure_ascii=False, separators=(",", ":"))
        return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    except Exception:
        return ""

def _decoder_favoris(valeur):
    try:
        if not valeur:
            return []
        payload = base64.urlsafe_b64decode(str(valeur).encode("ascii")).decode("utf-8")
        favoris = json.loads(payload)
        if isinstance(favoris, list):
            return favoris
    except Exception:
        pass
    return []

def _synchroniser_favoris_url():
    encode = _encoder_favoris(st.session_state.wishlist)
    if encode:
        if st.query_params.get("favoris") != encode:
            st.query_params["favoris"] = encode
    elif "favoris" in st.query_params:
        del st.query_params["favoris"]

# ====================== SESSION STATE ======================
if 'cart' not in st.session_state:
    # 🆕 Session toute fraîche : on tente de restaurer le panier depuis l'URL
    # avant de retomber sur un panier vide.
    st.session_state.cart = _decoder_panier(st.query_params.get("panier", ""))
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'refresh_token' not in st.session_state:
    st.session_state.refresh_token = 0
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False
if 'admin_token' not in st.session_state:
    st.session_state.admin_token = ""
if 'pending_cart_toast' not in st.session_state:
    st.session_state.pending_cart_toast = None
if 'wishlist' not in st.session_state:
    st.session_state.wishlist = _decoder_favoris(st.query_params.get("favoris", ""))

# 🔧 FIX : affiche le toast "ajouté au panier" mémorisé au tour précédent.
# On ne l'affiche plus directement au moment de l'ajout car la mise à jour
# de l'URL (persistance du panier) déclenche elle-même un rerun juste après,
# ce qui "avalait" le toast avant que le téléphone ait le temps de l'afficher.
if st.session_state.pending_cart_toast:
    st.toast(st.session_state.pending_cart_toast, icon="🛍️")
    st.session_state.pending_cart_toast = None

# ====================== HELPERS ======================
def format_fcfa(n):
    return f"{int(n):,} FCFA".replace(",", " ")

def format_etoiles(moyenne):
    """Affiche une moyenne (ex: 4.3) sous forme d'étoiles pleines/vides."""
    pleines = round(moyenne)
    return "⭐" * pleines + "☆" * (5 - pleines)

def image_valide(valeur):
    """Nettoie une valeur d'image venant du Sheet et renvoie '' si elle est
    absente. 🔧 FIX BUG PHOTOS : une cellule 'image' vide devient NaN en
    pandas ; str(NaN) donne littéralement le texte "nan", qui passait ensuite
    tous les tests de "valeur non vide" (bool(nan) est True) et finissait
    comme src="nan" dans la fiche produit (photo cassée) ou faisait planter
    st.image() dans les onglets Modifier/Supprimer (qui n'acceptent pas NaN)."""
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return ""
    texte = str(valeur).strip()
    return "" if texte.lower() in ("", "nan", "none") else texte

def normalize_col(col):
    """Met en minuscule, remplace les espaces par des underscores et supprime les accents d'un nom de colonne."""
    col = str(col).lower().strip()
    col = ''.join(c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn')
    col = re.sub(r'\s+', '_', col)
    return col

def get_unique_values(df, col):
    """Retourne la liste des valeurs uniques d'une colonne, sans planter si elle est absente."""
    if df.empty or col not in df.columns:
        return ["Toutes"]
    return ["Toutes"] + sorted(df[col].dropna().astype(str).unique())

def get_identifiant(row):
    """Identifiant stable d'un produit (son id s'il existe, sinon son nom) —
    utilisé pour la wishlist et la galerie photo, PAS la position de la ligne
    dans le tableau qui change à chaque tri/filtre.
    🔧 FIX : une cellule "id" vide devient NaN en pandas, qui est "vrai" en
    Python (contrairement à une chaîne vide) — donc str(NaN) = "nan" était
    utilisé comme identifiant partagé par TOUS les articles sans id, ce qui
    faisait apparaître un seul favori comme s'il s'appliquait à tout le monde.
    """
    id_val = row.get('id', '')
    if pd.isna(id_val):
        id_val = ''
    id_val = str(id_val).strip()
    if id_val:
        return id_val
    return str(row.get('nom', ''))

def parse_variants(valeur):
    """Découpe une chaîne 'S, M, L' ou 'Rouge / Bleu' en liste de valeurs propres, sans doublons."""
    if not valeur or str(valeur).strip().lower() in ("", "nan", "unique"):
        return []
    morceaux = re.split(r"[,/;]", str(valeur))
    vues = []
    for m in morceaux:
        m = m.strip()
        if m and m not in vues:
            vues.append(m)
    return vues

def parse_image_list(valeur):
    """Découpe une liste d'URLs d'images séparées par des virgules (ne coupe PAS sur '/', contrairement à parse_variants)."""
    if not valeur or str(valeur).strip().lower() in ("", "nan"):
        return []
    morceaux = str(valeur).split(",")
    vues = []
    for m in morceaux:
        m = m.strip()
        if m and m not in vues:
            vues.append(m)
    return vues

# 🔧 FIX BUG UPLOAD SILENCIEUX : cette fonction avalait certains échecs sans
# les signaler. Trois cas précis passaient inaperçus (aucune erreur affichée,
# mais pas d'image non plus) :
#  1. ImgBB peut répondre avec un code HTTP 200 mais "success": false (clé API
#     invalide, format non pris en charge comme certains .webp, etc.) — seul
#     res.status_code était vérifié, jamais le contenu réel de la réponse.
#  2. Une réponse non-JSON (page d'erreur HTML d'un proxy, etc.) faisait
#     planter res.json() AVANT le return, remontant un message peu clair.
#  3. Aucune limite de taille : un très gros fichier peut dépasser le timeout
#     réseau et échouer sans qu'on sache pourquoi.
TAILLE_MAX_IMAGE_MO = 20

def upload_image_to_imgbb(file_bytes):
    if not file_bytes:
        return None, "Fichier vide ou illisible"
    if len(file_bytes) > TAILLE_MAX_IMAGE_MO * 1024 * 1024:
        return None, f"Image trop lourde (max {TAILLE_MAX_IMAGE_MO} Mo) — réduis la taille du fichier"
    if not IMGBB_API_KEY:
        return None, "Clé API ImgBB manquante (à configurer dans les secrets de l'appli)"

    try:
        b64 = base64.b64encode(file_bytes).decode()
        res = requests.post("https://api.imgbb.com/1/upload",
                           data={"key": IMGBB_API_KEY, "image": b64}, timeout=30)
    except requests.exceptions.Timeout:
        return None, "L'envoi a expiré (connexion trop lente ou fichier trop lourd)"
    except Exception as e:
        return None, f"Erreur réseau lors de l'envoi : {e}"

    try:
        data_json = res.json()
    except ValueError:
        return None, f"Réponse invalide de l'hébergeur d'images (code {res.status_code})"

    if res.status_code != 200 or not data_json.get("success"):
        message_erreur = (data_json.get("error") or {}).get("message")
        return None, message_erreur or f"Échec de l'envoi (code {res.status_code})"

    url = (data_json.get("data") or {}).get("url")
    if not url:
        return None, "L'hébergeur d'images n'a renvoyé aucune URL"
    return url, None

def call_passerelle(payload, timeout=20):
    try:
        r = requests.post(URL_PASSERELLE, json=payload, timeout=timeout)
        if r.status_code != 200:
            return None, f"Erreur serveur ({r.status_code})"
        return r.json(), None
    except Exception as e:
        return None, str(e)

# 🔧 FIX SÉCURITÉ : à utiliser pour toutes les actions admin (au lieu de
# call_passerelle direct). Injecte automatiquement le jeton de session — le
# mot de passe, lui, n'est plus jamais renvoyé après la connexion initiale.
# Si le jeton a expiré (session de plus de 6h), on déconnecte proprement et
# on redemande le mot de passe, plutôt que d'afficher une erreur incompréhensible.
def call_passerelle_admin(payload, timeout=20):
    payload = {**payload, "token": st.session_state.admin_token}
    reponse, err = call_passerelle(payload, timeout=timeout)
    if reponse and reponse.get("session_expiree"):
        st.session_state.admin_logged_in = False
        st.session_state.admin_token = ""
        st.warning("🔒 Session expirée, merci de te reconnecter.")
        st.rerun()
    return reponse, err

# ====================== CHARGEMENT CONFIG (nom boutique / whatsapp) ======================
@st.cache_data(ttl=90, show_spinner=False)
def load_config(refresh_token=0):
    reponse, err = call_passerelle({"action": "get_config"})
    if err or not reponse or reponse.get("status") != "success":
        return {"nom_boutique": "Collection Luxe N'Djamena", "whatsapp": "", "logo": "", "email_admin": "", "seuil_alerte_stock": "3", "heure_bilan_quotidien": "20", "panier_abandonne_actif": "non", "delai_relance_panier_minutes": "60"}
    return {
        "nom_boutique": reponse.get("nom_boutique") or "Collection Luxe N'Djamena",
        "whatsapp": reponse.get("whatsapp") or "",
        "logo": reponse.get("logo") or "",
        "email_admin": reponse.get("email_admin") or "",
        "seuil_alerte_stock": reponse.get("seuil_alerte_stock") or "3",
        "heure_bilan_quotidien": reponse.get("heure_bilan_quotidien") or "20",
        "panier_abandonne_actif": reponse.get("panier_abandonne_actif") or "non",
        "delai_relance_panier_minutes": reponse.get("delai_relance_panier_minutes") or "60"
    }

# ====================== 🆕 CHARGEMENT AVIS CLIENTS (moyennes) ======================
# Un seul appel pour récupérer la note moyenne + le nombre d'avis de TOUS
# les articles d'un coup (affiché sur chaque fiche produit), plutôt qu'un
# appel par article. Le détail des avis d'un article précis (commentaires)
# est chargé séparément, seulement quand le client ouvre "⭐ Avis clients".
@st.cache_data(ttl=90, show_spinner=False)
def load_avis_moyennes(refresh_token=0):
    reponse, err = call_passerelle({"action": "get_avis"})
    if err or not reponse or reponse.get("status") != "success":
        return {}
    return reponse.get("moyennes", {})

@st.cache_data(ttl=30, show_spinner=False)
def load_avis_article(article_id, refresh_token=0):
    reponse, err = call_passerelle({"action": "get_avis", "article_id": article_id, "limit": 20})
    if err or not reponse or reponse.get("status") != "success":
        return []
    return reponse.get("avis", [])

config = load_config(st.session_state.get("refresh_token", 0))
NOM_BOUTIQUE = config["nom_boutique"]
NUMERO_WHATSAPP = re.sub(r"\D", "", str(config.get("whatsapp") or ""))
LOGO_URL = config.get("logo") or ""

if LOGO_URL:
    st.markdown(
        f'''<div class="hero-banner">
                <img class="hero-bg" src="{LOGO_URL}">
                <div class="hero-content">
                    <h1>{NOM_BOUTIQUE}</h1>
                    <p>Élégance &amp; Raffinement</p>
                </div>
            </div>''',
        unsafe_allow_html=True
    )
else:
    st.markdown(f'<div class="hero"><h1 class="main-title">{NOM_BOUTIQUE}</h1></div>', unsafe_allow_html=True)

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

        # 🔧 FIX AFFICHAGE PROMO : "images_supplementaires" (10e colonne) et
        # "prix_promo" (11e colonne) sont TOUJOURS écrites à ces positions
        # fixes par Code.gs (ajout_article / modification_article), quel que
        # soit le texte réellement présent dans l'en-tête de ces colonnes sur
        # le Sheet. Avant ce correctif, on ne les retrouvait QUE si leur
        # en-tête correspondait à un nom attendu — un en-tête vide, mal
        # orthographié ou simplement différent ("Prix Promotionnel" au lieu
        # de "Prix Promo") faisait passer la colonne pour "Unnamed", et elle
        # était supprimée juste en dessous, avant même d'atteindre
        # calculer_prix_effectif : la promo restait donc invisible même si
        # elle était bien enregistrée. On fixe maintenant ces deux noms par
        # POSITION, qui est la seule chose garantie par le script d'écriture.
        colonnes = list(df.columns)
        if len(colonnes) > 9:
            colonnes[9] = "images_supplementaires"
        if len(colonnes) > 10:
            colonnes[10] = "prix_promo"
        df.columns = colonnes

        df.columns = [normalize_col(col) for col in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^unnamed', case=False)]
        df = df.dropna(subset=['nom', 'prix'])
        df['prix_numeric'] = pd.to_numeric(df['prix'], errors='coerce').fillna(0)
        df['stock'] = pd.to_numeric(df.get('stock', 0), errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return pd.DataFrame()

def uniformiser_colonne_images_supp(df):
    """Renomme la colonne des photos supplémentaires vers un nom standard, même si l'en-tête
    du Google Sheet est abrégé, mal orthographié ou sans accents (ex: 'imag_suplé',
    'images_supp', 'Images Supplémentaires', ...)."""
    if df.empty:
        return df
    for c in df.columns:
        if c != 'images_supplementaires' and 'imag' in c and ('suppl' in c or 'supl' in c or 'sup' in c):
            return df.rename(columns={c: 'images_supplementaires'})
    return df

# 🆕 PRIX PROMOTIONNELS : calcule un prix "effectif" par article (le prix promo
# s'il est renseigné et inférieur au prix normal, sinon le prix normal). Toute
# la boutique (filtre, tri, panier, partage) utilise ensuite ce prix effectif —
# le prix normal reste affiché barré à titre indicatif quand une promo est active.
def calculer_prix_effectif(df):
    if df.empty:
        df['prix_promo_numeric'] = pd.Series(dtype=float)
        df['en_promo'] = pd.Series(dtype=bool)
        df['prix_effectif_numeric'] = pd.Series(dtype=float)
        return df
    if 'prix_promo' in df.columns:
        df['prix_promo_numeric'] = pd.to_numeric(df['prix_promo'], errors='coerce')
    else:
        df['prix_promo_numeric'] = float('nan')
    df['en_promo'] = df['prix_promo_numeric'].notna() & (df['prix_promo_numeric'] > 0) & (df['prix_promo_numeric'] < df['prix_numeric'])
    df['prix_effectif_numeric'] = df['prix_numeric'].where(~df['en_promo'], df['prix_promo_numeric'])
    return df

df_catalogue = load_data(ID_SHEET, st.session_state.refresh_token)
df_catalogue = uniformiser_colonne_images_supp(df_catalogue)
df_catalogue = calculer_prix_effectif(df_catalogue)
avis_moyennes = load_avis_moyennes(st.session_state.refresh_token)

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

favoris_uniquement = st.checkbox(
    f"❤️ Afficher uniquement mes favoris ({len(st.session_state.wishlist)})",
    key="filtre_favoris"
) if st.session_state.wishlist else False

# ====================== FILTRAGE ======================
df_f = df_catalogue.copy()
if not df_f.empty:
    if search:
        df_f = df_f[df_f['nom'].astype(str).str.contains(search, case=False, na=False)]
    if cat_filter != "Toutes" and 'categorie' in df_f.columns:
        df_f = df_f[df_f['categorie'].astype(str).str.contains(cat_filter, case=False, na=False)]
    if taille_filter != "Toutes" and 'tailles' in df_f.columns:
        df_f = df_f[df_f['tailles'].astype(str).str.contains(taille_filter, case=False, na=False)]

    df_f = df_f[(df_f['prix_effectif_numeric'] >= min_price) & (df_f['prix_effectif_numeric'] <= max_price)]

    if favoris_uniquement:
        df_f = df_f[df_f.apply(lambda r: get_identifiant(r) in st.session_state.wishlist, axis=1)]

    if sort_option == "Prix croissant":
        df_f = df_f.sort_values('prix_effectif_numeric')
    elif sort_option == "Prix décroissant":
        df_f = df_f.sort_values('prix_effectif_numeric', ascending=False)

st.caption(f"**{len(df_f)} article(s)** trouvé(s)")

# ====================== PAGINATION ======================
ARTICLES_PAR_PAGE = 12
total_articles = len(df_f)
total_pages = max(1, -(-total_articles // ARTICLES_PAR_PAGE))  # arrondi au supérieur

if 'catalog_page' not in st.session_state:
    st.session_state.catalog_page = 1

# Si les filtres changent, on revient à la page 1 pour éviter une page vide
filtres_signature = (search, cat_filter, taille_filter, sort_option, min_price, max_price, favoris_uniquement)
if st.session_state.get('catalog_filters_signature') != filtres_signature:
    st.session_state.catalog_filters_signature = filtres_signature
    st.session_state.catalog_page = 1

if st.session_state.catalog_page > total_pages:
    st.session_state.catalog_page = total_pages
if st.session_state.catalog_page < 1:
    st.session_state.catalog_page = 1

debut = (st.session_state.catalog_page - 1) * ARTICLES_PAR_PAGE
df_page = df_f.iloc[debut:debut + ARTICLES_PAR_PAGE]

def afficher_controles_pagination(position):
    if total_pages <= 1:
        return
    pc1, pc2, pc3 = st.columns([1, 2, 1])
    with pc1:
        if st.button("⬅️ Précédent", key=f"prev_{position}", disabled=st.session_state.catalog_page <= 1,
                     use_container_width=True):
            st.session_state.catalog_page -= 1
            st.rerun()
    with pc2:
        st.markdown(
            f"<div style='text-align:center; padding-top:8px;'>Page {st.session_state.catalog_page} / {total_pages}</div>",
            unsafe_allow_html=True
        )
    with pc3:
        if st.button("Suivant ➡️", key=f"next_{position}", disabled=st.session_state.catalog_page >= total_pages,
                     use_container_width=True):
            st.session_state.catalog_page += 1
            st.rerun()

# ====================== 🆕 PANIER (relocalisé de la barre latérale) ======================
# 🔧 FIX MOBILE : le panier ne vivait qu'en barre latérale, repliée par
# défaut sur mobile derrière une petite flèche peu visible — beaucoup de
# clients ne la trouvaient jamais. Il est maintenant ici, directement dans
# le contenu principal, juste au-dessus des produits, et s'ouvre tout seul
# dès qu'il contient un article.
nb_articles_label = sum(item['quantite'] for item in st.session_state.cart)
titre_panier = f"🛒 Mon Panier ({nb_articles_label})" if nb_articles_label else "🛒 Mon Panier (vide)"
with st.expander(titre_panier, expanded=bool(st.session_state.cart)):
    total_placeholder = st.empty()
    if st.session_state.cart:
        for item in st.session_state.cart[:]:
            c1, c2, c3 = st.columns([5, 2, 1])
            with c1:
                variante_item = " / ".join(v for v in [item.get('taille', ''), item.get('couleur', '')] if v)
                if variante_item:
                    st.write(f"{item['nom']}")
                    st.caption(variante_item)
                else:
                    st.write(item['nom'])
            with c2:
                item['quantite'] = st.number_input("Qté", min_value=1, value=item['quantite'], key=f"q_{item['id']}")
            with c3:
                if st.button("🗑️", key=f"del_{item['id']}"):
                    st.session_state.cart = [i for i in st.session_state.cart if i['id'] != item['id']]
                    _synchroniser_panier_url()
                    st.rerun()

        # Recalcul APRÈS mise à jour des quantités par les number_input ci-dessus
        nb_articles = sum(item['quantite'] for item in st.session_state.cart)
        total = sum(item['prix'] * item['quantite'] for item in st.session_state.cart)
        # 🆕 Les changements de quantité ne passent pas par st.rerun() explicite
        # (le widget number_input redéclenche l'exécution tout seul) — on
        # resynchronise donc l'URL ici, à chaque exécution du script.
        _synchroniser_panier_url()
        total_placeholder.success(f"**Total : {format_fcfa(total)}**")

        st.markdown("---")

        def _ligne_article(item):
            variante = " / ".join(v for v in [item.get('taille', ''), item.get('couleur', '')] if v)
            suffixe = f" ({variante})" if variante else ""
            return f"- {item['nom']}{suffixe} × {item['quantite']} = {format_fcfa(item['prix']*item['quantite'])} FCFA"

        st.markdown("**📇 Vos coordonnées**")
        client_nom_saisi = st.text_input("Votre nom *", key="client_nom_input")
        client_telephone_saisi = st.text_input(
            "Votre téléphone *", key="client_telephone_input",
            placeholder="Ex : 66000000"
        )

        entete_msg = (
            f"Bonjour, je m'appelle {client_nom_saisi.strip()}, voici ma commande :"
            if client_nom_saisi.strip() else "Bonjour, voici ma commande :"
        )
        msg = entete_msg + "\n\n" + "\n".join(
            [_ligne_article(item) for item in st.session_state.cart]
        ) + f"\n\nTotal : {format_fcfa(total)} FCFA"
        wa_url = f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}"

        coordonnees_completes = client_nom_saisi.strip() and client_telephone_saisi.strip()
        if not coordonnees_completes:
            st.caption("⚠️ Merci de renseigner votre nom et votre téléphone avant d'envoyer la commande.")

        # 🆕 PANIER ABANDONNÉ : dès que le client a rempli ses coordonnées, on
        # enregistre discrètement un "checkpoint" côté serveur (sans bloquer
        # l'affichage, sans toast) — seulement si quelque chose a changé depuis
        # le dernier enregistrement, pour ne pas spammer l'API à chaque rerun.
        if coordonnees_completes:
            signature_panier_abandonne = (
                client_nom_saisi.strip(), re.sub(r"\D", "", client_telephone_saisi),
                tuple((i['id'], i['quantite']) for i in st.session_state.cart), total
            )
            if st.session_state.get("derniere_signature_panier_abandonne") != signature_panier_abandonne:
                try:
                    call_passerelle({
                        "action": "enregistrer_panier_abandonne",
                        "client_nom": client_nom_saisi.strip(),
                        "client_telephone": re.sub(r"\D", "", client_telephone_saisi),
                        "articles": st.session_state.cart,
                        "total": total
                    }, timeout=8)
                except Exception:
                    pass
                st.session_state.derniere_signature_panier_abandonne = signature_panier_abandonne

        if st.button("✅ Envoyer ma commande", type="primary", use_container_width=True,
                     disabled=not coordonnees_completes):
            with st.spinner("Enregistrement..."):
                payload = {
                    "action": "nouvelle_commande",
                    "client_nom": client_nom_saisi.strip(),
                    "client_telephone": re.sub(r"\D", "", client_telephone_saisi),
                    "articles": st.session_state.cart,
                    "total": total
                }
                # 🔧 FIX : 20s était trop court — le serveur (Apps Script) peut parfois
                # mettre plus de temps à répondre (démarrage à froid, envoi d'email...),
                # sans que la commande échoue réellement côté serveur.
                reponse, err = call_passerelle(payload, timeout=40)
                if err or not reponse or reponse.get("status") != "success":
                    # 🔧 FIX : on n'affiche plus l'erreur technique brute au client (illisible
                    # et anxiogène) — un message clair + une solution de secours immédiate.
                    st.error(
                        "❌ La commande met du temps à s'enregistrer. Elle est peut-être "
                        "quand même passée — pas de souci, tu peux confirmer directement sur "
                        "WhatsApp en un clic ci-dessous 👇"
                    )
                    st.link_button("📲 Envoyer ma commande sur WhatsApp", wa_url, use_container_width=True)
                else:
                    warnings = (reponse or {}).get("stock_warnings", [])
                    if warnings:
                        st.warning("⚠️ Stock insuffisant pour : " + ", ".join(warnings))
                    st.success("✅ Commande enregistrée ! Cliquez ci-dessous pour l'envoyer sur WhatsApp 👇")
                    id_commande_recue = (reponse or {}).get("id_commande", "")
                    if id_commande_recue:
                        st.info(
                            f"📦 Votre numéro de commande : **{id_commande_recue}**\n\n"
                            "Conservez-le précieusement, il vous permet de suivre l'état de votre commande "
                            "ci-dessous, dans « Suivre ma commande »."
                        )
                    load_data.clear()  # le stock a été décrémenté côté serveur
                    st.session_state.cart = []
                    st.session_state.derniere_signature_panier_abandonne = None
                    _synchroniser_panier_url()
                    st.session_state.refresh_token += 1
                    st.markdown(
                        f'''<a href="{wa_url}" target="_blank" rel="noopener"
                                style="display:block; text-align:center; background:#25D366; color:white;
                                       font-weight:600; padding:12px 16px; border-radius:8px;
                                       text-decoration:none; margin-top:8px;">
                                📱 Envoyer la confirmation sur WhatsApp
                            </a>''',
                        unsafe_allow_html=True
                    )
    else:
        st.info("Votre panier est vide.")

# ====================== AFFICHAGE PRODUITS ======================
if not df_f.empty:
    afficher_controles_pagination("haut")
    st.markdown("")
    cols = st.columns(3)
    for pos, (idx, row) in enumerate(df_page.iterrows()):
        with cols[pos % 3]:
            prix_original = int(row['prix_numeric'])
            en_promo = bool(row.get('en_promo', False))
            prix = int(row['prix_effectif_numeric']) if en_promo else prix_original
            stock = int(row['stock'])
            en_rupture = stock <= 0

            # 🔧 FIX STABILITÉ GALERIE : identifiant stable du produit (l'id de
            # la fiche s'il existe, sinon son nom) — PAS la position de la ligne
            # dans le tableau, qui change à chaque tri/filtre/ajout/suppression
            # d'article et faisait dériver la photo affichée vers le mauvais
            # article après coup.
            identifiant_produit = get_identifiant(row)

            # 🆕 AVIS CLIENTS : note moyenne + nombre d'avis de cet article (déjà
            # chargés en une seule fois pour tout le catalogue dans avis_moyennes).
            info_avis = avis_moyennes.get(identifiant_produit) or avis_moyennes.get(row['nom'])
            bloc_avis = (
                f'<div style="margin-top:4px; font-size:0.9rem; color:#b58328;">'
                f'{format_etoiles(info_avis["moyenne"])} '
                f'<span style="color:#666;">{info_avis["moyenne"]} ({info_avis["count"]} avis)</span></div>'
                if info_avis else
                '<div style="margin-top:4px; font-size:0.85rem; color:#999;">Aucun avis pour le moment</div>'
            )

            # Galerie : photo principale + photos supplémentaires (colonne "images_supplementaires")
            galerie = [g for g in (
                [image_valide(row.get('image', ''))] + parse_image_list(row.get('images_supplementaires', ''))
            ) if g]
            if not galerie:
                galerie = ['https://placehold.co/300x300?text=Image+non+disponible']
            cle_galerie = f"galerie_{identifiant_produit}"
            if cle_galerie not in st.session_state:
                st.session_state[cle_galerie] = 0
            st.session_state[cle_galerie] = st.session_state[cle_galerie] % len(galerie)
            image_affichee = galerie[st.session_state[cle_galerie]]

            reduction_pct = round((1 - prix / prix_original) * 100) if en_promo and prix_original > 0 else 0
            bloc_prix = (
                f'<div class="badge-promo">PROMO -{reduction_pct}%</div><br>'
                f'<span class="price-barre">{format_fcfa(prix_original)}</span>'
                f'<span class="price">{format_fcfa(prix)}</span>'
                if en_promo else
                f'<div class="price">{format_fcfa(prix)}</div>'
            )
            st.markdown(f"""
                <div class="product-card">
                    <a href="{image_affichee}" target="_blank">
                        <img src="{image_affichee}" style="width:100%; border-radius:12px; aspect-ratio:1/1; object-fit:cover;"
                             onerror="this.src='https://placehold.co/300x300?text=Image+non+disponible';">
                    </a>
                    <h3>{row['nom']}</h3>
                    {bloc_prix}
                    <div class="{'stock-low' if stock < 5 else 'stock'}">Stock : {stock} pièce(s)</div>
                    {bloc_avis}
                </div>
            """, unsafe_allow_html=True)

            if len(galerie) > 1:
                nav1, nav2, nav3 = st.columns([1, 2, 1])
                with nav1:
                    if st.button("◀", key=f"prev_img_{idx}_{row.get('nom')}", use_container_width=True):
                        st.session_state[cle_galerie] = (st.session_state[cle_galerie] - 1) % len(galerie)
                        st.rerun()
                with nav2:
                    st.markdown(
                        f"<div style='text-align:center; padding-top:6px;'>Photo {st.session_state[cle_galerie]+1}/{len(galerie)}</div>",
                        unsafe_allow_html=True
                    )
                with nav3:
                    if st.button("▶", key=f"next_img_{idx}_{row.get('nom')}", use_container_width=True):
                        st.session_state[cle_galerie] = (st.session_state[cle_galerie] + 1) % len(galerie)
                        st.rerun()

            # 🆕 WISHLIST + PARTAGE
            est_favori = identifiant_produit in st.session_state.wishlist
            colf, colp = st.columns(2)
            with colf:
                if st.button("❤️ Favori" if est_favori else "🤍 Favori",
                             key=f"fav_{idx}_{row.get('nom')}", use_container_width=True):
                    if est_favori:
                        st.session_state.wishlist = [f for f in st.session_state.wishlist if f != identifiant_produit]
                    else:
                        st.session_state.wishlist = st.session_state.wishlist + [identifiant_produit]
                    _synchroniser_favoris_url()
                    st.rerun()
            with colp:
                texte_partage = f"🛍️ Regarde cet article : {row['nom']} — {format_fcfa(prix)} chez {NOM_BOUTIQUE} !"
                lien_partage = f"https://wa.me/?text={urllib.parse.quote(texte_partage)}"
                st.link_button("📤 Partager", lien_partage, use_container_width=True)

            # 🆕 VUE RAPIDE : toutes les photos + le détail complet sans quitter la grille.
            with st.expander("👁️ Vue rapide"):
                if len(galerie) > 1:
                    st.caption(f"{len(galerie)} photo(s)")
                    miniatures = st.columns(min(len(galerie), 4))
                    for i_photo, url_photo in enumerate(galerie[:4]):
                        with miniatures[i_photo]:
                            st.image(url_photo, use_container_width=True)
                st.markdown(f"**{row['nom']}**")
                if en_promo:
                    st.write(f"~~{format_fcfa(prix_original)}~~ → **{format_fcfa(prix)}** (-{reduction_pct}%)")
                else:
                    st.write(format_fcfa(prix))
                st.caption(f"Stock : {stock} pièce(s)" if stock > 0 else "Rupture de stock")
                if options_taille := parse_variants(row.get('tailles', '')):
                    st.caption(f"Tailles disponibles : {', '.join(options_taille)}")
                if options_couleur := parse_variants(row.get('couleurs', '')):
                    st.caption(f"Couleurs disponibles : {', '.join(options_couleur)}")

            # ====================== 🆕 AVIS CLIENTS ======================
            libelle_avis = f"⭐ Avis clients ({info_avis['count']})" if info_avis else "⭐ Laisser un avis"
            with st.expander(libelle_avis):
                if info_avis:
                    st.markdown(f"**{format_etoiles(info_avis['moyenne'])} {info_avis['moyenne']}/5** — {info_avis['count']} avis")
                    for avis_item in load_avis_article(identifiant_produit, st.session_state.refresh_token):
                        st.markdown(f"{format_etoiles(avis_item.get('note', 0))} — **{avis_item.get('client_nom', '')}**")
                        if avis_item.get('commentaire'):
                            st.caption(avis_item['commentaire'])
                    st.markdown("---")
                else:
                    st.caption("Aucun avis pour le moment. Soyez le premier à donner votre avis !")

                with st.form(f"form_avis_{idx}_{row.get('nom')}", clear_on_submit=True):
                    avis_nom = st.text_input("Votre nom", key=f"avis_nom_{idx}_{row.get('nom')}")
                    avis_note_label = st.select_slider(
                        "Votre note", options=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"],
                        value="⭐⭐⭐⭐⭐", key=f"avis_note_{idx}_{row.get('nom')}"
                    )
                    avis_commentaire = st.text_area(
                        "Votre commentaire (facultatif)", max_chars=500,
                        key=f"avis_comment_{idx}_{row.get('nom')}"
                    )
                    if st.form_submit_button("📨 Envoyer mon avis"):
                        if not avis_nom.strip():
                            st.warning("Merci de renseigner votre nom.")
                        else:
                            reponse_avis, err_avis = call_passerelle({
                                "action": "laisser_avis",
                                "article_id": identifiant_produit,
                                "article_nom": row['nom'],
                                "client_nom": avis_nom.strip(),
                                "note": avis_note_label.count("⭐"),
                                "commentaire": avis_commentaire.strip()
                            })
                            if err_avis or not reponse_avis or reponse_avis.get("status") != "success":
                                st.error(f"❌ {(reponse_avis or {}).get('message', err_avis or 'Erreur')}")
                            else:
                                st.success(f"✅ {reponse_avis.get('message', 'Avis envoyé')}")

            options_taille = parse_variants(row.get('tailles', ''))
            options_couleur = parse_variants(row.get('couleurs', ''))

            taille_choisie = ""
            couleur_choisie = ""
            if options_taille:
                if len(options_taille) == 1:
                    taille_choisie = options_taille[0]
                else:
                    taille_choisie = st.selectbox(
                        "Taille", options_taille, key=f"taille_{idx}_{row.get('nom')}"
                    )
            if options_couleur:
                if len(options_couleur) == 1:
                    couleur_choisie = options_couleur[0]
                else:
                    couleur_choisie = st.selectbox(
                        "Couleur", options_couleur, key=f"couleur_{idx}_{row.get('nom')}"
                    )

            if st.button("🛒 Ajouter au panier" if not en_rupture else "❌ Rupture de stock",
                        key=f"add_{idx}_{row.get('nom')}", disabled=en_rupture):
                existing = next((item for item in st.session_state.cart
                                  if item['nom'] == row['nom']
                                  and item.get('taille', '') == taille_choisie
                                  and item.get('couleur', '') == couleur_choisie), None)
                if existing:
                    existing['quantite'] += 1
                else:
                    st.session_state.cart.append({
                        "id": str(uuid.uuid4()),
                        # 🔧 FIX FIABILITÉ : identifiant catalogue réel de l'article (colonne
                        # "id" du Sheet), transmis au serveur pour qu'il retrouve la bonne
                        # ligne sans ambiguïté même si deux articles partagent le même nom.
                        "produit_id": str(row.get('id', '') or ''),
                        "nom": row['nom'],
                        "prix": prix,
                        "image": row.get('image', ''),
                        "taille": taille_choisie,
                        "couleur": couleur_choisie,
                        "quantite": 1
                    })
                variante = " / ".join(v for v in [taille_choisie, couleur_choisie] if v)
                label_toast = f"{row['nom']} ({variante})" if variante else row['nom']
                st.session_state.pending_cart_toast = f"✅ {label_toast} ajouté au panier !"
                _synchroniser_panier_url()
                st.rerun()

            # ====================== 🆕 ALERTE RETOUR EN STOCK ======================
            if en_rupture:
                with st.expander("🔔 Me prévenir quand disponible"):
                    type_contact = st.radio(
                        "Comment veux-tu être prévenu(e) ?", ["Email", "Téléphone (WhatsApp)"],
                        key=f"type_alerte_{idx}_{row.get('nom')}", horizontal=True
                    )
                    contact_saisi = st.text_input(
                        "Email" if type_contact == "Email" else "Numéro de téléphone",
                        key=f"contact_alerte_{idx}_{row.get('nom')}",
                        placeholder="ex: nom@email.com" if type_contact == "Email" else "ex: 66 12 34 56"
                    )
                    if st.button("🔔 M'alerter", key=f"btn_alerte_{idx}_{row.get('nom')}"):
                        if not contact_saisi.strip():
                            st.warning("Merci de renseigner un contact.")
                        else:
                            reponse_alerte, err_alerte = call_passerelle({
                                "action": "inscrire_alerte_stock",
                                "nom_article": row['nom'],
                                "contact_type": "email" if type_contact == "Email" else "telephone",
                                "contact": contact_saisi.strip()
                            })
                            if err_alerte or not reponse_alerte or reponse_alerte.get("status") != "success":
                                st.error(f"❌ {(reponse_alerte or {}).get('message', err_alerte or 'Erreur')}")
                            else:
                                st.success(f"✅ {reponse_alerte.get('message', 'Inscription enregistrée')}")
    st.markdown("---")
    afficher_controles_pagination("bas")
else:
    st.info("Aucun article ne correspond à vos critères.")

with st.sidebar:
    # ====================== SUIVI DE COMMANDE (visible à tous les clients) ======================
    st.markdown("---")
    with st.expander("📦 Suivre ma commande"):
        id_suivi = st.text_input(
            "Numéro de commande",
            key="id_suivi_input",
            placeholder="Ex : CMD-1234567890-1234"
        )
        if st.button("🔍 Vérifier le statut", key="btn_suivi", use_container_width=True):
            if not id_suivi.strip():
                st.warning("Merci d'entrer un numéro de commande.")
            else:
                with st.spinner("Recherche en cours..."):
                    reponse_suivi, err_suivi = call_passerelle({
                        "action": "suivre_commande",
                        "id_commande": id_suivi.strip()
                    })
                if err_suivi or not reponse_suivi or reponse_suivi.get("status") != "success":
                    message_erreur = (reponse_suivi or {}).get("message") or err_suivi or "Commande introuvable."
                    st.error(f"❌ {message_erreur}")
                else:
                    cmd = reponse_suivi.get("commande", {})
                    st.success(f"Statut actuel : **{cmd.get('statut', 'En cours')}**")
                    st.write(f"Total : {format_fcfa(cmd.get('total', 0))}")
                    articles_cmd = cmd.get("articles", [])
                    if articles_cmd:
                        st.caption("Articles commandés :")
                        for art in articles_cmd:
                            st.caption(f"- {art.get('nom', '')} × {art.get('quantite', '')}")

    # ====================== ADMINISTRATION AVANCÉE (cachée aux clients) ======================
    # Section visible uniquement si l'URL contient ?admin=1, ou une fois déjà connecté.
    show_admin_section = st.query_params.get("admin", "") == "1" or st.session_state.admin_logged_in

    if show_admin_section:
        st.markdown("---")
        st.header("⚙️ Administration")
        pwd = st.text_input("Mot de passe admin", type="password", key="admin_input")

        if pwd:
            verif, err = call_passerelle({"action": "connexion_admin", "password": pwd})
            if not err and verif and verif.get("status") == "success":
                st.session_state.admin_logged_in = True
                st.session_state.admin_token = verif.get("token", "")
            else:
                st.error("❌ Mot de passe incorrect")
                st.session_state.admin_logged_in = False
                st.session_state.admin_token = ""

    if st.session_state.admin_logged_in:
        # 🔒 FIX SÉCURITÉ : bouton de déconnexion explicite. Avant ce correctif,
        # il n'existait aucun moyen de révoquer le jeton de session côté
        # serveur — il restait valable jusqu'à expiration (6h) même après
        # avoir quitté la page. Le clic appelle "deconnexion_admin" pour que
        # le jeton soit immédiatement invalidé côté serveur, puis nettoie la
        # session locale.
        col_titre_admin, col_deconnexion = st.columns([4, 1])
        with col_deconnexion:
            if st.button("🚪 Se déconnecter", use_container_width=True):
                call_passerelle_admin({"action": "deconnexion_admin"})
                st.session_state.admin_logged_in = False
                st.session_state.admin_token = ""
                # 🔧 FIX : sans ça, la déconnexion ne "sortait" pas vraiment de la
                # page admin. "show_admin_section" (plus bas) reste vrai tant que
                # l'URL contient "?admin=1", donc l'écran "Mot de passe admin"
                # réapparaissait immédiatement au lieu de repartir sur la boutique.
                if "admin" in st.query_params:
                    del st.query_params["admin"]
                st.rerun()

        # 🔒 FIX SÉCURITÉ : l'email admin n'est plus renvoyé par l'appel
        # public "get_config" (voir Code.gs) — on le récupère ici séparément,
        # via un appel authentifié, uniquement pour préremplir le formulaire
        # ⚙️ Paramètres ci-dessous. `config` reste inchangé pour tout le
        # reste de la page (nom, logo, whatsapp restent publics).
        config_admin, _err_config_admin = call_passerelle_admin({"action": "get_config"})
        if config_admin and config_admin.get("status") == "success":
            config = {**config, "email_admin": config_admin.get("email_admin", "")}

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Dashboard", "➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer", "⚙️ Paramètres", "⭐ Avis"])

        with tab1:  # DASHBOARD
            st.subheader("📊 Tableau de Bord")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Articles totaux", len(df_catalogue))
            with col2:
                low_stock = len(df_catalogue[df_catalogue['stock'] < 5]) if not df_catalogue.empty else 0
                st.metric("Stock faible (< 5)", low_stock)

            with col3:
                stats_payload = {"action": "get_stats"}
                stats, _ = call_passerelle_admin(stats_payload)
                total_sales = stats.get("total_sales", 0) if stats else 0
                st.metric("CA Total", format_fcfa(total_sales))

            with col4:
                orders_count = stats.get("orders_count", 0) if stats else 0
                st.metric("Commandes", orders_count)

            # ====================== 🆕 GRAPHIQUES : ÉVOLUTION DES VENTES + TOP ARTICLES ======================
            st.markdown("---")
            st.subheader("📈 Évolution des ventes")

            periode_label = st.radio(
                "Période", ["7 derniers jours", "30 derniers jours"],
                horizontal=True, key="periode_dashboard"
            )
            jours_periode = 7 if periode_label == "7 derniers jours" else 30

            dash_payload = {
                "action": "get_dashboard_stats",
                "jours": jours_periode
            }
            dash_data, err_dash = call_passerelle_admin(dash_payload)

            if err_dash or not dash_data or dash_data.get("status") != "success":
                st.warning("Impossible de charger les statistiques du graphique pour le moment.")
            else:
                series = dash_data.get("series", [])
                top_articles = dash_data.get("top_articles", [])
                par_categorie = dash_data.get("par_categorie", [])
                top_clients = dash_data.get("top_clients", [])
                panier_moyen = dash_data.get("panier_moyen", 0)
                taux_annulation = dash_data.get("taux_annulation", 0)
                comparaison = dash_data.get("comparaison", {})

                # 🆕 STATS AVANCÉES : panier moyen, taux d'annulation, évolution vs période précédente
                def _fleche_evolution(pct):
                    if pct > 0:
                        return f"▲ +{pct:.0f}%"
                    if pct < 0:
                        return f"▼ {pct:.0f}%"
                    return "▬ 0%"

                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                with col_a1:
                    st.metric("🧺 Panier moyen", format_fcfa(panier_moyen))
                with col_a2:
                    st.metric("❌ Taux d'annulation", f"{taux_annulation:.1f}%")
                with col_a3:
                    st.metric(
                        "💰 Évolution CA",
                        _fleche_evolution(comparaison.get("evolution_ca_pct", 0)),
                        help="Comparé à la période précédente de même durée"
                    )
                with col_a4:
                    st.metric(
                        "🧾 Évolution commandes",
                        _fleche_evolution(comparaison.get("evolution_commandes_pct", 0)),
                        help="Comparé à la période précédente de même durée"
                    )

                if series:
                    df_series = pd.DataFrame(series).set_index("date")

                    col_ca, col_cmd = st.columns(2)
                    with col_ca:
                        st.caption("💰 Chiffre d'affaires par jour (FCFA)")
                        st.line_chart(df_series[["ca"]])
                    with col_cmd:
                        st.caption("🧾 Nombre de commandes par jour")
                        st.bar_chart(df_series[["commandes"]])

                st.markdown("**🏆 Top articles vendus sur la période**")
                if top_articles:
                    df_top = pd.DataFrame(top_articles)
                    df_top_affiche = df_top.rename(columns={
                        "nom": "Article", "quantite": "Quantité vendue", "ca": "CA généré"
                    })
                    df_top_affiche["CA généré"] = df_top_affiche["CA généré"].apply(format_fcfa)
                    st.dataframe(df_top_affiche, use_container_width=True, hide_index=True)

                    st.bar_chart(df_top.set_index("nom")["quantite"])
                else:
                    st.info("Aucune vente enregistrée sur cette période.")

                # 🆕 Ventes par catégorie sur la période
                st.markdown("**📦 Ventes par catégorie (période sélectionnée)**")
                if par_categorie:
                    df_cat = pd.DataFrame(par_categorie)
                    df_cat_affiche = df_cat.rename(columns={
                        "categorie": "Catégorie", "quantite": "Quantité vendue", "ca": "CA généré"
                    })
                    col_cat_tbl, col_cat_chart = st.columns([1.2, 1])
                    with col_cat_tbl:
                        df_cat_affiche_fmt = df_cat_affiche.copy()
                        df_cat_affiche_fmt["CA généré"] = df_cat_affiche_fmt["CA généré"].apply(format_fcfa)
                        st.dataframe(df_cat_affiche_fmt, use_container_width=True, hide_index=True)
                    with col_cat_chart:
                        st.bar_chart(df_cat.set_index("categorie")["ca"])
                else:
                    st.info("Aucune vente par catégorie sur cette période.")

                # 🆕 Fidélité client : meilleurs clients sur tout l'historique
                st.markdown("**🥇 Meilleurs clients (tout l'historique)**")
                if top_clients:
                    df_clients = pd.DataFrame(top_clients)
                    colonnes_clients = ["client", "nb_commandes", "total_depense"]
                    if "telephone" in df_clients.columns:
                        colonnes_clients.insert(1, "telephone")
                    df_clients_affiche = df_clients[colonnes_clients].rename(columns={
                        "client": "Client", "telephone": "Téléphone",
                        "nb_commandes": "Nb commandes", "total_depense": "Total dépensé"
                    })
                    df_clients_affiche["Total dépensé"] = df_clients_affiche["Total dépensé"].apply(format_fcfa)
                    st.dataframe(df_clients_affiche, use_container_width=True, hide_index=True)
                else:
                    st.info("Aucun client fidèle pour le moment.")

            st.markdown("---")
            st.subheader("📋 Dernières Commandes")
            orders_payload = {"action": "get_orders", "limit": 15}
            orders_data, err = call_passerelle_admin(orders_payload)

            if orders_data and orders_data.get("status") == "success":
                orders_list = orders_data.get("orders", [])
                if orders_list:
                    orders_df = pd.DataFrame(orders_list)
                    orders_df['date'] = pd.to_datetime(orders_df['date']).dt.strftime("%d/%m/%Y %H:%M")
                    orders_df['total'] = orders_df['total'].apply(format_fcfa)
                    # id_commande et telephone peuvent être vides pour les commandes créées avant les mises à jour du script
                    colonnes_affichees = ['date', 'client', 'total', 'articles_count', 'statut']
                    if 'telephone' in orders_df.columns:
                        colonnes_affichees.insert(2, 'telephone')
                    if 'id_commande' in orders_df.columns:
                        colonnes_affichees.insert(0, 'id_commande')
                    st.dataframe(orders_df[colonnes_affichees],
                               use_container_width=True, hide_index=True)

                    csv = orders_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Exporter en CSV", csv, "commandes.csv", "text/csv")

                    # ====================== 🆕 CHANGER LE STATUT D'UNE COMMANDE ======================
                    st.markdown("---")
                    st.markdown("**🔄 Changer le statut d'une commande**")

                    def _libelle_commande(o):
                        ref = o.get("id_commande") or "(sans id — ancienne commande)"
                        return f"{ref} — {o.get('client', '')} — {format_fcfa(o.get('total', 0))} — {o.get('statut', '')}"

                    commande_choisie = st.selectbox(
                        "Commande",
                        options=list(range(len(orders_list))),
                        format_func=lambda i: _libelle_commande(orders_list[i]),
                        key="select_commande_statut"
                    )
                    nouveau_statut = st.selectbox(
                        "Nouveau statut",
                        ["En cours", "Payé", "Livré", "Annulé"],
                        key="select_nouveau_statut"
                    )
                    if st.button("💾 Mettre à jour le statut", key="btn_maj_statut"):
                        commande_cible = orders_list[commande_choisie]
                        payload_statut = {
                            "action": "modifier_statut_commande",
                            "nouveau_statut": nouveau_statut
                        }
                        # Priorité à l'id_commande ; sinon on retombe sur la date exacte
                        # (utile pour les commandes créées avant l'ajout de l'id)
                        if commande_cible.get("id_commande"):
                            payload_statut["id_commande"] = commande_cible["id_commande"]
                        else:
                            payload_statut["date"] = commande_cible.get("date")

                        reponse, err = call_passerelle_admin(payload_statut)
                        if err or not reponse or reponse.get("status") != "success":
                            st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                        else:
                            st.success("✅ Statut mis à jour !")
                            # On garde les infos en mémoire pour proposer le lien WhatsApp
                            # après le rechargement de la page (sinon il disparaîtrait aussitôt).
                            st.session_state.dernier_maj_statut = {
                                "client": commande_cible.get("client", ""),
                                "telephone": commande_cible.get("telephone", ""),
                                "id_commande": commande_cible.get("id_commande", ""),
                                "nouveau_statut": nouveau_statut
                            }
                            st.session_state.refresh_token += 1
                            st.rerun()

                    # ====================== NOTIFIER LE CLIENT PAR WHATSAPP ======================
                    if st.session_state.get("dernier_maj_statut"):
                        info_maj = st.session_state.dernier_maj_statut
                        ref_cmd = info_maj.get("id_commande") or "votre commande"
                        tel_client = re.sub(r"\D", "", str(info_maj.get("telephone", "") or ""))

                        messages_statut = {
                            "Payé": f"Bonjour {info_maj.get('client', '')}, votre commande {ref_cmd} a bien été reçue et le paiement est confirmé ✅. Merci pour votre confiance !",
                            "Livré": f"Bonjour {info_maj.get('client', '')}, votre commande {ref_cmd} a été livrée 📦✅. Merci pour votre achat, à bientôt !",
                            "Annulé": f"Bonjour {info_maj.get('client', '')}, nous sommes désolés : votre commande {ref_cmd} a été annulée. N'hésitez pas à nous contacter pour plus d'informations.",
                            "En cours": f"Bonjour {info_maj.get('client', '')}, votre commande {ref_cmd} est en cours de traitement. Nous vous tiendrons informé(e) !"
                        }
                        message_client = messages_statut.get(info_maj["nouveau_statut"], "")

                        st.markdown("---")
                        if tel_client:
                            wa_client_url = f"https://wa.me/{tel_client}?text={urllib.parse.quote(message_client)}"
                            st.info(
                                f"📲 Prévenir **{info_maj.get('client', 'le client')}** du nouveau statut "
                                f"« {info_maj['nouveau_statut']} » ?"
                            )
                            st.caption(
                                "⚠️ Vérifie que le numéro comporte bien l'indicatif pays avant d'envoyer "
                                "(le client l'a saisi tel quel au moment de la commande)."
                            )
                            st.markdown(
                                f'''<a href="{wa_client_url}" target="_blank" rel="noopener"
                                        style="display:block; text-align:center; background:#25D366; color:white;
                                               font-weight:600; padding:10px 16px; border-radius:8px;
                                               text-decoration:none; margin-top:4px;">
                                        📱 Envoyer la notification WhatsApp
                                    </a>''',
                                unsafe_allow_html=True
                            )
                        else:
                            st.warning(
                                "⚠️ Aucun numéro de téléphone enregistré pour cette commande "
                                "(commande créée avant l'ajout de ce champ) — notification impossible."
                            )
                        if st.button("Fermer", key="fermer_notif_statut"):
                            del st.session_state.dernier_maj_statut
                            st.rerun()
                else:
                    st.info("Aucune commande enregistrée.")
            else:
                st.warning("Impossible de charger les commandes.")

            st.subheader("⚠️ Alertes Stock")
            if not df_catalogue.empty:
                # 🔧 FIX : utilise le vrai seuil configuré (⚙️ Paramètres) au lieu
                # d'une valeur fixe de 10 qui ne correspondait à rien de réglable.
                seuil_alerte_dashboard = int(float(config.get("seuil_alerte_stock", 3)))
                alerts = df_catalogue[df_catalogue['stock'] <= seuil_alerte_dashboard].copy()
                if not alerts.empty:
                    st.dataframe(alerts[['nom', 'stock', 'prix']].sort_values('stock'),
                               use_container_width=True)
                else:
                    st.success("✅ Aucun stock critique")

            # ====================== 🆕 PANIERS ABANDONNÉS ======================
            st.markdown("---")
            st.subheader("🛒 Paniers abandonnés")
            if str(config.get("panier_abandonne_actif", "non")) != "oui":
                st.info(
                    "La relance des paniers abandonnés est désactivée. "
                    "Active-la dans l'onglet ⚙️ Paramètres pour commencer à suivre les clients "
                    "qui remplissent leurs coordonnées sans finaliser leur commande."
                )
            else:
                paniers_data, err_paniers = call_passerelle_admin({"action": "get_paniers_abandonnes"})
                if err_paniers or not paniers_data or paniers_data.get("status") != "success":
                    st.warning("Impossible de charger les paniers abandonnés pour le moment.")
                else:
                    paniers_liste = paniers_data.get("paniers", [])
                    if not paniers_liste:
                        st.success("✅ Aucun panier abandonné en attente pour le moment.")
                    else:
                        st.caption(f"{len(paniers_liste)} panier(s) en attente de finalisation ou déjà relancé(s).")
                        for panier in paniers_liste:
                            articles_panier = panier.get("articles", [])
                            resume_articles = ", ".join(
                                f"{a.get('nom', '')} × {a.get('quantite', 1)}" for a in articles_panier
                            )
                            statut_panier = panier.get("statut", "en_attente")
                            badge_statut = "🔔 Relance envoyée" if statut_panier == "relance_envoyee" else "⏳ En attente"
                            with st.container():
                                st.markdown(
                                    f"**{panier.get('client', 'Client')}** — {format_fcfa(panier.get('total', 0))} · {badge_statut}"
                                )
                                st.caption(resume_articles or "Détail des articles indisponible")
                                telephone_panier = re.sub(r"\D", "", str(panier.get("telephone", "") or ""))
                                if telephone_panier:
                                    message_relance_manuelle = (
                                        f"Bonjour {panier.get('client', '')}, vous avez laissé des articles dans "
                                        f"votre panier chez {NOM_BOUTIQUE}. Souhaitez-vous toujours les commander ? 😊"
                                    )
                                    wa_relance_url = f"https://wa.me/{telephone_panier}?text={urllib.parse.quote(message_relance_manuelle)}"
                                    st.link_button("📲 Relancer sur WhatsApp", wa_relance_url)
                                else:
                                    st.caption("⚠️ Pas de téléphone enregistré pour ce panier.")
                                st.markdown("---")

        # ====================== AJOUTER ======================
        with tab2:
            st.subheader("➕ Ajouter un article")
            with st.form("add_form", clear_on_submit=True):
                nom = st.text_input("Nom de l'article *")
                prix = st.number_input("Prix (FCFA)", min_value=0, step=1000)
                prix_promo = st.number_input(
                    "Prix promotionnel (FCFA, optionnel)", min_value=0, step=1000, value=0,
                    help="Laisser à 0 pour ne pas activer de promo. Doit être inférieur au prix normal."
                )
                uploaded = st.file_uploader("Photo principale *", type=["jpg", "png", "jpeg"])
                photos_supp = st.file_uploader(
                    "Photos supplémentaires (optionnel)", type=["jpg", "png", "jpeg"],
                    accept_multiple_files=True, key="add_photos_supp"
                )
                tailles = st.text_input("Tailles", "Unique")
                couleurs = st.text_input("Couleurs", "")
                categorie = st.text_input("Catégorie", "Vêtements")
                stock = st.number_input("Stock initial", min_value=0, value=10)

                if st.form_submit_button("Ajouter au catalogue"):
                    if not nom or not uploaded:
                        st.warning("Nom et photo principale sont obligatoires.")
                    elif prix_promo and prix_promo >= prix:
                        st.warning("Le prix promotionnel doit être inférieur au prix normal.")
                    else:
                        with st.spinner("Upload + enregistrement..."):
                            img_url, err = upload_image_to_imgbb(uploaded.getvalue())
                            if err:
                                st.error(err)
                            else:
                                urls_supp = []
                                for fichier_supp in (photos_supp or []):
                                    url_supp, err_supp = upload_image_to_imgbb(fichier_supp.getvalue())
                                    if err_supp:
                                        st.warning(f"⚠️ Une photo supplémentaire n'a pas pu être envoyée : {err_supp}")
                                    elif url_supp:
                                        urls_supp.append(url_supp)

                                payload = {
                                    "action": "ajout_article",
                                    "nom": nom, "prix": prix, "image": img_url,
                                    "images_supplementaires": ", ".join(urls_supp),
                                    "tailles": tailles, "couleurs": couleurs,
                                    "categorie": categorie, "stock": stock,
                                    "prix_promo": prix_promo or ""
                                }
                                reponse, err = call_passerelle_admin(payload)
                                if err or not reponse or reponse.get("status") != "success":
                                    st.error(f"❌ Erreur : {err or (reponse or {}).get('message', 'réponse invalide')}")
                                else:
                                    st.toast("✅ Article ajouté !")
                                    load_data.clear()  # 🔧 FIX cache
                                    st.session_state.refresh_token += 1
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
                        photo_actuelle = image_valide(row_edit.get('image', ''))
                        if photo_actuelle:
                            st.image(photo_actuelle, width=120, caption="Photo principale actuelle")
                        else:
                            st.caption("Pas de photo actuelle")
                    with col_img2:
                        nouvelle_photo = st.file_uploader(
                            "Remplacer la photo principale (optionnel)", type=["jpg", "png", "jpeg"], key="edit_photo"
                        )

                    photos_supp_actuelles = parse_image_list(row_edit.get('images_supplementaires', ''))
                    if photos_supp_actuelles:
                        st.caption(f"📷 {len(photos_supp_actuelles)} photo(s) supplémentaire(s) actuelle(s) :")
                        cols_apercu = st.columns(min(len(photos_supp_actuelles), 4))
                        for i_apercu, url_apercu in enumerate(photos_supp_actuelles[:4]):
                            with cols_apercu[i_apercu]:
                                st.image(url_apercu, width=80)

                    supprimer_photos_supp = st.checkbox(
                        "🗑️ Supprimer toutes les photos supplémentaires actuelles", key="edit_supp_clear"
                    ) if photos_supp_actuelles else False

                    nouvelles_photos_supp = st.file_uploader(
                        "Ajouter des photos supplémentaires (optionnel)", type=["jpg", "png", "jpeg"],
                        accept_multiple_files=True, key="edit_photos_supp"
                    )

                    nouveau_nom = st.text_input("Nom de l'article", value=str(row_edit.get('nom', '')))
                    nouveau_prix = st.number_input(
                        "Prix (FCFA)", min_value=0, step=1000,
                        value=int(row_edit.get('prix_numeric', 0))
                    )
                    valeur_promo_actuelle = row_edit.get('prix_promo_numeric', None)
                    try:
                        valeur_promo_actuelle = int(valeur_promo_actuelle) if pd.notna(valeur_promo_actuelle) else 0
                    except (ValueError, TypeError):
                        valeur_promo_actuelle = 0
                    nouveau_prix_promo = st.number_input(
                        "Prix promotionnel (FCFA, optionnel)", min_value=0, step=1000,
                        value=valeur_promo_actuelle,
                        help="Laisser à 0 pour désactiver la promo. Doit être inférieur au prix normal."
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
                        if nouveau_prix_promo and nouveau_prix_promo >= nouveau_prix:
                            st.warning("Le prix promotionnel doit être inférieur au prix normal.")
                            st.stop()
                        with st.spinner("Mise à jour en cours..."):
                            image_url = row_edit.get('image', '')
                            if nouvelle_photo is not None:
                                image_url, err = upload_image_to_imgbb(nouvelle_photo.getvalue())
                                if err:
                                    st.error(f"Erreur upload photo : {err}")
                                    st.stop()

                            # Liste de départ : vide si l'admin a coché "supprimer", sinon les photos actuelles
                            liste_supp = [] if supprimer_photos_supp else list(photos_supp_actuelles)
                            for fichier_supp in (nouvelles_photos_supp or []):
                                url_supp, err_supp = upload_image_to_imgbb(fichier_supp.getvalue())
                                if err_supp:
                                    st.warning(f"⚠️ Une photo supplémentaire n'a pas pu être envoyée : {err_supp}")
                                elif url_supp:
                                    liste_supp.append(url_supp)

                            payload = {
                                "action": "modification_article",
                                "ancien_nom": article_to_edit,
                                # si la colonne "id" existe dans le Google Sheet (ajoutée par la
                                # mise à jour du script), on la transmet pour un matching fiable ;
                                # sinon le script retombe automatiquement sur "ancien_nom"
                                "id": str(row_edit.get('id', '') or ''),
                                "nom": nouveau_nom,
                                "prix": nouveau_prix,
                                "image": image_url,
                                "images_supplementaires": ", ".join(liste_supp),
                                "tailles": nouvelles_tailles,
                                "couleurs": nouvelles_couleurs,
                                "categorie": nouvelle_categorie,
                                "stock": nouveau_stock,
                                "prix_promo": nouveau_prix_promo or ""
                            }
                            reponse, err = call_passerelle_admin(payload)
                            if err or not reponse or reponse.get("status") != "success":
                                st.error(f"❌ Erreur lors de la mise à jour : {err or (reponse or {}).get('message', 'réponse invalide')}")
                            else:
                                st.toast("✅ Article mis à jour !")
                                load_data.clear()  # 🔧 FIX cache
                                st.session_state.refresh_token += 1
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
                    photo_suppr = image_valide(row_suppr.get('image', ''))
                    if photo_suppr:
                        st.image(photo_suppr, width=120)
                    else:
                        st.caption("Pas de photo")
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
                                    "nom": article_suppr,
                                    # 🆕 idem : transmet l'id si disponible, sinon fallback sur "nom"
                                    "id": str(row_suppr.get('id', '') or '')
                                }
                                reponse, err = call_passerelle_admin(payload)
                                if err or not reponse or reponse.get("status") != "success":
                                    st.error(f"❌ Erreur lors de la suppression : {err or (reponse or {}).get('message', '')}")
                                else:
                                    st.toast("✅ Article supprimé !")
                                    load_data.clear()  # 🔧 FIX cache
                                    st.session_state.refresh_token += 1
                                    st.session_state.confirm_delete = False
                                    st.rerun()
                    with col_conf2:
                        if st.button("❌ Annuler", use_container_width=True):
                            st.session_state.confirm_delete = False
                            st.rerun()
            else:
                st.info("Aucun article disponible.")

        # ====================== PARAMÈTRES ======================
        with tab5:
            st.subheader("⚙️ Paramètres de la boutique")
            st.caption("Ces réglages sont enregistrés dans ton Google Sheet — plus besoin de toucher au code.")

            with st.form("form_nom_boutique"):
                st.markdown("**Nom de la boutique**")
                nouveau_nom_boutique = st.text_input("Nom affiché en haut de l'appli", value=NOM_BOUTIQUE)
                if st.form_submit_button("💾 Enregistrer le nom"):
                    reponse, err = call_passerelle_admin({
                        "action": "modifier_config",
                        "nouveau_nom_boutique": nouveau_nom_boutique
                    })
                    if err or not reponse or reponse.get("status") != "success":
                        st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                    else:
                        st.toast("✅ Nom de la boutique mis à jour !")
                        load_config.clear()
                        st.rerun()

            st.markdown("---")
            st.markdown("**Logo de la boutique**")
            if LOGO_URL:
                st.image(LOGO_URL, width=140, caption="Logo actuel")
            nouveau_logo_fichier = st.file_uploader(
                # 🔧 FIX : "webp" retiré — ImgBB ne traite pas toujours ce format de
                # façon fiable via son API, ce qui provoquait un échec d'envoi du
                # logo sans qu'aucune image ne soit finalement enregistrée.
                "Choisir une nouvelle image de logo", type=["png", "jpg", "jpeg"], key="upload_logo"
            )
            if st.button("💾 Enregistrer le logo", disabled=nouveau_logo_fichier is None):
                with st.spinner("Envoi de l'image..."):
                    url_logo, err_img = upload_image_to_imgbb(nouveau_logo_fichier.getvalue())
                if err_img or not url_logo:
                    st.error(f"❌ Erreur lors de l'envoi de l'image : {err_img or 'inconnue'}")
                else:
                    reponse, err = call_passerelle_admin({
                        "action": "modifier_config",
                        "nouveau_logo": url_logo
                    })
                    if err or not reponse or reponse.get("status") != "success":
                        st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                    else:
                        st.toast("✅ Logo mis à jour !")
                        load_config.clear()
                        st.rerun()

            st.markdown("---")
            with st.form("form_whatsapp"):
                st.markdown("**Numéro WhatsApp**")
                nouveau_whatsapp = st.text_input(
                    "Numéro (avec indicatif pays, ex : 23566000000)",
                    value=config["whatsapp"]
                )
                if st.form_submit_button("💾 Enregistrer le numéro"):
                    reponse, err = call_passerelle_admin({
                        "action": "modifier_config",
                        "nouveau_whatsapp": re.sub(r"\D", "", nouveau_whatsapp)
                    })
                    if err or not reponse or reponse.get("status") != "success":
                        st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                    else:
                        st.toast("✅ Numéro WhatsApp mis à jour !")
                        load_config.clear()
                        st.rerun()

            st.markdown("---")
            with st.form("form_email_admin"):
                st.markdown("**📧 Email de notification des commandes**")
                st.caption("Une notification automatique sera envoyée à cette adresse à chaque nouvelle commande.")
                nouvel_email_admin = st.text_input(
                    "Adresse email",
                    value=config.get("email_admin", "")
                )
                if st.form_submit_button("💾 Enregistrer l'email"):
                    reponse, err = call_passerelle_admin({
                        "action": "modifier_config",
                        "nouveau_email_admin": nouvel_email_admin.strip()
                    })
                    if err or not reponse or reponse.get("status") != "success":
                        st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                    else:
                        st.toast("✅ Email de notification mis à jour !")
                        load_config.clear()
                        st.rerun()

            st.markdown("---")
            with st.form("form_seuil_stock"):
                st.markdown("**⚠️ Seuil d'alerte de stock bas**")
                st.caption(
                    "Dès qu'un article passe à ce niveau (ou en dessous) suite à une commande, "
                    "un email d'alerte est envoyé automatiquement à l'adresse ci-dessus, "
                    "pour prévenir la rupture de stock à l'avance."
                )
                try:
                    valeur_seuil_actuelle = int(float(config.get("seuil_alerte_stock", 3)))
                except (ValueError, TypeError):
                    valeur_seuil_actuelle = 3
                nouveau_seuil = st.number_input(
                    "Pièces restantes déclenchant l'alerte",
                    min_value=0, max_value=100, step=1, value=valeur_seuil_actuelle
                )
                if st.form_submit_button("💾 Enregistrer le seuil"):
                    reponse, err = call_passerelle_admin({
                        "action": "modifier_config",
                        "nouveau_seuil_alerte_stock": nouveau_seuil
                    })
                    if err or not reponse or reponse.get("status") != "success":
                        st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                    else:
                        st.toast("✅ Seuil d'alerte mis à jour !")
                        load_config.clear()
                        st.rerun()

            st.markdown("---")
            with st.form("form_heure_bilan"):
                st.markdown("**📊 Heure du bilan quotidien**")
                st.caption(
                    "Chaque jour à cette heure, un email récap (commandes, chiffre d'affaires, "
                    "état du stock) t'est envoyé automatiquement à l'adresse ci-dessus."
                )
                try:
                    valeur_heure_actuelle = int(float(config.get("heure_bilan_quotidien", 20)))
                except (ValueError, TypeError):
                    valeur_heure_actuelle = 20
                nouvelle_heure = st.number_input(
                    "Heure d'envoi (0-23)",
                    min_value=0, max_value=23, step=1, value=valeur_heure_actuelle
                )
                if st.form_submit_button("💾 Enregistrer l'heure"):
                    reponse, err = call_passerelle_admin({
                        "action": "modifier_config",
                        "nouvelle_heure_bilan_quotidien": nouvelle_heure
                    })
                    if err or not reponse or reponse.get("status") != "success":
                        st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                    else:
                        st.toast(f"✅ Bilan quotidien réglé sur {nouvelle_heure}h !")
                        load_config.clear()
                        st.rerun()

            st.markdown("---")
            with st.form("form_panier_abandonne"):
                st.markdown("**🛒 Récupération de panier abandonné**")
                st.caption(
                    "Dès qu'un client renseigne son nom et son téléphone dans le panier sans "
                    "finaliser sa commande, il est suivi ici. Passé le délai ci-dessous sans "
                    "commande confirmée, tu reçois un email avec un lien WhatsApp prérempli "
                    "pour le relancer personnellement."
                )
                panier_abandonne_actif_actuel = str(config.get("panier_abandonne_actif", "non")) == "oui"
                nouveau_panier_abandonne_actif = st.checkbox(
                    "Activer la relance des paniers abandonnés",
                    value=panier_abandonne_actif_actuel
                )
                try:
                    valeur_delai_actuelle = int(float(config.get("delai_relance_panier_minutes", 60)))
                except (ValueError, TypeError):
                    valeur_delai_actuelle = 60
                nouveau_delai_relance = st.number_input(
                    "Délai avant relance (minutes)",
                    min_value=5, max_value=1440, step=5, value=valeur_delai_actuelle
                )
                if st.form_submit_button("💾 Enregistrer"):
                    reponse, err = call_passerelle_admin({
                        "action": "modifier_config",
                        "nouveau_panier_abandonne_actif": "oui" if nouveau_panier_abandonne_actif else "non",
                        "nouveau_delai_relance_panier_minutes": nouveau_delai_relance
                    })
                    if err or not reponse or reponse.get("status") != "success":
                        st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                    else:
                        st.toast("✅ Paramètres de relance mis à jour !")
                        load_config.clear()
                        st.rerun()

            st.markdown("---")
            with st.form("form_mot_de_passe"):
                st.markdown("**Mot de passe admin**")
                nouveau_mdp = st.text_input("Nouveau mot de passe", type="password")
                confirmation_mdp = st.text_input("Confirmer le nouveau mot de passe", type="password")
                if st.form_submit_button("💾 Changer le mot de passe"):
                    if not nouveau_mdp:
                        st.warning("Le mot de passe ne peut pas être vide.")
                    elif nouveau_mdp != confirmation_mdp:
                        st.warning("Les deux mots de passe ne correspondent pas.")
                    else:
                        reponse, err = call_passerelle_admin({
                            "action": "modifier_config",
                            "nouveau_mot_de_passe": nouveau_mdp
                        })
                        if err or not reponse or reponse.get("status") != "success":
                            st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                        else:
                            st.success("✅ Mot de passe mis à jour ! Reconnecte-toi avec le nouveau mot de passe la prochaine fois.")

        # ====================== 🆕 MODÉRATION DES AVIS CLIENTS ======================
        with tab6:
            st.subheader("⭐ Modération des avis clients")
            st.caption(
                "Les avis laissés par les clients apparaissent d'abord ici, en attente. "
                "Approuve-les pour qu'ils deviennent visibles sur la boutique, ou supprime "
                "ceux qui ne conviennent pas."
            )
            avis_data, err_avis_admin = call_passerelle_admin({"action": "get_avis_admin"})
            if err_avis_admin or not avis_data or avis_data.get("status") != "success":
                st.warning("Impossible de charger les avis pour le moment.")
            else:
                tous_avis = avis_data.get("avis", [])
                avis_en_attente = [a for a in tous_avis if a.get("statut") != "approuve"]
                avis_approuves = [a for a in tous_avis if a.get("statut") == "approuve"]

                st.markdown(f"**⏳ En attente de validation ({len(avis_en_attente)})**")
                if not avis_en_attente:
                    st.success("✅ Aucun avis en attente.")
                else:
                    for avis_a in avis_en_attente:
                        with st.container():
                            st.markdown(
                                f"{format_etoiles(avis_a.get('note', 0))} — **{avis_a.get('article_nom', '')}** "
                                f"— par {avis_a.get('client_nom', '')}"
                            )
                            if avis_a.get("commentaire"):
                                st.caption(avis_a["commentaire"])
                            col_approuver, col_supprimer = st.columns(2)
                            with col_approuver:
                                if st.button("✅ Approuver", key=f"approuver_{avis_a.get('id')}", use_container_width=True):
                                    rep, err = call_passerelle_admin({
                                        "action": "moderer_avis", "id_avis": avis_a.get("id"), "decision": "approuver"
                                    })
                                    if err or not rep or rep.get("status") != "success":
                                        st.error(f"❌ {(rep or {}).get('message', err or 'Erreur')}")
                                    else:
                                        st.toast("✅ Avis approuvé !")
                                        load_avis_moyennes.clear()
                                        st.rerun()
                            with col_supprimer:
                                if st.button("🗑️ Supprimer", key=f"supprimer_attente_{avis_a.get('id')}", use_container_width=True):
                                    rep, err = call_passerelle_admin({
                                        "action": "moderer_avis", "id_avis": avis_a.get("id"), "decision": "supprimer"
                                    })
                                    if err or not rep or rep.get("status") != "success":
                                        st.error(f"❌ {(rep or {}).get('message', err or 'Erreur')}")
                                    else:
                                        st.toast("🗑️ Avis supprimé.")
                                        st.rerun()
                            st.markdown("---")

                st.markdown(f"**✅ Avis publiés ({len(avis_approuves)})**")
                if not avis_approuves:
                    st.caption("Aucun avis publié pour le moment.")
                else:
                    for avis_p in avis_approuves:
                        with st.container():
                            st.markdown(
                                f"{format_etoiles(avis_p.get('note', 0))} — **{avis_p.get('article_nom', '')}** "
                                f"— par {avis_p.get('client_nom', '')}"
                            )
                            if avis_p.get("commentaire"):
                                st.caption(avis_p["commentaire"])
                            if st.button("🗑️ Retirer de la boutique", key=f"supprimer_publie_{avis_p.get('id')}"):
                                rep, err = call_passerelle_admin({
                                    "action": "moderer_avis", "id_avis": avis_p.get("id"), "decision": "supprimer"
                                })
                                if err or not rep or rep.get("status") != "success":
                                    st.error(f"❌ {(rep or {}).get('message', err or 'Erreur')}")
                                else:
                                    st.toast("🗑️ Avis retiré.")
                                    load_avis_moyennes.clear()
                                    st.rerun()
                            st.markdown("---")
