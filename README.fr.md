<p align="center">
  <img src="assets/banner.png" alt="Kisk — le point de ralliement de votre légion" width="720">
</p>

<h1 align="center">Kisk</h1>

<p align="center">
  <strong>Le point de ralliement de votre légion Aion 2.</strong>
</p>

<p align="center">
  Organisez vos groupes, coordonnez votre légion, et soyez prêts pour le combat.
</p>

<p align="center">
  🇬🇧 <a href="README.md">English version</a>
</p>

---

## 🎯 Qu'est-ce que Kisk ?

**Kisk** est un bot Discord conçu pour simplifier l'organisation d'une légion Aion 2.

Créez un groupe, choisissez un horaire, sélectionnez votre rôle, et laissez Kisk s'occuper du reste.

Que vous organisiez un donjon, un raid, un champ de bataille, une sortie PvP, une faille ou du farm dans l'abysse, Kisk offre à votre légion un seul endroit pour se coordonner :

* 👥 Qui vient ?
* 🛡️ Quels rôles manquent encore ?
* 📅 Quand joue-t-on ?
* ⏰ Qui a besoin d'un rappel ?
* 🪑 Qui attend une place ?
* 🏖️ Qui est absent ?
* 📊 Qui est disponible cette semaine ?

Comme le kisk en jeu, c'est le **point de ralliement que vous posez avant le combat.**

> **Kisk commence par l'organisation des groupes et vise à devenir la couche de coordination des communautés Aion 2.**

---

## ✨ Fonctionnalités

### 🎯 Gestion des groupes et des événements

* **`/event`** crée un appel de groupe avec :

  * un titre
  * un type d'activité
  * une composition de groupe
  * un horaire
  * une description
* Types d'activité pris en charge :

  * 🏰 Donjon
  * 🐉 Raid
  * 🚩 Champ de bataille
  * ⚔️ PvP
  * 🌀 Faille
  * 🌌 Abysse
  * 🎲 Autre

### 👥 Compositions de groupe

Trois configurations intégrées sont disponibles :

**Groupe de 5**

`1 Tank / 1 Heal / 3 DPS`

Composition de donjon classique.

**Groupe de 10**

`2 Tanks / 2 Heals / 6 DPS`

Pensé pour le contenu de groupe plus large comme les raids et les champs de bataille.

**Ouvert**

Premier arrivé, premier servi.

Choisissez entre **2 et 25 places**, sans restriction de rôle. Parfait pour le farm dans l'abysse et les autres activités où la composition est flexible.

### 🖱️ Inscription en un clic

Les joueurs rejoignent directement depuis le message de l'événement.

Choisissez votre rôle :

> 🛡️ Tank · 💚 Heal · 🗡️ DPS

Le groupe se met à jour immédiatement.

Les joueurs peuvent :

* changer de rôle
* quitter l'événement
* revenir
* consulter la composition actuelle

### 🪑 Liste d'attente intelligente

Quand un événement est complet, les joueurs supplémentaires sont automatiquement placés sur la liste d'attente.

Quand une place se libère :

1. Kisk trouve le premier joueur compatible.
2. Le promeut automatiquement.
3. Le notifie sur Discord.

Aucun réajustement manuel nécessaire.

### ⏰ Horaires intelligents

Kisk comprend les expressions de temps naturelles telles que :

```text
21:00
9pm
tomorrow 20:30
30/08 21:00
demain 21h
```

Les horaires des événements sont affichés à l'aide des **horodatages Discord tenant compte du fuseau horaire**, afin que chaque joueur voie l'heure locale correcte.

### 🔔 Rappels automatiques

Kisk rappelle automatiquement au groupe qu'un événement va commencer.

Le délai de rappel est configurable.

Par défaut :

**15 minutes avant l'événement.**

### 📅 Vue d'ensemble des événements

Utilisez :

```text
/events
```

pour voir les activités à venir avec des liens cliquables vers leurs messages Discord.

### ❌ Annulation

Le créateur de l'événement ou un modérateur peut annuler un événement.

Toutes les personnes inscrites sont notifiées automatiquement.

### 👤 Profils des joueurs

Les joueurs peuvent enregistrer leurs personnages avec :

```text
/profile set
```

Les profils prennent en charge :

* le personnage principal
* le reroll
* le nom du personnage
* la classe
* le rôle préféré

La classe du personnage peut ensuite apparaître à côté de son nom dans les listes de groupe.

Utilisez :

```text
/profile show
/roster
```

pour parcourir les informations des joueurs.

### 🏖️ Absences

Prévenez la légion quand vous êtes absent :

```text
/away start: 30/08 until: 05/09 reason: holidays
```

Consultez qui est actuellement absent :

```text
/absences
```

Revenez plus tôt avec :

```text
/back
```

### 📣 Annonces

Les modérateurs peuvent utiliser :

```text
/announce
```

pour créer des annonces mises en forme directement depuis Discord.

Les pings de rôle optionnels sont pris en charge.

### 📊 Sondages

Créez des sondages interactifs avec :

```text
/vote
```

Jusqu'à cinq options sont prises en charge.

Les sondages offrent :

* des boutons Discord
* des résultats en direct
* une clôture contrôlée
* une gestion par l'auteur ou un modérateur

### 📆 Disponibilités hebdomadaires

Publiez un tableau de disponibilités du lundi au dimanche :

```text
/availability post
```

Les joueurs peuvent indiquer les soirées où ils sont disponibles.

Les modérateurs peuvent configurer une republication hebdomadaire automatique :

```text
/availability weekly
```

Cela donne aux organisateurs un aperçu rapide des moments où la légion est la plus active.

### ✅ Fin d'un événement

Quand la sortie est terminée, appuyez sur :

**Done ✅**

Kisk envoie un GG au groupe et archive l'annonce de l'événement.

### 🎛️ Panneau sans commande

Les modérateurs peuvent utiliser :

```text
/panel
```

pour publier un message épinglé dont les boutons guident les membres pour créer
un événement ou signaler une absence **sans taper la moindre commande**.

La création se fait en deux temps : le bouton ouvre un message privé avec deux
menus déroulants — le **type** (Dungeon, Raid, Battleground, PvP, Rift, Abyss,
Other) et la **composition** (groupe de 5, groupe de 10, ou groupe libre de 5,
10 ou 25 places) — puis **Continue** ouvre un court formulaire pour le titre,
l'horaire et la description. Rien à écrire, rien à inventer : le seul type en
texte libre est le nom facultatif qu'on peut donner à un événement **Other**.

Associez-le à `/channels` pour garder le panneau dans son propre salon pendant
que ses résultats atterrissent ailleurs :

```text
/channels events: #events absences: #absences
```

### 👋 Accueil des nouveaux venus

Les modérateurs peuvent utiliser :

```text
/welcome
```

pour présenter les nouveaux membres et expliquer comment utiliser Kisk.

### 🧭 Onboarding de profil

Indiquez une fois à Kisk votre rôle « membre validé » :

```text
/onboard role: @Membre
```

Ensuite, dès qu'un membre reçoit ce rôle, Kisk lui envoie en MP un bouton qui
ouvre un formulaire guidé à menus déroulants pour enregistrer son personnage
principal — **classe** (avec les icônes de classes Aion 2), **rôle** et nom —
puis pour ajouter un reroll, le tout sans taper la moindre commande. Si ses MP
sont fermés, Kisk bascule sur le salon de bienvenue (ou le salon système du
serveur). Tout le flux côté membre est bilingue **anglais / français**.

### 🤖 Statut du bot

Kisk peut afficher le prochain événement à venir dans son statut Discord :

```text
Playing 🏰 Fire Temple — tomorrow 21:00
```

### 💾 Persistance

Kisk enregistre son état dans SQLite.

Les événements, inscriptions, profils, absences et autres données persistantes survivent aux redémarrages du bot.

Les boutons continuent de fonctionner une fois le bot de retour en ligne.

---

Où va Kisk ? Voir la **[feuille de route et la vision](ROADMAP.fr.md)**.

---

# 🚀 Démarrage rapide

## Prérequis

* Python **3.11+**
* Une application et un bot Discord
* Un serveur Discord où vous avez la permission d'installer le bot

---

## 1. Créer le bot Discord

Rendez-vous sur le [portail développeur Discord](https://discord.com/developers/applications) et créez une nouvelle application.

Nommez-la :

```text
Kisk
```

Vous pouvez utiliser :

```text
assets/avatar.png
assets/banner.png
```

pour l'identité visuelle du bot.

### Créer le bot

Ouvrez l'onglet **Bot** et réinitialisez/copiez le token du bot.

⚠️ **Ne partagez jamais votre token de bot.**

Quiconque possède le token peut contrôler votre bot.

Si le token est un jour exposé, réinitialisez-le immédiatement.

### Activer l'intent requis

Activez :

**SERVER MEMBERS INTENT**

Il est nécessaire pour la fonctionnalité d'accueil des nouveaux venus de Kisk.

Les autres intents privilégiés ne sont pas requis.

### Installer le bot

Dans l'onglet **Installation** (ou OAuth2 → URL Generator), activez :

**Scopes**

* `bot`
* `applications.commands`

**Permissions**

* Send Messages
* Embed Links
* Read Message History

Ouvrez l'URL d'installation générée et invitez Kisk sur votre serveur.

---

# 💻 2. Lancer Kisk en local

Clonez le dépôt :

```bash
git clone https://github.com/NaxosOne/aion2-group-bot.git
cd aion2-group-bot
```

Créez un environnement virtuel :

```bash
python -m venv .venv
```

Activez-le :

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Installez les dépendances :

```bash
pip install -r requirements.txt
```

Créez votre fichier d'environnement :

### Linux / macOS

```bash
cp .env.example .env
```

### Windows

```powershell
copy .env.example .env
```

Modifiez `.env` et configurez :

```env
DISCORD_TOKEN=your_token_here
GUILD_ID=your_guild_id_here
```

`GUILD_ID` permet aux commandes slash d'apparaître immédiatement sur votre serveur de développement.

Démarrez Kisk :

```bash
python -m bot.main
```

Dès que vous voyez :

```text
Logged in as ...
```

Kisk est en ligne.

Essayez :

```text
/event
```

🎉

---

# ☁️ 3. Héberger Kisk 24/7

Un bot Discord doit rester en ligne en permanence pour répondre aux interactions et envoyer les rappels programmés.

Consultez **[DEPLOYMENT.md](DEPLOYMENT.md)** pour les options d'hébergement en production, y compris des solutions gratuites ou quasi gratuites comme Oracle Cloud et Railway.

---

# 🎮 Utilisation

## Groupes

```text
/event title: Fire Temple HM
       type: Dungeon
       comp: Party of 5
       when: tomorrow 21:00
       ping: @Aion2

/event title: Evening BG
       type: Battleground
       comp: Party of 10
       when: 9pm

/event title: Abyss farming
       type: Abyss
       comp: Open
       size: 8

/events
```

`ping` est optionnel : indique un rôle à notifier quand l'événement est publié.
Le ping `@everyone` est réservé aux modérateurs.

## Profils

```text
/profile set character: Main name: Kratos class: Templar role: Tank

/profile show [member]

/roster
```

## Absences

```text
/away start: 30/08 until: 05/09 reason: holidays

/absences

/back
```

## Communication

```text
/announce [ping: @role]

/vote question: What tonight? option1: Dungeon option2: PvP option3: Nothing
```

## Disponibilités

```text
/availability post

/availability weekly
```

## Nouveaux membres

```text
/welcome                      → accueillir les nouveaux dans ce salon (modérateurs)
/onboard role: @Membre        → MP aux nouveaux de ce rôle pour configurer leur profil
```

## Panneau & salons

```text
/panel                                          → publier le panneau à boutons
/channels events: #events absences: #absences   → où sont postés les résultats
```

**Astuce pour un serveur bien rangé** : publiez `/panel` dans un salon dédié et
épinglez-le, puis lancez `/channels events: #events absences: #absences` pour
que le panneau ne soit jamais enterré sous ses propres résultats. Les membres
qui n'aiment pas taper des commandes cliquent simplement sur **Créer un
événement** ou **Signaler une absence** et remplissent le formulaire ; l'événement
apparaît dans le salon des événements et ils reçoivent un lien vers celui-ci.

Les emojis de rôle, de type d'événement et de **classe Aion 2** peuvent être
remplacés par les vôtres — importez-les comme emojis personnalisés dans le
portail développeur (onglet **Emojis**), puis définissez `EMOJI_TANK`,
`EMOJI_DUNGEON`, `EMOJI_GLADIATOR`, … dans `.env`. Un pack d'icônes de rôle et
de type est fourni dans [`assets/emoji/`](assets/emoji/README.md). Les emojis
personnalisés
apparaissent dans les embeds, les boutons et les messages ; Discord affiche les
listes de choix des commandes slash en texte brut, où seuls les emojis Unicode
fonctionnent.

---

# 🏗️ Structure du projet

```text
assets/
  avatar.png
  banner.png
  emoji/               Role + event-type icon pack (PNG + SVG)
  ...

bot/
  main.py              Entry point: connection and command sync
  config.py            Environment/configuration
  db.py                SQLite persistence
  logic.py             Party and waitlist logic
  embeds.py            Discord announcement embeds
  views.py             Buttons and interactions
  actions.py           Event/absence logic shared by commands and forms
  errors.py            Always answer the user when something fails

  cogs/
    groups.py           /event, /events, reminders and bot status
    profiles.py         /profile and /roster
    legion.py           /away, /absences, /back, /announce, /welcome
    polls.py            /vote and /availability
    panel.py            /panel: buttons opening fill-in forms
    onboarding.py       /onboard: DM new members to set up their profile

  utils/
    time_parse.py       Natural-language time parsing
    onboarding.py       Pure onboarding helpers (role/profile checks)

tests/
  test_logic.py
  test_time_parse.py
  test_onboarding.py
```

### Architecture

Kisk s'efforce de garder sa logique métier indépendante du code spécifique à Discord.

```text
                 Discord
                    │
                    ▼
             ┌─────────────┐
             │    Kisk     │
             └──────┬──────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       Commands    Views    Scheduler
          │         │         │
          └─────────┼─────────┘
                    ▼
               Core Logic
                    │
                    ▼
                  SQLite
```

La composition des groupes, les listes d'attente et l'analyse du temps sont maintenues sous forme de logique testable plutôt que fortement couplées aux interactions Discord.

---

# 🧪 Tests

La logique métier peut être testée indépendamment. Installez les dépendances de
développement et lancez la suite avec pytest :

```bash
pip install -e ".[dev]"
pytest
```

Lorsque vous ajoutez une fonctionnalité, privilégiez l'ajout de tests pour la logique sous-jacente avant de la brancher à Discord.

Une attention particulière doit être portée à :

* les fuseaux horaires
* les transitions d'heure d'été/hiver
* la promotion depuis la liste d'attente
* le changement de rôle
* les inscriptions en double
* les redémarrages du bot
* les rappels programmés

---

# 🤝 Contribuer

Kisk est un projet communautaire et les contributions sont les bienvenues.

Si vous souhaitez travailler sur une fonctionnalité plus importante, ouvrez d'abord une issue afin que nous puissions discuter de l'approche avant de l'implémenter.

Les bons domaines de contribution incluent :

* 🐛 Corrections de bugs
* 🧪 Tests
* 📚 Documentation
* 🌍 Traductions
* 🎨 UX Discord
* ⚙️ Logique de groupe centrale
* 📅 Planification
* 👥 Gestion de légion
* 🧠 Formation des groupes

Avant d'ouvrir une PR :

1. Gardez les changements ciblés.
2. Ajoutez ou mettez à jour les tests le cas échéant.
3. Assurez-vous que les fonctionnalités existantes fonctionnent toujours.
4. Mettez à jour la documentation si le comportement change.

---

# 🌍 Classes Aion 2

Les classes actuellement suggérées par `/profile` sont volontairement configurables.

La liste se trouve dans :

```text
bot/cogs/profiles.py
```

Mettez à jour `AION_CLASSES` à mesure que les noms définitifs des classes Aion 2 seront connus.

Les classes sont actuellement des suggestions plutôt qu'une validation stricte, donc des valeurs personnalisées restent possibles.

---

# 📜 Philosophie

Kisk est construit autour d'une idée simple :

> **Le bot devrait organiser les corvées pour que les joueurs puissent se concentrer sur le jeu.**

Cela signifie :

* des commandes simples
* une configuration minimale
* une automatisation utile
* aucune bureaucratie inutile
* aucun système de gestion géant imposé aux guildes occasionnelles

Kisk devrait aider une légion à se coordonner sans transformer le jeu en second travail.

---

# 📄 Licence

Voir [LICENSE](LICENSE).
