import streamlit as st
import pandas as pd
import uuid
import re
import html as html_lib
import unicodedata
import base64
import hashlib
import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime, timezone
from supabase import create_client, Client

st.set_page_config(page_title="Destiny Luxury Collection", page_icon="👗", layout="wide")

# ====================== 0. STYLE (thème "luxe" sobre : fond sombre, accents dorés) ======================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Playfair Display', serif !important; letter-spacing: 0.3px; }

    .stApp { background: linear-gradient(180deg, #0d0d0f 0%, #16151a 100%); }

    /* Cartes produit */
    div[data-testid="column"] > div > div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stVerticalBlock"] div.element-container:has(img) {
        border-radius: 14px;
    }
    img {
        border-radius: 12px !important;
    }

    /* Boutons */
    .stButton > button {
        border-radius: 8px;
        border: 1px solid #c9a35c;
        color: #c9a35c;
        background: transparent;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: #c9a35c;
        color: #16151a;
        border-color: #c9a35c;
    }
    .stFormSubmitButton > button {
        border-radius: 8px;
        background: #c9a35c;
        color: #16151a;
        font-weight: 600;
        border: none;
    }
    .stFormSubmitButton > button:hover {
        background: #dab873;
    }

    /* Prix et titres produits */
    div[data-testid="stMarkdownContainer"] strong { color: #eae4d8; }

    /* Bandeau logo */
    .destiny-hero { text-align:center; padding: 2rem 0 1rem 0; }
    .destiny-hero h1 { font-size: 2.4rem; color: #eae4d8; margin-top: 0.8rem; }
    .destiny-hero img { border-radius: 16px; box-shadow: 0 8px 30px rgba(201,163,92,0.15); }
</style>
""", unsafe_allow_html=True)

# ====================== 1. SECRETS ======================
# 🔒 FIX : après un très long aller-retour infructueux avec Supabase Auth
# (confirmation d'email, CAPTCHA, providers...), on repart sur le système
# simple qu'avait l'app Apps Script d'origine : un mot de passe hashé
# (SHA-256) stocké dans la table config, comparé directement en Python.
# Zéro dépendance à Supabase Auth = zéro risque de retomber sur "Invalid
# login credentials" pour des raisons de configuration externes.
# SUPABASE_SECRET_KEY (clé "secret" / service_role) est nécessaire pour que
# les actions admin puissent lire/écrire en base MÊME si les policies RLS
# ne couvrent que le rôle anon -- cette clé bypasse RLS, donc ne la mets
# JAMAIS ailleurs que dans st.secrets.
SECRETS_REQUIS = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SECRET_KEY", "IMGBB_API_KEY"]
SECRETS_MANQUANTS = [s for s in SECRETS_REQUIS if s not in st.secrets]
if SECRETS_MANQUANTS:
    st.error(f"Secrets manquants : {', '.join(SECRETS_MANQUANTS)}")
    st.stop()

EMAIL_ACTIVE = "GMAIL_ADDRESS" in st.secrets and "GMAIL_APP_PASSWORD" in st.secrets


def normaliser(valeur):
    return unicodedata.normalize("NFC", str(valeur or "")).strip()


# ====================== 2. CLIENTS SUPABASE ======================
@st.cache_resource
def get_public_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


@st.cache_resource
def get_admin_client() -> Client:
    # 🔒 La clé secret/service_role bypasse toujours RLS, quel que soit le
    # visiteur qui exécute le code -- mais l'AFFICHAGE de l'admin reste
    # protégé par admin_connecte (propre à chaque session ci-dessous), donc
    # ce n'est utilisable qu'après avoir tapé le bon mot de passe.
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SECRET_KEY"])


sb = get_public_client()

if "admin_connecte" not in st.session_state:
    st.session_state.admin_connecte = False


# 🔑 Pour définir/réinitialiser le mot de passe admin directement en base
# (si tu ne connais pas le mot de passe original migré depuis Sheets),
# lance ceci dans le SQL Editor Supabase en remplaçant la valeur :
#   update config set valeur = encode(sha256('TonNouveauMotDePasse'::bytea), 'hex')
#   where cle = 'mot_de_passe';
def hash_mot_de_passe(valeur):
    return hashlib.sha256(str(valeur or "").encode("utf-8")).hexdigest()


def admin_login(mot_de_passe):
    config_actuelle = charger_config(st.session_state.refresh_token)
    hash_attendu = config_actuelle.get("mot_de_passe", "")
    if hash_attendu and hash_mot_de_passe(mot_de_passe) == hash_attendu:
        st.session_state.admin_connecte = True
        return True
    return False


def admin_logout():
    st.session_state.admin_connecte = False


# ====================== 3. IMGBB (upload d'images) ======================
def televerser_image_imgbb(fichier):
    """Envoie un fichier uploadé vers ImgBB, renvoie l'URL hébergée ou None."""
    try:
        image_b64 = base64.b64encode(fichier.read()).decode()
        reponse = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": st.secrets["IMGBB_API_KEY"], "image": image_b64},
            timeout=30
        )
        donnees = reponse.json()
        if donnees.get("success"):
            return donnees["data"]["url"]
    except Exception:
        pass
    return None


# ====================== 4. DONNÉES (mise en cache + TTL) ======================
@st.cache_data(ttl=60)
def charger_catalogue(_refresh=0):
    reponse = sb.table("catalogue").select("*").execute()
    df = pd.DataFrame(reponse.data)
    if df.empty:
        return df
    for col in ["prix", "prix_promo", "stock"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=60)
def charger_config(_refresh=0):
    reponse = sb.table("config").select("*").execute()
    return {row["cle"]: row["valeur"] for row in reponse.data}


@st.cache_data(ttl=30)
def charger_avis_moyennes(_refresh=0):
    reponse = sb.table("avis").select("*").eq("statut", "approuve").execute()
    par_article = {}
    for row in reponse.data:
        cle_id = normaliser(row.get("article_id"))
        cle_nom = normaliser(row.get("article_nom"))
        for cle in {c for c in [cle_id, cle_nom] if c}:
            if cle not in par_article:
                par_article[cle] = {"somme": 0, "count": 0}
            par_article[cle]["somme"] += row.get("note") or 0
            par_article[cle]["count"] += 1
    return {
        cle: {"moyenne": round(v["somme"] / v["count"], 1), "count": v["count"]}
        for cle, v in par_article.items()
    }


@st.cache_data(ttl=30)
def charger_avis_article(article_id, _refresh=0):
    reponse = sb.table("avis").select("*").eq("statut", "approuve").execute()
    article_id = normaliser(article_id)
    trouves = [
        r for r in reponse.data
        if normaliser(r.get("article_id")) == article_id or normaliser(r.get("article_nom")) == article_id
    ]
    trouves.sort(key=lambda r: r.get("date", ""), reverse=True)
    return trouves[:20]


if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = 0
if "cart" not in st.session_state:
    st.session_state.cart = []
if "dernier_panier_signature" not in st.session_state:
    st.session_state.dernier_panier_signature = None


def forcer_rafraichissement():
    st.session_state.refresh_token += 1
    charger_catalogue.clear()
    charger_config.clear()
    charger_avis_moyennes.clear()


# ====================== 5. PANIER ABANDONNÉ (auto-sauvegarde) ======================
# ⚠️ Nécessite que la colonne "telephone" de paniersabandonnés soit en TEXT
# (pas bigint) -- sinon un numéro commençant par 0 perd son zéro initial.
# Voir la conversation précédente pour la commande ALTER TABLE correspondante.
def sauvegarder_panier_abandonne(tel, nom, articles):
    tel = (tel or "").strip()
    nom = (nom or "").strip()
    if not tel or not articles:
        return
    total = sum(a["prix"] * a["quantite"] for a in articles)
    signature = (tel, nom, tuple((a["nom"], a["quantite"]) for a in articles), total)
    if st.session_state.dernier_panier_signature == signature:
        return  # rien de changé depuis la dernière sauvegarde, on évite une écriture inutile

    maintenant = datetime.now(timezone.utc).isoformat()
    donnees = {
        "date_derniere_maj": maintenant,
        "client_nom": nom,
        "telephone": tel,
        "articles": [{"nom": a["nom"], "prix": a["prix"], "quantite": a["quantite"]} for a in articles],
        "total": total,
        "statut": "en_attente"
    }
    try:
        existant = sb.table("paniersabandonnés").select("telephone").eq("telephone", tel).execute()
        if existant.data:
            sb.table("paniersabandonnés").update(donnees).eq("telephone", tel).execute()
        else:
            donnees["date_creation"] = maintenant
            sb.table("paniersabandonnés").insert(donnees).execute()
        st.session_state.dernier_panier_signature = signature
    except Exception:
        pass  # la sauvegarde du panier abandonné est un bonus, jamais bloquant


def marquer_panier_converti(tel):
    tel = (tel or "").strip()
    if not tel:
        return
    try:
        sb.table("paniersabandonnés").update({"statut": "converti"}).eq("telephone", tel).execute()
    except Exception:
        pass


# ====================== 6. EMAIL (Gmail SMTP, avec repli journalisé) ======================
def envoyer_notification_commande(id_commande, client_nom, tel, articles, total, introuvables):
    corps = "Nouvelle commande reçue sur Destiny Luxury Collection !\n\n"
    corps += f"Référence : {id_commande}\n"
    corps += f"Client : {client_nom}\nTéléphone : {tel}\n\nArticles :\n"
    for a in articles:
        corps += f"- {a['nom']} x {a['quantite']} = {a['prix'] * a['quantite']} FCFA\n"
    corps += f"\nTotal : {total} FCFA\n"
    if introuvables:
        corps += f"\n⚠️ Article(s) non reconnus dans le Catalogue (prix ignoré) : {', '.join(introuvables)}\n"

    envoye = False
    if EMAIL_ACTIVE:
        try:
            config = charger_config(st.session_state.refresh_token)
            destinataire = config.get("email_admin") or st.secrets["GMAIL_ADDRESS"]
            msg = MIMEText(corps, "plain", "utf-8")
            msg["Subject"] = f"Nouvelle commande — {total} FCFA"
            msg["From"] = st.secrets["GMAIL_ADDRESS"]
            msg["To"] = destinataire
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as serveur:
                serveur.login(st.secrets["GMAIL_ADDRESS"], st.secrets["GMAIL_APP_PASSWORD"])
                serveur.send_message(msg)
            envoye = True
        except Exception:
            envoye = False

    try:
        sb.table("emailsenattente").insert({
            "horodatage": datetime.now(timezone.utc).isoformat(),
            "id_commande": id_commande,
            "payload": corps,
            "envoye": "oui" if envoye else "non"
        }).execute()
    except Exception:
        pass

    return envoye


# ====================== 7. INTERFACE PUBLIQUE ======================
config = charger_config(st.session_state.refresh_token)
df_catalogue = charger_catalogue(st.session_state.refresh_token)
avis_moyennes = charger_avis_moyennes(st.session_state.refresh_token)

NOM_BOUTIQUE = html_lib.escape(config.get("nom_boutique", "Destiny Luxury Collection"))
LOGO_URL = config.get("logo", "")
LOGO_SUR = LOGO_URL if re.match(r"^https?://", str(LOGO_URL).strip(), re.IGNORECASE) else ""
WHATSAPP = re.sub(r"\D", "", str(config.get("whatsapp") or ""))

# 🔒 FIX : l'admin n'apparaît plus comme un onglet visible par tous les
# visiteurs. Seule une personne connaissant l'URL secrète
# "https://tonapp.streamlit.app/?admin=1" voit l'interface de connexion
# admin -- les clients normaux ne voient que la boutique.
mode_admin = st.query_params.get("admin") == "1"

if not mode_admin:
    if LOGO_SUR:
        st.markdown(
            f'<div class="destiny-hero"><img src="{html_lib.escape(LOGO_SUR, quote=True)}" '
            f'style="max-height:200px;"><h1>{NOM_BOUTIQUE}</h1></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(f'<div class="destiny-hero"><h1>{NOM_BOUTIQUE}</h1></div>', unsafe_allow_html=True)

    colonne_produits, colonne_panier = st.columns([3, 1])

    with colonne_produits:
        if df_catalogue.empty:
            st.info("Le catalogue est vide pour le moment.")
        else:
            recherche = st.text_input("🔍 Rechercher un article")
            categories = ["Toutes"] + sorted(df_catalogue["categorie"].dropna().unique().tolist())
            categorie_choisie = st.selectbox("Catégorie", categories)

            df_affiche = df_catalogue.copy()
            if recherche:
                df_affiche = df_affiche[df_affiche["nom"].str.contains(recherche, case=False, na=False)]
            if categorie_choisie != "Toutes":
                df_affiche = df_affiche[df_affiche["categorie"] == categorie_choisie]

            colonnes_grille = st.columns(3)
            for idx, (_, row) in enumerate(df_affiche.iterrows()):
                with colonnes_grille[idx % 3]:
                    identifiant_produit = normaliser(row.get("id") or row.get("nom"))
                    nom_affiche = html_lib.escape(str(row["nom"]))

                    # ---- Galerie multi-images ----
                    image_principale = str(row.get("image") or "")
                    images_supp = [
                        u.strip() for u in str(row.get("images_supplementaires") or "").split(",") if u.strip()
                    ]
                    toutes_images = [u for u in [image_principale] + images_supp
                                      if re.match(r"^https?://", u.strip(), re.IGNORECASE)]

                    if toutes_images:
                        if len(toutes_images) > 1:
                            choix_photo = st.selectbox(
                                "Photo", options=list(range(len(toutes_images))),
                                format_func=lambda i: f"Photo {i + 1}",
                                key=f"galerie_{idx}", label_visibility="collapsed"
                            )
                        else:
                            choix_photo = 0
                        st.image(toutes_images[choix_photo], use_container_width=True)

                    st.markdown(f"**{nom_affiche}**")

                    info_avis = (
                        avis_moyennes.get(identifiant_produit)
                        or avis_moyennes.get(normaliser(row["nom"]))
                    )
                    if info_avis:
                        st.caption(f"⭐ {info_avis['moyenne']} ({info_avis['count']} avis)")

                    stock = int(row.get("stock") or 0)
                    en_rupture = stock <= 0
                    prix = row.get("prix") or 0
                    prix_promo = row.get("prix_promo") or 0
                    en_promo = prix_promo and 0 < prix_promo < prix

                    if en_promo:
                        reduction_pct = round((1 - prix_promo / prix) * 100) if prix else 0
                        st.markdown(f"~~{int(prix)} FCFA~~ **{int(prix_promo)} FCFA** 🏷️ -{reduction_pct}%")
                    else:
                        st.markdown(f"**{int(prix)} FCFA**")

                    if en_rupture:
                        st.error("Rupture de stock")
                        with st.expander("🔔 Me prévenir quand disponible"):
                            contact = st.text_input("Email ou téléphone", key=f"alerte_{idx}")
                            if st.button("M'alerter", key=f"btn_alerte_{idx}"):
                                if contact.strip():
                                    sb.table("alertesstock").insert({
                                        "date_inscription": datetime.now(timezone.utc).isoformat(),
                                        "article": str(row["nom"]),
                                        "contact_type": "email" if "@" in contact else "telephone",
                                        "contact": contact.strip(),
                                        "statut": "en_attente"
                                    }).execute()
                                    st.success("Inscription enregistrée !")
                    else:
                        options_taille = [t.strip() for t in str(row.get("tailles") or "").split(",") if t.strip()]
                        options_couleur = [c.strip() for c in str(row.get("couleurs") or "").split(",") if c.strip()]
                        taille_choisie = st.selectbox("Taille", options_taille, key=f"taille_{idx}") if options_taille else ""
                        couleur_choisie = st.selectbox("Couleur", options_couleur, key=f"couleur_{idx}") if options_couleur else ""

                        if st.button("🛒 Ajouter au panier", key=f"add_{idx}"):
                            existant = next(
                                (a for a in st.session_state.cart
                                 if a["nom"] == row["nom"] and a.get("taille") == taille_choisie
                                 and a.get("couleur") == couleur_choisie),
                                None
                            )
                            if existant:
                                existant["quantite"] += 1
                            else:
                                st.session_state.cart.append({
                                    "produit_id": str(row.get("id") or ""),
                                    "nom": row["nom"],
                                    "prix": float(prix_promo if en_promo else prix),
                                    "taille": taille_choisie,
                                    "couleur": couleur_choisie,
                                    "quantite": 1
                                })
                            st.rerun()

                    with st.expander("💬 Avis clients"):
                        for avis_item in charger_avis_article(identifiant_produit, st.session_state.refresh_token):
                            st.markdown(f"**{html_lib.escape(str(avis_item['client_nom']))}** — {'⭐' * int(avis_item['note'])}")
                            if avis_item.get("commentaire"):
                                st.caption(html_lib.escape(str(avis_item["commentaire"])))
                        with st.form(f"form_avis_{idx}", clear_on_submit=True):
                            nom_avis = st.text_input("Votre nom", key=f"nom_avis_{idx}")
                            note_avis = st.select_slider(
                                "Note", options=[1, 2, 3, 4, 5], value=5, key=f"note_avis_{idx}"
                            )
                            commentaire_avis = st.text_area("Commentaire (facultatif)", max_chars=500, key=f"comm_avis_{idx}")
                            if st.form_submit_button("Envoyer mon avis"):
                                if not nom_avis.strip():
                                    st.warning("Merci de renseigner votre nom.")
                                else:
                                    resultat = sb.rpc("laisser_avis", {
                                        "p_article_id": identifiant_produit,
                                        "p_article_nom": str(row["nom"]),
                                        "p_client_nom": nom_avis.strip(),
                                        "p_note": int(note_avis),
                                        "p_commentaire": commentaire_avis.strip()
                                    }).execute()
                                    donnee = resultat.data or {}
                                    if donnee.get("status") == "success":
                                        st.success(donnee.get("message"))
                                    else:
                                        st.error(donnee.get("message", "Erreur lors de l'envoi"))

    with colonne_panier:
        st.subheader("🛒 Panier")
        if not st.session_state.cart:
            st.caption("Panier vide")
        else:
            total_panier = 0
            for i, item in enumerate(st.session_state.cart):
                sous_total = item["prix"] * item["quantite"]
                total_panier += sous_total
                variante = " / ".join(v for v in [item.get("taille"), item.get("couleur")] if v)
                label = f"{item['nom']} ({variante})" if variante else item["nom"]
                st.write(f"{label} × {item['quantite']} = {int(sous_total)} FCFA")
                if st.button("🗑️", key=f"suppr_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()

            st.markdown(f"### Total : {int(total_panier)} FCFA")

            # Champs HORS formulaire (contrairement à avant) pour permettre la
            # sauvegarde automatique du panier abandonné pendant la saisie,
            # avant même que le client ait cliqué sur "Confirmer".
            client_nom = st.text_input("Votre nom", key="checkout_nom")
            client_tel = st.text_input("Votre téléphone", key="checkout_tel")

            if client_tel.strip():
                sauvegarder_panier_abandonne(client_tel, client_nom, st.session_state.cart)

            if st.button("✅ Confirmer la commande"):
                if not client_nom.strip() or not client_tel.strip():
                    st.warning("Merci de renseigner votre nom et votre téléphone.")
                else:
                    articles_payload = [
                        {"produit_id": a["produit_id"], "nom": a["nom"], "quantite": a["quantite"]}
                        for a in st.session_state.cart
                    ]
                    resultat = sb.rpc("passer_commande", {
                        "p_client_nom": client_nom.strip(),
                        "p_tel": client_tel.strip(),
                        "p_articles": articles_payload
                    }).execute()
                    donnee = resultat.data or {}
                    envoyer_notification_commande(
                        donnee.get("id_commande"), client_nom.strip(), client_tel.strip(),
                        donnee.get("articles", []), donnee.get("total", 0), donnee.get("introuvables", [])
                    )
                    marquer_panier_converti(client_tel.strip())
                    st.session_state.cart = []
                    st.session_state.dernier_panier_signature = None
                    forcer_rafraichissement()
                    st.success(f"Commande {donnee.get('id_commande')} enregistrée ! Total : {int(donnee.get('total', 0))} FCFA")
                    if donnee.get("ruptures"):
                        st.warning(f"Stock épuisé pour : {', '.join(donnee['ruptures'])}")
                    st.rerun()


# ====================== 8. ADMIN ======================
else:
    if not st.session_state.admin_connecte:
        st.subheader("Connexion admin")
        mdp_admin = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            try:
                if admin_login(mdp_admin):
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
            except Exception as e:
                st.error(f"Échec de connexion : {e}")
    else:
        sb_admin = get_admin_client()
        st.success("Connecté en tant qu'admin")
        if st.button("Se déconnecter"):
            admin_logout()
            st.rerun()

        (tab_catalogue, tab_promos, tab_commandes, tab_avis,
         tab_config, tab_alertes, tab_paniers) = st.tabs(
            ["📦 Catalogue", "🏷️ Promotions", "🧾 Commandes", "💬 Avis",
             "⚙️ Config", "🔔 Alertes stock", "🛒 Paniers abandonnés"]
        )

        with tab_catalogue:
            st.write("### Articles existants")
            for idx_row, row in enumerate(df_catalogue.to_dict("records")):
                with st.expander(f"{row['nom']} — stock {int(row.get('stock') or 0)}"):
                    with st.form(f"edit_{idx_row}_{row['id']}"):
                        nouveau_nom = st.text_input("Nom", value=row["nom"])
                        nouveau_prix = st.number_input("Prix", value=float(row.get("prix") or 0))
                        nouveau_stock = st.number_input("Stock", value=int(row.get("stock") or 0), step=1)
                        nouvelle_categorie = st.text_input("Catégorie", value=row.get("categorie") or "")
                        nouvelles_tailles = st.text_input("Tailles (séparées par virgule)", value=row.get("tailles") or "")
                        nouvelles_couleurs = st.text_input("Couleurs (séparées par virgule)", value=row.get("couleurs") or "")

                        nouvelle_image_fichier = st.file_uploader(
                            "Remplacer l'image principale", type=["jpg", "jpeg", "png", "webp"], key=f"img_{idx_row}_{row['id']}"
                        )
                        nouvelles_images_supp = st.file_uploader(
                            "Ajouter des images supplémentaires", type=["jpg", "jpeg", "png", "webp"],
                            accept_multiple_files=True, key=f"imgs_{idx_row}_{row['id']}"
                        )

                        if st.form_submit_button("Enregistrer"):
                            maj = {
                                "nom": nouveau_nom, "prix": nouveau_prix, "stock": nouveau_stock,
                                "categorie": nouvelle_categorie, "tailles": nouvelles_tailles,
                                "couleurs": nouvelles_couleurs
                            }
                            if nouvelle_image_fichier is not None:
                                url = televerser_image_imgbb(nouvelle_image_fichier)
                                if url:
                                    maj["image"] = url
                                else:
                                    st.warning("Échec de l'envoi de l'image principale vers ImgBB — le reste a été enregistré.")
                            if nouvelles_images_supp:
                                urls_existantes = [u.strip() for u in str(row.get("images_supplementaires") or "").split(",") if u.strip()]
                                for f in nouvelles_images_supp:
                                    url = televerser_image_imgbb(f)
                                    if url:
                                        urls_existantes.append(url)
                                maj["images_supplementaires"] = ", ".join(urls_existantes)
                            sb_admin.table("catalogue").update(maj).eq("id", row["id"]).execute()
                            forcer_rafraichissement()
                            st.success("Article mis à jour")
                            st.rerun()
                    if st.button("🗑️ Supprimer", key=f"del_{idx_row}_{row['id']}"):
                        try:
                            sb_admin.table("catalogue").delete().eq("id", row["id"]).execute()
                            forcer_rafraichissement()
                            st.success("Article supprimé")
                            st.rerun()
                        except Exception as e:
                            message_erreur = str(e)
                            if "23503" in message_erreur or "foreign key" in message_erreur.lower():
                                st.error(
                                    "Impossible de supprimer cet article : il est encore référencé par au moins "
                                    "une commande, un avis, une alerte stock ou un panier abandonné. "
                                    "Tu peux plutôt mettre son stock à 0 pour le masquer, ou supprimer d'abord "
                                    "les éléments liés."
                                )
                            else:
                                st.error(f"Échec de la suppression : {message_erreur}")

            st.write("### Ajouter un article")
            with st.form("ajout_article", clear_on_submit=True):
                nom = st.text_input("Nom de l'article")
                prix = st.number_input("Prix", min_value=0.0)
                stock = st.number_input("Stock", min_value=0, step=1)
                categorie = st.text_input("Catégorie")
                tailles = st.text_input("Tailles (séparées par virgule)")
                couleurs = st.text_input("Couleurs (séparées par virgule)")
                image_fichier = st.file_uploader("Image principale", type=["jpg", "jpeg", "png", "webp"])
                images_supp_fichiers = st.file_uploader(
                    "Images supplémentaires (facultatif)", type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True
                )
                if st.form_submit_button("Ajouter"):
                    if not nom.strip():
                        st.warning("Le nom de l'article est requis.")
                    else:
                        url_principale = televerser_image_imgbb(image_fichier) if image_fichier else ""
                        urls_supp = []
                        for f in (images_supp_fichiers or []):
                            url = televerser_image_imgbb(f)
                            if url:
                                urls_supp.append(url)
                        sb_admin.table("catalogue").insert({
                            "id": str(uuid.uuid4()),
                            "nom": nom, "prix": prix, "stock": stock,
                            "image": url_principale, "images_supplementaires": ", ".join(urls_supp),
                            "categorie": categorie, "tailles": tailles, "couleurs": couleurs,
                            "date_ajout": datetime.now(timezone.utc).isoformat()
                        }).execute()
                        forcer_rafraichissement()
                        st.success("Article ajouté")
                        st.rerun()

        with tab_promos:
            st.write("### Appliquer une promotion en masse")
            if df_catalogue.empty:
                st.caption("Aucun article dans le catalogue.")
            else:
                with st.form("promo_masse"):
                    articles_selectionnes = st.multiselect("Articles concernés", df_catalogue["nom"].tolist())
                    type_reduction = st.radio("Type de réduction", ["Pourcentage", "Montant fixe (FCFA)"])
                    valeur_reduction = st.number_input("Valeur de la réduction", min_value=0.0)
                    if st.form_submit_button("Appliquer la promotion"):
                        if not articles_selectionnes:
                            st.warning("Sélectionne au moins un article.")
                        else:
                            for nom_article in articles_selectionnes:
                                ligne = df_catalogue[df_catalogue["nom"] == nom_article].iloc[0]
                                prix_original = float(ligne["prix"])
                                if type_reduction == "Pourcentage":
                                    nouveau_prix_promo = round(prix_original * (1 - valeur_reduction / 100))
                                else:
                                    nouveau_prix_promo = max(0, prix_original - valeur_reduction)
                                sb_admin.table("catalogue").update(
                                    {"prix_promo": nouveau_prix_promo}
                                ).eq("id", ligne["id"]).execute()
                            forcer_rafraichissement()
                            st.success(f"Promotion appliquée à {len(articles_selectionnes)} article(s)")
                            st.rerun()

                st.write("### Retirer des promotions")
                articles_en_promo = df_catalogue[df_catalogue["prix_promo"].fillna(0) > 0]["nom"].tolist()
                if not articles_en_promo:
                    st.caption("Aucune promotion active actuellement.")
                else:
                    articles_a_retirer = st.multiselect("Articles à remettre au prix normal", articles_en_promo)
                    if st.button("Retirer la promotion sur la sélection"):
                        for nom_article in articles_a_retirer:
                            ligne = df_catalogue[df_catalogue["nom"] == nom_article].iloc[0]
                            sb_admin.table("catalogue").update({"prix_promo": None}).eq("id", ligne["id"]).execute()
                        forcer_rafraichissement()
                        st.success("Promotion(s) retirée(s)")
                        st.rerun()

        with tab_commandes:
            reponse = sb_admin.table("commandes").select("*").order("date", desc=True).limit(100).execute()
            statuts_possibles = ["En cours", "Confirmée", "Livrée", "Annulée"]
            for idx_cmd, cmd in enumerate(reponse.data):
                with st.expander(f"{cmd.get('id')} — {cmd.get('client_nom')} — {cmd.get('price')} FCFA — {cmd.get('statut')}"):
                    st.json(cmd.get("articles"))
                    statut_actuel = cmd.get("statut", "En cours")
                    index_defaut = statuts_possibles.index(statut_actuel) if statut_actuel in statuts_possibles else 0
                    nouveau_statut = st.selectbox(
                        "Statut", statuts_possibles, index=index_defaut, key=f"statut_{idx_cmd}_{cmd.get('id')}"
                    )
                    if st.button("Mettre à jour", key=f"maj_{idx_cmd}_{cmd.get('id')}"):
                        sb_admin.table("commandes").update({"statut": nouveau_statut}).eq("id", cmd["id"]).execute()
                        st.rerun()

        with tab_avis:
            reponse = sb_admin.table("avis").select("*").eq("statut", "en_attente").execute()
            if not reponse.data:
                st.caption("Aucun avis en attente")
            for idx_avis, avis_item in enumerate(reponse.data):
                with st.expander(f"{avis_item['client_nom']} — {avis_item['article_nom']} — {'⭐' * int(avis_item['note'])}"):
                    st.write(avis_item.get("commentaire") or "(pas de commentaire)")
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Approuver", key=f"appr_{idx_avis}_{avis_item['id']}"):
                        sb_admin.table("avis").update({"statut": "approuve"}).eq("id", avis_item["id"]).execute()
                        forcer_rafraichissement()
                        st.rerun()
                    if col2.button("🗑️ Supprimer", key=f"suppr_avis_{idx_avis}_{avis_item['id']}"):
                        sb_admin.table("avis").delete().eq("id", avis_item["id"]).execute()
                        forcer_rafraichissement()
                        st.rerun()

        with tab_config:
            with st.form("form_config"):
                nom_boutique_input = st.text_input("Nom de la boutique", value=config.get("nom_boutique", ""))
                logo_input = st.text_input("URL du logo", value=config.get("logo", ""))
                whatsapp_input = st.text_input("Numéro WhatsApp", value=config.get("whatsapp", ""))
                email_admin_input = st.text_input("Email de notification", value=config.get("email_admin", ""))
                if st.form_submit_button("Enregistrer"):
                    for cle, valeur in [
                        ("nom_boutique", nom_boutique_input), ("logo", logo_input),
                        ("whatsapp", whatsapp_input), ("email_admin", email_admin_input)
                    ]:
                        sb_admin.table("config").upsert({"cle": cle, "valeur": valeur}).execute()
                    forcer_rafraichissement()
                    st.success("Configuration mise à jour")
                    st.rerun()

        with tab_alertes:
            reponse = sb_admin.table("alertesstock").select("*").eq("statut", "en_attente").execute()
            if not reponse.data:
                st.caption("Aucune alerte en attente")
            for alerte in reponse.data:
                st.write(f"{alerte['article']} — {alerte['contact_type']} : {alerte['contact']}")

        with tab_paniers:
            reponse = sb_admin.table("paniersabandonnés").select("*").eq("statut", "en_attente").execute()
            paniers = sorted(reponse.data, key=lambda p: p.get("date_derniere_maj", ""), reverse=True)
            if not paniers:
                st.caption("Aucun panier abandonné en attente")
            for idx_panier, panier in enumerate(paniers):
                total = panier.get("total") or 0
                with st.expander(f"{panier.get('client_nom') or 'Client'} — {panier.get('telephone')} — {total} FCFA"):
                    st.json(panier.get("articles"))
                    tel_relance = re.sub(r"\D", "", str(panier.get("telephone") or ""))
                    if tel_relance:
                        message = f"Bonjour, vous avez laissé des articles dans votre panier sur {config.get('nom_boutique', 'notre boutique')} — puis-je vous aider à finaliser votre commande ?"
                        lien_whatsapp = f"https://wa.me/{tel_relance}?text={requests.utils.quote(message)}"
                        st.link_button("💬 Relancer sur WhatsApp", lien_whatsapp)
                    if st.button("🗑️ Marquer comme traité", key=f"panier_traite_{idx_panier}_{panier.get('telephone')}"):
                        sb_admin.table("paniersabandonnés").update({"statut": "traite"}).eq("telephone", panier["telephone"]).execute()
                        st.rerun()
