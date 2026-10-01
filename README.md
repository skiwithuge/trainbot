# SNCF Train Bot (Antibes ⟷ Nice-Ville)

Bot Telegram personnel fournissant en temps réel les horaires de trains régionaux (TER & ZOU!), retards et alertes de trafic entre **Antibes** et **Nice-Ville**, avec diffusions programmées et requêtes à la demande pour utilisateurs autorisés.

---

## 🌟 Fonctionnalités

- 🚆 **TER & ZOU! uniquement** : Filtrage strict pour exclure les TGV / OUIGO et ne retenir que les trains régionaux de la ligne côtière (excluant également les autocars de substitution).
- ⏱️ **Temps réel et retards** : Détection des retards calculés à la minute près (`+X min`) et des trains supprimés (`🔴 Supprimé`).
- 📢 **Infos trafic & perturbations** : Synthèse des messages opérationnels et incidents de circulation SNCF.
- ⏰ **Alertes automatiques** :
  - **07:15** (du lundi au vendredi) : Départs **Antibes ➔ Nice-Ville**
  - **16:15** (du lundi au vendredi) : Départs **Nice-Ville ➔ Antibes**
  - Fuseau horaire configuré sur `Europe/Paris`.
- ⚡ **À la demande & interactif** :
  - `/trains` : Détection automatique du sens (matin vs après-midi) avec synthèse combinée trains TER + bus Envibus Ligne A
  - `/bus` : Prochains passages en direct de la Ligne A (Collège Bertone ➔ Pôle d'Échanges le matin, Pôle d'Échanges ➔ Collège Bertone le soir)
  - `/antibes` : Départs immédiats Antibes ➔ Nice-Ville (+ correspondances bus)
  - `/nice` : Départs immédiats Nice-Ville ➔ Antibes (+ correspondances bus)
  - Boutons interactifs intégrés : `🔄 Actualiser`, `↔️ Inverser sens`, et liens directs TER Sud / Envibus Ligne A
- 🔒 **Contrôle d'accès strict** :
  - Seuls les utilisateurs Telegram dont l'ID numérique figure dans `ALLOWED_USER_IDS` peuvent interagir avec le bot.
  - Tout utilisateur non autorisé reçoit un message refusant l'accès et affichant son identifiant Telegram afin qu'il puisse le transmettre à l'administrateur.

---

## 🚀 Déploiement dans un conteneur Proxmox LXC (Debian/Ubuntu)

### 1. Cloner ou transférer le dépôt dans le conteneur LXC

Dans la console de votre conteneur LXC :
```bash
git clone https://github.com/skiwithuge/trainbot.git /opt/trainbot
cd /opt/trainbot
```

### 2. Lancer le script d'installation automatique

```bash
chmod +x deploy/install.sh
./deploy/install.sh
```

Le script installe automatiquement Python 3, crée le venv, installe les dépendances et configure le service systemd `/etc/systemd/system/trainbot.service`.

### 3. Configurer vos clés dans `/opt/trainbot/.env`

Éditez le fichier `.env` :
```bash
nano /opt/trainbot/.env
```

Renseignez vos variables :
```env
TELEGRAM_BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRstuvWXyz"
SNCF_API_KEY="votre_cle_api_sncf_ici"
ALLOWED_USER_IDS="12345678,98765432"
TIMEZONE="Europe/Paris"
LOG_LEVEL="INFO"
```

> **Astuce pour trouver votre ID Telegram** : Envoyez simplement `/start` à votre bot après l'avoir lancé. Comme votre ID n'est pas encore dans la liste, il vous répondra en affichant directement votre identifiant numérique !

### 4. Démarrer et surveiller le service

```bash
# Démarrer le service
systemctl start trainbot

# Vérifier le statut
systemctl status trainbot

# Suivre les logs en temps réel
journalctl -u trainbot -f
```

---

## 🛠️ Développement local et tests

### Lancer la suite de tests

```bash
# Activer le venv
source .venv/bin/activate

# Lancer tous les tests avec pytest
PYTHONPATH=src pytest -v
```

### Lancer le bot localement

```bash
export TELEGRAM_BOT_TOKEN="votre_token"
export SNCF_API_KEY="votre_cle"
export ALLOWED_USER_IDS="votre_id"

python -m trainbot.main
```

---

## ℹ️ Périmètre des données SNCF

- **Données opérationnelles en direct (incluses)** : Horaires théoriques et temps réel, retards à la minute, voies/quais, suppressions de trains et perturbations de circulation (pannes, obstacles, incidents de voie).
- **Avis de confort à bord (exclus)** : Les avis mineurs de confort matériel (ex. toilettes hors service sur une rame) sont gérés sur le CMS commercial interne de SNCF Voyageurs et ne sont pas diffusés dans le flux Open Data officiel de circulation (voir [ADR 0001](file:///home/skiwithuge/workspace/antigravity/trainbot/docs/adr/0001-sncf-open-data-vs-voyageurs-cms.md)).

