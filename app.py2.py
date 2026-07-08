import streamlit as st
import pandas as pd
import requests
import urllib.parse
import base64
import time

# Configuration globale
st.set_page_config(
    page_title="Collection Luxe N'Djamena",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Style CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500&display=swap');
    html, body, [data-testid="stAppViewContainer"] { background-color: #ffffff; font-family: 'Poppins', sans-serif; }
    .main-title { font-family: 'Playfair Display', serif !important; font-size: clamp(2rem, 7vw, 3.2rem) !important; font-weight: 700 !important; color: #1a1a1a !important; text-align: center !important; line-height: 1.1 !important; margin-top: 20px; margin-bottom: 5px; }
    .stars-icon { text-align: center !important; font-size: 2.5rem !important; margin-bottom: 15px; line-height: 1; }
    .subtitle { text-align: center !important; color: #777777 !important; font-style: italic !important; font-size: 1.2rem !important; margin-bottom: 40px; }
    .product-card { background-color: #ffffff; border: 1px solid #f0f0f0; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.02); transition: transform 0.3s ease; margin-bottom: 10px; }
    .product-card:hover { transform: translateY(-4px); box-shadow: 0px 12px 30px rgba(0, 0, 0, 0.06); }
    .product-image { border-radius: 8px; object-fit: cover; width: 100%; height: 320px; margin-bottom: 15px; }
    .product-price { color: #b58328; font-weight: 600; font-size: 1.25rem; margin: 8px 0 16px 0; }
    </style>
""", unsafe_allow_html=True)

# Liens et Identifiants
NUMERO_WHATSAPP = "23408167043143"  
MOT_DE_PASSE_ADMIN = "Luxe2026"  
URL_PASSERELLE = "https://script.google.com/macros/s/AKfycbwAtKtO_g5HWgeUe0XwSnWLgJuMMLrz6BXfmTDF5iQEVW8qjrZDos67S7VW8RBH-oco/exec"

st.markdown('<h1 class="main-title">COLLECTION<br>LUXE<br>N\'DJAMENA</h1>', unsafe_allow_html=True)
st.markdown('<div class="stars-icon">✨</div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">L\'élégance et la haute couture à votre portée</p>', unsafe_allow_html=True)

# --- CHARGEMENT DU CATALOGUE ---
try:
    id_sheet = st.secrets["ID_DU_SHEET"]
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_sheet}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
    df_raw = pd.read_csv(url_csv)
    df_raw.columns = [col.lower().strip() for col in df_raw.columns]
   
    df_vitrine = df_raw.dropna(subset=['nom', 'prix', 'image'])
    df_vitrine = df_vitrine[(df_vitrine['nom'].astype(str).str.strip() != "") & 
                           (df_vitrine['prix'].astype(str).str.lower() != 'nan')]
    df_admin = df_raw.copy()
except Exception as e:
    st.error(f"⚠️ Liaison Google Sheets interrompue : {e}")
    df_vitrine = pd.DataFrame(columns=["nom", "prix", "image"])
    df_admin = pd.DataFrame(columns=["nom"])

# --- GRILLE D'AFFICHAGE CLIENT ---
if not df_vitrine.empty:
    cols = st.columns(3)
    for index, row in df_vitrine.reset_index().iterrows():
        with cols[index % 3]:
            try:
                prix_entier = int(float(row['prix']))
                text_prix = f"{prix_entier:,} FCFA".replace(",", " ")
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
    st.info("Aucune pièce disponible dans la vitrine actuellement.")

# --- ESPACE DE GESTION (SIDEBAR) ---
with st.sidebar:
    st.markdown("### ⚙️ Direction de la Boutique")
    password_input = st.text_input("Clé d'accès admin", type="password")
   
    if password_input == MOT_DE_PASSE_ADMIN:
        st.success("Accès autorisé 🔓")
        st.write("---")
       
        message_ajout_container = st.container()
        message_edit_container = st.container()
        message_suppr_container = st.container()
       
        # ====================== AJOUT ======================
        st.markdown("### ➕ Ajouter un nouvel article")
        with st.form("form_ajout", clear_on_submit=True):
            nom = st.text_input("Nom du vêtement / de la pièce :")
            prix = st.number_input("Prix de vente (FCFA) :", min_value=0, step=5000)
            uploaded_file = st.file_uploader("Photo du vêtement :", type=["png", "jpg", "jpeg"])
            tailles = st.text_input("Tailles disponibles :", value="Unique")
            couleurs = st.text_input("Couleurs disponibles :", value="Unique")
            stock = st.number_input("Quantité en stock :", min_value=1, value=1)
           
            if st.form_submit_button("🚀 Mettre en vente immédiatement"):
                if nom and prix and uploaded_file:
                    with st.spinner("Enregistrement en cours..."):
                        try:
                            img_bytes = uploaded_file.read()
                            base64_image = base64.b64encode(img_bytes).decode('utf-8')
                            api_key = st.secrets.get("IMGBB_API_KEY", "70be83b276ba6ccbf03b71597dfc2a5d")
                            
                            res_img = requests.post("https://api.imgbb.com/1/upload", 
                                                  data={"key": api_key, "image": base64_image})
                            res_json = res_img.json()
                            
                            if "data" in res_json:
                                img_url = res_json["data"]["url"]
                                payload = {
                                    "action": "ajout_article",
                                    "nom": nom.strip(),
                                    "prix": prix,
                                    "image": img_url,
                                    "tailles": tailles.strip(),
                                    "couleurs": couleurs.strip(),
                                    "stock": stock
                                }
                                res = requests.post(URL_PASSERELLE, json=payload, timeout=15)
                                if res.status_code == 200:
                                    message_ajout_container.success("🎉 Article ajouté avec succès !")
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    message_ajout_container.error("Échec de synchronisation.")
                            else:
                                message_ajout_container.error("Erreur lors de l'upload de l'image.")
                        except Exception as e:
                            message_ajout_container.error(f"Erreur : {e}")
                else:
                    message_ajout_container.warning("Nom, prix et photo sont obligatoires.")
        
        st.markdown("---")

        # ====================== MODIFIER ======================
        st.markdown("### ✏️ Modifier un article")
        if not df_admin.empty and 'nom' in df_admin.columns:
            liste_articles = [str(n).strip() for n in df_admin['nom'].dropna().unique() if str(n).strip() != ""]
            
            article_to_edit = st.selectbox("Sélectionnez l'article à modifier :", liste_articles, key="edit_select")
            
            # Charger les données actuelles
            article_data = df_admin[df_admin['nom'].astype(str).str.strip() == article_to_edit].iloc[0]
            
            with st.form("form_edit", clear_on_submit=True):
                new_nom = st.text_input("Nouveau nom :", value=article_data['nom'])
                new_prix = st.number_input("Nouveau prix (FCFA) :", min_value=0, step=5000, value=int(float(article_data['prix'])))
                new_tailles = st.text_input("Tailles :", value=article_data.get('tailles', 'Unique'))
                new_couleurs = st.text_input("Couleurs :", value=article_data.get('couleurs', 'Unique'))
                new_stock = st.number_input("Stock :", min_value=0, value=int(article_data.get('stock', 1)))
                
                st.markdown("**Image actuelle :**")
                st.image(article_data['image'], width=300)
                
                new_image = st.file_uploader("Nouvelle photo (laisser vide pour conserver l'ancienne) :", 
                                           type=["png", "jpg", "jpeg"], key="edit_image")
                
                if st.form_submit_button("💾 Enregistrer les modifications"):
                    with st.spinner("Mise à jour en cours..."):
                        try:
                            img_url = article_data['image'] # Par défaut, garder l'ancienne
                            
                            if new_image is not None:
                                img_bytes = new_image.read()
                                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                                api_key = st.secrets.get("IMGBB_API_KEY", "70be83b276ba6ccbf03b71597dfc2a5d")
                                res_img = requests.post("https://api.imgbb.com/1/upload", 
                                                      data={"key": api_key, "image": base64_image})
                                if "data" in res_img.json():
                                    img_url = res_img.json()["data"]["url"]
                            
                            payload = {
                                "action": "modification_article",
                                "ancien_nom": str(article_to_edit).strip(),
                                "nom": new_nom.strip(),
                                "prix": new_prix,
                                "image": img_url,
                                "tailles": new_tailles.strip(),
                                "couleurs": new_couleurs.strip(),
                                "stock": new_stock
                            }
                            
                            res = requests.post(URL_PASSERELLE, json=payload, timeout=15)
                            if res.status_code == 200:
                                message_edit_container.success("✅ Article modifié avec succès !")
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                message_edit_container.error("Échec de la mise à jour.")
                        except Exception as e:
                            message_edit_container.error(f"Erreur : {e}")
        
        st.markdown("---")

        # ====================== LISTE COMPLÈTE ======================
        st.markdown("### 📋 Liste complète des articles")
        if not df_admin.empty:
            display_cols = ['nom', 'prix', 'tailles', 'couleurs', 'stock', 'image']
            cols_to_show = [col for col in display_cols if col in df_admin.columns]
            
            df_display = df_admin[cols_to_show].copy()
            if 'prix' in df_display.columns:
                df_display['prix'] = df_display['prix'].apply(
                    lambda x: f"{int(float(x)):,} FCFA".replace(",", " ") if pd.notna(x) else x
                )
            
            st.dataframe(df_display, use_container_width=True, hide_index=True,
                        column_config={"image": st.column_config.ImageColumn("Photo", width="small")})
            
            csv = df_admin.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Télécharger le catalogue (CSV)", csv, "catalogue_luxe_ndjamena.csv", "text/csv")
        else:
            st.info("Aucun article disponible.")
        
        st.markdown("---")

        # ====================== SUPPRESSION ======================
        st.markdown("### 🗑️ Supprimer un article")
        if not df_admin.empty and 'nom' in df_admin.columns:
            liste_articles = [str(n).strip() for n in df_admin['nom'].dropna().unique() if str(n).strip() != ""]
            
            if liste_articles:
                article_a_supprimer = st.selectbox("Sélectionnez l'article à supprimer :", liste_articles, key="suppr_select")
                confirm = st.checkbox("Je confirme la suppression définitive", key="confirm_delete")
                
                if st.button("🔴 Supprimer définitivement", type="primary"):
                    if confirm:
                        with st.spinner("Suppression en cours..."):
                            try:
                                payload = {"action": "suppression_article", "nom": str(article_a_supprimer).strip()}
                                response = requests.post(URL_PASSERELLE, json=payload, timeout=15)
                                if response.status_code == 200 and response.json().get("status") == "success":
                                    message_suppr_container.success("✅ Article supprimé avec succès !")
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    message_suppr_container.error("Erreur lors de la suppression.")
                            except Exception as e:
                                message_suppr_container.error(f"Erreur : {e}")
                    else:
                        st.warning("Veuillez cocher la case de confirmation.")
    
    elif password_input != "":
        st.error("Mot de passe incorrect ❌")
