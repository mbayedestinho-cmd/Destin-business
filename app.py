import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import uuid
import re
import os
import json
import html as html_lib
import unicodedata
import base64
import hashlib
import hmac
import secrets
import logging
import smtplib
import requests
import bcrypt
from email.mime.text import MIMEText
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from supabase import create_client, Client

# 🔒 Logs serveur pour les erreurs techniques -- jamais affichées en clair à
# l'utilisateur (voir st.error(...) dans tout le fichier : les messages
# affichés sont désormais génériques, le détail part uniquement ici).
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("destiny_luxury")

# 🔄 Permet à la boutique de se rafraîchir toute seule (nouveaux prix, stock,
# logo...) sans que le client n'ait besoin d'appuyer sur "actualiser".
# Nécessite le paquet "streamlit-autorefresh" dans requirements.txt -- si le
# paquet n'est pas encore installé, l'app continue de fonctionner normalement,
# simplement sans l'auto-rafraîchissement (dégradation silencieuse).
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_DISPONIBLE = True
except ImportError:
    AUTOREFRESH_DISPONIBLE = False

st.set_page_config(page_title="Destiny Luxury Collection", page_icon="👗", layout="wide")

# ====================== 0. STYLE (thème "luxe" sobre : fond sombre, accents dorés) ======================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&family=Cormorant+Garamond:wght@600;700&family=Montserrat:wght@500;600;700&family=Poppins:wght@500;600;700&family=Oswald:wght@500;600;700&family=Raleway:wght@500;600;700&family=Bebas+Neue&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: var(--aura-font-titre, 'Playfair Display', serif) !important; letter-spacing: 0.3px; }

    /* 🎨 Variables de thème -- surchargées par boutique premium via
       injecter_theme_premium() (couleur d'accent ET police des titres).
       Par défaut : doré classique Destiny + Playfair Display. C'est aussi
       ce sur quoi l'appli retombe automatiquement dès que le mode premium
       est désactivé (voir injecter_theme_premium : elle ne s'exécute que
       pour une boutique premium, donc ces valeurs par défaut redeviennent
       actives immédiatement pour toutes les autres). */
    :root {
        --aura-accent: #c9a35c;
        --aura-accent-clair: #dab873;
        --aura-font-titre: 'Playfair Display', serif;
    }

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
        border: 1px solid var(--aura-accent);
        color: var(--aura-accent);
        background: transparent;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: var(--aura-accent);
        color: #16151a;
        border-color: var(--aura-accent);
    }
    .stFormSubmitButton > button {
        border-radius: 8px;
        background: var(--aura-accent);
        color: #16151a;
        font-weight: 600;
        border: none;
    }
    .stFormSubmitButton > button:hover {
        background: var(--aura-accent-clair);
    }

    /* Prix et titres produits */
    div[data-testid="stMarkdownContainer"] strong { color: #eae4d8; }
    .destiny-nom-produit {
        font-family: var(--aura-font-titre, 'Playfair Display', serif);
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

    /* ✨ Badge Aura Luxe -- animé, réservé aux boutiques premium. Utilise
       les variables de thème (couleur choisie par le marchand) : reste
       doré par défaut, se recolore automatiquement sinon. Style "plein
       scintillant" par défaut ; variantes ci-dessous sélectionnables
       depuis l'onglet Thème & badge. */
    .aura-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: linear-gradient(120deg, var(--aura-accent-clair), var(--aura-accent), var(--aura-accent-clair), var(--aura-accent));
        background-size: 300% 100%;
        animation: aura-shimmer 3.5s linear infinite;
        color: #16151a; font-weight: 700; font-size: 0.82rem;
        padding: 4px 12px; border-radius: 20px; letter-spacing: 0.3px;
        box-shadow: 0 2px 14px rgba(201,163,92,0.5);
    }
    @keyframes aura-shimmer {
        0% { background-position: 0% 50%; }
        100% { background-position: 300% 50%; }
    }

    /* Variante "Contour lumineux" : fond transparent, liseré pulsant. */
    .aura-badge.style-contour {
        background: transparent; animation: none; box-shadow: none;
        color: var(--aura-accent); border: 1.5px solid var(--aura-accent);
        animation: aura-badge-contour-pulse 2.2s ease-in-out infinite;
    }
    @keyframes aura-badge-contour-pulse {
        0%, 100% { box-shadow: 0 0 6px var(--aura-accent); }
        50% { box-shadow: 0 0 16px var(--aura-accent); }
    }

    /* Variante "Mat professionnel" : couleur pleine sobre, sans animation
       -- adaptée aux thèmes "bleu professionnel", "vert", etc. */
    .aura-badge.style-mat {
        background: var(--aura-accent); animation: none;
        color: #ffffff; box-shadow: 0 2px 10px rgba(0,0,0,0.35);
    }

    /* Variante "Verre givré" : discrète, translucide. */
    .aura-badge.style-glace {
        background: rgba(255,255,255,0.08); animation: none;
        color: var(--aura-accent); border: 1px solid var(--aura-accent);
        box-shadow: 0 2px 14px rgba(0,0,0,0.25); backdrop-filter: blur(6px);
    }

    /* 🔮 Bannière promo -- variante néon (module Aura Luxe) */
    .aura-banniere-neon {
        border: 1px solid var(--aura-accent) !important;
        box-shadow: 0 0 10px var(--aura-accent), 0 0 24px rgba(201,163,92,0.35), inset 0 0 12px rgba(201,163,92,0.12) !important;
        animation: aura-neon-pulse 2.4s ease-in-out infinite;
    }
    @keyframes aura-neon-pulse {
        0%, 100% { box-shadow: 0 0 8px var(--aura-accent), 0 0 18px rgba(201,163,92,0.3), inset 0 0 10px rgba(201,163,92,0.1); }
        50% { box-shadow: 0 0 16px var(--aura-accent), 0 0 34px rgba(201,163,92,0.55), inset 0 0 16px rgba(201,163,92,0.2); }
    }

    /* ⚡ Compte à rebours Flash Sale */
    .aura-flash-badge {
        display: inline-flex; align-items: center; gap: 5px;
        background: #2a1810; border: 1px solid #e0703f; color: #ffb27a;
        font-weight: 700; font-size: 0.8rem; padding: 3px 10px; border-radius: 14px;
        margin: 3px 0;
    }

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

    /* ✨ Variantes d'animation du logo (module Aura Luxe, premium) --
       ajoutées sur .destiny-hero en plus de la classe de base. Sans
       classe supplémentaire, le comportement par défaut ci-dessus
       (halo doré pulsant + balayage brillant) s'applique -- c'est aussi
       ce sur quoi l'appli retombe automatiquement si le mode premium
       est désactivé. */

    /* Halo néon autour du logo, sans pulsation de fond ni balayage. */
    .destiny-hero.anim-neon::before { animation: none; }
    .destiny-hero.anim-neon img {
        animation: aura-logo-neon 2.2s ease-in-out infinite;
        box-shadow: none; border: 2px solid var(--aura-accent);
    }
    .destiny-hero.anim-neon .destiny-hero-shine { display: none; }
    @keyframes aura-logo-neon {
        0%, 100% { box-shadow: 0 0 10px var(--aura-accent), 0 0 20px rgba(0,0,0,0); }
        50% { box-shadow: 0 0 26px var(--aura-accent), 0 0 50px var(--aura-accent); }
    }

    /* Flottement doux -- rendu plus "moderne / corporate" que le glow doré. */
    .destiny-hero.anim-douce::before { animation: none; }
    .destiny-hero.anim-douce img {
        animation: aura-logo-float 3.6s ease-in-out infinite;
        box-shadow: 0 14px 34px rgba(0,0,0,0.4), 0 0 20px var(--aura-accent);
    }
    .destiny-hero.anim-douce .destiny-hero-shine { display: none; }
    @keyframes aura-logo-float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-8px); }
    }

    /* Rotation discrète -- garde le halo tournant en fond, retire la
       pulsation de lumière et le balayage brillant sur le logo. */
    .destiny-hero.anim-rotation img {
        animation: none;
        box-shadow: 0 10px 34px rgba(0,0,0,0.45), 0 0 22px var(--aura-accent);
    }
    .destiny-hero.anim-rotation .destiny-hero-shine { display: none; }

    /* Aucune animation -- rendu sobre, entièrement statique. */
    .destiny-hero.anim-aucune::before { animation: none; opacity: 0.35; }
    .destiny-hero.anim-aucune img {
        animation: none; box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    }
    .destiny-hero.anim-aucune .destiny-hero-shine { display: none; }

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

    /* Boutons-liens (st.link_button) -- alignés sur le même style doré que
       les st.button classiques ci-dessus (auparavant non stylés). */
    div[data-testid="stLinkButton"] a {
        border-radius: 8px;
        border: 1px solid var(--aura-accent);
        color: var(--aura-accent) !important;
        background: transparent;
        font-weight: 500;
        transition: all 0.2s ease;
        text-decoration: none;
    }
    div[data-testid="stLinkButton"] a:hover {
        background: var(--aura-accent);
        color: #16151a !important;
        border-color: var(--aura-accent);
    }

    /* ====================== SIDEBAR — PANNEAU DE BORD ====================== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(165deg, #131218 0%, #19171c 55%, #131218 100%);
        border-right: 1px solid rgba(201,163,92,0.22);
        position: relative;
    }
    /* Faisceau doré qui balaie le bord droit de la sidebar en continu --
       signature "panneau de contrôle", dans le même doré que le hero et les
       badges Aura Luxe (aucune couleur étrangère à l'identité de la boutique). */
    section[data-testid="stSidebar"]::after {
        content: "";
        position: absolute;
        top: -160px; right: -1px;
        width: 2px; height: 160px;
        background: linear-gradient(180deg, transparent, var(--aura-accent-clair), transparent);
        animation: dlc-balayage 6s ease-in-out infinite;
        pointer-events: none;
        opacity: 0.85;
    }
    @keyframes dlc-balayage {
        0%   { top: -160px; }
        100% { top: 100%; }
    }

    /* Bandeau "Espace client" en tête de sidebar */
    .dlc-sidebar-masthead {
        display: flex; align-items: center; gap: 8px;
        margin: -0.5rem 0 1.1rem 0; padding-bottom: 0.7rem;
        border-bottom: 1px solid rgba(201,163,92,0.25);
    }
    .dlc-sidebar-masthead .dlc-dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--aura-accent);
        box-shadow: 0 0 8px var(--aura-accent);
        animation: dlc-pulse-dot 2s ease-in-out infinite;
    }
    @keyframes dlc-pulse-dot {
        0%, 100% { opacity: 0.4; } 50% { opacity: 1; }
    }
    .dlc-sidebar-masthead .dlc-masthead-texte {
        text-transform: uppercase; letter-spacing: 2.5px; font-size: 0.68rem;
        color: rgba(201,163,92,0.85); font-weight: 600;
    }

    /* Panneaux (Panier / Favoris / Suivi / Contact) -- verre dépoli discret,
       liseré doré qui se réveille au survol. */
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"],
    section[data-testid="stSidebar"] div[data-testid="stExpander"] {
        background: linear-gradient(160deg, rgba(255,255,255,0.035), rgba(255,255,255,0.008)) !important;
        border: 1px solid rgba(201,163,92,0.22) !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 18px rgba(0,0,0,0.35);
        margin-bottom: 14px;
        transition: border-color 0.25s ease, box-shadow 0.25s ease;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]:hover,
    section[data-testid="stSidebar"] div[data-testid="stExpander"]:hover {
        border-color: rgba(201,163,92,0.55) !important;
        box-shadow: 0 4px 22px rgba(0,0,0,0.4), 0 0 16px rgba(201,163,92,0.16);
    }
    section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
        font-family: 'Playfair Display', serif; font-weight: 700; color: #eae4d8;
    }

    /* En-tête interne d'un panneau : badge icône rond + eyebrow + titre */
    .dlc-panel-eyebrow {
        text-transform: uppercase; letter-spacing: 2px; font-size: 0.62rem;
        color: rgba(201,163,92,0.75); font-weight: 600; margin: 0 0 3px 46px;
    }
    .dlc-panel-entete {
        display: flex; align-items: center; gap: 12px; margin-bottom: 10px;
    }
    .dlc-panel-icone {
        display: flex; align-items: center; justify-content: center;
        width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
        background: linear-gradient(135deg, rgba(201,163,92,0.25), rgba(201,163,92,0.05));
        border: 1px solid rgba(201,163,92,0.45);
        font-size: 1rem;
    }
    .dlc-panel-titre {
        font-family: var(--aura-font-titre, 'Playfair Display', serif); font-size: 1.05rem; font-weight: 700;
        color: #eae4d8; letter-spacing: 0.2px;
    }

    /* Boutons de la sidebar : pilule, cohérente avec l'esthétique "panneau" */
    section[data-testid="stSidebar"] .stButton > button {
        border-radius: 20px;
        font-size: 0.87rem;
    }
</style>
""", unsafe_allow_html=True)

# ====================== 3bis. ZOOM IMAGE PRODUIT ======================
# 🐛 HISTORIQUE : un calque de zoom "maison" (lightbox en plein écran dans
# la page) a été tenté ici, mais s'est heurté à plusieurs pièges CSS/DOM
# propres à Streamlit (position:fixed emprisonné par un conteneur parent,
# scripts inertes selon comment ils sont injectés, cadres imbriqués...) --
# après plusieurs correctifs infructueux, on abandonne cette approche.
# Un clic sur une photo produit ouvre maintenant simplement l'image en
# pleine résolution dans un NOUVEL ONGLET : le zoom natif du téléphone/
# navigateur prend le relais, et se referme avec le geste "retour" habituel
# -- zéro dépendance aux subtilités de mise en page de Streamlit, garanti
# de fonctionner sur n'importe quel navigateur. Voir JS_OUVRIR_LIGHTBOX
# plus bas (nom conservé pour ne pas casser les appels existants).

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

# Fuseau horaire de la boutique -- utilisé pour convertir les dates/heures
# saisies par le marchand (heure locale) en UTC avant stockage. Confirmé à
# UTC+0 (Dakar/Abidjan/Bamako) ; à changer ici si la boutique change de zone.
FUSEAU_BOUTIQUE = ZoneInfo("Africa/Abidjan")


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


# ====================== 2bis. MARCHAND ACTIF (marketplace) ======================
# Multi-tenant : UN SEUL déploiement sert toutes les boutiques de la
# marketplace. Le marchand à afficher est déterminé par le paramètre d'URL
# ?boutique=<slug>, par exemple :
#   https://tonapp.streamlit.app/?boutique=bienvenu-boutique
# (même principe que ?admin=1 utilisé plus bas pour l'accès admin -- les
# deux peuvent se combiner : ?admin=1&boutique=bienvenu-boutique)
# Si le paramètre est absent (lien direct sans query string, ex. un ancien
# favori), on retombe sur le secret MARCHAND_SLUG s'il est défini, sinon sur
# un slug fixe de secours.
def determiner_slug_boutique():
    slug_url = st.query_params.get("boutique")
    if slug_url:
        # On mémorise le slug en session dès qu'on le connaît, pour pouvoir
        # le restaurer si le paramètre d'URL venait à disparaître (retour
        # navigateur, lien/raccourci sans query string, rechargement...).
        st.session_state["boutique_slug"] = slug_url
        return slug_url
    slug_session = st.session_state.get("boutique_slug")
    if slug_session:
        # Paramètre absent CETTE fois-ci, mais cette session sait déjà à
        # quelle boutique elle appartient -> on la restaure, et on remet le
        # paramètre dans l'URL pour rester cohérent au prochain partage/refresh.
        st.query_params["boutique"] = slug_session
        return slug_session
    return st.secrets.get("MARCHAND_SLUG", "destiny-luxury")


MARCHAND_SLUG = determiner_slug_boutique()


@st.cache_data(ttl=60)
def charger_marchand(slug):
    # 🔒 FIX MULTI-TENANT : l'ancienne version utilisait @st.cache_resource
    # SANS paramètre -- en cache-partagé-process, ça figeait le PREMIER
    # marchand chargé pour TOUS les visiteurs suivants, quel que soit leur
    # ?boutique=. Le cache est maintenant conditionné au slug (une entrée de
    # cache par boutique) et se rafraîchit après 60s.
    #
    # Client admin (service_role) utilisé volontairement : il bypasse RLS,
    # donc ça marche même si le marchand est suspendu (on veut pouvoir
    # afficher un message clair plutôt que planter silencieusement).
    reponse = get_admin_client().table("marchands").select("*").eq("slug", slug).execute()
    return reponse.data[0] if reponse.data else None


MARCHAND = charger_marchand(MARCHAND_SLUG)

if not MARCHAND:
    st.error(f"Boutique introuvable pour le lien utilisé (« {MARCHAND_SLUG} »). Vérifie l'URL.")
    st.stop()

MARCHAND_ID = MARCHAND["id"]

# L'accès n'est ouvert que pour un abonnement actif ou en délai de grâce --
# voir le commentaire de la table `marchands` dans le schéma SQL.
if MARCHAND["statut_abonnement"] not in ("actif", "en_grace"):
    messages_statut = {
        "en_attente_paiement": "Cette boutique est en cours d'activation et n'est pas encore ouverte au public.",
        "suspendu": "Cette boutique est temporairement indisponible.",
        "resilie": "Cette boutique n'est plus disponible.",
    }
    st.error(messages_statut.get(MARCHAND["statut_abonnement"], "Cette boutique n'est pas disponible actuellement."))
    st.stop()


# 🔒 ISOLATION MULTI-TENANT (fix pro, v2 -- namespacing automatique) :
# l'ancienne version maintenait une liste explicite des clés "par boutique"
# (CLES_SESSION_PAR_BOUTIQUE) et les effaçait au changement de MARCHAND_ID.
# Risque structurel : toute NOUVELLE clé de session_state ajoutée plus tard
# dans le code et oubliée dans cette liste fuit silencieusement d'une
# boutique à l'autre (panier, favoris, ou pire, admin_connecte).
#
# Ici, on élimine la liste : `ss` est un proxy qui remplace st.session_state
# partout dans le reste du fichier et namespace AUTOMATIQUEMENT chaque clé
# par MARCHAND_ID ("m<id>__cart" au lieu de "cart"). Deux boutiques ne
# peuvent plus jamais partager une clé, y compris pour du code écrit après
# ce commentaire -- il n'y a plus rien à maintenir ni à oublier.
#
# Seules "boutique_slug" et "_boutique_verrouillee_id" restent volontairement
# hors namespace : ce sont des clés de "bootstrap" lues AVANT de connaître
# MARCHAND_ID (résolution du slug depuis l'URL), donc elles continuent
# d'utiliser st.session_state directement (voir determiner_slug_boutique).
class EtatBoutique:
    """Proxy transparent autour de st.session_state, namespacé par MARCHAND_ID.

    Supporte la même API que st.session_state (attribut, [] , get, pop,
    setdefault, in) -- remplacement direct, aucune autre ligne à changer
    en dehors du split ci-dessus.
    """

    _CLES_GLOBALES = {"boutique_slug", "_boutique_verrouillee_id"}

    def __init__(self, get_marchand_id):
        object.__setattr__(self, "_get_marchand_id", get_marchand_id)

    def _cle(self, cle):
        if cle in self._CLES_GLOBALES:
            return cle
        return f"m{self._get_marchand_id()}__{cle}"

    def __getattr__(self, cle):
        try:
            return st.session_state[self._cle(cle)]
        except KeyError:
            raise AttributeError(cle)

    def __setattr__(self, cle, valeur):
        st.session_state[self._cle(cle)] = valeur

    def __delattr__(self, cle):
        del st.session_state[self._cle(cle)]

    def __getitem__(self, cle):
        return st.session_state[self._cle(cle)]

    def __setitem__(self, cle, valeur):
        st.session_state[self._cle(cle)] = valeur

    def __delitem__(self, cle):
        del st.session_state[self._cle(cle)]

    def __contains__(self, cle):
        return self._cle(cle) in st.session_state

    def get(self, cle, defaut=None):
        return st.session_state.get(self._cle(cle), defaut)

    def pop(self, cle, defaut=None):
        return st.session_state.pop(self._cle(cle), defaut)

    def setdefault(self, cle, defaut=None):
        return st.session_state.setdefault(self._cle(cle), defaut)


ss = EtatBoutique(lambda: MARCHAND_ID)
st.session_state["_boutique_verrouillee_id"] = MARCHAND_ID


if "admin_connecte" not in ss:
    ss.admin_connecte = False


# 🔒 FIX SÉCURITÉ : SHA-256 seul est un hash *rapide*, non conçu pour des
# mots de passe (pas de sel, cassable très vite par GPU en cas de fuite de
# la table config). On passe à bcrypt (sel intégré + facteur de coût), avec
# une compatibilité ascendante qui reconnaît encore un ancien hash SHA-256
# le temps que l'admin change son mot de passe une première fois.
#
# 🔑 Pour définir/réinitialiser le mot de passe admin directement en base
# (si tu ne connais pas le mot de passe actuel), lance ce script Python en
# local puis colle le résultat dans la colonne `mot_de_passe_hash` de la
# ligne correspondante dans la table `marchands` :
#   import bcrypt; print(bcrypt.hashpw(b"TonNouveauMotDePasse", bcrypt.gensalt(rounds=12)).decode())
def hash_mot_de_passe(valeur):
    return bcrypt.hashpw(str(valeur or "").encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _est_hash_sha256_heritage(hash_stocke):
    # Un hash SHA-256 hexadécimal fait exactement 64 caractères hex, tandis
    # qu'un hash bcrypt commence toujours par "$2".
    return bool(re.fullmatch(r"[0-9a-f]{64}", str(hash_stocke or "")))


def verifier_mot_de_passe(valeur, hash_stocke):
    valeur = str(valeur or "")
    hash_stocke = str(hash_stocke or "")
    if not hash_stocke:
        return False
    if _est_hash_sha256_heritage(hash_stocke):
        # Compatibilité avec un mot de passe migré avant ce correctif --
        # comparaison en temps constant pour éviter le timing attack.
        return hmac.compare_digest(
            hashlib.sha256(valeur.encode("utf-8")).hexdigest(), hash_stocke
        )
    try:
        return bcrypt.checkpw(valeur.encode("utf-8"), hash_stocke.encode("utf-8"))
    except ValueError:
        return False


# 🔒 FIX SÉCURITÉ : avant, rien ne limitait le nombre de tentatives de
# connexion admin -- un mot de passe pouvait être testé en boucle sans
# aucune limite (brute-force / dictionnaire). On verrouille désormais la
# session après plusieurs échecs successifs.
SEUIL_TENTATIVES_ADMIN = 5
DUREE_VERROU_ADMIN_SEC = 300  # 5 minutes
DUREE_SESSION_ADMIN_SEC = 1800  # 30 minutes d'inactivité avant déconnexion


def admin_login(mot_de_passe):
    """Retourne (succes: bool, message_erreur: str | None).
    🔒 AUDIT SÉCURITÉ #3 : le verrouillage anti-brute-force vit maintenant
    côté serveur (table tentatives_connexion via RPC), plus dans
    ss -- un nouvel onglet privé ne permet plus de
    contourner la limite de tentatives. En cas d'échec de la RPC (ex:
    fonction pas encore migrée), on retombe sur l'ancien comportement en
    session plutôt que de bloquer complètement la connexion."""
    cle_verrou = f"marchand_{MARCHAND_ID}"
    maintenant = datetime.now(timezone.utc).timestamp()

    try:
        verrou = sb.rpc("verifier_verrou_connexion", {"p_cle": cle_verrou}).execute().data
        if verrou and verrou.get("bloque"):
            restant = int(verrou.get("secondes_restantes", 0))
            return False, f"Trop de tentatives échouées. Réessaie dans {restant} seconde(s)."
    except Exception:
        logger.warning("RPC verifier_verrou_connexion indisponible, repli sur le verrou de session")
        verrou_jusqu_a = ss.get("admin_verrou_jusqu_a", 0)
        if maintenant < verrou_jusqu_a:
            restant = int(verrou_jusqu_a - maintenant)
            return False, f"Trop de tentatives échouées. Réessaie dans {restant} seconde(s)."

    config_actuelle = charger_config(MARCHAND_ID, ss.refresh_token)
    hash_attendu = config_actuelle.get("mot_de_passe", "")
    mot_de_passe_correct = verifier_mot_de_passe(mot_de_passe, hash_attendu)

    try:
        sb.rpc("enregistrer_tentative_connexion", {
            "p_cle": cle_verrou, "p_reussite": mot_de_passe_correct,
            "p_seuil": SEUIL_TENTATIVES_ADMIN, "p_duree_verrou_secondes": DUREE_VERROU_ADMIN_SEC
        }).execute()
    except Exception:
        logger.warning("RPC enregistrer_tentative_connexion indisponible, repli sur le verrou de session")

    if mot_de_passe_correct:
        # 🔒 AUDIT SÉCURITÉ : un hash SHA-256 (legacy, non salé) est bien
        # plus rapide à casser par force brute hors-ligne qu'un bcrypt en
        # cas de fuite de la base. Puisqu'on a le mot de passe en clair ICI
        # (juste vérifié), on referme la fenêtre de risque en migrant
        # silencieusement vers bcrypt -- le marchand ne voit aucune
        # différence, mais son compte n'est plus jamais vulnérable après
        # cette connexion.
        if _est_hash_sha256_heritage(hash_attendu):
            try:
                get_admin_client().table("marchands").update(
                    {"mot_de_passe_hash": hash_mot_de_passe(mot_de_passe)}
                ).eq("id", MARCHAND_ID).execute()
            except Exception:
                logger.exception("Échec migration hash mot de passe legacy vers bcrypt")
        ss.admin_connecte = True
        ss.admin_derniere_activite = maintenant
        ss.admin_tentatives = 0
        ss.admin_verrou_jusqu_a = 0
        return True, None

    # Repli local (utilisé seulement si la RPC ci-dessus a échoué) --
    # sinon le compteur en session reste à 0 et n'a aucun effet, la RPC
    # ayant déjà fait foi.
    tentatives = ss.get("admin_tentatives", 0) + 1
    ss.admin_tentatives = tentatives
    if tentatives >= SEUIL_TENTATIVES_ADMIN:
        ss.admin_verrou_jusqu_a = maintenant + DUREE_VERROU_ADMIN_SEC
        ss.admin_tentatives = 0
        return False, f"Trop de tentatives échouées. Réessaie dans {DUREE_VERROU_ADMIN_SEC // 60} minute(s)."
    return False, "Mot de passe incorrect."


def admin_logout():
    ss.admin_connecte = False
    ss.pop("admin_derniere_activite", None)


def session_admin_valide():
    """Vérifie que l'admin est connecté ET que sa session n'a pas expiré par
    inactivité (protège un poste laissé déverrouillé)."""
    if not ss.get("admin_connecte"):
        return False
    maintenant = datetime.now(timezone.utc).timestamp()
    derniere_activite = ss.get("admin_derniere_activite", 0)
    if maintenant - derniere_activite > DUREE_SESSION_ADMIN_SEC:
        admin_logout()
        return False
    ss.admin_derniere_activite = maintenant
    return True


def throttle(cle, delai_sec=10):
    """Anti-spam léger pour les actions publiques répétées (avis, alertes
    stock...) -- limite la fréquence par session, en complément des
    policies RLS côté Supabase qui restent la protection de fond."""
    maintenant = datetime.now(timezone.utc).timestamp()
    dernier = ss.get(f"throttle_{cle}", 0)
    if maintenant - dernier < delai_sec:
        return False
    ss[f"throttle_{cle}"] = maintenant
    return True


# ====================== 3. IMGBB (upload d'images) ======================
TAILLE_MAX_IMAGE_MO = 32  # limite du compte ImgBB gratuit

# 🐛 CORRECTIF UPLOAD MOBILE : st.file_uploader envoie toujours le fichier
# ORIGINAL (parfois 10-20 Mo, une photo de téléphone) en entier vers le
# serveur avant qu'on puisse le compresser -- sur une connexion 3G/4G
# instable, ce transfert lourd est celui qui échoue (coupure réseau brève =
# reconnexion Streamlit = "flash sombre" et fichier perdu). La compression
# ajoutée précédemment (voir compresser_image_avant_envoi) n'agissait qu'une
# fois le fichier déjà arrivé sur le serveur -- trop tard.
# Ce composant compresse l'image DANS LE TÉLÉPHONE (via <canvas>), avant
# tout envoi réseau, pour que le transfert soit petit et rapide dès le
# départ -- comme le font les applications professionnelles.
_composant_compression_image = components.declare_component(
    "compresseur_image",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "composant_compression_image")
)


def uploader_image_compressee(key):
    """Affiche le widget d'upload avec compression téléphone, et renvoie
    (contenu_bytes, nom_fichier) ou (None, None) si rien n'est sélectionné."""
    resultat = _composant_compression_image(key=key, default=None)
    if not resultat or not isinstance(resultat, dict):
        return None, None
    donnees_url = resultat.get("donnees") or ""
    if "," not in donnees_url:
        return None, None
    try:
        contenu = base64.b64decode(donnees_url.split(",", 1)[1])
    except Exception:
        return None, None
    return contenu, (resultat.get("nom") or "image.jpg")


# 🔒 FIX SÉCURITÉ : le paramètre `type=[...]` de st.file_uploader ne filtre
# que l'extension affichée -- un fichier renommé (ex. script déguisé en
# ".png") passait sans contrôle. On vérifie désormais la signature binaire
# réelle (magic bytes) du contenu avant tout envoi vers ImgBB.
SIGNATURES_IMAGE = (
    (b"\xff\xd8\xff", None),                 # JPEG
    (b"\x89PNG\r\n\x1a\n", None),            # PNG
    (b"RIFF", b"WEBP"),                       # WEBP : "RIFF" ....  "WEBP" (offset 8)
)


def est_image_valide(contenu: bytes) -> bool:
    for signature, marqueur_secondaire in SIGNATURES_IMAGE:
        if contenu.startswith(signature):
            if marqueur_secondaire is None:
                return True
            if contenu[8:12] == marqueur_secondaire:
                return True
    return False


def compresser_image_avant_envoi(contenu: bytes) -> bytes:
    """Redimensionne/compresse l'image avant l'envoi vers ImgBB.

    🐛 CORRECTIF : les photos de téléphone (souvent 5 à 20 Mo) partaient vers
    ImgBB telles quelles, encodées en base64 (+33% de poids), sur des
    connexions mobiles parfois instables -- d'où des envois qui réussissaient
    ou échouaient au hasard selon la qualité du réseau au moment T, avec
    plusieurs essais nécessaires. En ramenant l'image à une taille raisonnable
    ici, le transfert est nettement plus rapide et fiable, comme le font les
    applications professionnelles avant tout envoi.
    Retourne le contenu original si la compression échoue ou n'aide pas,
    pour ne jamais bloquer un envoi qui aurait fonctionné avant."""
    try:
        from PIL import Image
        from io import BytesIO
    except ImportError:
        return contenu

    try:
        image = Image.open(BytesIO(contenu))
        a_transparence = image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        )

        LARGEUR_MAX = 1600
        if image.width > LARGEUR_MAX:
            nouvelle_hauteur = int(image.height * (LARGEUR_MAX / image.width))
            image = image.resize((LARGEUR_MAX, nouvelle_hauteur), Image.LANCZOS)

        tampon = BytesIO()
        if a_transparence:
            image.save(tampon, format="PNG", optimize=True)
        else:
            image.convert("RGB").save(tampon, format="JPEG", quality=82, optimize=True)

        resultat = tampon.getvalue()
        return resultat if len(resultat) < len(contenu) else contenu
    except Exception:
        logger.exception("Échec compression image avant envoi -- envoi de l'original")
        return contenu


def _envoyer_vers_imgbb(image_b64: str):
    """Retourne (url, erreur). erreur=None signifie succès."""
    try:
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


def _envoyer_vers_freeimage_host(image_b64: str):
    """Hébergeur de secours (même famille d'API qu'ImgBB) -- utilisé
    uniquement si ImgBB échoue. Retourne (url, erreur)."""
    cle = _cle_secrete("FREEIMAGE_API_KEY")
    if not cle:
        return None, "Aucune clé FREEIMAGE_API_KEY configurée pour le secours."
    try:
        reponse = requests.post(
            "https://freeimage.host/api/1/upload",
            data={"key": cle, "source": image_b64, "format": "json"},
            timeout=60
        )
    except requests.exceptions.Timeout:
        return None, "Délai d'attente dépassé sur l'hébergeur de secours."
    except requests.exceptions.RequestException as e:
        return None, f"Erreur réseau lors de l'envoi vers l'hébergeur de secours : {e}"

    try:
        donnees = reponse.json()
    except Exception:
        return None, f"Réponse invalide de l'hébergeur de secours (code HTTP {reponse.status_code})."

    if donnees.get("status_code") == 200 and donnees.get("image", {}).get("url"):
        return donnees["image"]["url"], None

    message_erreur = (donnees.get("error") or {}).get("message", "erreur inconnue")
    return None, f"L'hébergeur de secours a refusé l'image : {message_erreur} (code HTTP {reponse.status_code})."


def televerser_octets_imgbb(contenu: bytes, deja_compressee: bool = False):
    """Envoie des octets d'image vers ImgBB, avec bascule automatique sur
    freeimage.host (hébergeur de secours, même famille d'API) si ImgBB est
    en panne ou refuse l'image -- pour que le marchand ne soit jamais
    bloqué par une indisponibilité ponctuelle d'un seul service.
    Renvoie un tuple (url, erreur) : url vaut None seulement si les DEUX
    hébergeurs ont échoué, et erreur détaille alors les deux raisons.
    `deja_compressee=True` (venant du composant navigateur) évite de
    recompresser inutilement une image déjà réduite côté client."""
    if not contenu:
        return None, None

    if not est_image_valide(contenu):
        return None, "Le fichier ne correspond pas à un format d'image valide (jpg/png/webp)."

    taille_mo = len(contenu) / (1024 * 1024)
    if taille_mo > TAILLE_MAX_IMAGE_MO:
        return None, f"Fichier trop volumineux ({taille_mo:.1f} Mo, max {TAILLE_MAX_IMAGE_MO} Mo)."

    if not deja_compressee:
        contenu = compresser_image_avant_envoi(contenu)

    image_b64 = base64.b64encode(contenu).decode()

    url, erreur_imgbb = _envoyer_vers_imgbb(image_b64)
    if url:
        return url, None

    logger.warning(f"Échec ImgBB, bascule sur l'hébergeur de secours : {erreur_imgbb}")
    url, erreur_secours = _envoyer_vers_freeimage_host(image_b64)
    if url:
        return url, None

    return None, f"{erreur_imgbb} — Secours également indisponible : {erreur_secours}"


def televerser_image_imgbb(fichier):
    """Envoie un fichier venant de st.file_uploader vers ImgBB (compatibilité
    -- conservé là où le composant navigateur n'est pas encore branché).
    Renvoie un tuple (url, erreur)."""
    if fichier is None:
        return None, None
    try:
        contenu = fichier.getvalue()  # ne consomme pas le flux, contrairement à .read()
    except Exception as e:
        return None, f"Impossible de lire le fichier ({e})."
    return televerser_octets_imgbb(contenu, deja_compressee=False)




# ====================== 3bis. GALERIE PHOTOS AVEC GLISSEMENT (SWIPE) ======================
# 🐛 Après plusieurs correctifs infructueux sur un calque de zoom "maison"
# (voir historique plus haut dans le fichier), on ouvre simplement l'image
# en pleine résolution dans un nouvel onglet -- fiable partout, sans aucune
# dépendance aux subtilités de mise en page de Streamlit.
JS_OUVRIR_LIGHTBOX = (
    "try { window.parent.open(this.src, '_blank'); }"
    "catch(e) { window.location.href = this.src; }"
)


def afficher_galerie_swipe(images, hauteur=280, cle=""):
    """Affiche une galerie photo qu'on peut faire glisser au doigt (mobile) ou
    à la souris pour passer d'une image à l'autre, avec des points cliquables
    en complément sur ordinateur. Un clic/tap sur la photo l'ouvre en plein
    écran (zoom) via le lightbox global.
    🐛 CORRECTIF : une photo unique passait avant par afficher_image_zoomable
    (rendue directement dans la page, hors iframe) -- son onclick ne
    s'ouvrait jamais chez certains utilisateurs, alors que la galerie
    (rendue dans un iframe components.html) fonctionnait. Cause exacte non
    confirmée (probable ré-exécution du markdown lors des reruns Streamlit
    qui perd le binding), mais plutôt que de maintenir deux mécanismes de
    rendu différents pour le même clic, on utilise maintenant TOUJOURS ce
    composant iframe, même pour une seule photo -- un seul chemin, déjà
    confirmé fonctionnel, pour toutes les photos produit."""
    images = [u for u in images if u]
    if not images:
        return

    diapositives = "".join(
        f'<div class="dlc-slide"><img src="{html_lib.escape(u, quote=True)}" loading="lazy" '
        f"onclick=\"{JS_OUVRIR_LIGHTBOX}\"></div>"
        for u in images
    )
    points = (
        "".join(f'<span class="dlc-dot" data-i="{i}"></span>' for i in range(len(images)))
        if len(images) > 1 else ""
    )
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
        cursor: zoom-in;
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


def bouton_partager(titre_produit, texte_partage, slug_boutique, produit_id, cle=""):
    """Bouton « Partager » : ouvre le partage natif du téléphone (WhatsApp,
    SMS, etc. via l'API navigator.share) avec le lien de la boutique et de
    l'article. Sur un ordinateur (pas de partage natif), le lien est copié
    dans le presse-papier -- avec un repli sur une fenêtre "copier ce lien"
    si le presse-papier est bloqué par le navigateur."""
    id_bouton = f"dlc-partage-{re.sub(r'[^a-zA-Z0-9_-]', '', str(cle))}"
    titre_js = json.dumps(str(titre_produit))
    texte_js = json.dumps(str(texte_partage))
    slug_js = json.dumps(str(slug_boutique))
    produit_js = json.dumps(str(produit_id))
    code_html = f"""
    <button id="{id_bouton}" class="dlc-btn-partage">🔗 Partager</button>
    <style>
      .dlc-btn-partage {{
        width:100%; padding:0.45rem 0.6rem; border-radius:8px;
        border:1px solid #c9a35c; background:transparent; color:#c9a35c;
        font-family:'Inter',sans-serif; font-weight:500; font-size:0.95rem;
        cursor:pointer; transition:all 0.2s ease; white-space:nowrap;
      }}
      .dlc-btn-partage:hover {{ background:#c9a35c; color:#16151a; }}
    </style>
    <script>
      (function() {{
        const bouton = document.getElementById("{id_bouton}");
        bouton.addEventListener("click", async function() {{
          let lien;
          try {{
            const url = new URL(window.top.location.href);
            url.searchParams.set("boutique", {slug_js});
            url.searchParams.set("produit", {produit_js});
            lien = url.toString();
          }} catch (e) {{
            lien = window.location.href;
          }}
          const donnees = {{ title: {titre_js}, text: {texte_js}, url: lien }};
          try {{
            if (navigator.share) {{
              await navigator.share(donnees);
              return;
            }}
            throw new Error("partage natif indisponible");
          }} catch (e) {{
            try {{
              await navigator.clipboard.writeText(lien);
              bouton.textContent = "✅ Lien copié !";
              setTimeout(() => {{ bouton.textContent = "🔗 Partager"; }}, 2000);
            }} catch (e2) {{
              window.prompt("Copie ce lien pour le partager :", lien);
            }}
          }}
        }});
      }})();
    </script>
    """
    components.html(code_html, height=46, scrolling=False)


def bouton_copier_texte(texte, cle, libelle="📋 Copier le texte"):
    """Petit bouton qui copie `texte` dans le presse-papier, avec repli sur
    une fenêtre "copier ce texte" si le presse-papier est bloqué par le
    navigateur (mêmes limites que bouton_partager)."""
    id_bouton = f"dlc-copier-{re.sub(r'[^a-zA-Z0-9_-]', '', str(cle))}"
    texte_js = json.dumps(str(texte))
    libelle_js = json.dumps(str(libelle))
    code_html = f"""
    <button id="{id_bouton}" class="dlc-btn-partage">{html_lib.escape(libelle)}</button>
    <style>
      .dlc-btn-partage {{
        width:100%; padding:0.45rem 0.6rem; border-radius:8px;
        border:1px solid #c9a35c; background:transparent; color:#c9a35c;
        font-family:'Inter',sans-serif; font-weight:500; font-size:0.95rem;
        cursor:pointer; transition:all 0.2s ease; white-space:nowrap;
      }}
      .dlc-btn-partage:hover {{ background:#c9a35c; color:#16151a; }}
    </style>
    <script>
      (function() {{
        const bouton = document.getElementById("{id_bouton}");
        bouton.addEventListener("click", async function() {{
          try {{
            await navigator.clipboard.writeText({texte_js});
            bouton.textContent = "✅ Copié !";
            setTimeout(() => {{ bouton.textContent = {libelle_js}; }}, 2000);
          }} catch (e) {{
            window.prompt("Copie ce texte :", {texte_js});
          }}
        }});
      }})();
    </script>
    """
    components.html(code_html, height=46, scrolling=False)


def entete_panneau_sidebar(icone, titre, eyebrow):
    """En-tête d'un « panneau » de la sidebar (Panier, Favoris, Contact...) :
    badge icône rond doré + petit label capitalisé (eyebrow) + titre en
    Playfair Display, pour un rendu panneau de bord cohérent avec le hero."""
    st.markdown(
        f'<div class="dlc-panel-eyebrow">{html_lib.escape(str(eyebrow))}</div>'
        f'<div class="dlc-panel-entete">'
        f'<div class="dlc-panel-icone">{icone}</div>'
        f'<div class="dlc-panel-titre">{html_lib.escape(str(titre))}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


ANIMATIONS_LOGO = {
    "glow": "Doré scintillant (défaut)",
    "neon": "Halo néon",
    "douce": "Flottement doux",
    "rotation": "Rotation discrète",
    "aucune": "Aucune (sobre)",
}


def afficher_hero(logo_url, titre, sous_titre="", animation_logo="glow"):
    """Affiche le bandeau logo + effet lumineux en arrière-plan, avec un
    titre (ex: nom de la boutique, ou message de bienvenue) et un sous-titre
    facultatif. Réutilisé pour la boutique ET pour l'écran d'accueil admin.
    `animation_logo` (module Aura Luxe, premium) choisit la variante
    d'animation du logo -- "glow" (valeur par défaut) reproduit exactement
    le rendu doré historique, donc une boutique standard ou repassée en
    standard retombe automatiquement dessus."""
    classe_anim = f" anim-{animation_logo}" if animation_logo and animation_logo != "glow" else ""
    sous_titre_html = f'<div class="destiny-tagline">{sous_titre}</div>' if sous_titre else ""
    if logo_url:
        st.markdown(
            f'<div class="destiny-hero{classe_anim}">'
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
            f'<div class="destiny-hero{classe_anim}"><h1>{titre}</h1>{sous_titre_html}</div>',
            unsafe_allow_html=True
        )


# ====================== 3bis. ASSISTANT IA -- descriptions & posts (module premium) ======================
# 🤖 Génère du texte marketing (descriptions produits, posts réseaux
# sociaux) via une rotation de 3 API : si la clé/quota d'une API pose
# problème, la suivante prend le relais automatiquement -- le marchand
# n'a jamais à s'en soucier.
#   1. Groq (rapide, modèles Llama) -- primaire
#   2. Gemini 1.5 Flash (Google) -- secours
#   3. DeepSeek -- dernier recours
# Nécessite GROQ_API_KEY / GEMINI_API_KEY / DEEPSEEK_API_KEY dans les
# secrets Streamlit. Une clé manquante ne bloque rien : ce fournisseur est
# simplement sauté dans la rotation.
def _cle_secrete(nom):
    try:
        return st.secrets.get(nom)
    except Exception:
        return None


def _generer_via_groq(prompt, max_tokens):
    cle = _cle_secrete("GROQ_API_KEY")
    if not cle:
        return None
    reponse = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {cle}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.85,
        },
        timeout=30,
    )
    reponse.raise_for_status()
    return reponse.json()["choices"][0]["message"]["content"].strip()


def _generer_via_gemini(prompt, max_tokens):
    cle = _cle_secrete("GEMINI_API_KEY")
    if not cle:
        return None
    reponse = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={cle}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.85},
        },
        timeout=30,
    )
    reponse.raise_for_status()
    return reponse.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _generer_via_deepseek(prompt, max_tokens):
    cle = _cle_secrete("DEEPSEEK_API_KEY")
    if not cle:
        return None
    reponse = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {cle}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.85,
        },
        timeout=30,
    )
    reponse.raise_for_status()
    return reponse.json()["choices"][0]["message"]["content"].strip()


def generer_texte_ia(prompt, max_tokens=400):
    """Essaie Groq, puis Gemini, puis DeepSeek dans cet ordre. Retourne
    (texte, erreur) -- texte vaut None si les 3 fournisseurs ont échoué ou
    n'ont pas de clé configurée."""
    fournisseurs = [
        ("Groq", _generer_via_groq),
        ("Gemini", _generer_via_gemini),
        ("DeepSeek", _generer_via_deepseek),
    ]
    aucune_cle = True
    dernieres_erreurs = []
    for nom_fournisseur, fonction in fournisseurs:
        if not _cle_secrete({"Groq": "GROQ_API_KEY", "Gemini": "GEMINI_API_KEY", "DeepSeek": "DEEPSEEK_API_KEY"}[nom_fournisseur]):
            continue
        aucune_cle = False
        try:
            texte = fonction(prompt, max_tokens)
            if texte:
                return texte, None
            dernieres_erreurs.append(f"{nom_fournisseur} : réponse vide")
        except Exception as exc:
            logger.exception(f"Échec génération IA via {nom_fournisseur}, tentative du fournisseur suivant")
            dernieres_erreurs.append(f"{nom_fournisseur} : {exc}")
            continue
    if aucune_cle:
        return None, "Aucune clé API IA n'est configurée (GROQ_API_KEY / GEMINI_API_KEY / DEEPSEEK_API_KEY)."
    # 🔎 Détail technique inclus volontairement -- cet écran est réservé au
    # marchand/admin (pas affiché aux clients), donc utile pour diagnostiquer
    # une clé invalide, un quota dépassé ou un modèle retiré par le fournisseur.
    return None, "Les fournisseurs IA configurés ont échoué : " + " | ".join(dernieres_erreurs)


# ====================== 3ter. GÉNÉRATEUR DE VISUEL RÉSEAUX SOCIAUX (module premium) ======================
# 🖼️ Compose un visuel premium (format portrait 4:5, optimisé Instagram/
# Facebook) à partir de la photo d'un article + son nom + une description
# marketing + son prix + une signature boutique élégante, que le marchand
# peut ensuite télécharger et publier lui-même sur ses réseaux.
# Nécessite Pillow + numpy (déjà utilisés ailleurs dans l'app).

def _police_visuel(taille, style="sans_bold"):
    """Charge une police avec repli en cascade. `style` : "serif_bold" /
    "serif" (titraille chic) ou "sans_bold" / "sans" (texte courant).
    Essaie d'abord les polices système DejaVu (présentes sur la plupart des
    serveurs Linux), puis celles embarquées par matplotlib si le paquet est
    installé, et ne retombe QUE EN DERNIER RECOURS sur la police par défaut
    de Pillow -- mais en lui demandant explicitement `taille` (Pillow >= 10.1
    sait la redimensionner nettement ; l'ancien repli, une bitmap minuscule
    figée à ~10px, est ce qui rendait le texte illisible sur certains
    serveurs où aucune police système n'est présente)."""
    from PIL import ImageFont
    chemins_par_style = {
        "serif_bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSerif-Bold.ttf",
        ],
        "serif": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
        ],
        "sans_bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        ],
        "sans": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        ],
    }
    for chemin in chemins_par_style.get(style, chemins_par_style["sans_bold"]):
        try:
            return ImageFont.truetype(chemin, taille)
        except Exception:
            continue
    # 🔒 Repli n°2 : polices embarquées avec matplotlib (souvent déjà présent
    # comme dépendance de plotly/pandas dans l'environnement Python lui-même,
    # donc indépendant des paquets système de la machine).
    try:
        import matplotlib
        base = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
        nom_fichier = {
            "serif_bold": "DejaVuSerif-Bold.ttf", "serif": "DejaVuSerif.ttf",
            "sans_bold": "DejaVuSans-Bold.ttf", "sans": "DejaVuSans.ttf",
        }.get(style, "DejaVuSans-Bold.ttf")
        return ImageFont.truetype(os.path.join(base, nom_fichier), taille)
    except Exception:
        pass
    # 🔒 Repli final : police vectorielle intégrée à Pillow -- toujours
    # disponible, quel que soit le serveur, et correctement mise à l'échelle.
    try:
        return ImageFont.load_default(size=taille)
    except TypeError:
        return ImageFont.load_default()  # Pillow < 10.1 : pas de paramètre size


def _texte_espace(dessin, centre_x, y, texte, font, fill, suivi=4):
    """Dessine `texte` centré horizontalement sur `centre_x`, lettre par
    lettre, avec un espacement `suivi` (tracking) -- effet signature/logo
    de maison de luxe, impossible à obtenir avec draw.text() seul."""
    largeurs = [dessin.textlength(c, font=font) for c in texte]
    largeur_totale = sum(largeurs) + suivi * (len(texte) - 1)
    x = centre_x - largeur_totale / 2
    for caractere, largeur in zip(texte, largeurs):
        dessin.text((x, y), caractere, font=font, fill=fill)
        x += largeur + suivi


def _reduire_texte(dessin, texte, font, largeur_max):
    """Tronque `texte` avec une ellipse si sa largeur dépasse `largeur_max`."""
    if dessin.textlength(texte, font=font) <= largeur_max:
        return texte
    while texte and dessin.textlength(texte + "…", font=font) > largeur_max:
        texte = texte[:-1]
    return texte + "…"


def _plier_texte(dessin, texte, font, largeur_max, max_lignes=2):
    """Découpe `texte` en `max_lignes` lignes maximum tenant dans
    `largeur_max`, avec ellipse sur la dernière ligne si le texte déborde."""
    mots = texte.split()
    lignes, ligne_actuelle = [], ""
    for mot in mots:
        essai = f"{ligne_actuelle} {mot}".strip()
        if dessin.textlength(essai, font=font) <= largeur_max:
            ligne_actuelle = essai
        else:
            if ligne_actuelle:
                lignes.append(ligne_actuelle)
            ligne_actuelle = mot
        if len(lignes) == max_lignes:
            break
    if ligne_actuelle and len(lignes) < max_lignes:
        lignes.append(ligne_actuelle)
    if len(lignes) == max_lignes and len(" ".join(lignes)) < len(texte):
        lignes[-1] = _reduire_texte(dessin, lignes[-1], font, largeur_max)
    return lignes


def _arrondir_coins_haut(image, rayon):
    """Retourne `image` (RGB) convertie en RGBA avec les deux coins hauts
    arrondis -- pour que la photo produit s'intègre en douceur au cadre."""
    from PIL import Image, ImageDraw
    largeur, hauteur = image.size
    masque = Image.new("L", (largeur, hauteur), 255)
    d = ImageDraw.Draw(masque)
    d.pieslice([0, 0, rayon * 2, rayon * 2], 180, 270, fill=0)
    d.rectangle([0, 0, rayon, rayon], fill=0)
    d.pieslice([largeur - rayon * 2, 0, largeur, rayon * 2], 270, 360, fill=0)
    d.rectangle([largeur - rayon, 0, largeur, rayon], fill=0)
    d.rectangle([0, 0, largeur, rayon], fill=255)
    d.pieslice([0, 0, rayon * 2, rayon * 2], 180, 270, fill=255)
    d.pieslice([largeur - rayon * 2, 0, largeur, rayon * 2], 270, 360, fill=255)
    d.rectangle([rayon, 0, largeur - rayon, rayon], fill=255)
    image_rgba = image.convert("RGBA")
    image_rgba.putalpha(masque)
    return image_rgba


def _assombrir_vignette(image, intensite=0.30):
    """Applique une légère vignette (assombrissement des bords) sur la
    photo produit pour un rendu plus cinématographique -- calcul vectorisé
    avec numpy, donc négligeable en temps de génération."""
    import numpy as np
    largeur, hauteur = image.size
    yy, xx = np.mgrid[0:hauteur, 0:largeur]
    cx, cy = largeur / 2, hauteur / 2
    distance = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
    facteur = 1 - intensite * np.clip(distance - 0.55, 0, 1) / 0.45
    facteur = np.clip(facteur, 1 - intensite, 1)
    pixels = np.asarray(image.convert("RGB")).astype("float32")
    pixels *= facteur[..., None]
    from PIL import Image
    return Image.fromarray(pixels.astype("uint8"), mode="RGB")


def _degrade_horizontal(largeur, hauteur, couleur_a, couleur_b):
    """Petit dégradé linéaire horizontal (utilisé pour le ruban d'accroche
    doré façon shimmer, cohérent avec le badge Aura Luxe du site)."""
    from PIL import Image
    import numpy as np
    t = np.linspace(0, 1, largeur)
    ligne = (np.array(couleur_a) * (1 - t[:, None]) + np.array(couleur_b) * t[:, None]).astype("uint8")
    bande = np.tile(ligne[:, None, :], (1, hauteur, 1)).transpose(1, 0, 2)
    return Image.fromarray(bande, mode="RGB")


def generer_visuel_produit(url_image_produit, nom_produit, prix, nom_boutique, prix_promo=None,
                            accroche=None, description_marketing=None, couleur_accent=None):
    """Retourne les octets PNG du visuel premium généré, ou (None, message_erreur).
    `accroche` : très courte formule (ex: "NOUVELLE COLLECTION"), affichée en
    ruban doré sur la photo.
    `description_marketing` : phrase marketing complète (ex: générée par
    l'IA), affichée en évidence sous le nom du produit.
    `couleur_accent` (ex: "#2f6fed") reprend la couleur de thème choisie par
    le marchand premium -- doré Destiny par défaut si absente/invalide.

    🔎 Le visuel est composé en interne à une résolution 2x (2160x2700) puis
    réduit à la taille finale (1080x1350) avec un filtre Lanczos : ce
    sur-échantillonnage élimine le crénelage/"dédoublement" des lettres que
    l'on obtient en dessinant du texte fin directement à la résolution
    finale, et donne un rendu net même une fois réaffiché en miniature."""
    try:
        from PIL import Image, ImageDraw
        from io import BytesIO
    except ImportError:
        return None, "Le paquet Pillow n'est pas installé (ajoute \"Pillow\" à requirements.txt)."

    if couleur_accent and re.match(r"^#[0-9a-fA-F]{6}$", couleur_accent):
        accent_rgb = tuple(int(couleur_accent[i:i + 2], 16) for i in (1, 3, 5))
    else:
        accent_rgb = (201, 163, 92)  # doré Destiny par défaut
    accent_clair_rgb = tuple(min(255, c + 35) for c in accent_rgb)

    SCALE = 2  # sur-échantillonnage -- voir docstring
    BASE_LARGEUR, BASE_HAUTEUR = 1080, 1350  # format 4:5 final -- optimisé Instagram/Facebook
    LARGEUR, HAUTEUR = BASE_LARGEUR * SCALE, BASE_HAUTEUR * SCALE
    MARGE_CADRE = 26 * SCALE

    toile = Image.new("RGB", (LARGEUR, HAUTEUR), color=(11, 11, 13))
    dessin = ImageDraw.Draw(toile)

    # ---- Photo produit : couvre le haut du visuel, coins hauts arrondis + vignette ----
    zone_photo_h = int(HAUTEUR * 0.58)
    if url_image_produit:
        try:
            reponse = requests.get(url_image_produit, timeout=15)
            photo = Image.open(BytesIO(reponse.content)).convert("RGB")
            ratio = max(LARGEUR / photo.width, zone_photo_h / photo.height)
            nouvelle_taille = (int(photo.width * ratio), int(photo.height * ratio))
            photo = photo.resize(nouvelle_taille)
            gauche = (photo.width - LARGEUR) // 2
            haut = (photo.height - zone_photo_h) // 2
            photo = photo.crop((gauche, haut, gauche + LARGEUR, haut + zone_photo_h))
            photo = _assombrir_vignette(photo, intensite=0.28)
            photo_arrondie = _arrondir_coins_haut(photo, rayon=28 * SCALE)
            toile.paste(photo_arrondie, (0, 0), photo_arrondie)
        except Exception:
            pass  # pas de photo -> on garde juste le fond sombre, pas bloquant

    # Fondu doux en bas de la photo pour une transition élégante vers le panneau texte
    import numpy as _np
    fondu_h = 90 * SCALE
    alpha_colonne = _np.linspace(0, 235, fondu_h).astype("uint8")          # 0 (haut, transparent) -> 235 (bas, quasi opaque)
    masque_fondu_img = Image.fromarray(_np.tile(alpha_colonne[:, None], (1, LARGEUR)), mode="L")
    noir = Image.new("RGB", (LARGEUR, fondu_h), (11, 11, 13))
    toile.paste(noir, (0, zone_photo_h - fondu_h), masque_fondu_img)

    # ---- Ruban d'accroche doré (dégradé shimmer) en haut de la photo ----
    if accroche and accroche.strip():
        hauteur_ruban = 84 * SCALE
        ruban = _degrade_horizontal(LARGEUR, hauteur_ruban, accent_clair_rgb, accent_rgb)
        toile.paste(ruban, (0, 0))
        dessin.text((MARGE_CADRE + 16 * SCALE, 28 * SCALE), accroche.strip().upper()[:44],
                    font=_police_visuel(36 * SCALE, "sans_bold"), fill=(22, 21, 26))

    # ---- Trait fin doré séparant photo et panneau ----
    dessin.rectangle([0, zone_photo_h, LARGEUR, zone_photo_h + 4 * SCALE], fill=accent_rgb)

    # ---- Préparation du contenu texte (polices grand format, lisibles même en miniature) ----
    marge = 64 * SCALE
    largeur_texte = LARGEUR - 2 * marge

    nom_font = _police_visuel(64 * SCALE, "serif_bold")
    desc_font = _police_visuel(32 * SCALE, "sans")
    prix_font = _police_visuel(60 * SCALE, "serif_bold")
    prix_barre_font = _police_visuel(32 * SCALE, "sans")
    signature_font = _police_visuel(32 * SCALE, "serif_bold")

    nom_affiche = _reduire_texte(dessin, (nom_produit or "").strip(), nom_font, largeur_texte)
    lignes_desc = (
        _plier_texte(dessin, description_marketing.strip(), desc_font, largeur_texte, max_lignes=2)
        if description_marketing and description_marketing.strip() else []
    )
    signature = (nom_boutique or "").strip().upper()[:36]

    # ---- Calcul des hauteurs pour centrer le bloc verticalement dans le panneau
    #      (évite le grand vide en bas obtenu quand le contenu est simplement
    #      empilé depuis le haut sans tenir compte de l'espace disponible) ----
    interligne_desc = int(32 * SCALE * 1.35)
    h_titre = int(64 * SCALE * 1.2)
    h_desc = len(lignes_desc) * interligne_desc
    h_prix = int(60 * SCALE * 1.55)
    h_signature = int(32 * SCALE * 1.3)
    espace_titre_desc = int(20 * SCALE) if lignes_desc else 0
    espace_avant_prix = int(34 * SCALE)
    espace_avant_signature = int(48 * SCALE)

    hauteur_bloc = h_titre + espace_titre_desc + h_desc + espace_avant_prix + h_prix + espace_avant_signature + h_signature
    haut_panneau = zone_photo_h + 8 * SCALE
    bas_panneau = HAUTEUR - 50 * SCALE
    y = haut_panneau + max(30 * SCALE, (bas_panneau - haut_panneau - hauteur_bloc) // 2)

    # ---- Nom du produit ----
    dessin.text((marge, y), nom_affiche, font=nom_font, fill=(240, 236, 227))
    y += h_titre + espace_titre_desc

    # ---- Description marketing ----
    for ligne in lignes_desc:
        dessin.text((marge, y), ligne, font=desc_font, fill=(199, 192, 176))
        y += interligne_desc
    y += espace_avant_prix

    # ---- Prix (badge promo doré si applicable) ----
    if prix_promo and float(prix_promo) > 0 and float(prix_promo) < float(prix or 0):
        texte_prix = f"{int(prix_promo)} FCFA"
        texte_ancien = f"{int(prix)} FCFA"
        largeur_prix = dessin.textlength(texte_prix, font=prix_font)
        dessin.rounded_rectangle(
            [marge - 20 * SCALE, y - 14 * SCALE, marge + largeur_prix + 40 * SCALE, y + h_prix - 14 * SCALE],
            radius=16 * SCALE, fill=accent_rgb
        )
        dessin.text((marge, y), texte_prix, font=prix_font, fill=(22, 21, 26))
        dessin.text((marge + largeur_prix + 56 * SCALE, y + 18 * SCALE), texte_ancien,
                    font=prix_barre_font, fill=(140, 134, 122))
    else:
        dessin.text((marge, y), f"{int(prix or 0)} FCFA", font=prix_font, fill=(240, 236, 227))
    y += h_prix + espace_avant_signature

    # ---- Signature boutique (façon maison de luxe : capitales espacées, encadrées de traits fins) ----
    if signature:
        centre_x = LARGEUR // 2
        largeur_signature = sum(dessin.textlength(c, font=signature_font) for c in signature) + 5 * SCALE * (len(signature) - 1)
        demi = largeur_signature / 2
        y_ligne = y + h_signature // 2
        dessin.line([(marge, y_ligne), (centre_x - demi - 26 * SCALE, y_ligne)], fill=accent_rgb, width=2)
        dessin.line([(centre_x + demi + 26 * SCALE, y_ligne), (LARGEUR - marge, y_ligne)], fill=accent_rgb, width=2)
        _texte_espace(dessin, centre_x, y, signature, signature_font, accent_rgb, suivi=5 * SCALE)

    # ---- Fin liseré doré tout autour du visuel (cadre premium) ----
    dessin.rectangle([MARGE_CADRE // 2, MARGE_CADRE // 2, LARGEUR - MARGE_CADRE // 2, HAUTEUR - MARGE_CADRE // 2],
                      outline=accent_rgb, width=2 * SCALE)

    # ---- Réduction finale (2x -> 1x) : lisse le crénelage, rendu net à toute taille d'affichage ----
    toile_finale = toile.resize((BASE_LARGEUR, BASE_HAUTEUR), Image.LANCZOS)

    tampon = BytesIO()
    toile_finale.save(tampon, format="PNG")
    return tampon.getvalue(), None


# ====================== 4bis. PANIER PERSISTANT (survit à un redéploiement) ======================
# 🔒 FIX : le panier vit normalement dans ss, qui est stocké en
# mémoire côté serveur. Or un redéploiement de l'app (ex: ajout d'un paquet
# dans requirements.txt) redémarre le serveur et efface TOUTE la mémoire de
# TOUTES les sessions en cours -- même chose si le client perd sa connexion
# WiFi/4G un instant. Pour que le panier d'un client ne disparaisse pas dans
# ces cas-là, on le duplique dans l'URL de la page : dès qu'il change, il est
# encodé dans le paramètre ?panier=... . Si le navigateur se reconnecte
# (après un redéploiement ou une coupure réseau), l'app relit ce paramètre et
# reconstruit le panier automatiquement, sans que le client s'en aperçoive.
def _cle_url_boutique(nom):
    # 🔒 Même logique de namespacing que `ss` (voir EtatBoutique) mais pour
    # les paramètres d'URL : "panier"/"favoris" sans suffixe seraient
    # partagés par TOUTES les boutiques dans la même URL/onglet, et
    # réimporteraient le panier d'une boutique dans une autre au moment où
    # ss.cart n'existe pas encore pour la nouvelle boutique.
    return f"{nom}_m{MARCHAND_ID}"


def synchroniser_panier_url():
    try:
        cle = _cle_url_boutique("panier")
        if ss.cart:
            st.query_params[cle] = json.dumps(ss.cart, separators=(",", ":"))
        elif cle in st.query_params:
            del st.query_params[cle]
    except Exception:
        pass  # la persistance du panier est un bonus, jamais bloquant


# ====================== 4ter. FAVORIS PERSISTANTS ======================
# Même principe que le panier ci-dessus : la liste de favoris (identifiants
# d'articles) vit dans ss et est dupliquée dans l'URL
# (?favoris_m<id>=...) pour survivre à un redéploiement ou une coupure
# réseau, sans nécessiter de compte client.
def synchroniser_favoris_url():
    try:
        cle = _cle_url_boutique("favoris")
        if ss.favoris:
            st.query_params[cle] = json.dumps(ss.favoris, separators=(",", ":"))
        elif cle in st.query_params:
            del st.query_params[cle]
    except Exception:
        pass  # la persistance des favoris est un bonus, jamais bloquant


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
@st.cache_data(ttl=20)
def charger_catalogue(marchand_id, _refresh=0):
    reponse = sb.table("catalogue").select("*").eq("marchand_id", marchand_id).execute()
    df = pd.DataFrame(reponse.data)
    for col in ["prix", "prix_promo", "stock"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=20)
def charger_collections(marchand_id, _refresh=0):
    """Toutes les collections du marchand (actives ou non), pour l'admin."""
    reponse = (
        sb.table("collections")
        .select("*")
        .eq("marchand_id", marchand_id)
        .order("created_at", desc=True)
        .execute()
    )
    return reponse.data or []


def collections_actives_non_expirees(collections: list) -> list:
    """Filtre une liste de collections pour ne garder que celles actives et
    pas encore expirées -- effet 'exclusivité' d'Aura Luxe : passé la date,
    la collection disparaît d'elle-même du site, sans action du marchand."""
    maintenant = datetime.now(timezone.utc)
    resultat = []
    for c in collections:
        if not c.get("actif"):
            continue
        expire_le = c.get("expire_le")
        if expire_le:
            try:
                date_expire = datetime.fromisoformat(str(expire_le).replace("Z", "+00:00"))
                if date_expire <= maintenant:
                    continue
            except ValueError:
                pass
        resultat.append(c)
    return resultat


def afficher_compte_a_rebours(date_fin_iso: str, cle: str):
    """Petit compte à rebours JS live (⏳ Termine dans HH:MM:SS) pour une
    Flash Sale -- module Aura Luxe. Ne bloque jamais l'affichage produit si
    la date est invalide : on n'affiche simplement rien."""
    try:
        # validation basique -- si ça plante ici, on ne montre rien plutôt
        # que de casser la carte produit.
        datetime.fromisoformat(str(date_fin_iso).replace("Z", "+00:00"))
    except Exception:
        return
    components.html(
        f"""
        <style>
            /* components.html rend dans un iframe isolé : le CSS de la page
            principale (.aura-flash-badge) ne traverse pas jusqu'ici, donc on
            redéfinit le style localement pour que le badge s'affiche bien. */
            body {{ margin: 0; padding: 0; }}
            .aura-flash-badge {{
                display: inline-flex; align-items: center; gap: 5px;
                background: #2a1810; border: 1px solid #e0703f; color: #ffb27a;
                font-weight: 700; font-size: 0.8rem; padding: 3px 10px; border-radius: 14px;
                font-family: sans-serif; white-space: nowrap;
            }}
        </style>
        <div id="cptdown_{cle}" class="aura-flash-badge">⚡ ...</div>
        <script>
        (function() {{
            const fin = new Date("{date_fin_iso}").getTime();
            const el = document.getElementById("cptdown_{cle}");
            function tick() {{
                const reste = fin - new Date().getTime();
                if (!el) return;
                if (reste <= 0) {{
                    el.innerHTML = "⚡ Offre terminée";
                    return;
                }}
                const h = Math.floor(reste / 3600000);
                const m = Math.floor((reste % 3600000) / 60000);
                const s = Math.floor((reste % 60000) / 1000);
                el.innerHTML = "⏳ Termine dans " + h + "h " + String(m).padStart(2,'0') + "m " + String(s).padStart(2,'0') + "s";
                setTimeout(tick, 1000);
            }}
            tick();
        }})();
        </script>
        """,
        height=40,
    )


@st.cache_data(ttl=20)
def charger_config(marchand_id, _refresh=0):
    # Les réglages spécifiques à CETTE boutique vivent maintenant dans
    # `marchands` (une ligne par marchand) et non plus dans `config`
    # (désormais réservée aux clés globales à la marketplace). On garde
    # les mêmes noms de clés en sortie pour ne rien casser ailleurs dans
    # le code.
    reponse = (
        sb.table("marchands")
        .select(
            "nom_boutique, slogan, logo, whatsapp, email_contact, "
            "seuil_stock_bas, heure_bilan, derniere_alerte_stock_date, "
            "dernier_bilan_date, mot_de_passe_hash, "
            "palier_abonnement, en_vedette, banniere_actif, banniere_titre, "
            "banniere_texte, banniere_code_promo, theme_couleur, banniere_style, "
            "police_titre, logo_animation, badge_style, badge_texte, "
            "vip_offre_actif, vip_offre_titre, vip_offre_texte, vip_offre_code, "
            "delai_relance_panier_h, seuil_stock_urgence"
        )
        .eq("id", marchand_id)
        .execute()
    )
    if not reponse.data:
        return {}
    ligne = reponse.data[0]
    return {
        "nom_boutique": ligne.get("nom_boutique"),
        "slogan": ligne.get("slogan"),
        "logo": ligne.get("logo"),
        "whatsapp": ligne.get("whatsapp"),
        "email_admin": ligne.get("email_contact"),
        "seuil_stock_bas": ligne.get("seuil_stock_bas"),
        "heure_bilan": ligne.get("heure_bilan"),
        "derniere_alerte_stock_date": (
            str(ligne["derniere_alerte_stock_date"]) if ligne.get("derniere_alerte_stock_date") else None
        ),
        "dernier_bilan_date": (
            str(ligne["dernier_bilan_date"]) if ligne.get("dernier_bilan_date") else None
        ),
        "mot_de_passe": ligne.get("mot_de_passe_hash"),
        # 📣 Module Marketing & Pub -- voir section 4bis-marketing plus bas.
        # "palier_abonnement" vaut "standard" ou "premium" et n'est modifiable
        # QUE depuis le Super Admin (1_Super_Admin.py), jamais par le marchand
        # lui-même : c'est ce qui garantit que le module reste payant.
        "palier_abonnement": ligne.get("palier_abonnement") or "standard",
        "en_vedette": bool(ligne.get("en_vedette")),
        "banniere_actif": bool(ligne.get("banniere_actif")),
        "banniere_titre": ligne.get("banniere_titre"),
        "banniere_texte": ligne.get("banniere_texte"),
        "banniere_code_promo": ligne.get("banniere_code_promo"),
        # 🎨 Identité premium (badge + thème couleur/police/animations +
        # style bannière) -- valeurs par défaut = rendu doré Destiny
        # d'origine, sur lequel l'appli retombe automatiquement dès que le
        # mode premium est désactivé (voir boutique_premium()).
        "theme_couleur": ligne.get("theme_couleur") or "#c9a35c",
        "police_titre": ligne.get("police_titre") or "playfair",
        "logo_animation": ligne.get("logo_animation") or "glow",
        "badge_style": ligne.get("badge_style") or "shimmer",
        "badge_texte": ligne.get("badge_texte") or "✨ Aura Luxe",
        "banniere_style": ligne.get("banniere_style") or "classique",
        # 👑 Club VIP
        "vip_offre_actif": bool(ligne.get("vip_offre_actif")),
        "vip_offre_titre": ligne.get("vip_offre_titre"),
        "vip_offre_texte": ligne.get("vip_offre_texte"),
        "vip_offre_code": ligne.get("vip_offre_code"),
        # 🛒 Relance panier abandonné (semi-auto) -- délai en heures après
        # lequel un panier devient "prêt à relancer" ; calculé côté cron
        # (voir scripts/taches_planifiees.py) mais aussi utilisé côté
        # affichage admin pour le tri/badge en temps réel.
        "delai_relance_panier_h": int(ligne.get("delai_relance_panier_h") or 24),
        # ⚡ Preuve sociale : en dessous de ce seuil, on affiche "il ne
        # reste que N !" sur la fiche produit (distinct du seuil d'alerte
        # email admin plus haut, généralement plus bas).
        "seuil_stock_urgence": int(ligne.get("seuil_stock_urgence") or 5),
    }


# 🎨 Palette de thèmes prêts à l'emploi (module Aura Luxe, premium) -- le
# marchand peut aussi choisir "Personnalisé" et prendre sa propre couleur
# via un color picker. "Or Royal" = couleur d'origine Destiny.
THEMES_PRESETS = {
    "Or Royal (défaut)": "#c9a35c",
    "Bleu Professionnel": "#2f6fed",
    "Vert Émeraude": "#1f8a5f",
    "Rose Poudré": "#d88bb1",
    "Argent Élégant": "#9aa4ad",
    "Rouge Bordeaux": "#8a2942",
    "Violet Améthyste": "#7c5cbf",
}

# 🔤 Polices disponibles pour les titres/nom de boutique (module Aura Luxe,
# premium). Toutes déjà importées dans le <style> global, donc le
# changement est instantané, sans rechargement de page. "playfair" =
# police d'origine Destiny.
POLICES_PRESETS = {
    "playfair": ("Playfair Display (défaut, élégant)", "'Playfair Display', serif"),
    "cormorant": ("Cormorant Garamond (classique)", "'Cormorant Garamond', serif"),
    "montserrat": ("Montserrat (moderne)", "'Montserrat', sans-serif"),
    "poppins": ("Poppins (doux)", "'Poppins', sans-serif"),
    "oswald": ("Oswald (impact)", "'Oswald', sans-serif"),
    "raleway": ("Raleway (minimaliste)", "'Raleway', sans-serif"),
    "bebas": ("Bebas Neue (affiche)", "'Bebas Neue', cursive"),
}


def injecter_theme_premium(config: dict):
    """Surcharge les variables CSS de thème (couleur d'accent + police des
    titres) avec les choix du marchand premium (boutons, badges, halo
    héro, titres...). Ne fait rien pour une boutique standard -- elle
    garde le rendu doré / Playfair Display d'origine. C'est ce mécanisme
    qui garantit le retour automatique à l'apparence initiale dès que le
    mode premium est désactivé côté Super Admin."""
    if not boutique_premium(config):
        return
    couleur = config.get("theme_couleur") or "#c9a35c"
    regles = []
    if re.match(r"^#[0-9a-fA-F]{6}$", couleur):
        # Version plus claire de la couleur pour le hover, en éclaircissant
        # chaque canal RVB de 20% vers le blanc.
        r, g, b = (int(couleur[i:i + 2], 16) for i in (1, 3, 5))
        r, g, b = (min(255, int(c + (255 - c) * 0.25)) for c in (r, g, b))
        couleur_claire = f"#{r:02x}{g:02x}{b:02x}"
        regles.append(f"--aura-accent: {couleur};")
        regles.append(f"--aura-accent-clair: {couleur_claire};")
    police_cle = config.get("police_titre") or "playfair"
    if police_cle in POLICES_PRESETS:
        regles.append(f"--aura-font-titre: {POLICES_PRESETS[police_cle][1]};")
    if regles:
        st.markdown(f"<style>:root {{ {' '.join(regles)} }}</style>", unsafe_allow_html=True)


STYLES_BADGE_AURA = {
    "shimmer": "Doré scintillant (défaut)",
    "contour": "Contour lumineux",
    "mat": "Mat professionnel",
    "glace": "Verre givré",
}


def afficher_badge_aura(style="shimmer", texte="✨ Aura Luxe"):
    """Petit badge animé 'Aura Luxe' -- affiché à côté du nom de la
    boutique pour les visiteurs, uniquement si premium. La couleur suit
    automatiquement le thème choisi par le marchand (variables CSS
    --aura-accent), `style` change l'apparence (plein/contour/mat/givré)
    et `texte` permet de personnaliser le libellé affiché."""
    classe_style = f" style-{style}" if style and style != "shimmer" else ""
    st.markdown(
        f'<span class="aura-badge{classe_style}">{html_lib.escape(str(texte or "✨ Aura Luxe"))}</span>',
        unsafe_allow_html=True
    )


def boutique_premium(config: dict) -> bool:
    """La boutique a-t-elle le module Marketing & Pub débloqué ? Ce champ
    n'est modifiable QUE depuis le Super Admin (côté marchand, aucun bouton
    ne permet de le changer) -- c'est ce qui garantit que le module reste
    payant et activé manuellement après paiement."""
    return (config.get("palier_abonnement") or "standard") == "premium"


@st.cache_data(ttl=30)
def charger_tous_avis_approuves(marchand_id, _refresh=0):
    """Un SEUL appel réseau vers Supabase pour récupérer tous les avis
    approuvés. Avant, chaque produit de la grille refaisait ce même appel
    (SELECT * sur toute la table) rien que pour filtrer différemment en
    Python ensuite -- avec 12 produits sur la page, ça faisait 12
    aller-retours réseau redondants, une cause majeure de latence perçue
    (surtout en mobile où chaque round-trip pèse plus lourd)."""
    reponse = sb.table("avis").select("*").eq("statut", "approuve").eq("marchand_id", marchand_id).execute()
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
def charger_avis_moyennes(marchand_id, _refresh=0):
    par_article = {}
    for row in charger_tous_avis_approuves(marchand_id, _refresh):
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


# ====================== 6ter. PREUVE SOCIALE / URGENCE ======================
@st.cache_data(ttl=60)
def charger_vues_articles_jour(marchand_id, _refresh=0):
    """Nombre de vues aujourd'hui par article (clé = nom normalisé), pour le
    badge « X personnes ont vu cet article aujourd'hui »."""
    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    try:
        reponse = (
            sb.table("vues_articles")
            .select("article_nom, compteur")
            .eq("marchand_id", marchand_id)
            .eq("jour", aujourdhui)
            .execute()
        )
    except Exception:
        return {}
    return {normaliser(r.get("article_nom")): int(r.get("compteur") or 0) for r in (reponse.data or [])}


def enregistrer_vue_article(nom_article, identifiant_produit):
    """Incrémente le compteur de vues du jour pour cet article, au plus une
    fois par session (via throttle) pour éviter qu'un rechargement de page
    ne gonfle artificiellement le chiffre affiché aux autres visiteurs."""
    if not throttle(f"vue_{identifiant_produit}", 3600):
        return
    try:
        sb.rpc("enregistrer_vue_article", {
            "p_article": nom_article,
            "p_marchand_id": MARCHAND_ID
        }).execute()
    except Exception:
        pass  # jamais bloquant : la preuve sociale est un bonus, pas une fonction critique


@st.cache_data(ttl=300)
def charger_meilleure_vente_du_mois(marchand_id, _refresh=0):
    """Nom (normalisé) de l'article le plus commandé depuis le 1er du mois
    en cours, pour le bandeau « 🔥 Meilleure vente » auto-attribué."""
    debut_mois = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        reponse = (
            sb.table("commandes")
            .select("articles")
            .eq("marchand_id", marchand_id)
            .gte("date", debut_mois.isoformat())
            .execute()
        )
    except Exception:
        return None
    compteur = {}
    for cmd in (reponse.data or []):
        for art in (cmd.get("articles") or []):
            cle = normaliser(art.get("nom", ""))
            if cle:
                compteur[cle] = compteur.get(cle, 0) + (art.get("quantite") or 0)
    if not compteur:
        return None
    return max(compteur, key=compteur.get)


if "refresh_token" not in ss:
    ss.refresh_token = 0
if "cart" not in ss:
    ss.cart = []
    # 🔄 Tentative de restauration du panier depuis l'URL (voir
    # synchroniser_panier_url ci-dessus) -- couvre le cas d'un redéploiement
    # ou d'une reconnexion réseau pendant que le client faisait ses achats.
    panier_url = st.query_params.get(_cle_url_boutique("panier"))
    if panier_url:
        try:
            panier_restaure = json.loads(panier_url)
            if isinstance(panier_restaure, list):
                ss.cart = panier_restaure
        except Exception:
            pass
if "favoris" not in ss:
    ss.favoris = []
    # 🔄 Restauration des favoris depuis l'URL (voir synchroniser_favoris_url
    # ci-dessus), même logique que pour le panier.
    favoris_url = st.query_params.get(_cle_url_boutique("favoris"))
    if favoris_url:
        try:
            favoris_restaures = json.loads(favoris_url)
            if isinstance(favoris_restaures, list):
                ss.favoris = favoris_restaures
        except Exception:
            pass
if "dernier_panier_signature" not in ss:
    ss.dernier_panier_signature = None
if "message_toast" not in ss:
    ss.message_toast = None
if "icone_toast" not in ss:
    ss.icone_toast = "✅"
if "jouer_son" not in ss:
    ss.jouer_son = False
if "acces_choisi" not in ss:
    ss.acces_choisi = None

# 🔔 st.toast() et le son ne s'affichaient jamais : ils étaient déclenchés
# juste avant st.rerun(), qui interrompt le script et jette l'écran en cours
# avant que le navigateur n'ait eu le temps de les afficher/jouer. On les
# stocke donc dans la session et on les affiche ici, tout en haut du script,
# une fois que le rerun est terminé et que la nouvelle page est stable.
if ss.message_toast:
    st.toast(ss.message_toast, icon=ss.icone_toast)
    ss.message_toast = None
if ss.jouer_son:
    jouer_son_ajout()
    ss.jouer_son = False


def forcer_rafraichissement():
    ss.refresh_token += 1
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
    if ss.dernier_panier_signature == signature:
        return  # rien de changé depuis la dernière sauvegarde, on évite une écriture inutile

    # 🐛 CORRECTIF : passait avant par sb.table(...).insert/update() avec la
    # clé anonyme -- très probablement bloqué en silence par le RLS (le
    # except: pass ci-dessous avalait l'erreur), exactement comme pour
    # "alertesstock" avant sa migration vers une fonction RPC. On applique
    # ici le même remède : passer par une fonction RPC SECURITY DEFINER
    # (voir correctif_avis_paniers.sql -- "enregistrer_panier_abandonne").
    try:
        sb.rpc("enregistrer_panier_abandonne", {
            "p_telephone": tel,
            "p_client_nom": nom,
            "p_articles": [{"nom": a["nom"], "prix": a["prix"], "quantite": a["quantite"]} for a in articles],
            "p_total": total,
            "p_marchand_id": MARCHAND_ID
        }).execute()
        ss.dernier_panier_signature = signature
    except Exception:
        pass  # la sauvegarde du panier abandonné est un bonus, jamais bloquant


def marquer_panier_converti(tel):
    tel = (tel or "").strip()
    if not tel:
        return
    try:
        sb.rpc("marquer_panier_converti", {
            "p_telephone": tel,
            "p_marchand_id": MARCHAND_ID
        }).execute()
    except Exception:
        pass


# ====================== 6. EMAIL (Gmail SMTP, avec repli journalisé) ======================
def envoyer_notification_commande(id_commande, client_nom, tel, articles, total, introuvables):
    nom_boutique_actuel = charger_config(MARCHAND_ID, ss.refresh_token).get(
        "nom_boutique", "notre boutique"
    )
    corps = f"Nouvelle commande reçue sur {nom_boutique_actuel} !\n\n"
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
            config = charger_config(MARCHAND_ID, ss.refresh_token)
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
        reponse = (
            sb_bg.table("alertesstock")
            .select("*")
            .eq("article", nom_article)
            .eq("statut", "en_attente")
            .eq("marchand_id", MARCHAND_ID)
            .execute()
        )
    except Exception:
        return
    nom_boutique_actuel = charger_config(MARCHAND_ID, ss.refresh_token).get("nom_boutique", "notre boutique")
    for alerte in (reponse.data or []):
        if alerte.get("contact_type") == "email":
            nom_client_alerte = (alerte.get("nom_client") or "").strip()
            salutation = f"Bonjour {nom_client_alerte}," if nom_client_alerte else "Bonjour,"
            corps = (
                f"{salutation}\n\nBonne nouvelle ! L'article \"{nom_article}\" est de nouveau disponible "
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
            get_admin_client().table("marchands").update(
                {"derniere_alerte_stock_date": aujourdhui}
            ).eq("id", MARCHAND_ID).execute()
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
        reponse = sb_bg.table("commandes").select("*").gte("date", debut_jour).eq("marchand_id", MARCHAND_ID).execute()
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
            get_admin_client().table("marchands").update(
                {"dernier_bilan_date": aujourdhui}
            ).eq("id", MARCHAND_ID).execute()
        except Exception:
            pass


# ====================== 7. INTERFACE PUBLIQUE ======================
config = charger_config(MARCHAND_ID, ss.refresh_token)
df_catalogue = charger_catalogue(MARCHAND_ID, ss.refresh_token)
avis_moyennes = charger_avis_moyennes(MARCHAND_ID, ss.refresh_token)
avis_par_article = indexer_avis_par_article(charger_tous_avis_approuves(MARCHAND_ID, ss.refresh_token))

# 🔔 Vérifications silencieuses (n'affichent rien, ne bloquent jamais la
# page) -- envoient au plus un email par jour chacune, dès que quelqu'un
# charge l'app après les conditions requises.
try:
    verifier_alerte_stock_bas(df_catalogue, config)
    verifier_bilan_quotidien(config)
except Exception:
    pass

NOM_BOUTIQUE = html_lib.escape(config.get("nom_boutique") or "Destiny Luxury Collection")
SLOGAN_BOUTIQUE = html_lib.escape(config.get("slogan") or "Élégance • Exclusivité • Luxe")
LOGO_URL = config.get("logo") or ""
LOGO_SUR = LOGO_URL if re.match(r"^https?://", str(LOGO_URL).strip(), re.IGNORECASE) else ""
WHATSAPP = re.sub(r"\D", "", str(config.get("whatsapp") or ""))

# 🎨 Thème premium (couleur d'accent + police des titres) -- injecté ici,
# AVANT le branchement client/admin ci-dessous, pour que les écrans de
# connexion admin reflètent eux aussi l'identité de la boutique (et pas
# seulement la vitrine client). Ne fait rien pour une boutique standard.
injecter_theme_premium(config)

# 🔒 FIX : l'admin n'apparaît plus comme un onglet visible par tous les
# visiteurs. Seule une personne connaissant l'URL secrète
# "https://tonapp.streamlit.app/?admin=1" voit l'interface de connexion
# admin -- les clients normaux ne voient que la boutique.
mode_admin = st.query_params.get("admin") == "1"

# 🔀 Si un visiteur arrivé sur l'URL secrète ?admin=1 a choisi "client" sur
# l'écran d'accueil ci-dessous, on le renvoie directement vers la boutique
# (sans avoir à retirer le paramètre d'URL).
if mode_admin and not ss.admin_connecte and ss.acces_choisi == "client":
    mode_admin = False

if not mode_admin:
    # 🔄 Rafraîchissement automatique et silencieux de la boutique (toutes
    # les 20 secondes) : dès que l'admin enregistre un changement (prix,
    # stock, nom, logo...), les clients déjà en train de naviguer le voient
    # apparaître tout seul, sans avoir à recharger la page. On ne l'active
    # PAS côté admin pour ne pas interrompre la saisie des formulaires.
    if AUTOREFRESH_DISPONIBLE:
        st_autorefresh(interval=20000, key="rafraichissement_boutique")

    afficher_hero(LOGO_SUR, NOM_BOUTIQUE, SLOGAN_BOUTIQUE, animation_logo=config.get("logo_animation") or "glow")

    if boutique_premium(config):
        st.markdown('<div style="text-align:center; margin-top:-12px; margin-bottom:14px;">', unsafe_allow_html=True)
        afficher_badge_aura(style=config.get("badge_style") or "shimmer", texte=config.get("badge_texte") or "✨ Aura Luxe")
        st.markdown('</div>', unsafe_allow_html=True)

    # 📣 Bannière promo (module Marketing & Pub, premium uniquement) --
    # même si les champs restent en base pour une boutique repassée en
    # standard, on ne l'affiche que si la boutique est ENCORE premium.
    if boutique_premium(config) and config.get("banniere_actif") and config.get("banniere_titre"):
        code_html = (
            f'<span class="destiny-promo-badge">Code : {html_lib.escape(config.get("banniere_code_promo"))}</span>'
            if config.get("banniere_code_promo") else ""
        )
        classe_neon = " aura-banniere-neon" if config.get("banniere_style") == "neon" else ""
        st.markdown(
            f'<div class="{classe_neon.strip()}" style="border:1px solid var(--aura-accent); border-radius:12px; padding:14px 18px; '
            f'margin-bottom:18px; background:rgba(201,163,92,0.08); text-align:center;">'
            f'<div style="color:#eae4d8; font-weight:700; font-size:1.1rem;">'
            f'{html_lib.escape(config.get("banniere_titre") or "")}</div>'
            f'<div style="color:#c9b98f; margin-top:4px;">{html_lib.escape(config.get("banniere_texte") or "")}</div>'
            f'<div style="margin-top:8px;">{code_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with st.container():
        if df_catalogue.empty:
            st.info("Le catalogue est vide pour le moment.")
        else:
            recherche = st.text_input("🔍 Rechercher un article")
            categories = ["Toutes"] + sorted(df_catalogue["categorie"].dropna().unique().tolist())
            categorie_choisie = st.selectbox("Catégorie", categories)

            # ❤️ Favoris -- permet au client de retrouver en un clic les
            # articles qu'il a marqués comme favoris, sans avoir à les
            # rechercher dans tout le catalogue.
            favoris_uniquement = st.checkbox(
                f"❤️ Afficher uniquement mes favoris ({len(ss.favoris)})",
                disabled=not ss.favoris
            )

            df_affiche = df_catalogue.copy()
            if recherche:
                df_affiche = df_affiche[df_affiche["nom"].str.contains(recherche, case=False, na=False)]
            if categorie_choisie != "Toutes":
                df_affiche = df_affiche[df_affiche["categorie"] == categorie_choisie]
            if favoris_uniquement:
                df_affiche = df_affiche[
                    df_affiche.apply(
                        lambda r: normaliser(r.get("id") or r.get("nom")) in ss.favoris,
                        axis=1
                    )
                ]

            # ⭐ Collections temporaires (module Aura Luxe, premium uniquement)
            # -- une collection expirée disparaît automatiquement du filtre,
            # sans aucune action du marchand.
            if boutique_premium(config):
                collections_dispo = collections_actives_non_expirees(
                    charger_collections(MARCHAND_ID, ss.refresh_token)
                )
                if collections_dispo:
                    noms_collections = {c["nom"]: c["id"] for c in collections_dispo}
                    collection_choisie = st.selectbox(
                        "⭐ Collection", ["Toutes"] + list(noms_collections.keys())
                    )
                    if collection_choisie != "Toutes":
                        df_affiche = df_affiche[df_affiche["collection_id"] == noms_collections[collection_choisie]]

            # ⚡ Preuve sociale / urgence -- chargés une seule fois pour toute
            # la grille (pas par produit) pour limiter les appels réseau.
            vues_du_jour = charger_vues_articles_jour(MARCHAND_ID, ss.refresh_token)
            meilleure_vente = charger_meilleure_vente_du_mois(MARCHAND_ID, ss.refresh_token)
            seuil_urgence_stock = int(config.get("seuil_stock_urgence", 5) or 5)

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

                    enregistrer_vue_article(str(row["nom"]).strip(), identifiant_produit)

                    badge_meilleure_vente = (
                        '<div class="destiny-promo-badge" style="display:inline-block; margin-bottom:6px;">🔥 Meilleure vente du mois</div>'
                        if meilleure_vente and identifiant_produit == meilleure_vente
                        else ""
                    )
                    st.markdown(
                        f'{badge_meilleure_vente}<div class="destiny-nom-produit">{nom_affiche}</div>',
                        unsafe_allow_html=True
                    )

                    vues_jour_produit = vues_du_jour.get(identifiant_produit, 0)
                    if vues_jour_produit >= 5:
                        st.caption(f"👀 {vues_jour_produit} personne(s) ont vu cet article aujourd'hui")

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
                        # ⚡ Flash Sale (module Aura Luxe, premium uniquement) --
                        # un compte à rebours live si une date de fin est définie.
                        if boutique_premium(config) and row.get("promo_expire_le"):
                            afficher_compte_a_rebours(str(row["promo_expire_le"]), cle=f"flash_{idx}")
                    else:
                        st.markdown(f'<span class="destiny-prix-normal">{int(prix)} FCFA</span>', unsafe_allow_html=True)

                    if row.get("description"):
                        with st.expander("📝 Description"):
                            st.write(str(row["description"]))

                    # 🎨 Fiche produit épurée : favoris + stock + achat regroupés
                    # dans une seule fenêtre dépliante au lieu de s'empiler en
                    # boutons bruts sous le prix -- rend la grille beaucoup
                    # plus lisible sur mobile (moins de défilement par carte).
                    with st.expander("🛍️ Détails & achat", expanded=not en_rupture):
                        est_favori = identifiant_produit in ss.favoris
                        if st.button(
                            "❤️ Retirer des favoris" if est_favori else "🤍 Ajouter aux favoris",
                            key=f"favori_{idx}"
                        ):
                            if est_favori:
                                ss.favoris.remove(identifiant_produit)
                            else:
                                ss.favoris.append(identifiant_produit)
                            synchroniser_favoris_url()
                            st.rerun()

                        if en_rupture:
                            st.error("Rupture de stock")
                            bouton_partager(
                                str(row["nom"]),
                                f"Découvre {row['nom']} chez {NOM_BOUTIQUE}",
                                MARCHAND_SLUG, identifiant_produit, cle=f"partage_{idx}"
                            )
                            st.caption("🔔 Me prévenir quand disponible")
                            nom_alerte = st.text_input("Votre nom", key=f"alerte_nom_{idx}")
                            contact = st.text_input("Email ou téléphone", key=f"alerte_{idx}")
                            if st.button("M'alerter", key=f"btn_alerte_{idx}"):
                                if not nom_alerte.strip() or not contact.strip():
                                    st.warning("Merci de renseigner votre nom et un email ou un téléphone.")
                                elif not throttle(f"alerte_{identifiant_produit}", 15):
                                    st.warning("Merci de patienter avant de retenter.")
                                else:
                                    # 🆕 Passe par une fonction RPC (creer_alerte_stock) plutôt
                                    # qu'un insert direct : la policy RLS sur "alertesstock" ne
                                    # permettait pas l'insertion anonyme (erreur 401 / 42501),
                                    # et pour une marketplace multi-marchands on veut que le
                                    # marchand_id et le statut soient validés côté serveur plutôt
                                    # que fournis tels quels par le client.
                                    try:
                                        sb.rpc("creer_alerte_stock", {
                                            "p_nom": nom_alerte.strip(),
                                            "p_article": str(row["nom"]),
                                            "p_contact_type": "email" if "@" in contact else "telephone",
                                            "p_contact": contact.strip(),
                                            "p_marchand_id": MARCHAND_ID
                                        }).execute()
                                        st.success("Inscription enregistrée !")
                                    except Exception:
                                        st.error("Une erreur est survenue, merci de réessayer.")
                        else:
                            if 0 < stock <= seuil_urgence_stock:
                                st.warning(f"⚡ Il ne reste que {stock} en stock !")
                            options_taille = [t.strip() for t in str(row.get("tailles") or "").split(",") if t.strip()]
                            options_couleur = [c.strip() for c in str(row.get("couleurs") or "").split(",") if c.strip()]
                            taille_choisie = st.selectbox("Taille", options_taille, key=f"taille_{idx}") if options_taille else ""
                            couleur_choisie = st.selectbox("Couleur", options_couleur, key=f"couleur_{idx}") if options_couleur else ""

                            col_panier, col_partager = st.columns([3, 1])
                            with col_panier:
                                if st.button("🛒 Ajouter au panier", key=f"add_{idx}"):
                                    existant = next(
                                        (a for a in ss.cart
                                         if a["nom"] == row["nom"] and a.get("taille") == taille_choisie
                                         and a.get("couleur") == couleur_choisie),
                                        None
                                    )
                                    if existant:
                                        existant["quantite"] += 1
                                    else:
                                        ss.cart.append({
                                            "produit_id": str(row.get("id") or ""),
                                            "nom": row["nom"],
                                            "prix": float(prix_promo if en_promo else prix),
                                            "taille": taille_choisie,
                                            "couleur": couleur_choisie,
                                            "quantite": 1
                                        })
                                    ss.message_toast = f"{nom_affiche} ajouté au panier !"
                                    ss.icone_toast = "🛍️"
                                    ss.jouer_son = True
                                    synchroniser_panier_url()
                                    st.rerun()
                            with col_partager:
                                bouton_partager(
                                    str(row["nom"]),
                                    f"Découvre {row['nom']} chez {NOM_BOUTIQUE} — "
                                    f"{int(prix_promo if en_promo else prix)} FCFA",
                                    MARCHAND_SLUG, identifiant_produit, cle=f"partage_{idx}"
                                )

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
                                elif not throttle(f"avis_{identifiant_produit}", 15):
                                    st.warning("Merci de patienter avant de renvoyer un avis.")
                                else:
                                    # 🐛 CORRECTIF : p_marchand_id manquait ici -- l'avis
                                    # était bien enregistré côté Supabase, mais sans
                                    # marchand_id (ou avec la mauvaise valeur), donc il
                                    # n'apparaissait jamais dans l'onglet Avis de l'admin
                                    # (qui filtre par marchand_id). Voir aussi la fonction
                                    # SQL "laisser_avis" à mettre à jour en conséquence.
                                    #
                                    # 🐛 CORRECTIF 2 : le try/except manquait ici -- c'était
                                    # le seul appel RPC d'écriture du fichier sans gestion
                                    # d'erreur. Une panne côté fonction SQL (ex: contrainte
                                    # NOT NULL sur "id") remontait donc comme une exception
                                    # non interceptée -- rien d'affiché au client, tout part
                                    # uniquement dans les logs serveur.
                                    try:
                                        resultat = sb.rpc("laisser_avis", {
                                            "p_article_id": identifiant_produit,
                                            "p_article_nom": str(row["nom"]),
                                            "p_client_nom": nom_avis.strip(),
                                            "p_note": int(note_avis),
                                            "p_commentaire": commentaire_avis.strip(),
                                            "p_marchand_id": MARCHAND_ID
                                        }).execute()
                                    except Exception:
                                        logger.exception("Échec envoi avis")
                                        st.error("❌ L'envoi de l'avis a échoué. Réessaie dans un instant.")
                                    else:
                                        donnee = resultat.data or {}
                                        if donnee.get("status") == "success":
                                            st.success(donnee.get("message"))
                                        else:
                                            st.error(donnee.get("message", "Erreur lors de l'envoi"))

    # 👑 Club VIP (module Aura Luxe, premium uniquement) -- un visiteur peut
    # vérifier lui-même s'il fait partie du club en tapant son numéro. Le
    # contrôle passe par sb_admin (côté serveur uniquement, jamais exposé au
    # navigateur) car la table clients_vip ne doit pas être lisible en public.
    if boutique_premium(config) and config.get("vip_offre_actif") and config.get("vip_offre_titre"):
        with st.expander("👑 Club VIP"):
            st.caption("Déjà cliente ou client de la maison ? Vérifiez votre statut VIP.")
            tel_verif = st.text_input("Votre numéro de téléphone", key="vip_tel_verif")
            if st.button("Vérifier mon statut VIP", key="vip_verif_bouton"):
                tel_normalise = re.sub(r"\D", "", tel_verif or "")
                if not tel_normalise:
                    st.warning("Merci de saisir un numéro de téléphone.")
                else:
                    try:
                        resultat_vip = (
                            get_admin_client().table("clients_vip")
                            .select("id")
                            .eq("marchand_id", MARCHAND_ID)
                            .eq("telephone", tel_normalise)
                            .execute()
                        )
                    except Exception:
                        resultat_vip = None
                    if resultat_vip and resultat_vip.data:
                        st.success(f"✨ {config.get('vip_offre_titre')}")
                        if config.get("vip_offre_texte"):
                            st.write(config["vip_offre_texte"])
                        if config.get("vip_offre_code"):
                            st.code(config["vip_offre_code"])
                    else:
                        st.info("Ce numéro ne fait pas encore partie du Club VIP. Il vous suffit d'un premier achat pour y accéder !")

    with st.sidebar:
        st.markdown(
            '<div class="dlc-sidebar-masthead">'
            '<span class="dlc-dot"></span>'
            '<span class="dlc-masthead-texte">Espace client</span>'
            '</div>',
            unsafe_allow_html=True
        )

        with st.container(border=True):
            entete_panneau_sidebar("🛒", "Panier", "Commande en cours")
            if not ss.cart:
                st.caption("Panier vide")
            else:
                total_panier = 0
                for i, item in enumerate(ss.cart):
                    sous_total = item["prix"] * item["quantite"]
                    total_panier += sous_total
                    variante = " / ".join(v for v in [item.get("taille"), item.get("couleur")] if v)
                    label = f"{item['nom']} ({variante})" if variante else item["nom"]
                    st.write(f"{label} × {item['quantite']} = {int(sous_total)} FCFA")
                    if st.button("🗑️", key=f"suppr_{i}"):
                        ss.cart.pop(i)
                        synchroniser_panier_url()
                        st.rerun()

                st.markdown(f"### Total : {int(total_panier)} FCFA")

                # Champs HORS formulaire (contrairement à avant) pour permettre la
                # sauvegarde automatique du panier abandonné pendant la saisie,
                # avant même que le client ait cliqué sur "Confirmer".
                client_nom = st.text_input("Votre nom", key="checkout_nom")
                client_tel = st.text_input("Votre téléphone", key="checkout_tel")

                if client_tel.strip():
                    sauvegarder_panier_abandonne(client_tel, client_nom, ss.cart)

                if st.button("✅ Confirmer la commande"):
                    if not client_nom.strip() or not client_tel.strip():
                        st.warning("Merci de renseigner votre nom et votre téléphone.")
                    else:
                        articles_payload = [
                            {"produit_id": a["produit_id"], "nom": a["nom"], "quantite": a["quantite"]}
                            for a in ss.cart
                        ]
                        resultat = sb.rpc("passer_commande", {
                            "p_client_nom": client_nom.strip(),
                            "p_tel": client_tel.strip(),
                            "p_articles": articles_payload,
                            "p_marchand_id": MARCHAND_ID
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
                                f"Bonjour, je m'appelle {client_nom.strip()} et je viens de passer "
                                f"la commande {donnee.get('id_commande')} :\n"
                                f"{recap}\nTotal : {int(donnee.get('total', 0))} FCFA\n"
                                f"Mon téléphone : {client_tel.strip()}"
                            )
                            lien_whatsapp = f"https://wa.me/{WHATSAPP}?text={requests.utils.quote(message_whatsapp)}"
                            st.link_button("💬 Confirmer aussi sur WhatsApp", lien_whatsapp)

                        ss.cart = []
                        ss.dernier_panier_signature = None
                        synchroniser_panier_url()
                        forcer_rafraichissement()
                        st.success(f"Commande {donnee.get('id_commande')} enregistrée ! Total : {int(donnee.get('total', 0))} FCFA")
                        if donnee.get("ruptures"):
                            st.warning(f"Stock épuisé pour : {', '.join(donnee['ruptures'])}")

        # ❤️ Mes favoris -- toujours visible dans la sidebar, pour que le
        # client retrouve en un coup d'œil les articles qu'il a marqués,
        # sans avoir à refaire défiler tout le catalogue.
        with st.container(border=True):
            entete_panneau_sidebar("❤️", "Mes favoris", "Sélection")
            if not ss.favoris:
                st.caption("Aucun favori pour le moment.")
            else:
                articles_favoris = df_catalogue[
                    df_catalogue.apply(
                        lambda r: normaliser(r.get("id") or r.get("nom")) in ss.favoris,
                        axis=1
                    )
                ]
                for _, art_favori in articles_favoris.iterrows():
                    id_favori = normaliser(art_favori.get("id") or art_favori.get("nom"))
                    col_nom_favori, col_suppr_favori = st.columns([3, 1])
                    col_nom_favori.write(f"❤️ {art_favori['nom']} — {int(art_favori.get('prix') or 0)} FCFA")
                    if col_suppr_favori.button("🗑️", key=f"suppr_favori_{id_favori}"):
                        ss.favoris.remove(id_favori)
                        synchroniser_favoris_url()
                        st.rerun()

        # 🆕 Suivi de commande -- un client peut retrouver le statut de sa
        # commande avec son numéro de téléphone, sans avoir besoin de compte.
        # 🔒 FIX SÉCURITÉ : avant, n'importe quel visiteur pouvait consulter
        # les commandes (nom, montant, articles) de n'importe quel numéro de
        # téléphone deviné ou récupéré ailleurs, sans preuve qu'il lui
        # appartient (IDOR / énumération). On exige désormais un code de
        # vérification envoyé sur WhatsApp au numéro concerné avant
        # d'afficher quoi que ce soit.
        with st.expander("📦 Suivre ma commande"):
            if not WHATSAPP:
                st.caption("Le suivi de commande n'est pas disponible pour le moment.")
            else:
                tel_suivi = st.text_input("Numéro utilisé pour la commande", key="tel_suivi")
                if st.button("Recevoir un code de vérification", key="btn_suivi_code"):
                    tel_normalise = re.sub(r"\D", "", tel_suivi or "")
                    if not tel_normalise:
                        st.warning("Merci de saisir un numéro valide.")
                    elif not throttle(f"otp_suivi_{tel_normalise}", 60):
                        st.warning("Un code a déjà été demandé récemment pour ce numéro, patiente un peu.")
                    else:
                        code = f"{secrets.randbelow(1_000_000):06d}"
                        ss["otp_suivi"] = {
                            "tel": tel_normalise, "code": code,
                            "expire": datetime.now(timezone.utc).timestamp() + 300
                        }
                        message_otp = f"Code de vérification pour suivre ta commande : {code} (valable 5 min)."
                        lien_otp = f"https://wa.me/{tel_normalise}?text={requests.utils.quote(message_otp)}"
                        st.info("Clique ci-dessous pour recevoir ton code sur WhatsApp, puis reviens le saisir ici.")
                        st.link_button("💬 Recevoir le code sur WhatsApp", lien_otp)

                otp_en_cours = ss.get("otp_suivi")
                if otp_en_cours:
                    code_saisi = st.text_input("Code reçu par WhatsApp", key="code_suivi")
                    if st.button("Valider et voir mes commandes", key="btn_suivi_valider"):
                        if datetime.now(timezone.utc).timestamp() > otp_en_cours["expire"]:
                            st.error("Code expiré, redemande un code.")
                            ss.pop("otp_suivi", None)
                        elif not hmac.compare_digest(code_saisi.strip(), otp_en_cours["code"]):
                            st.error("Code incorrect.")
                        else:
                            resultat_suivi = (
                                sb.table("commandes")
                                .select("id, date, statut, price, articles")
                                .eq("tel", otp_en_cours["tel"])
                                .eq("marchand_id", MARCHAND_ID)
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
            with st.container(border=True):
                entete_panneau_sidebar("💬", "Contact", "Assistance directe")
                lien_contact = f"https://wa.me/{WHATSAPP}"
                st.link_button("Nous contacter sur WhatsApp", lien_contact, use_container_width=True)


# ====================== 8. ADMIN ======================
else:
    if not ss.admin_connecte:
        if ss.acces_choisi != "admin":
            # ---- Écran d'accueil : logo + effet lumineux + message de bienvenue ----
            afficher_hero(LOGO_SUR, f"Bienvenue chez {NOM_BOUTIQUE}", "Comment souhaitez-vous continuer ?", animation_logo=config.get("logo_animation") or "glow")
            col_client, col_admin = st.columns(2)
            with col_client:
                if st.button("🛍️ Je suis client / visiteur", use_container_width=True):
                    ss.acces_choisi = "client"
                    st.rerun()
            with col_admin:
                if st.button("🔐 Je suis administrateur", use_container_width=True):
                    ss.acces_choisi = "admin"
                    st.rerun()
        else:
            # ---- Écran de connexion admin (mot de passe) ----
            afficher_hero(LOGO_SUR, f"Bienvenue chez {NOM_BOUTIQUE}", "Connexion administrateur", animation_logo=config.get("logo_animation") or "glow")
            st.subheader("Connexion admin")
            mdp_admin = st.text_input("Mot de passe", type="password")
            col_connexion, col_retour = st.columns(2)
            with col_connexion:
                if st.button("Se connecter"):
                    try:
                        ok, message_erreur = admin_login(mdp_admin)
                        if ok:
                            st.rerun()
                        else:
                            st.error(message_erreur)
                    except Exception:
                        logger.exception("Échec de connexion admin")
                        st.error("Échec de connexion. Réessaie dans quelques instants.")
            with col_retour:
                if st.button("↩️ Retour"):
                    ss.acces_choisi = None
                    st.rerun()
    elif not session_admin_valide():
        st.warning("Session admin expirée par inactivité. Merci de te reconnecter.")
        ss.acces_choisi = None
        st.rerun()
    else:
        sb_admin = get_admin_client()
        st.success("Connecté en tant qu'admin")
        if st.button("Se déconnecter"):
            admin_logout()
            ss.acces_choisi = None
            st.rerun()

        (tab_catalogue, tab_promos, tab_commandes, tab_avis, tab_stats,
         tab_config, tab_alertes, tab_paniers, tab_marketing) = st.tabs(
            ["📦 Catalogue", "🏷️ Promotions", "🧾 Commandes", "💬 Avis", "📊 Statistiques",
             "⚙️ Config", "🔔 Alertes stock", "🛒 Paniers abandonnés", "✨ Aura Luxe"]
        )

        with tab_catalogue:
            # 🐛 CORRECTIF : un échec d'envoi vers ImgBB (ex: quota atteint,
            # erreur réseau) déclenchait un st.warning() juste avant un
            # st.rerun() -- le message n'avait donc que quelques centièmes
            # de seconde à l'écran avant de disparaître ("flash"), et
            # l'article était quand même enregistré SANS photo, sans que le
            # marchand ait pu lire pourquoi. Le message est maintenant
            # conservé ici tant qu'il n'a pas été explicitement fermé.
            if ss.get("alerte_upload_catalogue"):
                st.error(ss["alerte_upload_catalogue"])
                if st.button("OK, compris", key="fermer_alerte_upload_catalogue"):
                    del ss["alerte_upload_catalogue"]
                    st.rerun()

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

                        st.caption("Image principale")
                        contenu_principale, _nom = uploader_image_compressee(
                            key=f"img_{cle_unique}_{ss.refresh_token}"
                        )
                        st.caption("Images supplémentaires (jusqu'à 3, une à la fois)")
                        contenus_supp = []
                        for i in range(3):
                            contenu_supp, _nom_supp = uploader_image_compressee(
                                key=f"imgs_{cle_unique}_{i}_{ss.refresh_token}"
                            )
                            if contenu_supp:
                                contenus_supp.append(contenu_supp)

                        if st.form_submit_button("Enregistrer", disabled=id_manquant):
                            maj = {
                                "nom": nouveau_nom, "prix": int(nouveau_prix), "stock": nouveau_stock,
                                "categorie": nouvelle_categorie, "tailles": nouvelles_tailles,
                                "couleurs": nouvelles_couleurs
                            }
                            erreurs_images_edit = []
                            if contenu_principale is not None:
                                url, erreur_upload = televerser_octets_imgbb(contenu_principale, deja_compressee=True)
                                if url:
                                    maj["image"] = url
                                else:
                                    erreurs_images_edit.append(f"Photo principale : {erreur_upload or 'raison inconnue'}")
                            if contenus_supp:
                                urls_existantes = [u.strip() for u in str(row.get("images_supplementaires") or "").split(",") if u.strip()]
                                for c in contenus_supp:
                                    url, erreur_upload = televerser_octets_imgbb(c, deja_compressee=True)
                                    if url:
                                        urls_existantes.append(url)
                                    elif erreur_upload:
                                        erreurs_images_edit.append(f"Photo supplémentaire : {erreur_upload}")
                                maj["images_supplementaires"] = ", ".join(urls_existantes)
                            sb_admin.table("catalogue").update(maj).eq("id", row["id"]).eq("marchand_id", MARCHAND_ID).execute()
                            ancien_stock = int(row.get("stock") or 0)
                            if ancien_stock <= 0 and nouveau_stock > 0:
                                notifier_retour_stock(nouveau_nom)
                            forcer_rafraichissement()
                            if erreurs_images_edit:
                                ss["alerte_upload_catalogue"] = (
                                    "⚠️ « " + nouveau_nom + " » a été mis à jour, mais l'envoi de photo a échoué : "
                                    + " ; ".join(erreurs_images_edit) + ". Le reste a bien été enregistré."
                                )
                            else:
                                ss.pop("alerte_upload_catalogue", None)
                                st.success("Article mis à jour")
                            st.rerun()
                    if not id_manquant and st.button("🗑️ Supprimer", key=f"del_{cle_unique}"):
                        sb_admin.table("catalogue").delete().eq("id", row["id"]).eq("marchand_id", MARCHAND_ID).execute()
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
                st.caption("Image principale")
                contenu_principale, _nom = uploader_image_compressee(
                    key=f"ajout_img_principale_{ss.refresh_token}"
                )
                st.caption("Images supplémentaires (facultatif, jusqu'à 3, une à la fois)")
                contenus_supp = []
                for i in range(3):
                    c, _n = uploader_image_compressee(key=f"ajout_img_supp_{i}_{ss.refresh_token}")
                    if c:
                        contenus_supp.append(c)
                if st.form_submit_button("Ajouter"):
                    if not nom.strip():
                        st.warning("Le nom de l'article est requis.")
                    else:
                        url_principale = ""
                        erreurs_images = []
                        if contenu_principale:
                            url_principale, erreur_upload = televerser_octets_imgbb(contenu_principale, deja_compressee=True)
                            if erreur_upload:
                                erreurs_images.append(f"Photo principale : {erreur_upload}")
                        urls_supp = []
                        for c in contenus_supp:
                            url, erreur_upload = televerser_octets_imgbb(c, deja_compressee=True)
                            if url:
                                urls_supp.append(url)
                            elif erreur_upload:
                                erreurs_images.append(f"Photo supplémentaire : {erreur_upload}")
                        sb_admin.table("catalogue").insert({
                            "id": str(uuid.uuid4()),
                            "nom": nom, "prix": int(prix), "stock": stock,
                            "image": url_principale, "images_supplementaires": ", ".join(urls_supp),
                            "categorie": categorie, "tailles": tailles, "couleurs": couleurs,
                            "date_ajout": datetime.now(timezone.utc).isoformat(),
                            "marchand_id": MARCHAND_ID
                        }).execute()
                        forcer_rafraichissement()
                        if erreurs_images:
                            ss["alerte_upload_catalogue"] = (
                                "⚠️ « " + nom + " » a été ajouté, mais SANS photo -- l'envoi a échoué : "
                                + " ; ".join(erreurs_images)
                                + ". Ouvre l'article ci-dessus pour réessayer d'ajouter la photo."
                            )
                        else:
                            ss.pop("alerte_upload_catalogue", None)
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
                            sb_admin.table("catalogue").update({"prix_promo": None}).eq("id", ligne["id"]).eq("marchand_id", MARCHAND_ID).execute()
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
                                ).eq("id", ligne["id"]).eq("marchand_id", MARCHAND_ID).execute()
                            forcer_rafraichissement()
                            st.success(f"Promotion appliquée à {len(articles_selectionnes)} article(s)")
                            st.rerun()

        with tab_commandes:
            reponse = (
                sb_admin.table("commandes")
                .select("*")
                .eq("marchand_id", MARCHAND_ID)
                .order("date", desc=True)
                .limit(100)
                .execute()
            )
            statuts_possibles = ["En cours", "Confirmée", "Payée", "Livrée", "Annulée"]
            couleurs_statut = {
                "En cours": "#8a7350", "Confirmée": "#c9a35c", "Payée": "#3f8fd6",
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
                        sb_admin.table("commandes").update({"statut": nouveau_statut}).eq("id", cmd["id"]).eq("marchand_id", MARCHAND_ID).execute()
                        # 🔔 Notifie le client du nouveau statut -- pas d'envoi
                        # automatique possible sans API WhatsApp Business, donc
                        # on prépare le message et on laisse un clic l'envoyer,
                        # même mécanisme que les autres relances de l'app.
                        ss[f"notif_statut_{cle_unique}"] = nouveau_statut
                        st.rerun()

                    if ss.get(f"notif_statut_{cle_unique}"):
                        tel_client_cmd = re.sub(r"\D", "", str(cmd.get("tel") or ""))
                        statut_envoye = ss[f"notif_statut_{cle_unique}"]
                        # 🔔 Message clair et précis : référence courte + liste des
                        # articles, pas juste "votre commande" -- le client doit
                        # pouvoir identifier la commande concernée sans ambiguïté.
                        recap_articles = ", ".join(
                            f"{a.get('nom', '?')} x{int(a.get('quantite') or 0)}" for a in articles_cmd
                        ) or "vos articles"
                        nom_boutique_msg = config.get('nom_boutique', 'notre boutique')
                        prefixe_commande = f"votre commande {reference_courte} ({recap_articles}, {int(total_cmd)} FCFA)"
                        messages_par_statut = {
                            "En cours": f"Bonjour {cmd.get('client_nom') or ''}, {prefixe_commande} chez {nom_boutique_msg} est en cours de préparation. Nous vous tiendrons informé(e) !",
                            "Confirmée": f"Bonjour {cmd.get('client_nom') or ''}, bonne nouvelle : {prefixe_commande} chez {nom_boutique_msg} est confirmée !",
                            "Payée": f"Bonjour {cmd.get('client_nom') or ''}, nous confirmons la réception du paiement pour {prefixe_commande} chez {nom_boutique_msg}. Merci !",
                            "Livrée": f"Bonjour {cmd.get('client_nom') or ''}, {prefixe_commande} chez {nom_boutique_msg} a été livrée. Merci pour votre confiance !",
                            "Annulée": f"Bonjour {cmd.get('client_nom') or ''}, {prefixe_commande} chez {nom_boutique_msg} a été annulée. N'hésitez pas à nous contacter pour toute question.",
                        }
                        message_statut = st.text_area(
                            "Message au client",
                            value=messages_par_statut.get(statut_envoye, f"Le statut de votre commande a été mis à jour : {statut_envoye}."),
                            key=f"texte_notif_{cle_unique}",
                            height=90,
                        )
                        if tel_client_cmd:
                            st.link_button(
                                "💬 Notifier le client sur WhatsApp",
                                f"https://wa.me/{tel_client_cmd}?text={requests.utils.quote(message_statut)}"
                            )
                        else:
                            st.caption("Aucun numéro de téléphone enregistré pour cette commande.")

        with tab_avis:
            st.markdown("#### 🕓 En attente de validation")
            reponse = sb_admin.table("avis").select("*").eq("statut", "en_attente").eq("marchand_id", MARCHAND_ID).execute()
            if not reponse.data:
                st.caption("Aucun avis en attente")
            for idx, avis_item in enumerate(reponse.data):
                cle_unique = f"{idx}_{avis_item.get('id') or 'sansid'}"
                with st.expander(f"{avis_item['client_nom']} — {avis_item['article_nom']} — {'⭐' * int(avis_item['note'])}"):
                    st.write(avis_item.get("commentaire") or "(pas de commentaire)")
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Approuver", key=f"appr_{cle_unique}"):
                        sb_admin.table("avis").update({"statut": "approuve"}).eq("id", avis_item["id"]).eq("marchand_id", MARCHAND_ID).execute()
                        forcer_rafraichissement()
                        st.rerun()
                    if col2.button("🗑️ Supprimer", key=f"suppr_avis_{cle_unique}"):
                        sb_admin.table("avis").delete().eq("id", avis_item["id"]).eq("marchand_id", MARCHAND_ID).execute()
                        forcer_rafraichissement()
                        st.rerun()

            st.divider()
            # 🐛 CORRECTIF : les avis approuvés n'apparaissaient nulle part côté
            # admin (la requête ci-dessus ne charge que statut="en_attente"), donc
            # une fois publiés sous l'article, il n'y avait plus aucun moyen de les
            # supprimer. Cette section liste les avis publiés avec un bouton
            # suppression dédié.
            st.markdown("#### ✅ Avis publiés")
            reponse_publies = (
                sb_admin.table("avis")
                .select("*")
                .eq("statut", "approuve")
                .eq("marchand_id", MARCHAND_ID)
                .order("date", desc=True)
                .execute()
            )
            if not reponse_publies.data:
                st.caption("Aucun avis publié pour le moment")
            for idx, avis_item in enumerate(reponse_publies.data):
                cle_unique = f"pub_{idx}_{avis_item.get('id') or 'sansid'}"
                with st.expander(f"{avis_item['client_nom']} — {avis_item['article_nom']} — {'⭐' * int(avis_item['note'])}"):
                    st.write(avis_item.get("commentaire") or "(pas de commentaire)")
                    if st.button("🗑️ Supprimer", key=f"suppr_avis_{cle_unique}"):
                        sb_admin.table("avis").delete().eq("id", avis_item["id"]).eq("marchand_id", MARCHAND_ID).execute()
                        forcer_rafraichissement()
                        st.rerun()

        with tab_stats:
            st.write("### 📊 Statistiques avancées")
            reponse_stats = (
                sb_admin.table("commandes")
                .select("*")
                .eq("marchand_id", MARCHAND_ID)
                .order("date", desc=False)
                .execute()
            )
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
            st.write("### 🖼️ Identité de la boutique")
            st.caption("Nom, slogan et logo — ce bloc a son propre bouton, indépendant du reste de la configuration.")
            with st.form("form_identite"):
                nom_boutique_input = st.text_input(
                    "Nom de la boutique", value=config.get("nom_boutique") or "", key="input_nom_boutique"
                )
                slogan_input = st.text_input(
                    "Slogan (affiché sous le nom)", value=config.get("slogan") or "Élégance • Exclusivité • Luxe",
                    key="input_slogan"
                )

                st.write("**Logo de la boutique**")
                if config.get("logo") and re.match(r"^https?://", str(config.get("logo")).strip(), re.IGNORECASE):
                    st.image(config.get("logo"), width=150, caption="Logo actuel")
                else:
                    st.caption("Aucun logo pour le moment.")
                nouveau_logo_contenu, _nom_logo = uploader_image_compressee(
                    key=f"upload_logo_{ss.refresh_token}"
                )

                if st.form_submit_button("✅ Valider le nom, le slogan et le logo"):
                    logo_valeur = config.get("logo") or ""
                    echec_logo = False
                    if nouveau_logo_contenu is not None:
                        url_logo, erreur_upload = televerser_octets_imgbb(nouveau_logo_contenu, deja_compressee=True)
                        if url_logo:
                            logo_valeur = url_logo
                        else:
                            echec_logo = True
                            st.error(f"❌ Échec de l'envoi du logo : {erreur_upload or 'raison inconnue'} — l'ancien logo a été conservé.")

                    # 🔒 FIX : avant, si l'écriture en base échouait pour une
                    # raison quelconque (RLS, réseau, colonne manquante...),
                    # l'exception remontait sans être attrapée : le script
                    # plantait AVANT d'afficher le moindre message, et rien
                    # n'était enregistré -- ni le nom, ni le slogan, ni le
                    # logo -- sans que tu saches pourquoi. Le message
                    # d'erreur exact s'affiche maintenant clairement.
                    try:
                        sb_admin.table("marchands").update({
                            "nom_boutique": nom_boutique_input,
                            "slogan": slogan_input,
                            "logo": logo_valeur,
                        }).eq("id", MARCHAND_ID).execute()
                    except Exception:
                        logger.exception("Échec enregistrement identité boutique")
                        st.error("❌ L'enregistrement en base a échoué. Réessaie dans un instant.")
                    else:
                        forcer_rafraichissement()
                        if echec_logo:
                            st.warning("Le nom et le slogan ont bien été enregistrés, mais le logo n'a PAS changé (voir l'erreur ci-dessus).")
                        else:
                            st.success("✅ Nom, slogan et logo enregistrés avec succès.")
                        st.rerun()

            st.divider()
            st.write("### ⚙️ Contact et alertes")
            with st.form("form_config"):
                whatsapp_input = st.text_input("Numéro WhatsApp", value=config.get("whatsapp") or "")
                email_admin_input = st.text_input("Email de notification", value=config.get("email_admin") or "")

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

                st.write("**Relance panier abandonné & preuve sociale**")
                try:
                    delai_relance_defaut = int(config.get("delai_relance_panier_h", 24) or 24)
                except (TypeError, ValueError):
                    delai_relance_defaut = 24
                try:
                    seuil_urgence_defaut = int(config.get("seuil_stock_urgence", 5) or 5)
                except (TypeError, ValueError):
                    seuil_urgence_defaut = 5
                delai_relance_input = st.number_input(
                    "Relancer un panier abandonné après (heures)",
                    min_value=1, max_value=168, step=1, value=delai_relance_defaut,
                    help="Passé ce délai, le panier remonte en haut de l'onglet « Paniers abandonnés » avec un badge « Prêt à relancer »."
                )
                seuil_urgence_input = st.number_input(
                    "Afficher « il ne reste que N ! » en dessous de",
                    min_value=1, max_value=50, step=1, value=seuil_urgence_defaut
                )

                if st.form_submit_button("Enregistrer"):
                    try:
                        sb_admin.table("marchands").update({
                            "whatsapp": whatsapp_input,
                            "email_contact": email_admin_input,
                            "seuil_stock_bas": int(seuil_stock_input),
                            "heure_bilan": int(heure_bilan_input),
                            "delai_relance_panier_h": int(delai_relance_input),
                            "seuil_stock_urgence": int(seuil_urgence_input),
                        }).eq("id", MARCHAND_ID).execute()
                    except Exception:
                        logger.exception("Échec enregistrement config contact/alertes")
                        st.error("❌ L'enregistrement en base a échoué. Réessaie dans un instant.")
                    else:
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
                    if not verifier_mot_de_passe(mdp_actuel, hash_attendu):
                        st.error("Mot de passe actuel incorrect.")
                    elif not mdp_nouveau.strip():
                        st.warning("Le nouveau mot de passe ne peut pas être vide.")
                    elif len(mdp_nouveau) < 6:
                        st.warning("Le nouveau mot de passe doit contenir au moins 6 caractères.")
                    elif mdp_nouveau != mdp_nouveau_confirmation:
                        st.warning("La confirmation ne correspond pas au nouveau mot de passe.")
                    else:
                        sb_admin.table("marchands").update(
                            {"mot_de_passe_hash": hash_mot_de_passe(mdp_nouveau)}
                        ).eq("id", MARCHAND_ID).execute()
                        forcer_rafraichissement()
                        st.success("Mot de passe mis à jour avec succès — utilise-le dès ta prochaine connexion.")

        with tab_alertes:
            reponse = sb_admin.table("alertesstock").select("*").eq("statut", "en_attente").eq("marchand_id", MARCHAND_ID).execute()
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
                            nom_client_alerte = (alerte.get("nom_client") or "").strip()
                            if alerte.get("contact_type") == "telephone":
                                tel_alerte = re.sub(r"\D", "", str(alerte.get("contact") or ""))
                                salutation = f"Bonjour {nom_client_alerte}," if nom_client_alerte else "Bonjour,"
                                message_alerte = (
                                    f"{salutation} l'article \"{article_nom}\" est de nouveau disponible "
                                    f"sur {config.get('nom_boutique', 'notre boutique')} !"
                                )
                                lien_whatsapp_alerte = f"https://wa.me/{tel_alerte}?text={requests.utils.quote(message_alerte)}"
                                col1, col2 = st.columns([3, 2])
                                col1.write(f"📞 {nom_client_alerte or 'Client'} — {alerte.get('contact')}")
                                col2.link_button(
                                    "💬 WhatsApp", lien_whatsapp_alerte,
                                    key=f"wa_alerte_{alerte.get('id')}"
                                )
                            else:
                                st.write(f"✉️ {nom_client_alerte or 'Client'} — {alerte.get('contact')}")
                        if st.button("🔔 Notifier les inscrits par email maintenant", key=f"notif_{article_nom}"):
                            notifier_retour_stock(article_nom)
                            st.success("Emails envoyés aux inscrits par email pour cet article.")
                            st.rerun()

        with tab_paniers:
            # 🕓 Relance semi-auto : un panier devient "prêt à relancer" une
            # fois le délai configuré dépassé (voir Config > Relance panier
            # abandonné). Le job planifié (scripts/taches_planifiees.py) pose
            # aussi ce badge en base pour pouvoir prévenir l'admin par email,
            # mais on recalcule ici en direct pour ne pas dépendre du cron.
            delai_relance_h = int(config.get("delai_relance_panier_h", 24) or 24)
            reponse = sb_admin.table("paniersabandonnés").select("*").eq("statut", "en_attente").eq("marchand_id", MARCHAND_ID).execute()
            maintenant_utc = datetime.now(timezone.utc)

            def _heures_ecoulees(panier):
                try:
                    horodatage = pd.to_datetime(panier.get("date_derniere_maj"), utc=True)
                    return (maintenant_utc - horodatage.to_pydatetime()).total_seconds() / 3600
                except Exception:
                    return 0

            paniers = reponse.data or []
            for p in paniers:
                p["_heures_ecoulees"] = _heures_ecoulees(p)
                p["_pret_a_relancer"] = p["_heures_ecoulees"] >= delai_relance_h
            paniers.sort(key=lambda p: (not p["_pret_a_relancer"], -p["_heures_ecoulees"]))

            nb_prets = sum(1 for p in paniers if p["_pret_a_relancer"])
            if not paniers:
                st.caption("Aucun panier abandonné en attente")
            elif nb_prets:
                st.info(f"⏰ {nb_prets} panier(s) prêt(s) à relancer (délai de {delai_relance_h}h dépassé)")

            for idx, panier in enumerate(paniers):
                cle_unique = f"{idx}_{panier.get('telephone') or 'sanstelephone'}"
                total = panier.get("total") or 0
                badge_pret = " · ⏰ Prêt à relancer" if panier["_pret_a_relancer"] else f" · depuis {int(panier['_heures_ecoulees'])}h"
                with st.expander(f"{panier.get('client_nom') or 'Client'} — {panier.get('telephone')} — {total} FCFA{badge_pret}"):
                    st.json(panier.get("articles"))
                    tel_relance = re.sub(r"\D", "", str(panier.get("telephone") or ""))
                    message_relance_defaut = f"Bonjour, vous avez laissé des articles dans votre panier sur {config.get('nom_boutique', 'notre boutique')} — puis-je vous aider à finaliser votre commande ?"

                    # 🤖 Script de relance IA (module Aura Luxe) -- reprend les
                    # articles réellement laissés dans le panier pour un message
                    # personnalisé plutôt que le message générique par défaut.
                    if boutique_premium(config):
                        cle_message_ia = f"relance_ia_{cle_unique}"
                        if st.button("🤖 Générer un message de relance personnalisé", key=f"btn_{cle_message_ia}"):
                            noms_articles = ", ".join(
                                a.get("nom", "") for a in (panier.get("articles") or []) if a.get("nom")
                            ) or "les articles de son panier"
                            prompt_relance = (
                                f"Tu es le service client de la boutique de luxe « {config.get('nom_boutique', 'notre boutique')} ». "
                                f"Rédige un message WhatsApp court (2 à 3 phrases, chaleureux, pas insistant) pour relancer "
                                f"{panier.get('client_nom') or 'un client'} qui a laissé dans son panier : {noms_articles}, "
                                f"pour un total de {int(total)} FCFA. Donne-lui envie de finaliser sans le mettre sous pression. "
                                f"Réponds uniquement avec le texte du message, en français, sans introduction."
                            )
                            with st.spinner("Génération en cours..."):
                                texte_relance, erreur_relance = generer_texte_ia(prompt_relance, max_tokens=180)
                            if erreur_relance:
                                st.error(f"❌ {erreur_relance}")
                            else:
                                ss[cle_message_ia] = texte_relance

                        if ss.get(cle_message_ia):
                            message_relance_defaut = st.text_area(
                                "Message de relance (modifiable)",
                                value=ss[cle_message_ia],
                                key=f"texte_{cle_message_ia}",
                                height=100,
                            )

                    if tel_relance:
                        lien_whatsapp = f"https://wa.me/{tel_relance}?text={requests.utils.quote(message_relance_defaut)}"
                        st.link_button("💬 Relancer sur WhatsApp", lien_whatsapp)
                    if st.button("🗑️ Marquer comme traité", key=f"panier_traite_{cle_unique}"):
                        sb_admin.table("paniersabandonnés").update({"statut": "traite"}).eq("telephone", panier["telephone"]).eq("marchand_id", MARCHAND_ID).execute()
                        st.rerun()

        with tab_marketing:
            # 🔒 Module payant : ce n'est JAMAIS le marchand qui active son
            # propre accès. "palier_abonnement" est modifiable uniquement
            # depuis le Super Admin, après paiement. Ici on se contente de
            # lire la valeur et de verrouiller l'onglet si elle n'est pas
            # "premium" -- aucun bouton de déblocage n'existe côté marchand.
            if not boutique_premium(config):
                st.info(
                    "✨ **Aura Luxe** est le module premium de la boutique (thème complet "
                    "personnalisable -- couleur, police, animation du logo, style de badge --, "
                    "bannières promo néon, flash sales, collections temporaires, club VIP, "
                    "visuels réseaux sociaux, mise en vedette dans la vitrine commune, "
                    "diffusion WhatsApp). Contacte-nous pour l'activer sur ta boutique."
                )
            else:
                st.success("✨ Module Aura Luxe actif sur ta boutique.")

                (sous_tab_theme, sous_tab_banniere, sous_tab_visuel, sous_tab_ia, sous_tab_flash,
                 sous_tab_vip, sous_tab_vedette, sous_tab_diffusion) = st.tabs(
                    ["🎨 Thème & badge", "🏷️ Bannière promo", "🖼️ Visuel réseaux sociaux",
                     "🤖 Assistant IA", "⚡ Flash Sales & Collections", "👑 Club VIP",
                     "⭐ Mise en vedette", "💬 Diffusion WhatsApp"]
                )

                # ---- Thème complet (couleur + police + animation logo + badge) ----
                with sous_tab_theme:
                    st.caption(
                        "Personnalise l'identité visuelle complète de ta boutique : couleur "
                        "d'accent, police des titres, animation du logo et style du badge "
                        "✨ Aura Luxe. Aperçu en direct ci-dessous."
                    )
                    afficher_badge_aura(
                        style=config.get("badge_style") or "shimmer",
                        texte=config.get("badge_texte") or "✨ Aura Luxe",
                    )
                    with st.form("form_theme_couleur"):
                        st.markdown("**🎨 Couleur du thème**")
                        couleur_actuelle = config.get("theme_couleur") or "#c9a35c"
                        noms_presets = list(THEMES_PRESETS.keys()) + ["Personnalisé"]
                        preset_actuel = next(
                            (nom for nom, hexa in THEMES_PRESETS.items() if hexa.lower() == couleur_actuelle.lower()),
                            "Personnalisé"
                        )
                        preset_choisi = st.selectbox(
                            "Thème prédéfini",
                            noms_presets,
                            index=noms_presets.index(preset_actuel)
                        )
                        if preset_choisi == "Personnalisé":
                            couleur_choisie = st.color_picker(
                                "Couleur d'accent personnalisée", value=couleur_actuelle
                            )
                        else:
                            couleur_choisie = THEMES_PRESETS[preset_choisi]
                            st.color_picker(
                                "Aperçu de la couleur", value=couleur_choisie, disabled=True
                            )

                        st.markdown("**🔤 Police des titres**")
                        cles_polices = list(POLICES_PRESETS.keys())
                        libelles_polices = [POLICES_PRESETS[c][0] for c in cles_polices]
                        police_actuelle = config.get("police_titre") or "playfair"
                        index_police = cles_polices.index(police_actuelle) if police_actuelle in cles_polices else 0
                        police_choisie_libelle = st.selectbox(
                            "Police", libelles_polices, index=index_police
                        )
                        police_choisie = cles_polices[libelles_polices.index(police_choisie_libelle)]

                        st.markdown("**✨ Animation du logo**")
                        cles_anim = list(ANIMATIONS_LOGO.keys())
                        libelles_anim = [ANIMATIONS_LOGO[c] for c in cles_anim]
                        anim_actuelle = config.get("logo_animation") or "glow"
                        index_anim = cles_anim.index(anim_actuelle) if anim_actuelle in cles_anim else 0
                        anim_choisie_libelle = st.selectbox(
                            "Animation", libelles_anim, index=index_anim
                        )
                        anim_choisie = cles_anim[libelles_anim.index(anim_choisie_libelle)]

                        st.markdown("**🏷️ Badge Aura Luxe**")
                        cles_badge = list(STYLES_BADGE_AURA.keys())
                        libelles_badge = [STYLES_BADGE_AURA[c] for c in cles_badge]
                        style_badge_actuel = config.get("badge_style") or "shimmer"
                        index_badge = cles_badge.index(style_badge_actuel) if style_badge_actuel in cles_badge else 0
                        style_badge_libelle = st.selectbox(
                            "Style du badge", libelles_badge, index=index_badge
                        )
                        style_badge_choisi = cles_badge[libelles_badge.index(style_badge_libelle)]
                        texte_badge_choisi = st.text_input(
                            "Texte affiché sur le badge",
                            value=config.get("badge_texte") or "✨ Aura Luxe",
                            max_chars=30
                        )

                        if st.form_submit_button("💾 Enregistrer le thème"):
                            try:
                                sb_admin.table("marchands").update({
                                    "theme_couleur": couleur_choisie,
                                    "police_titre": police_choisie,
                                    "logo_animation": anim_choisie,
                                    "badge_style": style_badge_choisi,
                                    "badge_texte": texte_badge_choisi.strip() or "✨ Aura Luxe",
                                }).eq("id", MARCHAND_ID).execute()
                            except Exception:
                                logger.exception("Échec enregistrement thème")
                                st.error("❌ L'enregistrement a échoué. Réessaie dans un instant.")
                            else:
                                forcer_rafraichissement()
                                st.success("Thème mis à jour.")
                                st.rerun()

                    st.caption(
                        "ℹ️ Si le mode Aura Luxe venait à être désactivé, la boutique "
                        "reprend automatiquement son apparence dorée d'origine (couleur, "
                        "police et animations par défaut) -- ces réglages restent "
                        "enregistrés et reprennent effet dès la réactivation."
                    )

                # ---- Bannière promo interne à la boutique ----
                with sous_tab_banniere:
                    st.caption("Affichée en haut de ta boutique, juste sous le logo.")

                    with st.expander("🤖 Générer avec l'IA"):
                        brief_banniere = st.text_area(
                            "Décris ta promotion (occasion, réduction, dates, code...)",
                            key="brief_banniere_ia",
                            placeholder="Ex : Soldes d'été, -20% sur toute la collection, valable tout juillet, code DESTIN-Y"
                        )
                        if st.button("🤖 Générer titre + texte", key="generer_banniere_ia"):
                            if not brief_banniere.strip():
                                st.warning("Décris d'abord ta promotion.")
                            else:
                                prompt_banniere = (
                                    f"Tu rédiges une bannière promotionnelle pour la boutique de luxe "
                                    f"« {config.get('nom_boutique', 'la boutique')} ». À partir de ces informations "
                                    f"données par le marchand : « {brief_banniere.strip()} », propose un titre "
                                    f"court et accrocheur (5 mots maximum) et un texte d'accompagnement (une "
                                    f"phrase, 15 mots maximum). Si un code promo est mentionné dans les "
                                    f"informations, reprends-le tel quel, sinon n'en invente pas. "
                                    f"Réponds STRICTEMENT dans ce format, sans rien ajouter d'autre :\n"
                                    f"TITRE: <titre>\nTEXTE: <texte>\nCODE: <code ou VIDE si aucun>"
                                )
                                with st.spinner("Génération en cours..."):
                                    texte_banniere_ia, erreur_banniere_ia = generer_texte_ia(prompt_banniere, max_tokens=150)
                                if erreur_banniere_ia:
                                    st.error(f"❌ {erreur_banniere_ia}")
                                else:
                                    for ligne in texte_banniere_ia.splitlines():
                                        ligne_maj = ligne.strip().upper()
                                        if ligne_maj.startswith("TITRE:"):
                                            ss["banniere_titre_genere"] = ligne.split(":", 1)[1].strip()
                                        elif ligne_maj.startswith("TEXTE:"):
                                            ss["banniere_texte_genere"] = ligne.split(":", 1)[1].strip()
                                        elif ligne_maj.startswith("CODE:"):
                                            valeur_code = ligne.split(":", 1)[1].strip()
                                            if valeur_code and valeur_code.upper() != "VIDE":
                                                ss["banniere_code_genere"] = valeur_code
                                    st.success("Généré ! Vérifie et ajuste ci-dessous avant d'enregistrer.")
                                    st.rerun()

                    with st.form("form_banniere_promo"):
                        banniere_actif_input = st.checkbox(
                            "Afficher la bannière sur la boutique",
                            value=bool(config.get("banniere_actif"))
                        )
                        banniere_titre_input = st.text_input(
                            "Titre",
                            value=ss.get("banniere_titre_genere") or config.get("banniere_titre") or "",
                            placeholder="Ex : Soldes de fin d'année"
                        )
                        banniere_texte_input = st.text_area(
                            "Texte",
                            value=ss.get("banniere_texte_genere") or config.get("banniere_texte") or "",
                            placeholder="Ex : -20% sur toute la collection jusqu'au 31 décembre"
                        )
                        banniere_code_input = st.text_input(
                            "Code promo (facultatif)",
                            value=ss.get("banniere_code_genere") or config.get("banniere_code_promo") or "",
                            placeholder="Ex : NOEL20"
                        )
                        banniere_style_input = st.radio(
                            "Style",
                            ["classique", "neon"],
                            index=0 if config.get("banniere_style") != "neon" else 1,
                            format_func=lambda s: "Classique" if s == "classique" else "🔮 Néon (halo animé)",
                            horizontal=True,
                        )
                        if st.form_submit_button("💾 Enregistrer la bannière"):
                            if banniere_actif_input and not banniere_titre_input.strip():
                                st.warning("Ajoute au moins un titre avant d'activer la bannière.")
                            else:
                                try:
                                    sb_admin.table("marchands").update({
                                        "banniere_actif": banniere_actif_input,
                                        "banniere_titre": banniere_titre_input.strip() or None,
                                        "banniere_texte": banniere_texte_input.strip() or None,
                                        "banniere_code_promo": banniere_code_input.strip() or None,
                                        "banniere_style": banniere_style_input,
                                    }).eq("id", MARCHAND_ID).execute()
                                except Exception:
                                    logger.exception("Échec enregistrement bannière promo")
                                    st.error("❌ L'enregistrement a échoué. Réessaie dans un instant.")
                                else:
                                    for cle_generee in ("banniere_titre_genere", "banniere_texte_genere", "banniere_code_genere"):
                                        ss.pop(cle_generee, None)
                                    forcer_rafraichissement()
                                    st.success("Bannière mise à jour.")
                                    st.rerun()

                # ---- Générateur de visuel pour réseaux sociaux ----
                with sous_tab_visuel:
                    st.caption(
                        "Génère une image prête à publier (format portrait 4:5, optimisé "
                        "Instagram/Facebook) pour un article de ton catalogue, avec ton nom "
                        "de boutique en signature, le nom de l'article et son prix."
                    )
                    if df_catalogue.empty:
                        st.caption("Ajoute d'abord des articles dans l'onglet Catalogue.")
                    else:
                        options_produits = df_catalogue["nom"].dropna().tolist()
                        produit_choisi = st.selectbox("Article", options_produits, key="visuel_produit_choisi")
                        ligne_produit = df_catalogue[df_catalogue["nom"] == produit_choisi].iloc[0]

                        with st.expander("🤖 Suggérer une accroche avec l'IA", expanded=True):
                            brief_accroche = st.text_input(
                                "Occasion ou contexte (facultatif)",
                                key="brief_accroche_ia",
                                placeholder="Ex : Fête des mères, nouvelle collection, dernières pièces..."
                            )
                            if st.button("🤖 Suggérer une accroche", key="generer_accroche_ia"):
                                prompt_accroche = (
                                    f"Propose UNE accroche très courte (4 mots maximum, percutante, en français) "
                                    f"pour un visuel réseaux sociaux de la boutique de luxe "
                                    f"« {config.get('nom_boutique', 'la boutique')} », à propos de l'article "
                                    f"« {ligne_produit.get('nom')} »"
                                    + (f", contexte : {brief_accroche.strip()}" if brief_accroche.strip() else "")
                                    + ". Réponds uniquement avec l'accroche, sans guillemets ni ponctuation finale."
                                )
                                with st.spinner("Génération en cours..."):
                                    accroche_generee, erreur_accroche = generer_texte_ia(prompt_accroche, max_tokens=30)
                                if erreur_accroche:
                                    st.error(f"❌ {erreur_accroche}")
                                else:
                                    ss["accroche_visuel_generee"] = accroche_generee.strip().strip('"')
                                    st.rerun()

                        accroche_visuel = st.text_input(
                            "Accroche affichée sur le visuel (facultatif)",
                            value=ss.get("accroche_visuel_generee", ""),
                            key="accroche_visuel_input",
                            placeholder="Ex : NOUVELLE COLLECTION"
                        )

                        with st.expander("🤖 Suggérer une description marketing avec l'IA", expanded=True):
                            st.caption("Une phrase courte et percutante, mise en valeur sous le nom de l'article sur le visuel.")
                            if st.button("🤖 Suggérer une description", key="generer_description_marketing_ia"):
                                prompt_description = (
                                    f"Rédige UNE phrase marketing courte (12 mots maximum, élégante, en français, "
                                    f"sans guillemets) pour un visuel réseaux sociaux de la boutique de luxe "
                                    f"« {config.get('nom_boutique', 'la boutique')} », mettant en valeur l'article "
                                    f"« {ligne_produit.get('nom')} ». Réponds uniquement avec la phrase."
                                )
                                with st.spinner("Génération en cours..."):
                                    description_generee, erreur_description = generer_texte_ia(prompt_description, max_tokens=60)
                                if erreur_description:
                                    st.error(f"❌ {erreur_description}")
                                else:
                                    ss["description_visuel_generee"] = description_generee.strip().strip('"')
                                    st.rerun()

                        description_visuel = st.text_area(
                            "Description marketing affichée sur le visuel (facultatif)",
                            value=ss.get("description_visuel_generee", ""),
                            key="description_visuel_input",
                            placeholder="Ex : Une élégance intemporelle, pensée pour les femmes qui osent.",
                            height=80,
                        )

                        if st.button("🖼️ Générer le visuel", key="generer_visuel_produit"):
                            with st.spinner("Génération du visuel..."):
                                octets_image, erreur_visuel = generer_visuel_produit(
                                    url_image_produit=ligne_produit.get("image"),
                                    nom_produit=ligne_produit.get("nom"),
                                    prix=ligne_produit.get("prix"),
                                    prix_promo=ligne_produit.get("prix_promo"),
                                    nom_boutique=config.get("nom_boutique"),
                                    accroche=accroche_visuel,
                                    description_marketing=description_visuel,
                                    couleur_accent=config.get("theme_couleur"),
                                )
                            if erreur_visuel:
                                st.error(f"❌ {erreur_visuel}")
                            else:
                                st.image(octets_image, caption="Aperçu du visuel généré")
                                st.download_button(
                                    "⬇️ Télécharger le visuel",
                                    data=octets_image,
                                    file_name=f"pub_{normaliser(produit_choisi)}.png",
                                    mime="image/png",
                                )

                # ---- Assistant IA : descriptions produits + posts réseaux sociaux ----
                with sous_tab_ia:
                    st.caption(
                        "Génère du texte marketing via IA (rotation Groq → Gemini → DeepSeek : "
                        "si l'un est indisponible, le suivant prend le relais automatiquement)."
                    )
                    if df_catalogue.empty:
                        st.caption("Ajoute d'abord des articles dans l'onglet Catalogue.")
                    else:
                        st.markdown("#### ✍️ Description produit")
                        produit_ia_desc = st.selectbox(
                            "Article", df_catalogue["nom"].dropna().tolist(), key="ia_produit_description"
                        )
                        ligne_ia_desc = df_catalogue[df_catalogue["nom"] == produit_ia_desc].iloc[0]
                        ton_description = st.select_slider(
                            "Ton", ["Sobre & élégant", "Chaleureux", "Ultra-luxe & aspirationnel"],
                            value="Ultra-luxe & aspirationnel", key="ia_ton_description"
                        )
                        if st.button("🤖 Générer une description", key="ia_generer_description"):
                            prompt_description = (
                                f"Tu es rédacteur pour une boutique de luxe en ligne nommée "
                                f"« {config.get('nom_boutique', 'la boutique')} ». Rédige en français une "
                                f"description produit courte (3 à 4 phrases, pas de titre, pas de guillemets) "
                                f"pour l'article suivant : nom = « {ligne_ia_desc.get('nom')} », "
                                f"catégorie = « {ligne_ia_desc.get('categorie') or 'non précisée'} », "
                                f"prix = {int(ligne_ia_desc.get('prix') or 0)} FCFA. "
                                f"Ton souhaité : {ton_description}. N'invente aucune caractéristique technique "
                                f"précise (matière, dimensions...) que tu ne connais pas -- reste évocateur sur "
                                f"l'usage et le ressenti plutôt que sur des détails factuels non fournis."
                            )
                            with st.spinner("Génération en cours..."):
                                texte_genere, erreur_ia = generer_texte_ia(prompt_description, max_tokens=220)
                            if erreur_ia:
                                st.error(f"❌ {erreur_ia}")
                            else:
                                ss["ia_description_generee"] = texte_genere

                        if ss.get("ia_description_generee"):
                            description_finale = st.text_area(
                                "Description générée (modifiable avant enregistrement)",
                                value=ss["ia_description_generee"],
                                key="ia_description_editable",
                                height=120,
                            )
                            if st.button("💾 Enregistrer sur la fiche produit", key="ia_enregistrer_description"):
                                try:
                                    sb_admin.table("catalogue").update(
                                        {"description": description_finale.strip()}
                                    ).eq("id", ligne_ia_desc["id"]).eq("marchand_id", MARCHAND_ID).execute()
                                except Exception:
                                    logger.exception("Échec enregistrement description IA")
                                    st.error(
                                        "❌ L'enregistrement a échoué -- vérifie que la colonne "
                                        "\"description\" existe bien dans la table catalogue (voir migration SQL)."
                                    )
                                else:
                                    forcer_rafraichissement()
                                    st.success("Description enregistrée sur la fiche produit.")
                                    del ss["ia_description_generee"]
                                    st.rerun()

                        st.divider()
                        st.markdown("#### 📱 Post réseaux sociaux")
                        produit_ia_post = st.selectbox(
                            "Article", df_catalogue["nom"].dropna().tolist(), key="ia_produit_post"
                        )
                        ligne_ia_post = df_catalogue[df_catalogue["nom"] == produit_ia_post].iloc[0]
                        plateforme_post = st.radio(
                            "Plateforme", ["Instagram / Facebook", "WhatsApp"],
                            horizontal=True, key="ia_plateforme_post"
                        )
                        if st.button("🤖 Générer le post", key="ia_generer_post"):
                            if plateforme_post == "Instagram / Facebook":
                                consigne_post = (
                                    "Rédige une légende Instagram/Facebook accrocheuse (4 à 6 lignes), avec "
                                    "quelques emojis pertinents et 5 à 8 hashtags pertinents à la fin."
                                )
                            else:
                                consigne_post = (
                                    "Rédige un court message WhatsApp (2 à 3 phrases, ton chaleureux et direct, "
                                    "quelques emojis), sans hashtags, comme si la boutique écrivait à ses clients."
                                )
                            prompt_post = (
                                f"Tu gères les réseaux sociaux de la boutique de luxe « {config.get('nom_boutique', 'la boutique')} ». "
                                f"{consigne_post} Sujet : l'article « {ligne_ia_post.get('nom')} » à "
                                f"{int(ligne_ia_post.get('prix') or 0)} FCFA. Réponds uniquement avec le texte du post, "
                                f"en français, sans introduction ni explication."
                            )
                            with st.spinner("Génération en cours..."):
                                texte_post, erreur_post = generer_texte_ia(prompt_post, max_tokens=280)
                            if erreur_post:
                                st.error(f"❌ {erreur_post}")
                            else:
                                ss["ia_post_genere"] = texte_post

                        if ss.get("ia_post_genere"):
                            texte_post_genere = st.text_area(
                                "Post généré (copie-colle sur tes réseaux)",
                                value=ss["ia_post_genere"],
                                key="ia_post_editable",
                                height=160,
                            )
                            # 📌 Limite technique honnête : WhatsApp accepte un texte
                            # pré-rempli via wa.me, mais ni Facebook ni Instagram ne
                            # permettent d'ouvrir un post déjà rédigé depuis un simple
                            # lien web (ce n'est pas une limitation de l'app -- ces
                            # plateformes ne l'autorisent tout simplement pas sans leur
                            # API officielle de publication). On copie donc le texte
                            # dans le presse-papier et on ouvre la plateforme visée,
                            # pour qu'il ne reste qu'à coller.
                            st.caption(
                                "WhatsApp ouvre directement avec le texte prêt. Pour Facebook et "
                                "Instagram (qui ne permettent pas de pré-remplir un post depuis un "
                                "lien web), le texte est copié -- il ne reste qu'à le coller."
                            )
                            col_wa, col_fb, col_ig = st.columns(3)
                            with col_wa:
                                st.link_button(
                                    "💬 WhatsApp", f"https://wa.me/?text={requests.utils.quote(texte_post_genere)}",
                                    use_container_width=True
                                )
                            with col_fb:
                                bouton_copier_texte(texte_post_genere, cle="ia_post_fb", libelle="📘 Copier pour Facebook")
                                st.link_button("Ouvrir Facebook", "https://www.facebook.com/", use_container_width=True)
                            with col_ig:
                                bouton_copier_texte(texte_post_genere, cle="ia_post_ig", libelle="📸 Copier pour Instagram")
                                st.link_button("Ouvrir Instagram", "https://www.instagram.com/", use_container_width=True)

                        st.divider()
                        st.markdown("#### 🔁 Tunnel de vente WhatsApp")
                        st.caption("Trois messages prêts à envoyer à quelques jours d'intervalle (J0, relance, clôture).")
                        sujet_tunnel = st.text_input(
                            "Produit ou promo à mettre en avant", key="ia_sujet_tunnel",
                            placeholder="Ex : Nouvelle collection Sac Aurore, ou -15% ce week-end"
                        )
                        if st.button("🤖 Générer le tunnel", key="ia_generer_tunnel"):
                            if not sujet_tunnel.strip():
                                st.warning("Précise d'abord un produit ou une promo.")
                            else:
                                prompt_tunnel = (
                                    f"Tu gères le WhatsApp Business de la boutique de luxe « {config.get('nom_boutique', 'la boutique')} ». "
                                    f"Rédige 3 messages courts et distincts pour promouvoir : « {sujet_tunnel.strip()} ». "
                                    f"Message 1 (annonce, ton enthousiaste) ; Message 2 (relance 2 jours après pour ceux qui "
                                    f"n'ont pas répondu, ton léger, crée un peu d'urgence sans être insistant) ; "
                                    f"Message 3 (clôture, dernière chance, ton chaleureux). "
                                    f"Réponds STRICTEMENT dans ce format, sans rien ajouter d'autre :\n"
                                    f"MESSAGE 1:\n<texte>\nMESSAGE 2:\n<texte>\nMESSAGE 3:\n<texte>"
                                )
                                with st.spinner("Génération en cours..."):
                                    texte_tunnel, erreur_tunnel = generer_texte_ia(prompt_tunnel, max_tokens=450)
                                if erreur_tunnel:
                                    st.error(f"❌ {erreur_tunnel}")
                                else:
                                    ss["ia_tunnel_genere"] = texte_tunnel

                        if ss.get("ia_tunnel_genere"):
                            st.text_area(
                                "Tunnel généré (copie-colle chaque message au bon moment)",
                                value=ss["ia_tunnel_genere"],
                                key="ia_tunnel_editable",
                                height=260,
                            )

                        st.divider()
                        st.markdown("#### 🎁 Packs produits cohérents")
                        st.caption(
                            "L'IA propose un pack à partir de ton catalogue -- à valider avant de le transformer "
                            "en collection, elle ne connaît pas la vraie compatibilité matière/style de tes articles."
                        )
                        articles_pack = st.multiselect(
                            "Articles à combiner (laisse vide pour que l'IA choisisse dans tout le catalogue)",
                            df_catalogue["nom"].dropna().tolist(), key="ia_articles_pack"
                        )
                        if st.button("🤖 Proposer un pack", key="ia_generer_pack"):
                            if articles_pack:
                                liste_catalogue_pack = ", ".join(articles_pack)
                            else:
                                liste_catalogue_pack = ", ".join(df_catalogue["nom"].dropna().tolist()[:30])
                            prompt_pack = (
                                f"Voici le catalogue (ou une sélection) de la boutique de luxe « {config.get('nom_boutique', 'la boutique')} » : "
                                f"{liste_catalogue_pack}. Compose UN pack cohérent de 2 à 4 articles pris dans cette liste "
                                f"(ne pas inventer d'articles). Réponds STRICTEMENT dans ce format :\n"
                                f"NOM DU PACK: <nom accrocheur>\nARTICLES: <liste des articles séparés par des virgules, "
                                f"exactement comme dans la liste fournie>\nPOURQUOI: <1-2 phrases expliquant l'association>"
                            )
                            with st.spinner("Génération en cours..."):
                                texte_pack, erreur_pack = generer_texte_ia(prompt_pack, max_tokens=250)
                            if erreur_pack:
                                st.error(f"❌ {erreur_pack}")
                            else:
                                ss["ia_pack_genere"] = texte_pack

                        if ss.get("ia_pack_genere"):
                            st.text_area(
                                "Suggestion de pack (vérifie la cohérence avant de créer la collection)",
                                value=ss["ia_pack_genere"],
                                key="ia_pack_editable",
                                height=140,
                            )
                            st.caption(
                                "Pour transformer cette suggestion en vraie collection avec expiration, "
                                "utilise l'onglet « ⚡ Flash Sales & Collections » juste à côté."
                            )

                        st.divider()
                        st.markdown("#### 📅 Idées de contenu sur 30 jours")
                        if st.button("🤖 Générer un calendrier de contenu", key="ia_generer_calendrier"):
                            prompt_calendrier = (
                                f"Tu gères les réseaux sociaux de la boutique de luxe « {config.get('nom_boutique', 'la boutique')} », "
                                f"catégories principales : {', '.join(df_catalogue['categorie'].dropna().unique().tolist()[:8]) or 'articles de luxe'}. "
                                f"Propose 30 idées de contenu, une par jour (posts, stories, mises en avant produit, "
                                f"témoignages clients, coulisses...), variées et courtes (une ligne chacune). "
                                f"Réponds STRICTEMENT au format :\nJour 1: <idée>\nJour 2: <idée>\n... jusqu'à Jour 30."
                            )
                            with st.spinner("Génération en cours (peut prendre un peu plus de temps)..."):
                                texte_calendrier, erreur_calendrier = generer_texte_ia(prompt_calendrier, max_tokens=1100)
                            if erreur_calendrier:
                                st.error(f"❌ {erreur_calendrier}")
                            else:
                                ss["ia_calendrier_genere"] = texte_calendrier

                        if ss.get("ia_calendrier_genere"):
                            st.text_area(
                                "Calendrier généré",
                                value=ss["ia_calendrier_genere"],
                                key="ia_calendrier_editable",
                                height=400,
                            )

                        st.divider()
                        st.markdown("#### 🎯 Offre personnalisée à partir de l'historique client")
                        st.caption(
                            "⚠️ Envoie l'historique d'achat de ce client vers le fournisseur IA choisi "
                            "(Groq/Gemini/DeepSeek). N'utilise cette fonction que si tu es à l'aise avec ce partage."
                        )
                        tel_historique = st.text_input("Numéro de téléphone du client", key="ia_tel_historique")
                        if st.button("🤖 Analyser et proposer une offre", key="ia_generer_offre_client"):
                            tel_normalise_hist = re.sub(r"\D", "", tel_historique or "")
                            if not tel_normalise_hist:
                                st.warning("Merci de renseigner un numéro de téléphone.")
                            else:
                                reponse_historique = (
                                    sb_admin.table("commandes")
                                    .select("articles, price, date, statut")
                                    .eq("marchand_id", MARCHAND_ID)
                                    .eq("tel", tel_normalise_hist)
                                    .order("date", desc=True)
                                    .limit(20)
                                    .execute()
                                )
                                commandes_client = reponse_historique.data or []
                                if not commandes_client:
                                    st.info("Aucune commande trouvée pour ce numéro.")
                                else:
                                    resume_commandes = "; ".join(
                                        f"{c.get('date', '')[:10]} : {c.get('articles')} ({int(c.get('price') or 0)} FCFA, {c.get('statut')})"
                                        for c in commandes_client
                                    )
                                    prompt_offre = (
                                        f"Voici l'historique de commandes d'un client de la boutique de luxe "
                                        f"« {config.get('nom_boutique', 'la boutique')} » : {resume_commandes}. "
                                        f"Propose une courte offre personnalisée (2-3 phrases, message prêt à envoyer "
                                        f"par WhatsApp) qui s'appuie sur ce qu'il a déjà acheté, sans inventer de "
                                        f"remise chiffrée précise sauf si tu restes cohérent et raisonnable (max 15%)."
                                    )
                                    with st.spinner("Analyse en cours..."):
                                        texte_offre, erreur_offre = generer_texte_ia(prompt_offre, max_tokens=220)
                                    if erreur_offre:
                                        st.error(f"❌ {erreur_offre}")
                                    else:
                                        ss["ia_offre_genere"] = texte_offre

                        if ss.get("ia_offre_genere"):
                            st.text_area(
                                "Offre personnalisée générée",
                                value=ss["ia_offre_genere"],
                                key="ia_offre_editable",
                                height=120,
                            )

                # ---- Flash Sales (compte à rebours) + Collections temporaires ----
                with sous_tab_flash:
                    st.markdown("#### ⚡ Flash Sale sur un article")
                    st.caption(
                        "Applique un prix promo avec une date de fin précise : un compte "
                        "à rebours s'affiche automatiquement sur la boutique."
                    )
                    if df_catalogue.empty:
                        st.caption("Ajoute d'abord des articles dans l'onglet Catalogue.")
                    else:
                        with st.form("form_flash_sale"):
                            produit_flash = st.selectbox(
                                "Article", df_catalogue["nom"].dropna().tolist(), key="flash_produit_choisi"
                            )
                            ligne_flash = df_catalogue[df_catalogue["nom"] == produit_flash].iloc[0]
                            prix_flash = st.number_input(
                                "Prix flash (FCFA)", min_value=0.0,
                                value=float(ligne_flash.get("prix_promo") or 0) or float(ligne_flash.get("prix") or 0),
                                step=500.0,
                            )
                            col_date, col_heure = st.columns(2)
                            date_fin_flash = col_date.date_input("Date de fin", value=datetime.now().date())
                            heure_fin_flash = col_heure.time_input("Heure de fin", value=datetime.now().time().replace(second=0, microsecond=0))
                            desactiver_flash = st.checkbox("Désactiver le flash sale sur cet article")
                            if st.form_submit_button("⚡ Lancer / mettre à jour le flash sale"):
                                if desactiver_flash:
                                    maj_flash = {"prix_promo": None, "promo_expire_le": None}
                                else:
                                    fin_datetime = datetime.combine(
                                        date_fin_flash, heure_fin_flash, tzinfo=FUSEAU_BOUTIQUE
                                    ).astimezone(timezone.utc)
                                    maj_flash = {
                                        "prix_promo": prix_flash,
                                        "promo_expire_le": fin_datetime.isoformat(),
                                    }
                                try:
                                    sb_admin.table("catalogue").update(maj_flash).eq("id", ligne_flash["id"]).eq("marchand_id", MARCHAND_ID).execute()
                                except Exception:
                                    logger.exception("Échec enregistrement flash sale")
                                    st.error("❌ L'enregistrement a échoué. Réessaie dans un instant.")
                                else:
                                    forcer_rafraichissement()
                                    st.success("Flash sale désactivé." if desactiver_flash else "Flash sale enregistré.")
                                    st.rerun()

                    st.divider()
                    st.markdown("#### ⭐ Collections temporaires")
                    st.caption(
                        "Une collection expire d'elle-même après le nombre de jours choisi "
                        "-- elle disparaît alors du filtre de la boutique, effet d'exclusivité."
                    )
                    with st.form("form_nouvelle_collection", clear_on_submit=True):
                        nom_collection = st.text_input("Nom de la collection", placeholder="Ex : Collection Ramadan")
                        description_collection = st.text_area("Description (facultatif)")
                        duree_jours = st.number_input(
                            "Disparaît après combien de jours ? (0 = jamais)", min_value=0, value=7
                        )
                        if st.form_submit_button("➕ Créer la collection"):
                            if not nom_collection.strip():
                                st.warning("Merci de donner un nom à la collection.")
                            else:
                                expire_le = (
                                    (datetime.now(timezone.utc) + pd.Timedelta(days=int(duree_jours))).isoformat()
                                    if duree_jours > 0 else None
                                )
                                try:
                                    sb_admin.table("collections").insert({
                                        "marchand_id": MARCHAND_ID,
                                        "nom": nom_collection.strip(),
                                        "description": description_collection.strip() or None,
                                        "expire_le": expire_le,
                                        "actif": True,
                                    }).execute()
                                except Exception:
                                    logger.exception("Échec création collection")
                                    st.error("❌ La création a échoué. Réessaie dans un instant.")
                                else:
                                    forcer_rafraichissement()
                                    st.success("Collection créée.")
                                    st.rerun()

                    collections_du_marchand = charger_collections(MARCHAND_ID, ss.refresh_token)
                    if collections_du_marchand:
                        st.markdown("##### Tes collections")
                        for coll in collections_du_marchand:
                            statut_coll = "🟢 Active" if coll.get("actif") else "⚪ Désactivée"
                            if coll not in collections_actives_non_expirees(collections_du_marchand):
                                statut_coll = "⏳ Expirée" if coll.get("actif") else "⚪ Désactivée"
                            col_nom_coll, col_action_coll = st.columns([3, 1])
                            col_nom_coll.write(f"**{coll['nom']}** — {statut_coll}")
                            if col_action_coll.button("🗑️ Supprimer", key=f"suppr_coll_{coll['id']}"):
                                sb_admin.table("collections").delete().eq("id", coll["id"]).eq("marchand_id", MARCHAND_ID).execute()
                                forcer_rafraichissement()
                                st.rerun()

                        st.markdown("##### Assigner des articles à une collection")
                        noms_coll_actives = {c["nom"]: c["id"] for c in collections_du_marchand}
                        collection_cible = st.selectbox("Collection", list(noms_coll_actives.keys()), key="collection_cible_assign")
                        articles_a_assigner = st.multiselect(
                            "Articles à ajouter à cette collection",
                            df_catalogue["nom"].dropna().tolist(), key="articles_assign_collection"
                        )
                        if st.button("💾 Assigner à la collection", key="assigner_collection_bouton"):
                            ids_articles = df_catalogue[df_catalogue["nom"].isin(articles_a_assigner)]["id"].tolist()
                            if ids_articles:
                                sb_admin.table("catalogue").update(
                                    {"collection_id": noms_coll_actives[collection_cible]}
                                ).in_("id", ids_articles).eq("marchand_id", MARCHAND_ID).execute()
                                forcer_rafraichissement()
                                st.success(f"{len(ids_articles)} article(s) ajouté(s) à « {collection_cible} ».")
                                st.rerun()

                # ---- Club VIP ----
                with sous_tab_vip:
                    st.markdown("#### 👑 Offre exclusive Club VIP")
                    st.caption("Visible uniquement par les clients reconnus comme VIP sur ta boutique.")
                    with st.form("form_offre_vip"):
                        vip_actif_input = st.checkbox("Activer l'offre VIP", value=bool(config.get("vip_offre_actif")))
                        vip_titre_input = st.text_input(
                            "Titre de l'offre", value=config.get("vip_offre_titre") or "",
                            placeholder="Ex : Merci pour votre fidélité !"
                        )
                        vip_texte_input = st.text_area(
                            "Texte de l'offre", value=config.get("vip_offre_texte") or "",
                            placeholder="Ex : -15% sur votre prochaine commande, réservé à nos clients VIP."
                        )
                        vip_code_input = st.text_input(
                            "Code promo VIP (facultatif)", value=config.get("vip_offre_code") or ""
                        )
                        if st.form_submit_button("💾 Enregistrer l'offre VIP"):
                            if vip_actif_input and not vip_titre_input.strip():
                                st.warning("Ajoute au moins un titre avant d'activer l'offre VIP.")
                            else:
                                try:
                                    sb_admin.table("marchands").update({
                                        "vip_offre_actif": vip_actif_input,
                                        "vip_offre_titre": vip_titre_input.strip() or None,
                                        "vip_offre_texte": vip_texte_input.strip() or None,
                                        "vip_offre_code": vip_code_input.strip() or None,
                                    }).eq("id", MARCHAND_ID).execute()
                                except Exception:
                                    logger.exception("Échec enregistrement offre VIP")
                                    st.error("❌ L'enregistrement a échoué. Réessaie dans un instant.")
                                else:
                                    forcer_rafraichissement()
                                    st.success("Offre VIP mise à jour.")
                                    st.rerun()

                    st.divider()
                    st.markdown("#### Membres du Club VIP")
                    with st.form("form_ajout_vip", clear_on_submit=True):
                        nom_vip = st.text_input("Nom du client")
                        tel_vip = st.text_input("Téléphone")
                        if st.form_submit_button("➕ Ajouter au Club VIP"):
                            tel_vip_normalise = re.sub(r"\D", "", tel_vip or "")
                            if not tel_vip_normalise:
                                st.warning("Merci de renseigner un numéro de téléphone.")
                            else:
                                try:
                                    sb_admin.table("clients_vip").upsert({
                                        "marchand_id": MARCHAND_ID,
                                        "telephone": tel_vip_normalise,
                                        "nom": nom_vip.strip() or None,
                                    }, on_conflict="marchand_id,telephone").execute()
                                except Exception:
                                    logger.exception("Échec ajout client VIP")
                                    st.error("❌ L'ajout a échoué. Réessaie dans un instant.")
                                else:
                                    st.success("Client ajouté au Club VIP.")
                                    st.rerun()

                    reponse_vip_liste = (
                        sb_admin.table("clients_vip")
                        .select("id, nom, telephone")
                        .eq("marchand_id", MARCHAND_ID)
                        .order("ajoute_le", desc=True)
                        .execute()
                    )
                    membres_vip = reponse_vip_liste.data or []
                    if not membres_vip:
                        st.caption("Aucun membre VIP pour le moment.")
                    else:
                        for membre in membres_vip:
                            col_membre, col_suppr_membre = st.columns([3, 1])
                            col_membre.write(f"👑 {membre.get('nom') or 'Client'} — {membre['telephone']}")
                            if col_suppr_membre.button("🗑️", key=f"suppr_vip_{membre['id']}"):
                                sb_admin.table("clients_vip").delete().eq("id", membre["id"]).eq("marchand_id", MARCHAND_ID).execute()
                                st.rerun()

                # ---- Mise en vedette dans la vitrine commune ----
                with sous_tab_vedette:
                    st.caption(
                        "Une boutique en vedette apparaît dans la vitrine commune de la "
                        "marketplace, visible par tous les visiteurs à la recherche d'une "
                        "boutique — une publicité gratuite en plus de ta propre boutique."
                    )
                    with st.form("form_en_vedette"):
                        en_vedette_input = st.checkbox(
                            "Apparaître dans la vitrine commune",
                            value=bool(config.get("en_vedette"))
                        )
                        if st.form_submit_button("💾 Enregistrer"):
                            try:
                                sb_admin.table("marchands").update({
                                    "en_vedette": en_vedette_input,
                                }).eq("id", MARCHAND_ID).execute()
                            except Exception:
                                logger.exception("Échec enregistrement mise en vedette")
                                st.error("❌ L'enregistrement a échoué. Réessaie dans un instant.")
                            else:
                                forcer_rafraichissement()
                                st.success("Préférence de mise en vedette enregistrée.")
                                st.rerun()

                # ---- Diffusion WhatsApp vers les anciens clients ----
                with sous_tab_diffusion:
                    st.caption(
                        "Compose un message, puis clique sur chaque client pour lui "
                        "envoyer via WhatsApp (ouvre une conversation pré-remplie -- "
                        "l'envoi reste manuel, un clic par client, WhatsApp ne permettant "
                        "pas l'envoi groupé automatique sans une API Business payante)."
                    )
                    message_diffusion = st.text_area(
                        "Message à diffuser",
                        placeholder=f"Ex : Nouvelle collection disponible chez {config.get('nom_boutique', 'notre boutique')} !",
                        key="message_diffusion_marketing"
                    )
                    reponse_clients = (
                        sb_admin.table("commandes")
                        .select("client_nom, tel")
                        .eq("marchand_id", MARCHAND_ID)
                        .order("date", desc=True)
                        .limit(200)
                        .execute()
                    )
                    clients_vus = {}
                    for cmd_client in (reponse_clients.data or []):
                        tel_client = re.sub(r"\D", "", str(cmd_client.get("tel") or ""))
                        if tel_client and tel_client not in clients_vus:
                            clients_vus[tel_client] = cmd_client.get("client_nom") or "Client"

                    if not clients_vus:
                        st.caption("Aucun client avec un numéro de téléphone dans les commandes pour le moment.")
                    elif not message_diffusion.strip():
                        st.caption(f"{len(clients_vus)} client(s) trouvé(s) — écris un message ci-dessus pour générer les liens.")
                    else:
                        st.write(f"**{len(clients_vus)} client(s)** — clique pour envoyer à chacun :")
                        texte_encode = requests.utils.quote(message_diffusion)
                        for tel_client, nom_client in clients_vus.items():
                            col_nom, col_bouton = st.columns([3, 2])
                            col_nom.write(f"📞 {nom_client} — {tel_client}")
                            col_bouton.link_button(
                                "💬 WhatsApp",
                                f"https://wa.me/{tel_client}?text={texte_encode}",
                                key=f"diffusion_wa_{tel_client}"
                            )
