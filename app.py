import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import uuid
import re
import html as html_lib
import unicodedata
import base64
import hashlib
import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime, timezone
from supabase import create_client, Client

st.set_page_config(page_title="Destiny Luxury Collection", page_icon="👗", layout="wide")

# ====================== 0. STYLE (thème "luxe" sobre : fond sombre, accents dorés) ======================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Playfair Display', serif !important; letter-spacing: 0.3px; }

    .stApp { background: linear-gradient(180deg, #0d0d0f 0%, #16151a 100%); }

    /* Cartes produit */
    div[data-testid="column"] > div > div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stVerticalBlock"] div.element-container:has(img) {
        border-radius: 14px;
    }
    img {
        border-radius: 12px !important;
    }

    /* Boutons */
    .stButton > button {
        border-radius: 8px;
        border: 1px solid #c9a35c;
        color: #c9a35c;
        background: transparent;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: #c9a35c;
        color: #16151a;
        border-color: #c9a35c;
    }
    .stFormSubmitButton > button {
        border-radius: 8px;
        background: #c9a35c;
        color: #16151a;
        font-weight: 600;
        border: none;
    }
    .stFormSubmitButton > button:hover {
        background: #dab873;
    }

    /* Prix et titres produits */
    div[data-testid="stMarkdownContainer"] strong { color: #eae4d8; }
    .destiny-nom-produit {
        font-family: 'Playfair Display', serif;
        font-size: 1.12rem;
        font-weight: 700;
        color: #eae4d8;
        letter-spacing: 0.2px;
        margin: 6px 0 2px 0;
        line-height: 1.3;
    }

    /* Bandeau promo doré */
    .destiny-promo-ligne { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin: 2px 0 4px 0; }
    .destiny-promo-ancien-prix {
        color: #857f73; text-decoration: line-through; font-size: 0.85rem;
    }
    .destiny-promo-badge {
        display: inline-flex; align-items: center; gap: 5px;
        background: linear-gradient(135deg, #f0d9a6 0%, #c9a35c 45%, #a9803f 100%);
        color: #16151a; font-weight: 700; padding: 4px 11px; border-radius: 20px;
        font-size: 0.92rem; box-shadow: 0 2px 12px rgba(201,163,92,0.45);
        letter-spacing: 0.2px;
    }
    .destiny-prix-normal { color: #eae4d8; font-weight: 600; font-size: 1.05rem; }

    /* Bandeau logo -- effet "bling" premium plein écran */
    .destiny-hero {
        position: relative;
        left: 50%;
        right: 50%;
        margin-left: -50vw;
        margin-right: -50vw;
        width: 100vw;
        text-align: center;
        padding: 3.5rem 1rem 2.5rem 1rem;
        margin-top: -1rem;
        margin-bottom: 1.5rem;
        overflow: hidden;
        background:
            radial-gradient(ellipse at center, rgba(201,163,92,0.22) 0%, rgba(13,13,15,0) 68%),
            linear-gradient(180deg, #1b1810 0%, #0d0d0f 100%);
        border-bottom: 1px solid rgba(201,163,92,0.35);
    }
    .destiny-hero::before {
        content: "";
        position: absolute;
        top: 50%; left: 50%;
        width: 160%; height: 420px;
        transform: translate(-50%, -50%);
        background: conic-gradient(from 0deg, transparent, rgba(201,163,92,0.28), transparent 28%);
        animation: destiny-rotation 9s linear infinite;
        pointer-events: none;
    }
    @keyframes destiny-rotation { to { transform: translate(-50%, -50%) rotate(360deg); } }

    .destiny-hero-logo-wrap {
        position: relative;
        display: inline-block;
        z-index: 1;
        border-radius: 18px;
        overflow: hidden;
    }
    .destiny-hero img {
        max-height: 240px;
        max-width: min(90vw, 480px);
        display: block;
        border-radius: 18px;
        position: relative;
        animation: destiny-glow 3s ease-in-out infinite alternate;
    }
    @keyframes destiny-glow {
        from { box-shadow: 0 0 20px rgba(201,163,92,0.35), 0 0 45px rgba(201,163,92,0.18), 0 10px 40px rgba(0,0,0,0.55); }
        to   { box-shadow: 0 0 38px rgba(201,163,92,0.7), 0 0 85px rgba(201,163,92,0.38), 0 10px 40px rgba(0,0,0,0.55); }
    }
    .destiny-hero-shine {
        position: absolute;
        top: 0; left: -60%;
        width: 35%; height: 100%;
        background: linear-gradient(115deg, transparent, rgba(255,255,255,0.55), transparent);
        transform: skewX(-20deg);
        animation: destiny-shine 3.2s ease-in-out infinite;
        z-index: 2;
    }
    @keyframes destiny-shine {
        0%   { left: -60%; }
        45%  { left: 130%; }
        100% { left: 130%; }
    }
    .destiny-hero h1 {
        font-size: 2.6rem;
        color: #f4ecdc;
        margin-top: 1.1rem;
        letter-spacing: 1px;
        text-shadow: 0 0 20px rgba(201,163,92,0.55);
        position: relative; z-index: 1;
    }
    .destiny-hero .destiny-tagline {
        color: #c9a35c;
        letter-spacing: 4px;
        text-transform: uppercase;
        font-size: 0.78rem;
        margin-top: 0.5rem;
        position: relative; z-index: 1;
    }
</style>
""", unsafe_allow_html=True)

# ====================== 1. SECRETS ======================
# 🔒 FIX : après un très long aller-retour infructueux avec Supabase Auth
# (confirmation d'email, CAPTCHA, providers...), on repart sur le système
# simple qu'avait l'app Apps Script d'origine : un mot de passe hashé
# (SHA-256) stocké dans la table config, comparé directement en Python.
# Zéro dépendance à Supabase Auth = zéro risque de retomber sur "Invalid
# login credentials" pour des raisons de configuration externes.
# SUPABASE_SECRET_KEY (clé "secret" / service_role) est nécessaire pour que
# les actions admin puissent lire/écrire en base MÊME si les policies RLS
# ne couvrent que le rôle anon -- cette clé bypasse RLS, donc ne la mets
# JAMAIS ailleurs que dans st.secrets.
SECRETS_REQUIS = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SECRET_KEY", "IMGBB_API_KEY"]
SECRETS_MANQUANTS = [s for s in SECRETS_REQUIS if s not in st.secrets]
if SECRETS_MANQUANTS:
    st.error(f"Secrets manquants : {', '.join(SECRETS_MANQUANTS)}")
    st.stop()

EMAIL_ACTIVE = "GMAIL_ADDRESS" in st.secrets and "GMAIL_APP_PASSWORD" in st.secrets


def normaliser(valeur):
    return unicodedata.normalize("NFC", str(valeur or "")).strip()


# ====================== 2. CLIENTS SUPABASE ======================
@st.cache_resource
def get_public_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


@st.cache_resource
def get_admin_client() -> Client:
    # 🔒 La clé secret/service_role bypasse toujours RLS, quel que soit le
    # visiteur qui exécute le code -- mais l'AFFICHAGE de l'admin reste
    # protégé par admin_connecte (propre à chaque session ci-dessous), donc
    # ce n'est utilisable qu'après avoir tapé le bon mot de passe.
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SECRET_KEY"])


sb = get_public_client()

if "admin_connecte" not in st.session_state:
    st.session_state.admin_connecte = False


# 🔑 Pour définir/réinitialiser le mot de passe admin directement en base
# (si tu ne connais pas le mot de passe original migré depuis Sheets),
# lance ceci dans le SQL Editor Supabase en remplaçant la valeur :
#   update config set valeur = encode(sha256('TonNouveauMotDePasse'::bytea), 'hex')
#   where cle = 'mot_de_passe';
def hash_mot_de_passe(valeur):
    return hashlib.sha256(str(valeur or "").encode("utf-8")).hexdigest()


def admin_login(mot_de_passe):
    config_actuelle = charger_config(st.session_state.refresh_token)
    hash_attendu = config_actuelle.get("mot_de_passe", "")
    if hash_attendu and hash_mot_de_passe(mot_de_passe) == hash_attendu:
        st.session_state.admin_connecte = True
        return True
    return False


def admin_logout():
    st.session_state.admin_connecte = False


# ====================== 3. IMGBB (upload d'images) ======================
TAILLE_MAX_IMAGE_MO = 32  # limite du compte ImgBB gratuit


def televerser_image_imgbb(fichier):
    """Envoie un fichier uploadé vers ImgBB.
    Renvoie un tuple (url, erreur) : url vaut None en cas d'échec, et erreur
    contient alors un message explicite (au lieu d'échouer silencieusement)."""
    if fichier is None:
        return None, None

    try:
        contenu = fichier.getvalue()  # ne consomme pas le flux, contrairement à .read()
    except Exception as e:
        return None, f"Impossible de lire le fichier ({e})."

    taille_mo = len(contenu) / (1024 * 1024)
    if taille_mo > TAILLE_MAX_IMAGE_MO:
        return None, f"Fichier trop volumineux ({taille_mo:.1f} Mo, max {TAILLE_MAX_IMAGE_MO} Mo)."

    try:
        image_b64 = base64.b64encode(contenu).decode()
        reponse = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": st.secrets["IMGBB_API_KEY"], "image": image_b64},
            timeout=60
        )
    except requests.exceptions.Timeout:
        return None, "Délai d'attente dépassé (connexion trop lente ou fichier trop lourd)."
    except requests.exceptions.RequestException as e:
        return None, f"Erreur réseau lors de l'envoi vers ImgBB : {e}"

    try:
        donnees = reponse.json()
    except Exception:
        return None, f"Réponse invalide d'ImgBB (code HTTP {reponse.status_code})."

    if donnees.get("success"):
        return donnees["data"]["url"], None

    message_erreur = (donnees.get("error") or {}).get("message", "erreur inconnue")
    return None, f"ImgBB a refusé l'image : {message_erreur} (code HTTP {reponse.status_code})."


# ====================== 3bis. GALERIE PHOTOS AVEC GLISSEMENT (SWIPE) ======================
def afficher_galerie_swipe(images, hauteur=280, cle=""):
    """Affiche une galerie photo qu'on peut faire glisser au doigt (mobile) ou
    à la souris pour passer d'une image à l'autre, avec des points cliquables
    en complément sur ordinateur."""
    images = [u for u in images if u]
    if not images:
        return
    if len(images) == 1:
        st.image(images[0], use_container_width=True)
        return

    diapositives = "".join(
        f'<div class="dlc-slide"><img src="{html_lib.escape(u, quote=True)}" loading="lazy"></div>'
        for u in images
    )
    points = "".join(f'<span class="dlc-dot" data-i="{i}"></span>' for i in range(len(images)))
    id_composant = f"dlc-galerie-{re.sub(r'[^a-zA-Z0-9_-]', '', str(cle))}"

    code_html = f"""
    <div id="{id_composant}" class="dlc-galerie">
      <div class="dlc-piste">{diapositives}</div>
      <div class="dlc-dots">{points}</div>
    </div>
    <style>
      #{id_composant} {{ position:relative; width:100%; font-family:'Inter',sans-serif; }}
      #{id_composant} .dlc-piste {{
        display:flex; overflow-x:auto; scroll-snap-type:x mandatory;
        -webkit-overflow-scrolling:touch; border-radius:12px; scrollbar-width:none;
      }}
      #{id_composant} .dlc-piste::-webkit-scrollbar {{ display:none; }}
      #{id_composant} .dlc-slide {{
        flex:0 0 100%; scroll-snap-align:center; display:flex;
        align-items:center; justify-content:center; background:#0d0d0f;
      }}
      #{id_composant} .dlc-slide img {{
        width:100%; height:{hauteur}px; object-fit:cover; border-radius:12px; display:block;
      }}
      #{id_composant} .dlc-dots {{ display:flex; justify-content:center; gap:6px; margin-top:6px; }}
      #{id_composant} .dlc-dot {{
        width:6px; height:6px; border-radius:50%; background:#5a5a5f;
        transition:background .2s; cursor:pointer;
      }}
      #{id_composant} .dlc-dot.actif {{ background:#c9a35c; }}
    </style>
    <script>
      (function() {{
        const conteneur = document.getElementById("{id_composant}");
        const piste = conteneur.querySelector(".dlc-piste");
        const pts = conteneur.querySelectorAll(".dlc-dot");
        function majPoints() {{
          const i = Math.round(piste.scrollLeft / piste.clientWidth);
          pts.forEach((p, idx) => p.classList.toggle("actif", idx === i));
        }}
        piste.addEventListener("scroll", () => {{
          window.clearTimeout(piste._t);
          piste._t = window.setTimeout(majPoints, 60);
        }});
        pts.forEach(p => p.addEventListener("click", () => {{
          const i = parseInt(p.dataset.i, 10);
          piste.scrollTo({{ left: i * piste.clientWidth, behavior: "smooth" }});
        }}));
        majPoints();
      }})();
    </script>
    """
    components.html(code_html, height=hauteur + 26, scrolling=False)


def afficher_hero(logo_url, titre, sous_titre=""):
    """Affiche le bandeau logo + effet lumineux doré en arrière-plan, avec un
    titre (ex: nom de la boutique, ou message de bienvenue) et un sous-titre
    facultatif. Réutilisé pour la boutique ET pour l'écran d'accueil admin."""
    sous_titre_html = f'<div class="destiny-tagline">{sous_titre}</div>' if sous_titre else ""
    if logo_url:
        st.markdown(
            f'<div class="destiny-hero">'
            f'<div class="destiny-hero-logo-wrap">'
            f'<img src="{html_lib.escape(logo_url, quote=True)}">'
            f'<div class="destiny-hero-shine"></div>'
            f'</div>'
            f'<h1>{titre}</h1>'
            f'{sous_titre_html}'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="destiny-hero"><h1>{titre}</h1>{sous_titre_html}</div>',
            unsafe_allow_html=True
        )


def jouer_son_ajout():
    """Joue un petit carillon raffiné (généré à la volée, aucun fichier audio
    nécessaire) au moment où un article est ajouté au panier. Certains
    navigateurs mobiles bloquent l'audio automatique par défaut -- c'est une
    politique du navigateur, pas un bug de l'application."""
    components.html(
        """
        <script>
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const jouerNote = (freq, debut, duree, volume) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "sine";
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(0, ctx.currentTime + debut);
                gain.gain.linearRampToValueAtTime(volume, ctx.currentTime + debut + 0.01);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + debut + duree);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(ctx.currentTime + debut);
                osc.stop(ctx.currentTime + debut + duree);
            };
            jouerNote(880.0, 0, 0.12, 0.15);
            jouerNote(1318.5, 0.09, 0.2, 0.12);
        } catch (e) {}
        </script>
        """,
        height=0
    )


# ====================== 4. DONNÉES (mise en cache + TTL) ======================
@st.cache_data(ttl=60)
def charger_catalogue(_refresh=0):
    reponse = sb.table("catalogue").select("*").execute()
    df = pd.DataFrame(reponse.data)
    if df.empty:
        return df
    for col in ["prix", "prix_promo", "stock"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=60)
def charger_config(_refresh=0):
    reponse = sb.table("config").select("*").execute()
    return {row["cle"]: row["valeur"] for row in reponse.data}


@st.cache_data(ttl=30)
def charger_tous_avis_approuves(_refresh=0):
    """Un SEUL appel réseau vers Supabase pour récupérer tous les avis
    approuvés. Avant, chaque produit de la grille refaisait ce même appel
    (SELECT * sur toute la table) rien que pour filtrer différemment en
    Python ensuite -- avec 12 produits sur la page, ça faisait 12
    aller-retours réseau redondants, une cause majeure de latence perçue
    (surtout en mobile où chaque round-trip pèse plus lourd)."""
    reponse = sb.table("avis").select("*").eq("statut", "approuve").execute()
    return reponse.data


def indexer_avis_par_article(tous_avis):
    """Range chaque avis dans un dictionnaire {article: [avis...]} une seule
    fois, pour que l'affichage par produit ne soit plus qu'une simple lecture
    en mémoire (aucun réseau) au lieu d'une requête Supabase."""
    par_article = {}
    for row in tous_avis:
        for cle in {normaliser(row.get("article_id")), normaliser(row.get("article_nom"))}:
            if cle:
                par_article.setdefault(cle, []).append(row)
    for cle in par_article:
        par_article[cle].sort(key=lambda r: r.get("date", ""), reverse=True)
    return par_article


@st.cache_data(ttl=30)
def charger_avis_moyennes(_refresh=0):
    par_article = {}
    for row in charger_tous_avis_approuves(_refresh):
        cle_id = normaliser(row.get("article_id"))
        cle_nom = normaliser(row.get("article_nom"))
        for cle in {c for c in [cle_id, cle_nom] if c}:
            if cle not in par_article:
                par_article[cle] = {"somme": 0, "count": 0}
            par_article[cle]["somme"] += row.get("note") or 0
            par_article[cle]["count"] += 1
    return {
        cle: {"moyenne": round(v["somme"] / v["count"], 1), "count": v["count"]}
        for cle, v in par_article.items()
    }


if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = 0
if "cart" not in st.session_state:
    st.session_state.cart = []
if "dernier_panier_signature" not in st.session_state:
    st.session_state.dernier_panier_signature = None
if "message_toast" not in st.session_state:
    st.session_state.message_toast = None
if "icone_toast" not in st.session_state:
    st.session_state.icone_toast = "✅"
if "jouer_son" not in st.session_state:
    st.session_state.jouer_son = False
if "acces_choisi" not in st.session_state:
    st.session_state.acces_choisi = None

# 🔔 st.toast() et le son ne s'affichaient jamais : ils étaient déclenchés
# juste avant st.rerun(), qui interrompt le script et jette l'écran en cours
# avant que le navigateur n'ait eu le temps de les afficher/jouer. On les
# stocke donc dans la session et on les affiche ici, tout en haut du script,
# une fois que le rerun est terminé et que la nouvelle page est stable.
if st.session_state.message_toast:
    st.toast(st.session_state.message_toast, icon=st.session_state.icone_toast)
    st.session_state.message_toast = None
if st.session_state.jouer_son:
    jouer_son_ajout()
    st.session_state.jouer_son = False


def forcer_rafraichissement():
    st.session_state.refresh_token += 1
    charger_catalogue.clear()
    charger_config.clear()
    charger_avis_moyennes.clear()
    charger_tous_avis_approuves.clear()


# ====================== 5. PANIER ABANDONNÉ (auto-sauvegarde) ======================
# ⚠️ Nécessite que la colonne "telephone" de paniersabandonnés soit en TEXT
# (pas bigint) -- sinon un numéro commençant par 0 perd son zéro initial.
# Voir la conversation précédente pour la commande ALTER TABLE correspondante.
def sauvegarder_panier_abandonne(tel, nom, articles):
    tel = (tel or "").strip()
    nom = (nom or "").strip()
    if not tel or not articles:
        return
    total = sum(a["prix"] * a["quantite"] for a in articles)
    signature = (tel, nom, tuple((a["nom"], a["quantite"]) for a in articles), total)
    if st.session_state.dernier_panier_signature == signature:
        return  # rien de changé depuis la dernière sauvegarde, on évite une écriture inutile

    maintenant = datetime.now(timezone.utc).isoformat()
    donnees = {
        "date_derniere_maj": maintenant,
        "client_nom": nom,
        "telephone": tel,
        "articles": [{"nom": a["nom"], "prix": a["prix"], "quantite": a["quantite"]} for a in articles],
        "total": total,
        "statut": "en_attente"
    }
    try:
        existant = sb.table("paniersabandonnés").select("telephone").eq("telephone", tel).execute()
        if existant.data:
            sb.table("paniersabandonnés").update(donnees).eq("telephone", tel).execute()
        else:
            donnees["date_creation"] = maintenant
            sb.table("paniersabandonnés").insert(donnees).execute()
        st.session_state.dernier_panier_signature = signature
    except Exception:
        pass  # la sauvegarde du panier abandonné est un bonus, jamais bloquant


def marquer_panier_converti(tel):
    tel = (tel or "").strip()
    if not tel:
        return
    try:
        sb.table("paniersabandonnés").update({"statut": "converti"}).eq("telephone", tel).execute()
    except Exception:
        pass


# ====================== 6. EMAIL (Gmail SMTP, avec repli journalisé) ======================
def envoyer_notification_commande(id_commande, client_nom, tel, articles, total, introuvables):
    corps = "Nouvelle commande reçue sur Destiny Luxury Collection !\n\n"
    corps += f"Référence : {id_commande}\n"
    corps += f"Client : {client_nom}\nTéléphone : {tel}\n\nArticles :\n"
    for a in articles:
        corps += f"- {a['nom']} x {a['quantite']} = {a['prix'] * a['quantite']} FCFA\n"
    corps += f"\nTotal : {total} FCFA\n"
    if introuvables:
        corps += f"\n⚠️ Article(s) non reconnus dans le Catalogue (prix ignoré) : {', '.join(introuvables)}\n"

    envoye = False
    if EMAIL_ACTIVE:
        try:
            config = charger_config(st.session_state.refresh_token)
            destinataire = config.get("email_admin") or st.secrets["GMAIL_ADDRESS"]
            msg = MIMEText(corps, "plain", "utf-8")
            msg["Subject"] = f"Nouvelle commande — {total} FCFA"
            msg["From"] = st.secrets["GMAIL_ADDRESS"]
            msg["To"] = destinataire
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as serveur:
                serveur.login(st.secrets["GMAIL_ADDRESS"], st.secrets["GMAIL_APP_PASSWORD"])
                serveur.send_message(msg)
            envoye = True
        except Exception:
            envoye = False

    try:
        sb.table("emailsenattente").insert({
            "horodatage": datetime.now(timezone.utc).isoformat(),
            "id_commande": id_commande,
            "payload": corps,
            "envoye": "oui" if envoye else "non"
        }).execute()
    except Exception:
        pass

    return envoye


def envoyer_email_brut(destinataire, sujet, corps):
    """Envoie un email brut via Gmail SMTP. Renvoie True/False, ne lève jamais."""
    if not EMAIL_ACTIVE or not destinataire:
        return False
    try:
        msg = MIMEText(corps, "plain", "utf-8")
        msg["Subject"] = sujet
        msg["From"] = st.secrets["GMAIL_ADDRESS"]
        msg["To"] = destinataire
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as serveur:
            serveur.login(st.secrets["GMAIL_ADDRESS"], st.secrets["GMAIL_APP_PASSWORD"])
            serveur.send_message(msg)
        return True
    except Exception:
        return False


# ====================== 6bis. ALERTES AUTOMATIQUES ======================
# 🔔 Ces 3 fonctions utilisent le client admin (clé secrète, bypass RLS) car
# elles tournent en tâche de fond, quel que soit le visiteur qui a chargé la
# page -- ce ne sont pas des actions initiées par un client de la boutique.
def notifier_retour_stock(nom_article):
    """Prévient automatiquement par email les personnes inscrites à l'alerte
    de retour en stock pour cet article. Les contacts par téléphone restent
    visibles dans l'onglet Admin > Alertes stock pour une relance WhatsApp
    manuelle (pas d'API WhatsApp disponible pour un envoi 100% automatique)."""
    try:
        sb_bg = get_admin_client()
        reponse = sb_bg.table("alertesstock").select("*").eq("article", nom_article).eq("statut", "en_attente").execute()
    except Exception:
        return
    nom_boutique_actuel = charger_config(st.session_state.refresh_token).get("nom_boutique", "notre boutique")
    for alerte in (reponse.data or []):
        if alerte.get("contact_type") == "email":
            corps = (
                f"Bonne nouvelle ! L'article \"{nom_article}\" est de nouveau disponible "
                f"sur {nom_boutique_actuel}.\n\nVenez vite avant la prochaine rupture de stock !"
            )
            if envoyer_email_brut(alerte["contact"], f"{nom_article} est de retour en stock !", corps):
                try:
                    sb_bg.table("alertesstock").update({"statut": "notifie"}).eq("id", alerte["id"]).execute()
                except Exception:
                    pass


def verifier_alerte_stock_bas(df_catalogue, config):
    """Envoie un email à l'admin (une seule fois par jour) listant les
    articles dont le stock est descendu sous le seuil défini dans Config."""
    if not EMAIL_ACTIVE or df_catalogue.empty:
        return
    try:
        seuil = int(config.get("seuil_stock_bas", 3) or 3)
    except (TypeError, ValueError):
        seuil = 3
    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    if config.get("derniere_alerte_stock_date") == aujourdhui:
        return  # déjà envoyée aujourd'hui

    articles_bas = df_catalogue[df_catalogue["stock"] <= seuil]
    if articles_bas.empty:
        return

    destinataire = config.get("email_admin") or st.secrets.get("GMAIL_ADDRESS", "")
    corps = f"Seuil d'alerte configuré : {seuil} unité(s) ou moins.\n\nArticles concernés :\n"
    for _, ligne in articles_bas.iterrows():
        corps += f"- {ligne['nom']} : {int(ligne['stock'])} en stock\n"

    if envoyer_email_brut(destinataire, "⚠️ Alerte stock bas", corps):
        try:
            get_admin_client().table("config").upsert(
                {"cle": "derniere_alerte_stock_date", "valeur": aujourdhui}
            ).execute()
        except Exception:
            pass


def verifier_bilan_quotidien(config):
    """Envoie un récapitulatif quotidien des ventes à l'heure configurée dans
    Config (une seule fois par jour, déclenché à la première visite de l'app
    après l'heure fixée -- il n'y a pas de tâche planifiée côté serveur)."""
    if not EMAIL_ACTIVE:
        return
    try:
        heure_cible = int(config.get("heure_bilan", 20) or 20)
    except (TypeError, ValueError):
        heure_cible = 20
    maintenant = datetime.now(timezone.utc)
    aujourdhui = maintenant.date().isoformat()
    if maintenant.hour < heure_cible:
        return
    if config.get("dernier_bilan_date") == aujourdhui:
        return  # déjà envoyé aujourd'hui

    try:
        debut_jour = maintenant.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        sb_bg = get_admin_client()
        reponse = sb_bg.table("commandes").select("*").gte("date", debut_jour).execute()
    except Exception:
        return

    commandes_jour = reponse.data or []
    total_ventes = sum(float(c.get("price") or 0) for c in commandes_jour)
    nb_commandes = len(commandes_jour)
    corps = (
        f"Bilan des ventes du {aujourdhui} :\n\n"
        f"Nombre de commandes : {nb_commandes}\n"
        f"Chiffre d'affaires total : {int(total_ventes)} FCFA\n"
    )
    destinataire = config.get("email_admin") or st.secrets.get("GMAIL_ADDRESS", "")
    if envoyer_email_brut(destinataire, f"📊 Bilan des ventes — {aujourdhui}", corps):
        try:
            get_admin_client().table("config").upsert(
                {"cle": "dernier_bilan_date", "valeur": aujourdhui}
            ).execute()
        except Exception:
            pass


# ====================== 7. INTERFACE PUBLIQUE ======================
config = charger_config(st.session_state.refresh_token)
df_catalogue = charger_catalogue(st.session_state.refresh_token)
avis_moyennes = charger_avis_moyennes(st.session_state.refresh_token)
avis_par_article = indexer_avis_par_article(charger_tous_avis_approuves(st.session_state.refresh_token))

# 🔔 Vérifications silencieuses (n'affichent rien, ne bloquent jamais la
# page) -- envoient au plus un email par jour chacune, dès que quelqu'un
# charge l'app après les conditions requises.
try:
    verifier_alerte_stock_bas(df_catalogue, config)
    verifier_bilan_quotidien(config)
except Exception:
    pass

NOM_BOUTIQUE = html_lib.escape(config.get("nom_boutique", "Destiny Luxury Collection"))
LOGO_URL = config.get("logo", "")
LOGO_SUR = LOGO_URL if re.match(r"^https?://", str(LOGO_URL).strip(), re.IGNORECASE) else ""
WHATSAPP = re.sub(r"\D", "", str(config.get("whatsapp") or ""))

# 🔒 FIX : l'admin n'apparaît plus comme un onglet visible par tous les
# visiteurs. Seule une personne connaissant l'URL secrète
# "https://tonapp.streamlit.app/?admin=1" voit l'interface de connexion
# admin -- les clients normaux ne voient que la boutique.
mode_admin = st.query_params.get("admin") == "1"

# 🔀 Si un visiteur arrivé sur l'URL secrète ?admin=1 a choisi "client" sur
# l'écran d'accueil ci-dessous, on le renvoie directement vers la boutique
# (sans avoir à retirer le paramètre d'URL).
if mode_admin and not st.session_state.admin_connecte and st.session_state.acces_choisi == "client":
    mode_admin = False

if not mode_admin:
    afficher_hero(LOGO_SUR, NOM_BOUTIQUE, "Élégance • Exclusivité • Luxe")

    with st.container():
        if df_catalogue.empty:
            st.info("Le catalogue est vide pour le moment.")
        else:
            recherche = st.text_input("🔍 Rechercher un article")
            categories = ["Toutes"] + sorted(df_catalogue["categorie"].dropna().unique().tolist())
            categorie_choisie = st.selectbox("Catégorie", categories)

            df_affiche = df_catalogue.copy()
            if recherche:
                df_affiche = df_affiche[df_affiche["nom"].str.contains(recherche, case=False, na=False)]
            if categorie_choisie != "Toutes":
                df_affiche = df_affiche[df_affiche["categorie"] == categorie_choisie]

            colonnes_grille = st.columns(3)
            for idx, (_, row) in enumerate(df_affiche.iterrows()):
                with colonnes_grille[idx % 3]:
                    identifiant_produit = normaliser(row.get("id") or row.get("nom"))
                    nom_affiche = html_lib.escape(str(row["nom"]).strip())

                    # ---- Galerie multi-images ----
                    image_principale = str(row.get("image") or "")
                    images_supp = [
                        u.strip() for u in str(row.get("images_supplementaires") or "").split(",") if u.strip()
                    ]
                    toutes_images = [u for u in [image_principale] + images_supp
                                      if re.match(r"^https?://", u.strip(), re.IGNORECASE)]

                    if toutes_images:
                        afficher_galerie_swipe(toutes_images, hauteur=280, cle=f"prod_{idx}")

                    st.markdown(
                        f'<div class="destiny-nom-produit">{nom_affiche}</div>',
                        unsafe_allow_html=True
                    )

                    info_avis = (
                        avis_moyennes.get(identifiant_produit)
                        or avis_moyennes.get(normaliser(row["nom"]))
                    )
                    if info_avis:
                        st.caption(f"⭐ {info_avis['moyenne']} ({info_avis['count']} avis)")

                    stock = int(row.get("stock") or 0)
                    en_rupture = stock <= 0
                    prix = row.get("prix") or 0
                    prix_promo = row.get("prix_promo") or 0
                    en_promo = prix_promo and 0 < prix_promo < prix

                    if en_promo:
                        reduction_pct = round((1 - prix_promo / prix) * 100) if prix else 0
                        st.markdown(
                            f'<div class="destiny-promo-ligne">'
                            f'<span class="destiny-promo-ancien-prix">{int(prix)} FCFA</span>'
                            f'<span class="destiny-promo-badge">🏷️ {int(prix_promo)} FCFA · -{reduction_pct}%</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(f'<span class="destiny-prix-normal">{int(prix)} FCFA</span>', unsafe_allow_html=True)

                    if en_rupture:
                        st.error("Rupture de stock")
                        with st.expander("🔔 Me prévenir quand disponible"):
                            contact = st.text_input("Email ou téléphone", key=f"alerte_{idx}")
                            if st.button("M'alerter", key=f"btn_alerte_{idx}"):
                                if contact.strip():
                                    sb.table("alertesstock").insert({
                                        "date_inscription": datetime.now(timezone.utc).isoformat(),
                                        "article": str(row["nom"]),
                                        "contact_type": "email" if "@" in contact else "telephone",
                                        "contact": contact.strip(),
                                        "statut": "en_attente"
                                    }).execute()
                                    st.success("Inscription enregistrée !")
                    else:
                        options_taille = [t.strip() for t in str(row.get("tailles") or "").split(",") if t.strip()]
                        options_couleur = [c.strip() for c in str(row.get("couleurs") or "").split(",") if c.strip()]
                        taille_choisie = st.selectbox("Taille", options_taille, key=f"taille_{idx}") if options_taille else ""
                        couleur_choisie = st.selectbox("Couleur", options_couleur, key=f"couleur_{idx}") if options_couleur else ""

                        if st.button("🛒 Ajouter au panier", key=f"add_{idx}"):
                            existant = next(
                                (a for a in st.session_state.cart
                                 if a["nom"] == row["nom"] and a.get("taille") == taille_choisie
                                 and a.get("couleur") == couleur_choisie),
                                None
                            )
                            if existant:
                                existant["quantite"] += 1
                            else:
                                st.session_state.cart.append({
                                    "produit_id": str(row.get("id") or ""),
                                    "nom": row["nom"],
                                    "prix": float(prix_promo if en_promo else prix),
                                    "taille": taille_choisie,
                                    "couleur": couleur_choisie,
                                    "quantite": 1
                                })
                            st.session_state.message_toast = f"{nom_affiche} ajouté au panier !"
                            st.session_state.icone_toast = "🛍️"
                            st.session_state.jouer_son = True
                            st.rerun()

                    with st.expander("💬 Avis clients"):
                        for avis_item in avis_par_article.get(identifiant_produit, [])[:20]:
                            st.markdown(f"**{html_lib.escape(str(avis_item['client_nom']))}** — {'⭐' * int(avis_item['note'])}")
                            if avis_item.get("commentaire"):
                                st.caption(html_lib.escape(str(avis_item["commentaire"])))
                        with st.form(f"form_avis_{idx}", clear_on_submit=True):
                            nom_avis = st.text_input("Votre nom", key=f"nom_avis_{idx}")
                            note_avis = st.select_slider(
                                "Note", options=[1, 2, 3, 4, 5], value=5, key=f"note_avis_{idx}"
                            )
                            commentaire_avis = st.text_area("Commentaire (facultatif)", max_chars=500, key=f"comm_avis_{idx}")
                            if st.form_submit_button("Envoyer mon avis"):
                                if not nom_avis.strip():
                                    st.warning("Merci de renseigner votre nom.")
                                else:
                                    resultat = sb.rpc("laisser_avis", {
                                        "p_article_id": identifiant_produit,
                                        "p_article_nom": str(row["nom"]),
                                        "p_client_nom": nom_avis.strip(),
                                        "p_note": int(note_avis),
                                        "p_commentaire": commentaire_avis.strip()
                                    }).execute()
                                    donnee = resultat.data or {}
                                    if donnee.get("status") == "success":
                                        st.success(donnee.get("message"))
                                    else:
                                        st.error(donnee.get("message", "Erreur lors de l'envoi"))

    with st.sidebar:
        st.subheader("🛒 Panier")
        if not st.session_state.cart:
            st.caption("Panier vide")
        else:
            total_panier = 0
            for i, item in enumerate(st.session_state.cart):
                sous_total = item["prix"] * item["quantite"]
                total_panier += sous_total
                variante = " / ".join(v for v in [item.get("taille"), item.get("couleur")] if v)
                label = f"{item['nom']} ({variante})" if variante else item["nom"]
                st.write(f"{label} × {item['quantite']} = {int(sous_total)} FCFA")
                if st.button("🗑️", key=f"suppr_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()

            st.markdown(f"### Total : {int(total_panier)} FCFA")

            # Champs HORS formulaire (contrairement à avant) pour permettre la
            # sauvegarde automatique du panier abandonné pendant la saisie,
            # avant même que le client ait cliqué sur "Confirmer".
            client_nom = st.text_input("Votre nom", key="checkout_nom")
            client_tel = st.text_input("Votre téléphone", key="checkout_tel")

            if client_tel.strip():
                sauvegarder_panier_abandonne(client_tel, client_nom, st.session_state.cart)

            if st.button("✅ Confirmer la commande"):
                if not client_nom.strip() or not client_tel.strip():
                    st.warning("Merci de renseigner votre nom et votre téléphone.")
                else:
                    articles_payload = [
                        {"produit_id": a["produit_id"], "nom": a["nom"], "quantite": a["quantite"]}
                        for a in st.session_state.cart
                    ]
                    resultat = sb.rpc("passer_commande", {
                        "p_client_nom": client_nom.strip(),
                        "p_tel": client_tel.strip(),
                        "p_articles": articles_payload
                    }).execute()
                    donnee = resultat.data or {}
                    envoyer_notification_commande(
                        donnee.get("id_commande"), client_nom.strip(), client_tel.strip(),
                        donnee.get("articles", []), donnee.get("total", 0), donnee.get("introuvables", [])
                    )
                    marquer_panier_converti(client_tel.strip())

                    # 🆕 Bouton WhatsApp -- absent depuis la migration. Le
                    # client peut prévenir directement la boutique sur
                    # WhatsApp en plus de la commande déjà enregistrée en
                    # base, avec le récapitulatif pré-rempli.
                    if WHATSAPP:
                        recap = "\n".join(
                            f"- {a['nom']} x{a['quantite']}" for a in donnee.get("articles", [])
                        )
                        message_whatsapp = (
                            f"Bonjour, je viens de passer la commande {donnee.get('id_commande')} :\n"
                            f"{recap}\nTotal : {int(donnee.get('total', 0))} FCFA"
                        )
                        lien_whatsapp = f"https://wa.me/{WHATSAPP}?text={requests.utils.quote(message_whatsapp)}"
                        st.link_button("💬 Confirmer aussi sur WhatsApp", lien_whatsapp)

                    st.session_state.cart = []
                    st.session_state.dernier_panier_signature = None
                    forcer_rafraichissement()
                    st.success(f"Commande {donnee.get('id_commande')} enregistrée ! Total : {int(donnee.get('total', 0))} FCFA")
                    if donnee.get("ruptures"):
                        st.warning(f"Stock épuisé pour : {', '.join(donnee['ruptures'])}")

        # 🆕 Suivi de commande -- un client peut retrouver le statut de sa
        # commande avec son numéro de téléphone, sans avoir besoin de compte.
        st.divider()
        with st.expander("📦 Suivre ma commande"):
            tel_suivi = st.text_input("Numéro utilisé pour la commande", key="tel_suivi")
            if st.button("Rechercher", key="btn_suivi"):
                if tel_suivi.strip():
                    resultat_suivi = (
                        sb.table("commandes")
                        .select("id, date, statut, price, articles")
                        .eq("tel", tel_suivi.strip())
                        .order("date", desc=True)
                        .limit(5)
                        .execute()
                    )
                    if not resultat_suivi.data:
                        st.info("Aucune commande trouvée avec ce numéro.")
                    for cmd_suivi in resultat_suivi.data:
                        st.write(
                            f"**{cmd_suivi.get('id')}** — {cmd_suivi.get('statut')} "
                            f"— {int(cmd_suivi.get('price') or 0)} FCFA"
                        )

        if WHATSAPP:
            st.divider()
            lien_contact = f"https://wa.me/{WHATSAPP}"
            st.link_button("💬 Nous contacter sur WhatsApp", lien_contact)


# ====================== 8. ADMIN ======================
else:
    if not st.session_state.admin_connecte:
        if st.session_state.acces_choisi != "admin":
            # ---- Écran d'accueil : logo + effet lumineux doré + message de bienvenue ----
            afficher_hero(LOGO_SUR, f"Bienvenue chez {NOM_BOUTIQUE}", "Comment souhaitez-vous continuer ?")
            col_client, col_admin = st.columns(2)
            with col_client:
                if st.button("🛍️ Je suis client / visiteur", use_container_width=True):
                    st.session_state.acces_choisi = "client"
                    st.rerun()
            with col_admin:
                if st.button("🔐 Je suis administrateur", use_container_width=True):
                    st.session_state.acces_choisi = "admin"
                    st.rerun()
        else:
            # ---- Écran de connexion admin (mot de passe) ----
            afficher_hero(LOGO_SUR, f"Bienvenue chez {NOM_BOUTIQUE}", "Connexion administrateur")
            st.subheader("Connexion admin")
            mdp_admin = st.text_input("Mot de passe", type="password")
            col_connexion, col_retour = st.columns(2)
            with col_connexion:
                if st.button("Se connecter"):
                    try:
                        if admin_login(mdp_admin):
                            st.rerun()
                        else:
                            st.error("Mot de passe incorrect.")
                    except Exception as e:
                        st.error(f"Échec de connexion : {e}")
            with col_retour:
                if st.button("↩️ Retour"):
                    st.session_state.acces_choisi = None
                    st.rerun()
    else:
        sb_admin = get_admin_client()
        st.success("Connecté en tant qu'admin")
        if st.button("Se déconnecter"):
            admin_logout()
            st.session_state.acces_choisi = None
            st.rerun()

        (tab_catalogue, tab_promos, tab_commandes, tab_avis, tab_stats,
         tab_config, tab_alertes, tab_paniers) = st.tabs(
            ["📦 Catalogue", "🏷️ Promotions", "🧾 Commandes", "💬 Avis", "📊 Statistiques",
             "⚙️ Config", "🔔 Alertes stock", "🛒 Paniers abandonnés"]
        )

        with tab_catalogue:
            st.write("### Articles existants")
            for idx, (_, row) in enumerate(df_catalogue.iterrows()):
                # 🔧 FIX : certaines lignes ont un "id" vide ou dupliqué
                # (données historiques mal migrées) -- sans repère unique,
                # Streamlit plantait en créant deux widgets avec la même
                # clé. On force l'unicité avec la position dans la liste,
                # peu importe l'état des données.
                cle_unique = f"{idx}_{row.get('id') or 'sansid'}"
                id_manquant = not str(row.get("id") or "").strip()
                titre_article = f"{row['nom']} — stock {int(row.get('stock') or 0)}"
                if id_manquant:
                    titre_article += " ⚠️ id manquant"

                # 🆕 Miniature pour identifier l'article visuellement avant
                # de modifier/supprimer -- fini les listes uniquement en texte.
                colonne_miniature, colonne_expander = st.columns([1, 6])
                with colonne_miniature:
                    image_admin = str(row.get("image") or "")
                    if re.match(r"^https?://", image_admin.strip(), re.IGNORECASE):
                        st.image(image_admin, width=70)
                    else:
                        st.caption("🚫 pas de photo")
                with colonne_expander:
                    expander_article = st.expander(titre_article)
                with expander_article:
                    if id_manquant:
                        st.warning(
                            "Cet article n'a pas d'identifiant (id) en base -- modification et "
                            "suppression désactivées ici pour éviter de toucher la mauvaise ligne. "
                            "Corrige son id directement dans le Table Editor Supabase."
                        )
                    with st.form(f"edit_{cle_unique}"):
                        nouveau_nom = st.text_input("Nom", value=row["nom"])
                        nouveau_prix = st.number_input("Prix", value=float(row.get("prix") or 0))
                        nouveau_stock = st.number_input("Stock", value=int(row.get("stock") or 0), step=1)
                        nouvelle_categorie = st.text_input("Catégorie", value=row.get("categorie") or "")
                        nouvelles_tailles = st.text_input("Tailles (séparées par virgule)", value=row.get("tailles") or "")
                        nouvelles_couleurs = st.text_input("Couleurs (séparées par virgule)", value=row.get("couleurs") or "")

                        nouvelle_image_fichier = st.file_uploader(
                            "Remplacer l'image principale", type=["jpg", "jpeg", "png", "webp"], key=f"img_{cle_unique}"
                        )
                        nouvelles_images_supp = st.file_uploader(
                            "Ajouter des images supplémentaires", type=["jpg", "jpeg", "png", "webp"],
                            accept_multiple_files=True, key=f"imgs_{cle_unique}"
                        )

                        if st.form_submit_button("Enregistrer", disabled=id_manquant):
                            maj = {
                                "nom": nouveau_nom, "prix": int(nouveau_prix), "stock": nouveau_stock,
                                "categorie": nouvelle_categorie, "tailles": nouvelles_tailles,
                                "couleurs": nouvelles_couleurs
                            }
                            if nouvelle_image_fichier is not None:
                                url, erreur_upload = televerser_image_imgbb(nouvelle_image_fichier)
                                if url:
                                    maj["image"] = url
                                else:
                                    st.warning(f"Échec de l'envoi de l'image principale : {erreur_upload or 'raison inconnue'} — le reste a été enregistré.")
                            if nouvelles_images_supp:
                                urls_existantes = [u.strip() for u in str(row.get("images_supplementaires") or "").split(",") if u.strip()]
                                for f in nouvelles_images_supp:
                                    url, erreur_upload = televerser_image_imgbb(f)
                                    if url:
                                        urls_existantes.append(url)
                                    elif erreur_upload:
                                        st.warning(f"Image supplémentaire ignorée : {erreur_upload}")
                                maj["images_supplementaires"] = ", ".join(urls_existantes)
                            sb_admin.table("catalogue").update(maj).eq("id", row["id"]).execute()
                            ancien_stock = int(row.get("stock") or 0)
                            if ancien_stock <= 0 and nouveau_stock > 0:
                                notifier_retour_stock(nouveau_nom)
                            forcer_rafraichissement()
                            st.success("Article mis à jour")
                            st.rerun()
                    if not id_manquant and st.button("🗑️ Supprimer", key=f"del_{cle_unique}"):
                        sb_admin.table("catalogue").delete().eq("id", row["id"]).execute()
                        forcer_rafraichissement()
                        st.rerun()

            st.write("### Ajouter un article")
            with st.form("ajout_article", clear_on_submit=True):
                nom = st.text_input("Nom de l'article")
                prix = st.number_input("Prix", min_value=0.0)
                stock = st.number_input("Stock", min_value=0, step=1)
                categorie = st.text_input("Catégorie")
                tailles = st.text_input("Tailles (séparées par virgule)")
                couleurs = st.text_input("Couleurs (séparées par virgule)")
                image_fichier = st.file_uploader("Image principale", type=["jpg", "jpeg", "png", "webp"])
                images_supp_fichiers = st.file_uploader(
                    "Images supplémentaires (facultatif)", type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True
                )
                if st.form_submit_button("Ajouter"):
                    if not nom.strip():
                        st.warning("Le nom de l'article est requis.")
                    else:
                        url_principale = ""
                        if image_fichier:
                            url_principale, erreur_upload = televerser_image_imgbb(image_fichier)
                            if erreur_upload:
                                st.warning(f"Image principale non enregistrée : {erreur_upload}")
                        urls_supp = []
                        for f in (images_supp_fichiers or []):
                            url, erreur_upload = televerser_image_imgbb(f)
                            if url:
                                urls_supp.append(url)
                            elif erreur_upload:
                                st.warning(f"Image supplémentaire ignorée : {erreur_upload}")
                        sb_admin.table("catalogue").insert({
                            "id": str(uuid.uuid4()),
                            "nom": nom, "prix": int(prix), "stock": stock,
                            "image": url_principale, "images_supplementaires": ", ".join(urls_supp),
                            "categorie": categorie, "tailles": tailles, "couleurs": couleurs,
                            "date_ajout": datetime.now(timezone.utc).isoformat()
                        }).execute()
                        forcer_rafraichissement()
                        st.success("Article ajouté")
                        st.rerun()

        with tab_promos:
            st.write("### 🏷️ Promotions actives")
            df_en_promo = df_catalogue[df_catalogue["prix_promo"].fillna(0) > 0].copy()
            if df_en_promo.empty:
                st.caption("Aucune promotion active actuellement.")
            else:
                colonnes_promo = st.columns(3)
                for i, (_, ligne) in enumerate(df_en_promo.iterrows()):
                    with colonnes_promo[i % 3]:
                        image_promo = str(ligne.get("image") or "")
                        if re.match(r"^https?://", image_promo.strip(), re.IGNORECASE):
                            st.image(image_promo, use_container_width=True)
                        else:
                            st.caption("🚫 pas de photo")
                        prix_original_promo = float(ligne.get("prix") or 0)
                        prix_promo_valeur = float(ligne.get("prix_promo") or 0)
                        reduction_pct = (
                            round((1 - prix_promo_valeur / prix_original_promo) * 100)
                            if prix_original_promo else 0
                        )
                        st.markdown(f"**{html_lib.escape(str(ligne['nom']))}**")
                        st.markdown(
                            f'<div class="destiny-promo-ligne">'
                            f'<span class="destiny-promo-ancien-prix">{int(prix_original_promo)} FCFA</span>'
                            f'<span class="destiny-promo-badge">🏷️ {int(prix_promo_valeur)} FCFA · -{reduction_pct}%</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        if st.button("Retirer la promotion", key=f"retrait_promo_{ligne['id']}"):
                            sb_admin.table("catalogue").update({"prix_promo": None}).eq("id", ligne["id"]).execute()
                            forcer_rafraichissement()
                            st.rerun()

            st.divider()
            st.write("### Appliquer une promotion en masse")
            if df_catalogue.empty:
                st.caption("Aucun article dans le catalogue.")
            else:
                with st.form("promo_masse"):
                    articles_selectionnes = st.multiselect("Articles concernés", df_catalogue["nom"].tolist())
                    type_reduction = st.radio("Type de réduction", ["Pourcentage", "Montant fixe (FCFA)"])
                    valeur_reduction = st.number_input("Valeur de la réduction", min_value=0.0)
                    if st.form_submit_button("Appliquer la promotion"):
                        if not articles_selectionnes:
                            st.warning("Sélectionne au moins un article.")
                        else:
                            for nom_article in articles_selectionnes:
                                ligne = df_catalogue[df_catalogue["nom"] == nom_article].iloc[0]
                                prix_original = float(ligne["prix"])
                                if type_reduction == "Pourcentage":
                                    nouveau_prix_promo = round(prix_original * (1 - valeur_reduction / 100))
                                else:
                                    nouveau_prix_promo = max(0, prix_original - valeur_reduction)
                                sb_admin.table("catalogue").update(
                                    {"prix_promo": nouveau_prix_promo}
                                ).eq("id", ligne["id"]).execute()
                            forcer_rafraichissement()
                            st.success(f"Promotion appliquée à {len(articles_selectionnes)} article(s)")
                            st.rerun()

        with tab_commandes:
            reponse = sb_admin.table("commandes").select("*").order("date", desc=True).limit(100).execute()
            statuts_possibles = ["En cours", "Confirmée", "Livrée", "Annulée"]
            couleurs_statut = {
                "En cours": "#8a7350", "Confirmée": "#c9a35c",
                "Livrée": "#4caf7d", "Annulée": "#e35d5d"
            }
            commandes_data = reponse.data or []
            if not commandes_data:
                st.caption("Aucune commande pour le moment.")
            for idx, cmd in enumerate(commandes_data):
                cle_unique = f"{idx}_{cmd.get('id') or 'sansid'}"
                statut_actuel = cmd.get("statut") or "En cours"
                couleur_statut = couleurs_statut.get(statut_actuel, "#8a7350")
                reference = str(cmd.get("id") or "—")
                reference_courte = reference[:8] if reference != "—" else "—"
                try:
                    date_affichee = pd.to_datetime(cmd.get("date")).strftime("%d/%m/%Y %H:%M")
                except Exception:
                    date_affichee = str(cmd.get("date") or "—")
                total_cmd = cmd.get("price") or 0
                articles_cmd = cmd.get("articles") or []

                with st.expander(f"🧾 {reference_courte} — {cmd.get('client_nom') or 'Client'} — {int(total_cmd)} FCFA — {statut_actuel}"):
                    st.markdown(
                        f'''<div style="display:flex; justify-content:space-between; align-items:center;
                                      flex-wrap:wrap; gap:14px; padding:12px 16px; margin-bottom:14px;
                                      background:linear-gradient(135deg, rgba(201,163,92,0.12), rgba(201,163,92,0.03));
                                      border:1px solid rgba(201,163,92,0.3); border-radius:10px;">
                            <div>
                                <div style="color:#9a948a; font-size:0.72rem; letter-spacing:1px; text-transform:uppercase;">Référence</div>
                                <div style="color:#eae4d8; font-weight:600;">{reference_courte}</div>
                            </div>
                            <div>
                                <div style="color:#9a948a; font-size:0.72rem; letter-spacing:1px; text-transform:uppercase;">Client</div>
                                <div style="color:#eae4d8; font-weight:600;">{html_lib.escape(str(cmd.get('client_nom') or '—'))}</div>
                            </div>
                            <div>
                                <div style="color:#9a948a; font-size:0.72rem; letter-spacing:1px; text-transform:uppercase;">Téléphone</div>
                                <div style="color:#eae4d8; font-weight:600;">{html_lib.escape(str(cmd.get('tel') or '—'))}</div>
                            </div>
                            <div>
                                <div style="color:#9a948a; font-size:0.72rem; letter-spacing:1px; text-transform:uppercase;">Date</div>
                                <div style="color:#eae4d8; font-weight:600;">{date_affichee}</div>
                            </div>
                            <div>
                                <div style="color:#9a948a; font-size:0.72rem; letter-spacing:1px; text-transform:uppercase;">Total</div>
                                <div style="color:#c9a35c; font-weight:700; font-size:1.15rem;">{int(total_cmd)} FCFA</div>
                            </div>
                            <div style="padding:6px 14px; border-radius:20px; background:{couleur_statut}; color:#16151a; font-weight:700; font-size:0.8rem; white-space:nowrap;">
                                {statut_actuel}
                            </div>
                        </div>''',
                        unsafe_allow_html=True
                    )

                    if articles_cmd:
                        for art in articles_cmd:
                            image_art = str(art.get("image") or "")
                            col_img, col_info = st.columns([1, 5])
                            with col_img:
                                if re.match(r"^https?://", image_art.strip(), re.IGNORECASE):
                                    st.image(image_art, width=64)
                                else:
                                    st.caption("🚫")
                            with col_info:
                                variante = " / ".join(
                                    v for v in [art.get("taille"), art.get("couleur")]
                                    if v and str(v).lower() != "nan"
                                )
                                libelle_variante = f" ({variante})" if variante else ""
                                prix_art = float(art.get("prix") or 0)
                                qte_art = float(art.get("quantite") or 0)
                                st.markdown(
                                    f"**{html_lib.escape(str(art.get('nom', '?')))}**{libelle_variante}  \n"
                                    f"{int(qte_art)} × {int(prix_art)} FCFA = **{int(prix_art * qte_art)} FCFA**"
                                )
                    else:
                        st.caption("Aucun article enregistré pour cette commande.")

                    st.divider()
                    index_defaut = statuts_possibles.index(statut_actuel) if statut_actuel in statuts_possibles else 0
                    nouveau_statut = st.selectbox(
                        "Statut", statuts_possibles, index=index_defaut, key=f"statut_{cle_unique}"
                    )
                    if st.button("Mettre à jour", key=f"maj_{cle_unique}"):
                        sb_admin.table("commandes").update({"statut": nouveau_statut}).eq("id", cmd["id"]).execute()
                        st.rerun()

        with tab_avis:
            reponse = sb_admin.table("avis").select("*").eq("statut", "en_attente").execute()
            if not reponse.data:
                st.caption("Aucun avis en attente")
            for idx, avis_item in enumerate(reponse.data):
                cle_unique = f"{idx}_{avis_item.get('id') or 'sansid'}"
                with st.expander(f"{avis_item['client_nom']} — {avis_item['article_nom']} — {'⭐' * int(avis_item['note'])}"):
                    st.write(avis_item.get("commentaire") or "(pas de commentaire)")
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Approuver", key=f"appr_{cle_unique}"):
                        sb_admin.table("avis").update({"statut": "approuve"}).eq("id", avis_item["id"]).execute()
                        forcer_rafraichissement()
                        st.rerun()
                    if col2.button("🗑️ Supprimer", key=f"suppr_avis_{cle_unique}"):
                        sb_admin.table("avis").delete().eq("id", avis_item["id"]).execute()
                        forcer_rafraichissement()
                        st.rerun()

        with tab_stats:
            st.write("### 📊 Statistiques avancées")
            reponse_stats = sb_admin.table("commandes").select("*").order("date", desc=False).execute()
            commandes_stats = reponse_stats.data or []

            THEME_GRAPHIQUE = dict(
                template="plotly_dark", paper_bgcolor="#16151a", plot_bgcolor="#16151a",
                font=dict(family="Inter, sans-serif", color="#eae4d8"),
                margin=dict(l=10, r=10, t=50, b=10)
            )

            if not commandes_stats:
                st.caption("Pas encore assez de données pour générer des statistiques.")
            else:
                df_cmd = pd.DataFrame(commandes_stats)
                df_cmd["date_parsed"] = pd.to_datetime(df_cmd["date"], errors="coerce", utc=True)
                df_cmd["price"] = pd.to_numeric(df_cmd["price"], errors="coerce").fillna(0)
                df_cmd["jour"] = df_cmd["date_parsed"].dt.date

                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Chiffre d'affaires total", f"{int(df_cmd['price'].sum())} FCFA")
                col_m2.metric("Nombre de commandes", len(df_cmd))
                col_m3.metric(
                    "Panier moyen",
                    f"{int(df_cmd['price'].mean()) if len(df_cmd) else 0} FCFA"
                )

                # --- Chiffre d'affaires quotidien ---
                ca_par_jour = df_cmd.groupby("jour")["price"].sum().reset_index()
                fig_ca = go.Figure()
                fig_ca.add_trace(go.Scatter(
                    x=ca_par_jour["jour"], y=ca_par_jour["price"],
                    mode="lines+markers", line=dict(color="#c9a35c", width=3, shape="spline"),
                    marker=dict(size=6, color="#eae4d8"),
                    fill="tozeroy", fillcolor="rgba(201,163,92,0.15)"
                ))
                fig_ca.update_layout(title="Chiffre d'affaires quotidien (FCFA)", height=320, **THEME_GRAPHIQUE)
                st.plotly_chart(fig_ca, use_container_width=True)

                col_a, col_b = st.columns(2)
                with col_a:
                    par_statut = df_cmd["statut"].fillna("En cours").value_counts().reset_index()
                    par_statut.columns = ["statut", "nombre"]
                    fig_statut = px.pie(
                        par_statut, names="statut", values="nombre", hole=0.55,
                        color_discrete_sequence=["#c9a35c", "#8a7350", "#eae4d8", "#5a4a2f"]
                    )
                    fig_statut.update_layout(title="Commandes par statut", height=320, **THEME_GRAPHIQUE)
                    st.plotly_chart(fig_statut, use_container_width=True)

                with col_b:
                    compteur_articles = {}
                    for liste in df_cmd["articles"].dropna():
                        if isinstance(liste, list):
                            for art in liste:
                                nom_art = art.get("nom", "?")
                                qte = art.get("quantite", 0) or 0
                                compteur_articles[nom_art] = compteur_articles.get(nom_art, 0) + qte
                    if compteur_articles:
                        df_top = pd.DataFrame(
                            sorted(compteur_articles.items(), key=lambda x: x[1], reverse=True)[:10],
                            columns=["article", "quantite"]
                        ).sort_values("quantite")
                        fig_top = px.bar(df_top, x="quantite", y="article", orientation="h")
                        fig_top.update_traces(marker_color="#c9a35c")
                        fig_top.update_layout(title="Top 10 des articles les plus vendus", height=320, **THEME_GRAPHIQUE)
                        st.plotly_chart(fig_top, use_container_width=True)
                    else:
                        st.caption("Pas encore de détail d'articles vendus.")

                if not df_catalogue.empty:
                    try:
                        seuil_actuel = int(config.get("seuil_stock_bas", 3) or 3)
                    except (TypeError, ValueError):
                        seuil_actuel = 3
                    df_stock = df_catalogue[["nom", "stock"]].sort_values("stock")
                    couleurs_stock = [
                        "#e35d5d" if s <= seuil_actuel else "#c9a35c" for s in df_stock["stock"]
                    ]
                    fig_stock = go.Figure(go.Bar(
                        x=df_stock["stock"], y=df_stock["nom"], orientation="h",
                        marker_color=couleurs_stock
                    ))
                    fig_stock.update_layout(
                        title=f"Niveau de stock par article (rouge = seuil bas ≤ {seuil_actuel})",
                        height=max(320, 26 * len(df_stock)), **THEME_GRAPHIQUE
                    )
                    st.plotly_chart(fig_stock, use_container_width=True)

        with tab_config:
            with st.form("form_config"):
                nom_boutique_input = st.text_input("Nom de la boutique", value=config.get("nom_boutique", ""))

                st.write("**Logo de la boutique**")
                if config.get("logo") and re.match(r"^https?://", str(config.get("logo")).strip(), re.IGNORECASE):
                    st.image(config.get("logo"), width=150, caption="Logo actuel")
                else:
                    st.caption("Aucun logo pour le moment.")
                nouveau_logo_fichier = st.file_uploader(
                    "Choisir un logo (remplace l'actuel)", type=["jpg", "jpeg", "png", "webp"], key="upload_logo"
                )

                whatsapp_input = st.text_input("Numéro WhatsApp", value=config.get("whatsapp", ""))
                email_admin_input = st.text_input("Email de notification", value=config.get("email_admin", ""))

                st.write("**Alertes automatiques**")
                try:
                    seuil_defaut = int(config.get("seuil_stock_bas", 3) or 3)
                except (TypeError, ValueError):
                    seuil_defaut = 3
                try:
                    heure_defaut = int(config.get("heure_bilan", 20) or 20)
                except (TypeError, ValueError):
                    heure_defaut = 20
                seuil_stock_input = st.number_input(
                    "Seuil de stock bas (déclenche l'alerte email)",
                    min_value=0, step=1, value=seuil_defaut
                )
                heure_bilan_input = st.slider(
                    "Heure d'envoi du bilan quotidien des ventes (UTC, 0-23h)",
                    min_value=0, max_value=23, value=heure_defaut
                )

                if st.form_submit_button("Enregistrer"):
                    logo_valeur = config.get("logo", "")
                    if nouveau_logo_fichier is not None:
                        url_logo, erreur_upload = televerser_image_imgbb(nouveau_logo_fichier)
                        if url_logo:
                            logo_valeur = url_logo
                        else:
                            st.error(f"Échec de l'envoi du logo : {erreur_upload or 'raison inconnue'} — l'ancien logo a été conservé.")
                    for cle, valeur in [
                        ("nom_boutique", nom_boutique_input), ("logo", logo_valeur),
                        ("whatsapp", whatsapp_input), ("email_admin", email_admin_input),
                        ("seuil_stock_bas", str(int(seuil_stock_input))),
                        ("heure_bilan", str(int(heure_bilan_input)))
                    ]:
                        sb_admin.table("config").upsert({"cle": cle, "valeur": valeur}).execute()
                    forcer_rafraichissement()
                    st.success("Configuration mise à jour")
                    st.rerun()

            st.divider()
            st.write("### 🔐 Changer le mot de passe admin")
            with st.form("form_changer_mdp", clear_on_submit=True):
                mdp_actuel = st.text_input("Mot de passe actuel", type="password")
                mdp_nouveau = st.text_input("Nouveau mot de passe", type="password")
                mdp_nouveau_confirmation = st.text_input("Confirmer le nouveau mot de passe", type="password")
                if st.form_submit_button("Changer le mot de passe"):
                    hash_attendu = config.get("mot_de_passe", "")
                    if not hash_attendu or hash_mot_de_passe(mdp_actuel) != hash_attendu:
                        st.error("Mot de passe actuel incorrect.")
                    elif not mdp_nouveau.strip():
                        st.warning("Le nouveau mot de passe ne peut pas être vide.")
                    elif len(mdp_nouveau) < 6:
                        st.warning("Le nouveau mot de passe doit contenir au moins 6 caractères.")
                    elif mdp_nouveau != mdp_nouveau_confirmation:
                        st.warning("La confirmation ne correspond pas au nouveau mot de passe.")
                    else:
                        sb_admin.table("config").upsert(
                            {"cle": "mot_de_passe", "valeur": hash_mot_de_passe(mdp_nouveau)}
                        ).execute()
                        forcer_rafraichissement()
                        st.success("Mot de passe mis à jour avec succès — utilise-le dès ta prochaine connexion.")

        with tab_alertes:
            reponse = sb_admin.table("alertesstock").select("*").eq("statut", "en_attente").execute()
            alertes_en_attente = reponse.data or []
            if not alertes_en_attente:
                st.caption("Aucune alerte en attente")
            else:
                st.caption(
                    "Les inscrits par email sont notifiés automatiquement dès que le stock repasse "
                    "au-dessus de 0 (via l'onglet Catalogue). Les inscrits par téléphone sont à relancer "
                    "manuellement sur WhatsApp ci-dessous."
                )
                articles_concernes = sorted({a["article"] for a in alertes_en_attente})
                for article_nom in articles_concernes:
                    alertes_article = [a for a in alertes_en_attente if a["article"] == article_nom]
                    with st.expander(f"{article_nom} — {len(alertes_article)} inscrit(s)"):
                        for alerte in alertes_article:
                            if alerte.get("contact_type") == "telephone":
                                tel_alerte = re.sub(r"\D", "", str(alerte.get("contact") or ""))
                                message_alerte = (
                                    f"Bonjour, l'article \"{article_nom}\" est de nouveau disponible "
                                    f"sur {config.get('nom_boutique', 'notre boutique')} !"
                                )
                                lien_whatsapp_alerte = f"https://wa.me/{tel_alerte}?text={requests.utils.quote(message_alerte)}"
                                col1, col2 = st.columns([3, 2])
                                col1.write(f"📞 {alerte.get('contact')}")
                                col2.link_button(
                                    "💬 WhatsApp", lien_whatsapp_alerte,
                                    key=f"wa_alerte_{alerte.get('id')}"
                                )
                            else:
                                st.write(f"✉️ {alerte.get('contact')}")
                        if st.button("🔔 Notifier les inscrits par email maintenant", key=f"notif_{article_nom}"):
                            notifier_retour_stock(article_nom)
                            st.success("Emails envoyés aux inscrits par email pour cet article.")
                            st.rerun()

        with tab_paniers:
            reponse = sb_admin.table("paniersabandonnés").select("*").eq("statut", "en_attente").execute()
            paniers = sorted(reponse.data, key=lambda p: p.get("date_derniere_maj", ""), reverse=True)
            if not paniers:
                st.caption("Aucun panier abandonné en attente")
            for idx, panier in enumerate(paniers):
                cle_unique = f"{idx}_{panier.get('telephone') or 'sanstelephone'}"
                total = panier.get("total") or 0
                with st.expander(f"{panier.get('client_nom') or 'Client'} — {panier.get('telephone')} — {total} FCFA"):
                    st.json(panier.get("articles"))
                    tel_relance = re.sub(r"\D", "", str(panier.get("telephone") or ""))
                    if tel_relance:
                        message = f"Bonjour, vous avez laissé des articles dans votre panier sur {config.get('nom_boutique', 'notre boutique')} — puis-je vous aider à finaliser votre commande ?"
                        lien_whatsapp = f"https://wa.me/{tel_relance}?text={requests.utils.quote(message)}"
                        st.link_button("💬 Relancer sur WhatsApp", lien_whatsapp)
                    if st.button("🗑️ Marquer comme traité", key=f"panier_traite_{cle_unique}"):
                        sb_admin.table("paniersabandonnés").update({"statut": "traite"}).eq("telephone", panier["telephone"]).execute()
                        st.rerun()
