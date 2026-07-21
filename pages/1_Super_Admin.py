import streamlit as st
import bcrypt
import re
from datetime import datetime, timezone
from supabase import create_client, Client

# ====================================================================
# SUPER ADMIN — gestion des marchands (multi-boutiques)
# ====================================================================
st.set_page_config(page_title="Super Admin — Boutiques", page_icon="🛠️", layout="centered")


@st.cache_resource
def get_admin_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SECRET_KEY"])


sb = get_admin_client()

STATUTS = ["actif", "en_grace", "en_attente_paiement", "suspendu", "resilie"]
LABELS_STATUT = {
    "actif": "🟢 Actif",
    "en_grace": "🟡 En grâce",
    "en_attente_paiement": "🟠 En attente de paiement",
    "suspendu": "🔴 Suspendu",
    "resilie": "⚫ Résilié",
}

SEUIL_TENTATIVES = 5
DUREE_VERROU_SEC = 300


def hash_mot_de_passe(valeur: str) -> str:
    return bcrypt.hashpw(valeur.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def slug_valide(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug or ""))


if "super_admin_connecte" not in st.session_state:
    st.session_state.super_admin_connecte = False

if not st.session_state.super_admin_connecte:
    st.title("🛠️ Super Admin")
    st.caption("Accès réservé au propriétaire de l'application.")

    maintenant = datetime.now(timezone.utc).timestamp()
    verrou_jusqu_a = st.session_state.get("super_admin_verrou_jusqu_a", 0)
    if maintenant < verrou_jusqu_a:
        restant = int(verrou_jusqu_a - maintenant)
        st.error(f"Trop de tentatives échouées. Réessaie dans {restant} seconde(s).")
        st.stop()

    with st.form("super_admin_login"):
        mdp = st.text_input("Mot de passe maître", type="password")
        if st.form_submit_button("Se connecter"):
            secret_attendu = st.secrets.get("SUPER_ADMIN_PASSWORD")
            if secret_attendu and mdp == secret_attendu:
                st.session_state.super_admin_connecte = True
                st.session_state.super_admin_tentatives = 0
                st.rerun()
            else:
                tentatives = st.session_state.get("super_admin_tentatives", 0) + 1
                st.session_state.super_admin_tentatives = tentatives
                if tentatives >= SEUIL_TENTATIVES:
                    st.session_state.super_admin_verrou_jusqu_a = maintenant + DUREE_VERROU_SEC
                    st.session_state.super_admin_tentatives = 0
                    st.error(f"Trop de tentatives échouées. Réessaie dans {DUREE_VERROU_SEC // 60} minute(s).")
                else:
                    st.error("Mot de passe incorrect.")
    st.stop()


col_titre, col_deco = st.columns([4, 1])
with col_titre:
    st.title("🛠️ Boutiques")
with col_deco:
    if st.button("Déconnexion"):
        st.session_state.super_admin_connecte = False
        st.rerun()

reponse = sb.table("marchands").select("*").order("nom_boutique").execute()
marchands = reponse.data or []

st.caption(f"{len(marchands)} boutique(s) enregistrée(s)")

with st.expander("➕ Ajouter une nouvelle boutique"):
    with st.form("ajouter_marchand", clear_on_submit=True):
        nouveau_nom = st.text_input("Nom de la boutique")
        nouveau_slug = st.text_input(
            "Identifiant URL (slug)",
            help="Lettres minuscules, chiffres et tirets uniquement. Ex : ma-boutique",
        )
        nouveau_mdp = st.text_input("Mot de passe admin initial", type="password")
        nouveau_statut = st.selectbox("Statut", STATUTS, index=0)
        if st.form_submit_button("Créer la boutique"):
            if not nouveau_nom.strip():
                st.warning("Le nom de la boutique est requis.")
            elif not slug_valide(nouveau_slug):
                st.warning("Le slug doit être en minuscules, sans espaces ni accents (ex : ma-boutique).")
            elif len(nouveau_mdp) < 6:
                st.warning("Le mot de passe doit contenir au moins 6 caractères.")
            elif any(m["slug"] == nouveau_slug for m in marchands):
                st.warning("Ce slug est déjà utilisé par une autre boutique.")
            else:
                try:
                    sb.table("marchands").insert({
                        "slug": nouveau_slug,
                        "nom_boutique": nouveau_nom,
                        "statut_abonnement": nouveau_statut,
                        "mot_de_passe_hash": hash_mot_de_passe(nouveau_mdp),
                    }).execute()
                except Exception as e:
                    st.error(f"Échec de la création : {e}")
                else:
                    st.success(f"Boutique « {nouveau_nom} » créée. Accessible via ?boutique={nouveau_slug}")
                    st.rerun()

st.divider()

if not marchands:
    st.caption("Aucune boutique pour le moment.")

for m in marchands:
    statut = m.get("statut_abonnement", "")
    with st.container(border=True):
        st.markdown(f"**{m.get('nom_boutique', 'Sans nom')}** — `{m.get('slug')}`")
        st.caption(LABELS_STATUT.get(statut, statut))

        cols = st.columns(4)
