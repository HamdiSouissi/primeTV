# Certificats

Le conteneur Nginx génère automatiquement au premier démarrage un certificat
**auto-signé** (`primetv.crt` / `primetv.key`) si aucun n'est présent.

* Développement / réseau privé : rien à faire.
* Production : remplacez ces fichiers par ceux de votre ACME (Let's Encrypt)
  ou utilisez le profil Traefik (`docker compose --profile tls up -d`), qui gère
  l'obtention automatique des certificats.

Les certificats privés ne doivent **jamais** être versionnés : ce dossier est
ignoré par Git, seul ce README est conservé.
