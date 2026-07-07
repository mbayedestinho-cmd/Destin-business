import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
# --- INITIALISATION DE LA MÉMOIRE DE TRACAGE ---
if 'suivi_clics' not in st.session_state:
    st.session_state['suivi_clics'] = {}
# 1. Configuration de la page
st.set_page_config(
    page_title="Collection Luxe N'Djamena",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)
# --- CONFIGURATIONS ---
NUMERO_WHATSAPP = "23408167043143" 
MOT_DE_PASSE_ADMIN = "Luxe2026"  
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbwAtKtO_g5HWgeUe0XwSnWLgJuMMLrz6BXfmTDF5iQEVW8qjrZDos67S7VW8RBH-oco/exec"
# 2. Design Haute Couture
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500&display=swap');
  
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #ffffff;
        font-family: 'Poppins', sans-serif;
    }
  
    .main-title {
        font-family: 'Playfair Display', serif !important;
        font-size: clamp(2rem, 7vw, 3.2rem) !important;
        font-weight: 700 !important;
        color: #1a1a1a !important;
        text-align: center !important;
        line-height: 1.1 !important;
        margin-top: 20px;
        margin-bottom: 5px;
    }
  
    .stars-icon {
        text-align: center !important;
        font-size: 2.5rem !important;
        margin-bottom: 15px;
        line-height: 1;
    }
  
    .subtitle {
        text-align: center !important;
        color: #777777 !important;
        font-style: italic !important;
        font-size: 1.2rem !important;
        margin-bottom: 40px;
    }
  
    .product-card {
        background-color: #ffffff;
        border: 1px solid #f0f0f0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.02);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 30px;
    }
    .product-card:hover {
        transform: translateY(-4px);
        box-shadow: 0px 12px 30px rgba(0, 0, 0, 0.06);
    }
  
    .product-image {
        border-radius: 8px;
        object-fit: cover;
        width: 100%;
        height: 320px;
        margin-bottom: 15px;
    }
  
    .product-price {
        color: #b58328;
        font-weight: 600;
        font-size: 1.25rem;
        margin: 8px 0 16px 0;
    }
    </style>
""", unsafe_allow_html=True)
# --- EN-TÊTE ---
st.markdown('<h1 class="main-title">COLLECTION<br>LUXE<br>N\'DJAMENA</h1>', unsafe_allow_html=True)
st.markdown('<div class="stars-icon">✨</div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">L\'élégance et la haute couture à votre portée</p>', unsafe_allow_html=True)
# --- CONNEXION À GOOGLE SHEETS (LECTURE) ---
try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv"
    df = pd.read_csv(url_csv)
    df.columns = [col.lower().strip() for col in df.columns]
except Exception as e:
    st.error(f"⚠️ Erreur d'accès au catalogue : {e}")
    df = pd.DataFrame(columns=["nom", "prix", "image"])
# --- AFFICHAGE DES ARTICLES ---
if not df.empty:
    cols = st.columns(3)
    for index, row in df.iterrows():
        with cols[index % 3]:
            try:
                prix_formate = int(row['prix'])
                text_prix = f"{prix_formate:,} FCFA"
            except Exception:
                text_prix = f"{row['prix']} FCFA"
                prix_formate = row['prix']
               
            txt_whatsapp = f"Bonjour Collection Luxe N'Djamena, je souhaite commander cette pièce :\n\n- *Article :* {row['nom']}\n- *Prix :* {text_prix}"
            url_whatsapp = f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(txt_whatsapp)}"
           
            st.markdown(f"""
                <div class="product-card">
                    <img class="product-image" src="{row['image']}">
                    <h3 style='font-family: "Playfair Display", serif; font-size: 1.4rem; margin: 0 0 5px 0;'>{row['nom']}</h3>
                    <div class="product-price">{text_prix}</div>
                </div>
            """, unsafe_allow_html=True)
           
            if st.button(f"💬 Commander sur WhatsApp", key=f"btn_{index}_{row['nom']}"):
                try:
                    payload_clic = {
                        "action": "enregistrement_clic",
                        "article": row['nom'],
                        "prix": row['prix']
                    }
                    requests.post(URL_PASSERELLE, json=payload_clic, timeout=4)
                except Exception:
                    pass
                js = f"window.open('{url_whatsapp}')"
                st.components.v1.html(f"<script>{js}</script>", height=0)
                else:
    st.info("Le catalogue est en cours de mise à jour. Revenez dans un instant !")
# --- PANNEAU ADMIN SÉCURISÉ ---
with st.sidebar:
    st.markdown("### ⚙️ Authentification Admin")
    password_input = st.text_input("Entrez le mot de passe de la boutique", type="password")
   
    if password_input == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé 🔓")
        st.write("---")
        st.markdown("### ➕ Ajouter un nouvel article")
       
        with st.form("form_ajout", clear_on_submit=True):
            nom = st.text_input("Nom du vêtement / de la pièce :")
            prix = st.number_input("Prix de vente en boutique (FCFA) :", min_value=0, step=5000)
            uploaded_file = st.file_uploader("Photo du vêtement (JPG/PNG) :", type=["png", "jpg", "jpeg"])
            tailles_input = st.text_input("Tailles disponibles (ex: M, L, XL) :", value="Unique")
            couleurs_input = st.text_input("Couleurs disponibles (ex: Noir, Blanc) :", value="Unique")
            stock_input = st.number_input("Quantité en stock :", min_value=1, value=1)
           
            bouton_ajout = st.form_submit_button("🚀 Mettre en vente immédiatement")
           
            if bouton_ajout and nom and prix and uploaded_file:
                with st.spinner("Téléversement et enregistrement en cours..."):
                    try:
                        img_bytes = uploaded_file.read()
                        base64_image = base64.b64encode(img_bytes).decode('utf-8')
                      
                        api_key = st.secrets.get("IMGBB_API_KEY", "70be83b276ba6ccbf03b71597dfc2a5d")
                        res_img = requests.post(
                            "https://api.imgbb.com/1/upload",
                            data={"key": api_key, "image": base64_image}
                        )
                        img_url = res_img.json()["data"]["url"]
                      
                        payload = {
                            "nom": nom,
                            "prix": prix,
                            "image": img_url,
                            "tailles": tailles_input,
                            "couleurs": couleurs_input,
                            "stock": stock_input
                        }
                      
                        res = requests.post(URL_PASSERELLE, json=payload, timeout=10)
                        if res.status_code == 200:
                            st.success("🎉 Article mis en ligne avec succès ! Actualisez la page (F5).")
                        else:
                            st.error("Erreur lors de l'enregistrement dans le catalogue Sheets.")
                          
                    except Exception as e:
                        st.error(f"⚠️ Échec du téléversement de l'image : {e}")
                       
        # 🗑️ SECTION DE SUPPRESSION D'UN ARTICLE
        st.markdown("---")
        st.markdown("### 🗑️ Supprimer un article")
      
        if not df.empty:
            liste_articles = df.iloc[:, 0].tolist()
            article_a_supprimer = st.selectbox("Sélectionnez l'article à retirer :", liste_articles)
          
            if st.button("🔴 Supprimer définitivement"):
                try:
                    payload_suppression = {
                        "action": "suppression_article",
                        "nom": article_a_supprimer
                    }
                    response = requests.post(URL_PASSERELLE, json=payload_suppression, timeout=4)
                  
                    if response.status_code == 200:
                        st.success(f"L'article '{article_a_supprimer}' a été retiré avec succès ! Rappuyez sur F5.")
                    else:
                        st.error("Impossible de joindre Google Sheets pour la suppression.")
                except Exception as e:
                    st.error(f"Erreur de connexion : {e}")
                   
    elif password_input != "":
        st.error("Mot de passe incorrect ❌")
                
               
      
