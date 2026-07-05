import streamlit as st
# Configuration de la page optimisée pour mobile
st.set_page_config(page_title="Suivi Ventes Luxe", page_icon="🛍️", layout="centered")
# Style CSS personnalisé pour l'esthétique mobile
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        margin-bottom: 10px;
    }
    div[data-testid="stMetric"] label { font-weight: bold; color: #495057; }
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #4caf50, #8bc34a); }
    </style>
""", unsafe_allow_html=True)
st.title("🦅 Dashboard Nigeria ➡️ N'Djamena")
st.caption("Pilotez vos stocks à distance et suivez vos bénéfices en direct.")
st.markdown("---")
# --- 1. CONFIGURATION FINANCIÈRE DE BASE ---
TAUX = 2.3
MARGE_ERREUR = 0.05
INVESTISSEMENT_NAIRA = 250000
TRANSPORT_CFA = 40000
investissement_cfa = INVESTISSEMENT_NAIRA / TAUX
depenses_totales_cfa = investissement_cfa + TRANSPORT_CFA
# --- 2. BASE DE DONNÉES DES VÊTEMENTS ---
habits_db = [
    {"id": 1, "nom": "Habit Luxe Classique #1", "prix": 17500},
    {"id": 2, "nom": "Habit Luxe Classique #2", "prix": 17500},
    {"id": 3, "nom": "Habit Luxe Classique #3", "prix": 17500},
    {"id": 4, "nom": "Habit Luxe Classique #4", "prix": 17500},
    {"id": 5, "nom": "Habit Luxe Classique #5", "prix": 17500},
    {"id": 6, "nom": "Habit Luxe Classique #6", "prix": 17500},
    {"id": 7, "nom": "Habit Luxe Classique #7", "prix": 17500},
    {"id": 8, "nom": "Habit Luxe Classique #8", "prix": 17500},
    {"id": 9, "nom": "Habit Luxe Confort #1", "prix": 15000},
    {"id": 10, "nom": "Habit Luxe Confort #2", "prix": 15000},
    {"id": 11, "nom": "Habit Premium Business", "prix": 20000},
    {"id": 12, "nom": "L'Exception VIP (Grand Luxe)", "prix": 45000},
]
# --- 3. SECTION COMPTABILITÉ (EN HAUT SUR MOBILE) ---
st.subheader("💰 Performance Financière")
ca_reel_cfa = 0
nb_habits_vendus = 0
# Utilisation de boutons masqués ou gestion via les cases plus bas
# Pour un affichage mobile propre, on calcule d'abord l'état
for habit in habits_db:
    if st.session_state.get(f"status_{habit['id']}", False):
        ca_reel_cfa += habit['prix']
        nb_habits_vendus += 1
progression = nb_habits_vendus / 12
st.write(f"📈 **Progression des ventes :** {nb_habits_vendus} / 12 pièces liquidées")
st.progress(progression)
ca_theorique_total = sum(h["prix"] for h in habits_db)
benefice_brut_cfa = ca_reel_cfa - depenses_totales_cfa
if benefice_brut_cfa > 0:
    benefice_net_cfa = benefice_brut_cfa * (1 - MARGE_ERREUR)
    benefice_net_naira = benefice_net_cfa * TAUX
else:
    benefice_net_cfa = 0
    benefice_net_naira = 0
# Affichage des métriques empilées pour écran de smartphone
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Chiffre d'Affaires", value=f"{ca_reel_cfa:,} CFA")
    st.metric(label="Dépenses Totales", value=f"{int(depenses_totales_cfa):,} CFA")
with col2:
    st.metric(label="Bénéfice Net (CFA)", value=f"{int(benefice_net_cfa):,} F", delta=f"Cible: {ca_theorique_total:,} F", delta_color="normal")
    st.metric(label="Bénéfice Net (Naira)", value=f"{int(benefice_net_naira):,} ₦")
st.markdown("---")
# --- 4. GESTION DES VENTES (MAMAN) ---
st.subheader("🛒 Inventaire à N'Djamena")
st.caption("Cochez les articles vendus au fur et à mesure :")
for habit in habits_db:
    st.checkbox(f"🟩 {habit['nom']} — {habit['prix']:,} FCFA", key=f"status_{habit['id']}")
st.markdown("---")
# --- 5. MARKETING WHATSAPP ---
st.subheader("📱 Assistant Marketing")
saison = st.selectbox("Climat ou période :", ["Saison des pluies (Juillet)", "Période Festive"])
accroche = "🌧️ Malgré la pluie à N'Djamena, restez élégant !" if "pluies" in saison.lower() else "✨ Soyez le centre de l'attention !"
message_whatsapp = f"""{accroche}
📦 *ARRIVAGE EXCLUSIF DU NIGERIA*
⚠️ _Seulement 12 pièces uniques dispo._
👑 L'Exception VIP : 45,000 FCFA
🔹 Premium Business : 20,000 FCFA
🔹 Luxe Classique : 17,500 FCFA
🔹 Confort : 15,000 FCFA
📍 Dispo à N'Djamena (Essayage sur RDV avec Maman).
📲 Écrivez-moi vite pour bloquer votre modèle !"""
st.text_area("Message prêt à copier :", value=message_whatsapp, height=180)