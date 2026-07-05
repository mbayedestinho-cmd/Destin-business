import streamlit as st
import pandas as pd
import requests
# ==============================================================================
# 1. CONFIGURATION DE LA PAGE & STYLE VISUEL "LUXE"
# ==============================================================================
st.set_page_config(
    page_title="Collection Luxe N'Djamena",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="collapsed"
)
# Injection de styles CSS pour forcer un rendu premium et mobile-friendly
st.markdown("""
    <style>
    /* Fond de page blanc et épuré */
    .main { background-color: #FFFFFF; }
   
    /* Boutons personnalisés couleur Or / Or Doré */
    div.stButton > button:first-child, .stDownloadButton>button {
        background-color: #D4AF37 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
        width: 100% !important;
        padding: 12px !important;
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #B7791F !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.15);
    }
   
    /* Liens hypertexte transformés en boutons élégants */
    a.stLinkButton {
        width: 100% !important;
    }
   
    /* Séparateurs fins */
    hr { border-top: 1px solid #E2E8F0; }
    </style>
""", unsafe_allow_html=True)
# ==============================================================================
# 2. RÉCUPÉRATION SÉCURISÉE DES SECRETS STREAMLIT
# ==============================================================================
try:
    ID_SHEET = st.secrets["ID_DU_SHEET"]
    URL_PASSERELLE = st.secrets["URL_PASSERELLE_WEB"]
    CODE_ADMIN = st.secrets["CODE_SECRET_ADMIN"]
    NUMERO_WHATSAPP = st.secrets.get("NUMERO_WHATSAPP", "23566000000")
except Exception:
    st.error("⚠️ Erreur : Les secrets Streamlit (ID_DU_SHEET, URL_PASSERELLE_WEB, etc.) ne sont pas configurés sur votre tableau de bord Streamlit Cloud.")
    st.stop()
# ==============================================================================
# 3. SYSTÈME DE CHARGEMENT DE LA BASE DE DONNÉES (GOOGLE SHEETS)
# ==============================================================================
@st.cache_data(ttl=60) 
def charger_catalogue():
    url_csv = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/gviz/tq?tqx=out:csv"
    try:
        df = pd.read_csv(url_csv)
        df.columns = [col.lower().strip() for col in df.columns]
        return df.to_dict(orient="records")
    except Exception as e:
        st.error(f"Impossible de synchroniser le catalogue : {e}")
        return []
catalogue = charger_catalogue()
# ==============================================================================
# 4. STRUCTURE DE L'INTERFACE (ONGLETS FLUIDES)
# ==============================================================================
onglet_visiteur, onglet_admin = st.tabs(["🛒 Boutique Visiteur", "⚙️ Panneau de Contrôle Admin"])
# ------------------------------------------------------------------------------
# INTERFACE CLIENT : LA BOUTIQUE
# ------------------------------------------------------------------------------
with onglet_visiteur:
    st.title("👑 Collection Luxe N'Djamena")
    st.write("Parcourez nos pièces exclusives et commandez directement sur WhatsApp.")
    st.write("---")
   
    if not catalogue:
        st.info("🛍️ Le catalogue est vide ou en cours de chargement. Revenez dans un instant !")
    else:
        col_recherche, col_budget = st.columns([2, 1])
        with col_recherche:
            recherche = st.text_input("🔍 Rechercher un modèle...", placeholder="Ex: Robe, Costume, Veste...")
        with col_budget:
            prix_max = st.number_input("💰 Budget max (FCFA)", value=150000, step=5000)
           
        st.write("") 
       
        produits_filtres = [
            p for p in catalogue
            if (str(recherche).lower() in str(p.get("nom", "")).lower()) and (float(p.get("prix", 0)) <= prix_max)
        ]
       
        if not produits_filtres:
            st.warning("Aucun vêtement ne correspond à vos critères actuels.")
        else:
            for produit in produits_filtres:
                nom = produit.get("nom", "Article sans nom")
                prix = produit.get("prix", 0)
                url_image = produit.get("image", "")
               
                st.subheader(f"{nom}")
                st.markdown(f"**💰 Prix :** {int(prix):,} FCFA".replace(",", " "))
               
                if pd.isna(url_image) or not str(url_image).startswith("http"):
                    st.info("📷 Image en cours de chargement par l'administrateur")
                else:
                    st.image(url_image, use_container_width=True)
               
                # Correction ici : Utilisation de la bonne varia
                message_client = f"Bonjour Collection Luxe N'Djamena, je souhaite commander l'article suivant :\n\n- *Produit :* {nom}\n- *Prix :* {int(prix):,} FCFA".replace(",", " ")
                texte_encode = requests.utils.quote(message_client)
                lien_whatsapp_final = f"https://wa.me/{NUMERO_WHATSAPP}?text={texte_encode}"
               
                st.link_button("🛍️ Commander cet article", lien_whatsapp_final)
                st.write("---")
# ------------------------------------------------------------------------------
# INTERFACE COMMERÇANT : LE PANNEAU DE GESTION
# ------------------------------------------------------------------------------
with onglet_admin:
    st.title("⚙️ Espace Administrator")
   
    mot_de_passe = st.text_input("Entrez le code secret de sécurité :", type="password")
   
    if mot_de_passe == CODE_ADMIN:
        st.success("🔓 Accès gestionnaire autorisé.")
        st.write("---")
        st.write("### ➕ Ajouter une nouveauté au catalogue")
       
        with st.form("formulaire_ajout", clear_on_submit=True):
            nouveau_nom = st.text_input("Nom du vêtement / de la pièce :", placeholder="Ex: Costume Slim Fit 3 Pièces")
            nouveau_prix = st.number_input("Prix de vente en boutique (FCFA) :", min_value=0, step=1000, value=25000)
            nouvelle_image_url = st.text_input("Lien direct (URL) de la photo :", placeholder="https://i.postimg.cc/.../photo.jpg")
           
            bouton_validation = st.form_submit_button("🚀 Mettre en vente immédiatement")
           
            if bouton_validation:
                if not nouveau_nom or not nouvelle_image_url:
                    st.error("❌ Erreur : Le nom de l'article et l'URL de sa photo sont obligatoires.")
                else:
                    donnees_produit = {
                        "nom": nouveau_nom,
                        "prix": int(nouveau_prix),
                        "image": nouvelle_image_url.strip()
                    }
                   
                    with st.spinner("Mise à jour du catalogue en cours..."):
                        try:
                            reponse = requests.post(URL_PASSERELLE, json=donnees_produit)
                            if reponse.status_code == 200:
                                st.success("🎉 Succès ! L'article est enregistré et visible sur la boutique.")
                                st.cache_data.clear()
                            else:
                                st.error(f"La passerelle Google a renvoyé un code d'erreur : {reponse.status_code}")
                        except Exception as erreur:
                            st.error(f"Erreur de communication réseau : {erreur}")
                           
    elif mot_de_passe != "":
        st.error("❌ Clé de sécurité incorrecte. Accès au panneau refusé.")
