import streamlit as st
import requests
import pandas as pd
# 1. Configuration de la page
st.set_page_config(
    page_title="Collection Luxe N'Djamena",
    page_icon="✨",
    layout="wide", # Utilise tout l'écran pour un effet moderne
    initial_sidebar_state="expanded"
)
# 2. Design VIP : Injection de CSS personnalisé pour le style Mode/Luxe
st.markdown("""
    <style>
    /* Changer la police globale et le fond */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;600&display=swap');
   
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #fcfbf9; /* Fond blanc cassé très élégant */
        font-family: 'Poppins', sans-serif;
    }
   
    /* Style des titres en police classique/luxe */
    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
        color: #1a1a1a !important;
        text-align: center;
    }
   
    /* Design des cartes de vêtements */
    .product-card {
        background-color: #ffffff;
        border: 1px solid #eef0f2;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.03);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 25px;
    }
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0px 10px 25px rgba(0, 0, 0, 0.08);
    }
   
    /* Style des images pour qu'elles soient toutes uniformes */
    .product-image {
        border-radius: 8px;
        object-fit: cover;
        width: 100%;
        height: 280px;
        margin-bottom: 15px;
    }
   
    /* Prix mis en valeur */
    .product-price {
        color: #b58328; /* Couleur Or/Bronze pour le côté Premium */
        font-weight: 600;
        font-size: 1.2rem;
        margin: 10px 0;
    }
   
    /* Personnalisation des boutons Streamlit */
    div.stButton > button {
        background-color: #1a1a1a !important; /* Bouton noir chic */
        color: white !important;
        border-radius: 6px !important;
        border: none !important;
        width: 100%;
        padding: 10px 0 !important;
        font-weight: 400 !important;
        transition: background 0.3s !important;
    }
    div.stButton > button:hover {
        background-color: #b58328 !important; /* Devient Or au survol */
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)
# --- EN-TÊTE DE LA BOUTIQUE ---
st.markdown("<h1>✨ COLLECTION LUXE N'DJAMENA ✨</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666; font-style: italic; font-size: 1.1rem;'>L'élégance et la haute couture à votre portée</p>", unsafe_allow_html=True)
st.write("---")
# --- CONNEXION RÉELLE À VOTRE GOOGLE SHEETS ---
try:
    # 1. Récupération de l'ID depuis vos secrets Streamlit Cloud
    id_sheet = st.secrets["ID_DU_SHEET"]
   
    # 2. Construction du lien d'export CSV automatique
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv"
   
    # 3. Lecture et traitement propre du tableau avec Pandas
    df = pd.read_csv(url_csv)
   
    # Nettoyage de sécurité : on force les noms de colonnes en minuscules
    df.columns = [col.lower().strip() for col in df.columns]
except Exception as e:
    st.error(f"⚠️ Impossible de charger le catalogue depuis Google Sheets : {e}")
    # En cas de problème, crée un tableau vide pour éviter le crash
    df = pd.DataFrame(columns=["nom", "prix", "image"])
# --- AFFICHAGE EN GRILLE MODERNE (3 colonnes) ---
st.subheader("🛍️ Notre Catalogue Exclusif")
# Création des colonnes dynamiques
cols = st.columns(3)
for index, row in df.iterrows():
    # Sélection de la colonne (0, 1 ou 2)
    with cols[index % 3]:
        # Encapsulation dans une carte HTML stylisée par notre CSS
        st.markdown(f"""
            <div class="product-card">
                <img class="product-image" src="{row['image']}">
                <h3 style='font-size: 1.3rem; margin-bottom: 5px;'>{row['nom']}</h3>
                <div class="product-price">{int(row['prix']):,} FCFA</div>
            </div>
        """, unsafe_allow_html=True)
       
        # Bouton d'action sous la carte
        if st.button(f"Commander {row['nom']}", key=f"btn_{index}"):
            st.success(f"🛒 {row['nom']} a été ajouté à votre panier !")
# --- PANNEAU ADMIN (Dissimulé proprement dans la barre latérale) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: left;'>⚙️ Zone Gestion Admin</h2>", unsafe_allow_html=True)
   
    with st.expander("➕ Ajouter une pièce"):
        st.text_input("Nom de l'article")
        st.number_input("Prix (FCFA)", min_value=0)
        st.text_input("Lien de la photo")
        st.button("Publier l'article")
       
    with st.expander("🗑️ Supprimer une pièce"):
        st.selectbox("Choisir l'article à retirer", df['nom'].tolist() if not df.empty else ["Aucun"])
        st.button("Confirmer la suppression")
