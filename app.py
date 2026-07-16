                        st.rerun()

            st.markdown("---")
            with st.form("form_mot_de_passe"):
                st.markdown("**Mot de passe admin**")
                nouveau_mdp = st.text_input("Nouveau mot de passe", type="password")
                confirmation_mdp = st.text_input("Confirmer le nouveau mot de passe", type="password")
                if st.form_submit_button("💾 Changer le mot de passe"):
                    if not nouveau_mdp:
                        st.warning("Le mot de passe ne peut pas être vide.")
                    elif nouveau_mdp != confirmation_mdp:
                        st.warning("Les deux mots de passe ne correspondent pas.")
                    else:
                        reponse, err = call_passerelle({
                            "action": "modifier_config",
                            "password": st.session_state.admin_password,
                            "nouveau_mot_de_passe": nouveau_mdp
                        })
                        if err or not reponse or reponse.get("status") != "success":
                            st.error(f"❌ Erreur : {err or (reponse or {}).get('message', '')}")
                        else:
                            st.success("✅ Mot de passe mis à jour ! Reconnecte-toi avec le nouveau mot de passe la prochaine fois.")
                            st.session_state.admin_password = nouveau_mdp
                            time.sleep(1.5)
