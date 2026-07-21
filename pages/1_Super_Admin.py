import streamlit as st
import bcrypt
import re
from datetime import datetime, timezone
from supabase import create_client, Client

# ====================================================================
# SUPER ADMIN — gestion des marchands (multi-boutiques)
# ====================================================================
# Cette page est SÉPARÉE de l'admin de chaque boutique (qui reste géré
# dans app.py, protégé par le mot de passe propre à chaque marchand).
# Ici, un seul mot de passe MAÎTRE (toi seul le connais) donne accès à
# la liste de TOUTES les boutiques et permet de :
#   - en ajouter une nouvelle (avec coordonnées du marchand)
#   - changer son statut (actif / grâce / suspendu / résilié...)
#   - éditer les coordonnées du marchand (nom, téléphone, adresse)
#   - réinitialiser son mot de passe admin
#   - la supprimer définitivement
#
# 🔑 CONFIGURATION REQUISE (fichier .streamlit/secrets.toml, à côté des
# secrets déjà utilisés par app.py) :
#   SUPER_ADMIN_PASSWORD = "choisis-un-mot-de-passe-fort-different-des-autres"
#
# 🗄️ COLONNES REQUISES en base (à lancer une seule fois dans le SQL
# Editor de Supabase avant d'utiliser cette page) :
#   alter table public.marchands
#     add column if not exists nom_marchand text,
#     add column if not exists telephone_marchand text,
#     add column if not exists adresse_marchand text;
#
# 📱 Sur mobile : cette page apparaît automatiquement dans le menu ☰
# (barre de navigation Streamlit multipage) puisqu'elle est dans le
# dossier pages/. Tu peux aussi "Ajouter à l'écran d'accueil" depuis ton
# navigateur pour y accéder en un seul tap, comme une app.
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


# ---------------------- Connexion (mot de passe maître) ----------------------
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


# ---------------------- Panneau principal ----------------------
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

# ---------------------- Ajouter une boutique ----------------------
with st.expander("➕ Ajouter une nouvelle boutique"):
    with st.form("ajouter_marchand", clear_on_submit=True):
        nouveau_nom = st.text_input("Nom de la boutique")
        nouveau_slug = st.text_input(
            "Identifiant URL (slug)",
            help="Lettres minuscules, chiffres et tirets uniquement. Ex : ma-boutique",
        )
        nouveau_mdp = st.text_input("Mot de passe admin initial", type="password")
        nouveau_statut = st.selectbox("Statut", STATUTS, index=0)

        st.markdown("**Coordonnées du marchand**")
        nouveau_nom_marchand = st.text_input("Nom du marchand")
        nouveau_telephone = st.text_input("Téléphone")
        nouvelle_adresse = st.text_input("Adresse")

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
                        "nom_marchand": nouveau_nom_marchand or None,
                        "telephone_marchand": nouveau_telephone or None,
                        "adresse_marchand": nouvelle_adresse or None,
                    }).execute()
                except Exception as e:
                    st.error(f"Échec de la création : {e}")
                else:
                    st.success(f"Boutique « {nouveau_nom} » créée. Accessible via ?boutique={nouveau_slug}")
                    st.rerun()

st.divider()

# ---------------------- Liste des boutiques ----------------------
if not marchands:
    st.caption("Aucune boutique pour le moment.")

for m in marchands:
    statut = m.get("statut_abonnement", "")
    with st.container(border=True):
        st.markdown(f"**{m.get('nom_boutique', 'Sans nom')}** — `{m.get('slug')}`")
        st.markdown(LABELS_STATUT.get(statut, statut))

        # Coordonnées du marchand, affichées si renseignées
        nom_marchand = m.get("nom_marchand")
        telephone_marchand = m.get("telephone_marchand")
        adresse_marchand = m.get("adresse_marchand")
        if nom_marchand or telephone_marchand or adresse_marchand:
            if nom_marchand:
                st.caption(f"👤 {nom_marchand}")
            if telephone_marchand:
                st.caption(f"📞 {telephone_marchand}")
            if adresse_marchand:
                st.caption(f"📍 {adresse_marchand}")
        else:
            st.caption("Aucune coordonnée renseignée pour ce marchand.")

        # ---- Changer le statut : sélecteur explicite + bouton, pas de doute possible ----
        with st.form(f"statut_{m['id']}"):
            nouveau_statut_choisi = st.selectbox(
                "Statut de la boutique",
                STATUTS,
                index=STATUTS.index(statut) if statut in STATUTS else 0,
                format_func=lambda s: LABELS_STATUT.get(s, s),
                key=f"select_statut_{m['id']}",
            )
            if st.form_submit_button("💾 Enregistrer le statut"):
                sb.table("marchands").update(
                    {"statut_abonnement": nouveau_statut_choisi}
                ).eq("id", m["id"]).execute()
                st.success(f"Statut mis à jour : {LABELS_STATUT.get(nouveau_statut_choisi, nouveau_statut_choisi)}")
                st.rerun()

        # ---- Coordonnées du marchand ----
        with st.expander("✏️ Modifier les coordonnées du marchand"):
            with st.form(f"contact_{m['id']}"):
                edit_nom = st.text_input("Nom du marchand", value=nom_marchand or "")
                edit_tel = st.text_input("Téléphone", value=telephone_marchand or "")
                edit_adresse = st.text_input("Adresse", value=adresse_marchand or "")
                if st.form_submit_button("Enregistrer les coordonnées"):
                    sb.table("marchands").update({
                        "nom_marchand": edit_nom or None,
                        "telephone_marchand": edit_tel or None,
                        "adresse_marchand": edit_adresse or None,
                    }).eq("id", m["id"]).execute()
                    st.success("Coordonnées mises à jour.")
                    st.rerun()

        # ---- Mot de passe ----
        with st.expander("🔑 Réinitialiser le mot de passe"):
            with st.form(f"reset_mdp_{m['id']}", clear_on_submit=True):
                mdp_reset = st.text_input("Nouveau mot de passe", type="password", key=f"mdp_input_{m['id']}")
                if st.form_submit_button("Réinitialiser"):
                    if len(mdp_reset) < 6:
                        st.warning("Le mot de passe doit contenir au moins 6 caractères.")
                    else:
                        sb.table("marchands").update(
                            {"mot_de_passe_hash": hash_mot_de_passe(mdp_reset)}
                        ).eq("id", m["id"]).execute()
                        st.success("Mot de passe mis à jour.")

        # ---- Suppression ----
        with st.expander("🗑️ Supprimer définitivement"):
            st.warning(
                "Supprime la boutique et peut casser les données liées "
                "(catalogue, commandes, avis...) si elles référencent cette "
                "boutique. Préfère « Résilier » si tu veux juste bloquer l'accès."
            )
            confirmation = st.checkbox(
                f"Je confirme vouloir supprimer « {m.get('nom_boutique')} »",
                key=f"confirm_del_{m['id']}",
            )
            if st.button("Supprimer", key=f"del_{m['id']}", disabled=not confirmation):
                try:
                    sb.table("marchands").delete().eq("id", m["id"]).execute()
                except Exception as e:
                    st.error(f"Échec de la suppression : {e}")
                else:
                    st.success("Boutique supprimée.")
                    st.rerun()
