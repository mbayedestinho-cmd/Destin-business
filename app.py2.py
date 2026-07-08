import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time

# Configuration de la page
st.set_page_config(
    page_title="Collection Luxe N'Djamena",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLE GRAPHIQUE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500&display=swap');
    html, body, [data-testid="stAppViewContainer"] { background-color: #ffffff; font-family: 'Poppins', sans-serif; }
    .main-title { font-family: 'Playfair Display', serif !important; font-size: clamp(2rem, 7vw, 3.2rem) !important; font-weight: 700 !important; color: #1a1a1a !important; text-align: center !important; line-height: 1.1 !important; margin-top: 20px; margin-bottom: 5px; }
    .stars-icon { text-align: center !important; font-size: 2.5rem !important; margin-bottom: 15px; line-height: 1; }
    .subtitle { text-align: center !important; color: #777777 !important; font-style: italic !important; font-size: 1.2rem !important; margin-bottom: 40px; }
    .product-card { background-color: #ffffff; border: 1px solid #f0f0f0; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.02); transition: transform 0.3s ease, box-shadow 0.3s ease; margin-bottom: 10px; }
    .product-card:hover { transform: translateY(-4px); box-shadow: 0px 12px 30px rgba(0, 0, 0, 0.06); }
    .product-image { border-radius: 8px; object-fit: cover; width: 100%; height: 320px; margin-bottom: 15px; }
    .product-price { color: #b58328; font-weight: 600; font-size: 1.25rem; margin: 8px 0 16px 0; }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURATIONS ---
NUMERO_WHATSAPP = "23408167043143"  
MOT_DE_PASSE_ADMIN = "Luxe2026"   
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbwAtKtO_g5HWgeUe0XwSnWLgJuMMLrz6BXfmTDF5iQEVW8qjrZDos67S7VW8RBH-oco/exec" 

st.markdown('<h1 class="main-title">COLLECTION<br>LUXE<br>N\'DJAMENA</h1>', unsafe_allow_html=True)
st.markdown('<div class="stars-icon">✨</div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">L\'élégance et la haute couture à votre portée</p>', unsafe_allow_html=True)

# --- CHARGEMENT DU CATALOGUE SANS CACHE ---
try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
    df_raw = pd.read_csv(url_csv)
    df_raw.columns = [col.lower().strip() for col in df_raw.columns]
    
    # Nettoyage strict des lignes vides ou erronées pour la vitrine client
    df_vitrine = df_raw.dropna(subset=['nom'])
    df_vitrine = df_vitrine[df_vitrine['nom'].astype(str).str.strip() != ""]
    df_vitrine = df_vitrine[df_vitrine['prix'].astype(str).str.lower() != 'nan']
    
    df_admin = df_raw.copy()
except Exception as e:
    st.error(f"⚠️ Erreur Google Sheets : {e}")
    df_vitrine = pd.DataFrame(columns=["nom", "prix", "image"])
    df_admin = pd.DataFrame(columns=["nom"])

# --- VITRINE CLIENT ---
if not df_vitrine.empty:
    cols = st.columns(3)
    for index, row in df_vitrine.reset_index().iterrows():
        with cols[index % 3]:
            try:
                prix_formate = int(float(row['prix']))
                text_prix = f"{prix_formate:,} FCFA"
            except:
                text_prix = f"{row['prix']} FCFA"
                
            txt_whatsapp = f"Bonjour Collection Luxe N'Djamena, je souhaite commander :\n- *Article :* {row['nom']}\n- *Prix :* {text_prix}"
            url_whatsapp = f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(txt_whatsapp)}"
            
            st.markdown(f"""
                <div class="product-card">
                    <img class="product-image" src="{str(row['image'])}">
                    <h3 style='font-family: "Playfair Display", serif; font-size: 1.4rem;'>{row['nom']}</h3>
                    <div class="product-price">{text_prix}</div>
                </div>
            """, unsafe_allow_html=True)
            st.link_button("💬 Commander sur WhatsApp", url=url_whatsapp, use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
else:
    st.info("Aucun article disponible pour le moment.")

# --- ESPACE ADMIN (SIDEBAR) ---
with st.sidebar:
    st.markdown("### ⚙️ Espace Gestionnaire")
    password_input = st.text_input("Mot de passe", type="password")
    
    if password_input == MOT_DE_PASSE_ADMIN:
        st.success("Authentifié 🔓")
        st.write("---")
        
        # AJOUT D'ARTICLE
        st.markdown("### ➕ Ajouter une nouveauté")
        with st.form("form_ajout", clear_on_submit=True):
            nom = st.text_input("Nom de la pièce :")
            prix = st.number_input("Prix (FCFA) :", min_value=0, step=5000)
            uploaded_file = st.file_uploader("Photo :", type=["png", "jpg", "jpeg"])
            
            bouton_ajout = st.form_submit_button("🚀 Publier")
            
            if bouton_ajout:
                if nom and prix and uploaded_file:
                    with st.spinner("Téléversement de l'image..."):
                        try:
                            img_bytes = uploaded_file.read()
                            base64_image = base64.b64encode(img_bytes).decode('utf-8')
                            
                            # Clé API récupérée depuis secrets ou valeur par défaut
                            api_key = st.secrets.get("IMGBB_API_KEY", "70be83b276ba6ccbf03b71597dfc2a5d")
                            res_img = requests.post("https://api.imgbb.com/1/upload", data={"key": api_key, "image": base64_image})
                            res_json = res_img.json()
                            
                            if "data" in res_json:
                                img_url = res_json["data"]["url"]
                                payload = {"nom": nom.strip(), "prix": prix, "image": img_url}
                                res = requests.post(URL_PASSERELLE, json=payload, timeout=10)
                                
                                if res.status_code == 200:
                                    st.success("🎉 Article ajouté !")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Erreur d'enregistrement Google Sheets.")
                            else:
                                error_msg = res_json.get("error", {}).get("message", "Clé API invalide.")
                                st.error(f"Hébergeur ImgBB refusé : {error_msg}. Vérifiez votre clé API ImgBB.")
                        except Exception as e:
                            st.error(f"Erreur technique : {e}")
                else:
                    st.warning("Veuillez remplir tous les champs.")
                            
        st.markdown("---")
        
        # SUPPRESSION D'ARTICLE
        st.markdown("### 🗑️ Supprimer un article")
        if not df_admin.empty and 'nom' in df_admin.columns:
            liste_articles = [str(n).strip() for n in df_admin['nom'].dropna().unique() if str(n).strip() != ""]
            
            if liste_articles:
                article_a_supprimer = st.selectbox("Sélectionnez l'article à retirer :", liste_articles)
                
                if st.button("🔴 Supprimer définitivement"):
                    with st.spinner("Retrait en cours..."):
                        try:
                            payload_suppression = {
                                "action": "suppression_article",
                                "nom": str(article_a_supprimer).strip()
                            }
                            response = requests.post(URL_PASSERELLE, json=payload_suppression, timeout=10)
                            
                            if response.status_code == 200:
                                res_json = response.json()
                                if res_json.get("status") == "success":
                                    st.success(f"✅ {res_json.get('message')}")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"Refus de Google : {res_json.get('message')}")
                            else:
                                st.error(f"Erreur serveur (Code {response.status_code})")
                        except Exception as e:
                            st.error(f"Erreur : {e}")
            else:
                st.info("Aucun article trouvé dans le tableau.")
                
    elif password_input != "":
        st.error("Mot de passe incorrect ❌")
