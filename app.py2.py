import streamlit as st
import urllib.parse
# Configuration principale de l'application
st.set_page_config(page_title="Gestion Luxe & Collections", page_icon="👑", layout="wide")
# --- 1. INITIALISATION DE LA MÉMOIRE INTERNE (SESSION STATE) ---
if "catalogue" not in st.session_state:
    st.session_state.catalogue = [
        {"nom": "L'Exception VIP (Grand Luxe)", "prix": 45000, "image": None},
        {"nom": "Habit Premium Business", "prix": 20000, "image": None},
        {"nom": "Habit Luxe Classique", "prix": 17500, "image": None}
    ]
if "mon_whatsapp" not in st.session_state:
    st.session_state.mon_whatsapp = "234XXXXXXXXX"  # Met ton numéro ici (avec l'indicatif pays, sans le +)
if "mon_email" not in st.session_state:
    st.session_state.mon_email = "ton-email@example.com"  # Met ton adresse email ici
if "texte_marketing" not in st.session_state:
    st.session_state.texte_marketing = """🌧️ Malgré la pluie à N'Djamena, restez élégant !
Arrivage direct de vêtements exclusifs de haute qualité.
📦 *ARRIVAGE DU COLIS*
⚠️ _Stock ultra-limité pour préserver l'exclusivité._"""
# --- 2. CONFIGURATION DE L'INTERFACE EN ONGLETS ---
onglet_client, onglet_admin = st.tabs(["🛒 Boutique Visiteur", "⚙️ Panneau de Contrôle Admin"])
# =========================================================
# ONGLET CLIENT : CE QUE VOIENT LES ACHETEURS
# =========================================================
with onglet_client:
    st.title("👑 Collection Luxe N'Djamena")
    st.write("Parcourez nos pièces exclusives et commandez directement auprès de nous.")
    st.markdown("---")
   
    # Affichage dynamique sous forme de grille (3 colonnes)
    cols = st.columns(3)
    for idx, item in enumerate(st.session_state.catalogue):
        with cols[idx % 3]:
            st.subheader(item["nom"])
            st.write(f"💰 **Prix :** {item['prix']:,} FCFA")
           
            # Affichage de la photo si elle existe, sinon un bloc d'info
            if item["image"] is not None:
                st.image(item["image"], use_container_width=True)
            else:
                st.info("📷 Image en cours de chargement par l'administrateur")
           
            # Lien de commande client direct vers ton WhatsApp
            msg_commande = f"Bonjour ! Je souhaite réserver l'article suivant : {item['nom']} au prix de {item['prix']:,} FCFA."
            lien_commande = f"https://wa.me/{st.session_state.mon_whatsapp}?text={urllib.parse.quote(msg_commande)}"
           
            st.link_button("🛍️ Commander cet article", lien_commande, type="primary")
            st.markdown("<br>", unsafe_allow_html=True)
# =========================================================
# ONGLET ADMIN : TON ESPACE DE CONFIGURATION PRIVÉ
# =========================================================
with onglet_admin:
    st.title("⚙️ Zone d'Administration et Configuration")
   
    # 🚨 BLOC SPÉCIAL : BOUTONS DE REDIRECTION GOOGLE SHEET
    st.markdown("---")
    st.subheader("📊 Action Requise : Sauvegarde Permanente (Google Sheets)")
    st.info("Pour éviter que tes nouveaux habits ne s'effacent lors des redémarrages de l'application, clique ci-dessous pour lancer la configuration de ta base de données permanente.")
   
    # Message pré-rempli pour la demande d'assistance technique Google Sheet
    texte_aide_sheet = "Bonjour ! Je souhaite connecter mon fichier Google Sheets à mon application Streamlit pour sauvegarder mes prix, mes textes marketing et mes images de manière permanente."
    texte_encode_sheet = urllib.parse.quote(texte_aide_sheet)
   
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        lien_wa_help = f"https://wa.me/{st.session_state.mon_whatsapp}?text={texte_encode_sheet}"
        st.link_button("💬 Me dire comment gérer le Google Sheet sur WhatsApp", lien_wa_help, type="secondary")
       
    with col_btn2:
        lien_mail_help = f"mailto:{st.session_state.mon_email}?subject=Configuration%20Google%20Sheets%20Streamlit&body={texte_encode_sheet}"
        st.link_button("✉️ Me dire comment gérer le Google Sheet par Mail", lien_mail_help, type="secondary")
   
    st.markdown("---")
    # --- SECTION A : PARAMÈTRES DES COORDONNÉES ET TEXTES ---
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("🔧 Vos Coordonnées de Contact")
        st.session_state.mon_whatsapp = st.text_input("Numéro WhatsApp de réception (Format: 23480...)", st.session_state.mon_whatsapp)
        st.session_state.mon_email = st.text_input("Adresse Email de réception", st.session_state.mon_email)
       
    with col_p2:
        st.subheader("✍️ Paramétrage Personnel du Message Marketing")
        st.session_state.texte_marketing = st.text_area("Modifie et écris ton propre texte de saison ici :", st.session_state.texte_marketing, height=120)
    # --- SECTION B : FORMULAIRE D'AJOUT AVEC IMAGE ---
    st.markdown("---")
    st.subheader("✨ Ajouter une nouvelle pièce avec Image")
   
    with st.form("formulaire_ajout", clear_on_submit=True):
        nom_nouvel_habit = st.text_input("Nom de la pièce (ex: Grand Boubou VIP, Costume Nigeria Style)")
        prix_nouvel_habit = st.number_input("Prix de vente (FCFA)", min_value=0, value=15000, step=500)
        photo_nouvel_habit = st.file_uploader("Prendre une photo ou sélectionner un fichier", type=["png", "jpg", "jpeg"])
       
        bouton_validation = st.form_submit_button("Enregistrer et ajouter au catalogue")
       
        if bouton_validation and nom_nouvel_habit:
            # Ajout dynamique dans la liste
            st.session_state.catalogue.append({
                "nom": nom_nouvel_habit,
                "prix": prix_nouvel_habit,
                "image": photo_nouvel_habit
            })
            st.toast(f"✅ l'article '{nom_nouvel_habit}' a été ajouté à la boutique !")
            st.rerun()
    # --- SECTION C : NETTOYAGE ET SUPPRESSION DU STOCK ---
    st.markdown("---")
    st.subheader("🗑️ Liste de contrôle et suppression")
   
    for i, habit_actuel in enumerate(st.session_state.catalogue):
        col_list1, col_list2, col_list3 = st.columns([2, 1, 1])
        with col_list1:
            st.write(f"🔹 {habit_actuel['nom']}")
        with col_list2:
            st.write(f"{habit_actuel['prix']:,} FCFA")
        with col_list3:
            if st.button("Supprimer", key=f"delete_item_{i}"):
                st.session_state.catalogue.pop(i)
                st.rerun()
