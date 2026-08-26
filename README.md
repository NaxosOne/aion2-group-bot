# Discord Group Creator — Bot de groupes pour Aion 2

Un bot Discord pour organiser les groupes de 5 à la sortie d'Aion 2 : donjons,
sorties PvP, farm en abysses. Une commande crée un « call », et chacun s'inscrit
en un clic en choisissant son rôle (🛡️ Tank, 💚 Heal, 🗡️ DPS).

## Fonctionnalités

- **`/sortie`** : crée un appel de groupe avec titre, type (Donjon / PvP / Autre),
  horaire et description.
- **Deux modes de composition** :
  - **Standard** : 1 tank / 1 heal / 3 DPS (le classique donjon) ;
  - **Libre** : premier arrivé premier servi, peu importe les rôles (parfait
    pour le farm en abysses), avec une taille réglable (2 à 25 places).
- **Inscription par boutons** : on clique sur son rôle, l'affichage se met à
  jour instantanément. On peut changer de rôle ou quitter à tout moment.
- **Liste d'attente** : quand c'est complet, on est mis en réserve ; si une
  place se libère, le premier compatible est **promu et notifié automatiquement**.
- **Horaire intelligent** : tape `21h`, `demain 20h30` ou `30/08 21h` — l'heure
  s'affiche ensuite dans le fuseau horaire de chaque joueur (magie des
  timestamps Discord).
- **Rappels automatiques** : 15 minutes avant le début (configurable), le bot
  ping les inscrits dans le salon.
- **`/sorties`** : liste des sorties à venir avec liens cliquables.
- **Annulation** : le créateur (ou un modérateur) peut annuler, les inscrits
  sont prévenus.
- **Persistance** : tout est stocké en SQLite — les boutons continuent de
  fonctionner même si le bot redémarre.

## Comment fonctionne un bot Discord ? (les bases)

1. Tu crées une **application** sur le portail développeur de Discord ; elle
   contient un **bot** avec un **token** (son mot de passe).
2. Ton programme (ce dépôt) se connecte à Discord avec ce token et reste en
   ligne en permanence : c'est pour ça qu'il faut l'héberger quelque part.
3. Il enregistre des **commandes slash** (`/sortie`...) ; quand quelqu'un les
   utilise ou clique un bouton, Discord envoie une « interaction » au bot, qui
   répond (ici : en publiant ou modifiant le message du groupe).

## Installation pas à pas

### 1. Créer le bot sur le portail Discord

1. Va sur <https://discord.com/developers/applications> → **New Application**,
   donne-lui un nom (ex. « Aion 2 Groupes »).
2. Onglet **Bot** → **Reset Token** → copie le token quelque part de sûr.
   ⚠️ **Ne partage jamais ce token** (quiconque l'a contrôle ton bot). S'il
   fuite, reviens ici et fais « Reset Token ».
3. Aucun *privileged intent* n'est nécessaire : tu peux tout laisser désactivé.
4. Onglet **Installation** (ou OAuth2 → URL Generator) : coche les *scopes*
   `bot` et `applications.commands`, et les permissions **Send Messages**,
   **Embed Links** et **Read Message History**. Ouvre l'URL générée dans ton
   navigateur et invite le bot sur ton serveur.

### 2. Lancer le bot sur ton PC (pour tester)

Il faut Python 3.11 ou plus récent (<https://www.python.org/downloads/>).

```bash
git clone https://github.com/NaxosOne/discord-group-creator.git
cd discord-group-creator

python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env             # Windows : copy .env.example .env
# Édite .env : colle ton DISCORD_TOKEN, et mets ton GUILD_ID pour que les
# commandes apparaissent immédiatement sur ton serveur.

python -m bot.main
```

Quand tu vois `Connecté en tant que ...`, tape `/sortie` sur ton serveur. 🎉

### 3. L'héberger 24h/24

Voir **[DEPLOIEMENT.md](DEPLOIEMENT.md)** : les options gratuites ou quasi
gratuites (Oracle Cloud, Railway...), avec les étapes détaillées.

## Utilisation

```
/sortie titre: Donjon du Feu HM  type: Donjon  compo: Standard  quand: demain 21h
/sortie titre: Farm abysses      type: PvP     compo: Libre     taille: 5
/sorties        → liste des sorties à venir
```

Sous chaque annonce : boutons **Tank / Heal / DPS** pour s'inscrire (recliquer
sur un autre rôle pour changer), **Quitter**, et **Annuler la sortie**
(créateur/modérateurs). À savoir : changer de rôle te remet en fin de file,
tu ne peux donc jamais voler la place d'un titulaire.

## Structure du projet

```
bot/
  main.py              Point d'entrée : connexion, sync des commandes
  config.py            Lecture du .env (token, fuseau, rappels...)
  db.py                Stockage SQLite (sorties + inscriptions)
  logic.py             Répartition groupe / liste d'attente (pur, testé)
  embeds.py            Construction du message d'annonce
  views.py             Les boutons et leurs actions
  cogs/groups.py       /sortie, /sorties et la boucle de rappels
  utils/time_parse.py  "demain 21h" -> vraie date (pur, testé)
tests/                 python -m tests.test_logic ; python -m tests.test_time_parse
```

## Idées pour la suite (roadmap)

Des pistes pour enrichir le bot, de la plus simple à la plus ambitieuse :

- **Ping d'un rôle Discord** à la création (`@Aion2` pour notifier les membres) ;
- **Fil (thread) automatique** par sortie pour discuter sans polluer le salon ;
- **Choix de la classe Aion 2** en plus du rôle (via un menu déroulant) ;
- **Confirmation de présence** : bouton « Je confirme » à J-1 pour repérer les absents ;
- **Événements récurrents** (« tous les mardis 21h ») ;
- **Multi-groupes** pour les raids/sièges : un call qui remplit plusieurs groupes de 5 ;
- **Salon vocal temporaire** créé au début de la sortie et supprimé après ;
- **`/planning`** publié chaque semaine avec le calendrier des sorties ;
- **Statistiques de participation** (fiabilité, no-shows) ;
- **Modèles de sorties** enregistrés (`/sortie modele: DonjonHebdo`) ;
- **Permissions** : réserver la création de calls à un rôle « officier » ;
- **Export calendrier** (.ics) pour retrouver les sorties dans son agenda.
