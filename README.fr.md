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

**Avec quel personnage ?** Les joueurs ayant enregistré plusieurs personnages
reçoivent, après avoir choisi leur rôle, un menu déroulant privé listant leurs
personnages avec leurs icônes de classe. Le groupe affiche ensuite le
personnage par son nom, précédé de l'icône de sa classe, pour lire la compo
d'un coup d'œil :

```text
🛡️ Tank (1/1)
• @Naxos — 🛡️ Kratos (Templar)

💚 Heal (1/1)
• @Ael — ✨ Nami (Cleric)

🗡️ DPS (3/3)
• @Kyo — 🗡️ Loki (Assassin)
• @Ryu — 🏹 Zed (Ranger)
• @Mia — 🔥 Ashe (Sorcerer)
```

Recliquer sur le même rôle change de personnage sans perdre sa place dans la
file. Les joueurs avec un seul personnage (ou aucun) sont inscrits directement,
exactement comme avant.

**Les places libres sont visibles d'un coup d'œil.** Tant qu'un groupe standard
a de la place, chaque champ de rôle affiche ses places vides en lignes discrètes
`◦ libre`, et un court résumé **Manque : 1 Tank, 2 DPS** apparaît sous l'en-tête
— pour voir ce qui manque et combler le bon rôle.

### 🪑 Liste d'attente intelligente

Quand un événement est complet, les joueurs supplémentaires sont automatiquement placés sur la liste d'attente.

Quand une place se libère :

1. Kisk trouve le premier joueur compatible.
2. Le promeut automatiquement.
3. Le notifie sur Discord.

Aucun réajustement manuel nécessaire.

**Les admins peuvent réordonner la file.** Un bouton **Gérer la file** sur chaque
événement (admins uniquement — Gérer le serveur) ouvre un panneau privé listant
toutes les inscriptions dans l'ordre, marquées ✅ *dans la party* ou ⏳ *en
attente*. Choisis un joueur et fais-le monter ou descendre ; la party est
recalculée en direct (les places par rôle restent respectées) et tout joueur
poussé dans la party est notifié, exactement comme une promotion automatique.

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

### 🙋 RSVP — « tu viens ? »

Une heure avant un événement planifié (réglable via `RSVP_MINUTES`), Kisk poste
une courte invite **« tu viens ? »** qui ping le groupe, avec deux boutons —
**Je viens ✅** et **Pas dispo ❌**. L'invite se met à jour en direct avec les
confirmés, les absents et ceux qui n'ont pas répondu, pour que les organisateurs
comblent les places vides avant le début.

Les modérateurs peuvent aussi la déclencher immédiatement avec `/rsvp event:
<lien ou ID du message>` — pratique pour demander tout de suite sans attendre la
fenêtre automatique.

Dirigez les RSVP vers leur propre salon avec `/channels rsvp: #rsvp` pour ne pas
encombrer le salon des événements ; sinon ils apparaissent dans le salon de
l'événement.

### 📅 Vue d'ensemble des événements

Utilisez :

```text
/events
```

pour voir les activités à venir avec des liens cliquables vers leurs messages Discord.

Le bouton **Calendrier** sur n'importe quel événement te remet (en privé) un
fichier `.ics` des événements planifiés à venir du serveur — importe-le dans ton
agenda.

### ✏️ Modification

Le créateur de l'événement ou un modérateur peut modifier un événement publié
via le bouton **Modifier** : changer le **titre**, l'**heure** ou la
**description** dans un formulaire rapide (le type, la composition et la taille
restent fixes). Replanifier ré-arme le rappel et l'invite « tu viens ? » sur la
nouvelle heure et pingue la party ; vider le champ heure retire l'horaire.

### 🔁 Événements récurrents

Les modérateurs peuvent faire répéter un événement chaque semaine. Ajoute
`repeat: Weekly` à `/event` (une heure est requise) :

```text
/event title: Raid de légion type: Raid comp: Groupe de 10 when: mardi 21:00 repeat: Weekly
```

Kisk poste l'événement de chaque semaine **un jour à l'avance** pour laisser le
temps de s'inscrire. Gère-les avec :

```text
/recurring list          → les événements récurrents du serveur, avec leurs ids
/recurring stop id: 3    → en arrêter un (modérateurs)
```

### ❌ Annulation

Le créateur de l'événement ou un modérateur peut annuler un événement.

Toutes les personnes inscrites sont notifiées automatiquement.

### 👤 Profils des joueurs

Les joueurs peuvent enregistrer leurs personnages avec :

```text
/profile set name: Kratos class: Templar role: Tank
```

Chaque joueur peut enregistrer **jusqu'à 10 personnages** — un principal et
autant de rerolls qu'il en joue vraiment. Chaque personnage a un nom, une
classe et un rôle de prédilection.

Le premier personnage enregistré devient le **principal** : c'est celui affiché
par défaut dans les listes de groupe et sur le roster. Pour en changer :

```text
/profile main character: Loki
```

Relancer `/profile set` avec un nom déjà connu met à jour ce personnage au lieu
d'en créer un jumeau : corriger une classe ou un rôle tient en une commande.

Utilisez :

```text
/profile show [member]
/roster
```

pour parcourir les informations des joueurs. `/roster` affiche une ligne par
membre, triée par rôle — tanks, puis heals, puis DPS — et à rôle égal par
classe, puis par nom de personnage.

Pour supprimer un personnage, ou tout un profil :

```text
/profile delete character: Loki      → ce personnage précis
/profile delete                      → tous les personnages
```

Les modérateurs peuvent viser un autre membre avec `member:`. Kisk fait aussi le
**ménage automatiquement** quand quelqu'un quitte le serveur — tous ses
personnages, ses inscriptions, absences et disponibilités sont supprimés.

Ce ménage se déclenche au moment du départ, ce qui ne marche que si le bot est
en ligne. Un balayage quotidien, également joué au démarrage, rattrape ceux
partis pendant un redémarrage. Il ne fait jamais confiance à un cache de
membres vide : un profil n'est supprimé qu'une fois le départ confirmé par
Discord.

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

### 🧵 Fils de discussion

Chaque événement obtient automatiquement son **propre fil de discussion**
attaché à son message, pour que le groupe se coordonne sans polluer le salon.
Ça marche pour `/event` comme pour le panneau. Si le bot n'a pas la permission
**Create Public Threads**, Kisk saute simplement cette étape — l'événement est
quand même créé.

### 🔊 Salons vocaux temporaires

Désigne une catégorie une fois et chaque événement **planifié** obtient son
propre salon vocal temporaire :

```text
/channels voice: <catégorie>
```

Le salon (**🔊 <titre de l'événement>**) est créé autour de la fenêtre de rappel
avant l'événement pour que le groupe se rassemble en avance, et supprimé quand
l'événement est marqué **Terminé** ou **annulé** — avec un nettoyage de sécurité
quelques heures après le début si personne ne clique Terminer. Il faut la
permission **Gérer les salons** ; sans catégorie configurée, la fonction reste
désactivée.

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
puis pour ajouter autant d'autres personnages qu'il le souhaite, le tout sans
taper la moindre commande. Si ses MP
sont fermés, Kisk bascule sur le salon de bienvenue (ou le salon système du
serveur). Tout le flux côté membre s'affiche dans la langue du serveur (voir
`/language` ci-dessous).

### 🌍 Langue du serveur

Kisk parle **français** ou **anglais**, au choix par serveur :

```text
/language choice: Français
```

Tout ce que voient les membres — embeds d'événements et de RSVP, boutons, MP
d'onboarding, profils, sondages, panneau et messages d'erreur — apparaît alors
**uniquement** dans cette langue. Choisis **Auto** (par défaut) pour suivre
automatiquement la langue Discord du serveur. Seuls les modérateurs (Gérer le
serveur) peuvent la changer.

Seule exception : le sélecteur de commandes `/` de Discord — Discord localise les
noms et descriptions des commandes selon la langue du client Discord de **chaque
membre**, pas selon le réglage serveur, pour que ce menu reste lisible par tous.

### 🤖 Statut du bot

Kisk peut afficher le prochain événement à venir dans son statut Discord :

```text
Playing 🏰 Fire Temple — tomorrow 21:00
```

Le statut utilise toujours les icônes Unicode, même sur un serveur qui a
configuré les siennes : Discord affiche la présence d'un bot littéralement, un
emoji personnalisé y apparaîtrait donc sous forme de code `<:dungeon:123…>`.

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
* Create Public Threads *(pour le fil de discussion par événement ; optionnel — Kisk fonctionne sans)*

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
/profile set name: Kratos class: Templar role: Tank [main: True]
/profile main character: Loki                        → changer son personnage par défaut

/profile show [member]
/profile delete [character] [member]                 → character vide = tous
                                                       les modérateurs peuvent cibler un membre
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
/panel                                          → publier le panneau, ou rafraîchir l'existant
/channels events: #events absences: #absences rsvp: #rsvp   → où sont postés les résultats
/redeploy                                       → rafraîchir le panneau + les events ouverts (admins)
```

Relancer **`/panel`** édite le panneau déjà posté (pas de doublon).
**`/redeploy`** (admins) ré-affiche chaque événement ouvert avec les derniers
boutons et embed et rafraîchit le panneau — à lancer une fois après une mise à
jour du bot pour que les messages déjà postés récupèrent les nouveautés. Un
panneau posté avant l'existence de cette fonction n'est pas encore suivi :
relance `/panel` une fois pour l'enregistrer.

## Langue

```text
/language choice: Français     → langue du serveur : Français / English / Auto (modérateurs)
```

## Rôles & permissions

Kisk a deux niveaux de permission, basés par défaut sur les permissions Discord :

- **Modérateur** (Gérer les messages) — fermer un sondage, terminer/annuler/
  modifier un événement.
- **Admin** (Gérer le serveur) — réordonner la file, `/redeploy`, supprimer le
  profil d'un autre membre.

Tu peux aussi désigner un **rôle admin Kisk** pour donner les pouvoirs admin (et
donc modérateur) à des membres de confiance sans leur accorder « Gérer le
serveur » :

```text
/admin-role role: @Officiers   → traite @Officiers comme admins Kisk (Gérer le serveur requis)
/admin-role clear: true        → retire le rôle configuré
/admin-role                    → affiche le rôle actuel
```

Seul un membre avec « Gérer le serveur » réel peut le définir, donc le rôle ne
peut pas étendre sa propre portée. Le rôle prend effet immédiatement sur les
actions **à boutons** (Modifier, Gérer la file, …). Les slash-commands comme
`/redeploy` restent cachées par la barrière de permission Discord ; pour les
exposer au rôle, autorise la commande pour lui dans **Paramètres du serveur →
Intégrations**.

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
de type est fourni dans [`assets/emoji/`](assets/emoji/README.md). Les emojis personnalisés apparaissent dans les embeds, les boutons et les
messages. Deux surfaces sont du texte brut pour Discord et retombent toujours
sur les icônes Unicode : les listes de choix des commandes slash, et le statut
du bot lui-même.

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
  i18n.py              Per-server language resolution and string catalog

  cogs/
    groups.py           /event, /events, reminders and bot status
    profiles.py         /profile and /roster
    legion.py           /away, /absences, /back, /announce, /welcome
    polls.py            /vote and /availability
    panel.py            /panel: buttons opening fill-in forms
    onboarding.py       /onboard: DM new members to set up their profile
    settings.py         /language: choose the server's language

  locales/
    en.json             English strings (edit alongside fr.json)
    fr.json             French strings — same keys as en.json

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

La liste des classes est volontairement configurable, et tient en un seul endroit :

```text
bot/config.py       → CLASS_EMOJI
```

Chaque entrée associe une classe à son emoji par défaut, et alimente d'un coup
les menus de classe, le roster et le choix du personnage à l'inscription.

Le **Fist Fighter** est déjà dessiné (`assets/emoji/fistfighter.png`) et tient
à une ligne commentée : décommentez-la dans `CLASS_EMOJI` le jour de sa sortie
et il apparaîtra partout tout seul.

`/profile set` propose exactement ces classes et n'accepte rien d'autre : une
faute de frappe ne peut plus se glisser dans le roster. Les personnages
enregistrés sous une version antérieure, quand le champ était libre, continuent
de fonctionner — ils n'affichent simplement pas d'icône de classe. Relancer
`/profile set` avec le même nom de personnage les remet d'aplomb.

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
