import streamlit as st
import html as html_lib
from supabase import create_client, Client

# ====================================================================
# VITRINE DES BOUTIQUES — page publique de la marketplace
# ====================================================================
# Liste les boutiques qui ont le module Marketing & Pub (premium) ET qui
# ont choisi d'apparaître ici (onglet "📣 Marketing" > "⭐ Mise en vedette"
# dans leur admin, app.py). Une boutique suspendue ou résiliée n'apparaît
# jamais ici, même si elle a coché la case, pour ne pas envoyer de trafic
# vers une boutique fermée.
#
# 📱 Sur mobile : cette page apparaît automatiquement dans le menu ☰
# puisqu'elle est dans le dossier pages/, comme 1_Super_Admin.py.
# ====================================================================

st.set_page_config(page_title="Nos boutiques", page_icon="✨", layout="wide")


@st.cache_resource
def get_public_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


sb = get_public_client()


@st.cache_data(ttl=120)
def charger_boutiques_en_vedette():
    reponse = (
        sb.table("marchands")
        .select("nom_boutique, slogan, logo, slug, statut_abonnement, palier_abonnement, en_vedette, theme_couleur")
        .eq("palier_abonnement", "premium")
        .eq("en_vedette", True)
        .in_("statut_abonnement", ["actif", "en_grace"])
        .execute()
    )
    return reponse.data or []


st.markdown(
    """
    <style>
    @keyframes aura-shimmer-vitrine {
        0% { background-position: 0% 50%; }
        100% { background-position: 300% 50%; }
    }
    .aura-badge-vitrine {
        display: inline-flex; align-items: center; gap: 6px;
        background: linear-gradient(120deg, #f0d9a6, #c9a35c, #f0d9a6, #c9a35c);
        background-size: 300% 100%;
        animation: aura-shimmer-vitrine 3.5s linear infinite;
        color: #16151a; font-weight: 700; font-size: 0.78rem;
        padding: 3px 11px; border-radius: 20px; letter-spacing: 0.3px;
        margin-bottom: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<h1 style='text-align:center;'>✨ Nos boutiques</h1>"
    "<p style='text-align:center; color:#9a9086;'>Découvre les boutiques mises en avant sur la marketplace.</p>",
    unsafe_allow_html=True,
)

boutiques = charger_boutiques_en_vedette()

if not boutiques:
    st.info("Aucune boutique en vedette pour le moment — revenez bientôt !")
else:
    colonnes = st.columns(3)
    for idx, boutique in enumerate(boutiques):
        with colonnes[idx % 3]:
            couleur_accent = boutique.get("theme_couleur") or "#c9a35c"
            with st.container(border=True):
                st.markdown(
                    f'<div style="border-top:3px solid {html_lib.escape(couleur_accent, quote=True)}; '
                    f'margin:-17px -17px 12px -17px; border-radius:8px 8px 0 0;"></div>',
                    unsafe_allow_html=True,
                )
                st.markdown('<span class="aura-badge-vitrine">✨ Aura Luxe</span>', unsafe_allow_html=True)
                logo_url = boutique.get("logo") or ""
                if logo_url:
                    st.image(logo_url, use_container_width=True)
                st.markdown(f"### {html_lib.escape(boutique.get('nom_boutique') or 'Boutique')}")
                if boutique.get("slogan"):
                    st.caption(html_lib.escape(boutique["slogan"]))
                slug = boutique.get("slug") or ""
                st.link_button("🛍️ Visiter la boutique", f"/?boutique={slug}", use_container_width=True)
