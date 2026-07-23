"""
Tâches planifiées -- relance panier abandonné & fidélité 30 jours.

Ce script tourne HORS de Streamlit (pas de serveur applicatif qui reste
allumé en permanence), déclenché par un cron GitHub Actions. Il ne peut
PAS envoyer de message WhatsApp lui-même (aucune API WhatsApp Business
n'est configurée sur ce projet) -- il prépare le travail et prévient
l'admin de chaque boutique par email, avec un lien direct vers l'onglet
concerné, pour que l'envoi WhatsApp final reste un clic humain.

Variables d'environnement attendues (à définir en secrets GitHub Actions,
mêmes noms que dans .streamlit/secrets.toml) :
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
    GMAIL_ADDRESS, GMAIL_APP_PASSWORD
    APP_URL   -- URL publique de l'app Streamlit (pour le lien dans l'email)
"""

import os
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
APP_URL = os.environ.get("APP_URL", "")

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def envoyer_email(destinataire, sujet, corps):
    if not (GMAIL_ADDRESS and GMAIL_APP_PASSWORD and destinataire):
        print(f"[skip email] {sujet} -> {destinataire}")
        return
    msg = MIMEText(corps, "plain", "utf-8")
    msg["Subject"] = sujet
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = destinataire
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as serveur:
            serveur.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            serveur.send_message(msg)
        print(f"[ok] {sujet} -> {destinataire}")
    except Exception as exc:
        print(f"[erreur email] {sujet} -> {destinataire} : {exc}")


def marchands_actifs():
    reponse = (
        sb.table("marchands")
        .select("id, nom_boutique, slug, email_contact, whatsapp, delai_relance_panier_h, banniere_code_promo")
        .in_("statut_abonnement", ["actif", "en_grace"])
        .execute()
    )
    return reponse.data or []


def traiter_paniers_a_relancer(marchand):
    delai_h = int(marchand.get("delai_relance_panier_h") or 24)
    try:
        reponse = sb.rpc("paniers_prets_a_relancer", {
            "p_marchand_id": marchand["id"],
            "p_heures": delai_h,
        }).execute()
    except Exception as exc:
        print(f"[erreur RPC paniers] {marchand.get('nom_boutique')} : {exc}")
        return
    paniers = reponse.data or []
    if not paniers:
        return
    lien = f"{APP_URL}?boutique={marchand.get('slug', '')}" if APP_URL else ""
    corps = (
        f"{len(paniers)} panier(s) abandonné(s) ont dépassé le délai de {delai_h}h "
        f"et sont prêts à relancer sur {marchand.get('nom_boutique', 'votre boutique')} :\n\n"
    )
    for p in paniers:
        corps += f"- {p.get('client_nom') or 'Client'} ({p.get('telephone')}) — {p.get('total') or 0} FCFA\n"
    corps += (
        f"\nOuvre l'onglet Admin > 🛒 Paniers abandonnés pour envoyer les relances WhatsApp "
        f"(un clic par client, message déjà prêt).\n"
    )
    if lien:
        corps += f"\n{lien}\n"
    envoyer_email(marchand.get("email_contact"), f"⏰ {len(paniers)} panier(s) prêt(s) à relancer", corps)


def traiter_fidelite_30_jours(marchand):
    """Clients dont la dernière commande date d'il y a exactement 30 jours
    (fenêtre glissante d'un jour pour ne pas dépendre de l'heure exacte du
    cron) : on prévient l'admin avec le code promo boutique déjà configuré
    dans la bannière (pas de système de code par client -- réutilise le
    mécanisme existant pour rester simple)."""
    il_y_a_30j = datetime.now(timezone.utc) - timedelta(days=30)
    il_y_a_31j = datetime.now(timezone.utc) - timedelta(days=31)
    try:
        reponse = (
            sb.table("commandes")
            .select("client_nom, tel, date")
            .eq("marchand_id", marchand["id"])
            .gte("date", il_y_a_31j.isoformat())
            .lte("date", il_y_a_30j.isoformat())
            .execute()
        )
    except Exception as exc:
        print(f"[erreur requête fidélité] {marchand.get('nom_boutique')} : {exc}")
        return
    clients = reponse.data or []
    if not clients:
        return
    code_promo = marchand.get("banniere_code_promo") or "(aucun code promo configuré en ce moment)"
    lien = f"{APP_URL}?boutique={marchand.get('slug', '')}" if APP_URL else ""
    corps = (
        f"{len(clients)} client(s) n'ont pas commandé depuis 30 jours sur "
        f"{marchand.get('nom_boutique', 'votre boutique')}. Code promo actuel à leur proposer : {code_promo}\n\n"
    )
    for c in clients:
        corps += f"- {c.get('client_nom') or 'Client'} ({c.get('tel')})\n"
    corps += "\nOuvre l'onglet Admin > 🛒 Paniers abandonnés / Marketing pour envoyer un message WhatsApp à chacun.\n"
    if lien:
        corps += f"\n{lien}\n"
    envoyer_email(marchand.get("email_contact"), f"🎉 {len(clients)} client(s) à relancer (30 jours)", corps)


def main():
    for marchand in marchands_actifs():
        traiter_paniers_a_relancer(marchand)
        traiter_fidelite_30_jours(marchand)


if __name__ == "__main__":
    main()
