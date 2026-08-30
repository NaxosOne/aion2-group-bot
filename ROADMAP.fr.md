<p align="center">
  🇬🇧 <a href="ROADMAP.md">English version</a> · ⬅️ <a href="README.fr.md">Retour au README</a>
</p>

# 🗺️ Feuille de route

Kisk commence volontairement petit.

L'objectif à long terme est d'évoluer d'un simple bot de groupe vers un **outil de coordination complet pour les légions Aion 2**.

La feuille de route est flexible et évoluera avec le jeu et la communauté.

## ✅ Déjà livré

Les fondations sont en place :

* Horaires localisés — chaque joueur voit l'heure de l'événement dans son propre fuseau
* Promotion automatique depuis la liste d'attente — le premier joueur compatible est promu et notifié dès qu'une place se libère
* Panneau sans commande (`/panel`) avec salons de résultats dédiés (`/channels`)
* Pack d'emojis personnalisés — rôles, types d'événement et toutes les classes Aion 2
* Rappels automatiques, clôture et annulation d'événement
* Multi-serveur — Kisk fonctionne indépendamment sur autant de serveurs que voulu
* Onboarding de profil guidé (`/onboard`) — les membres validés reçoivent un MP pour enregistrer leur main (et reroll), dans la langue du serveur, avec repli sur salon
* Langue par serveur (`/language`) — choisir le français ou l'anglais (ou Auto pour suivre la langue Discord du serveur) ; chaque embed, bouton, MP d'onboarding et message s'affiche alors uniquement dans cette langue
* Gestion des profils — `/profile delete` (le tien, ou celui d'un membre pour les modérateurs) et nettoyage automatique au départ d'un membre du serveur
* Fil de discussion automatique sur chaque message d'événement (best-effort ; sauté si le bot n'a pas Create Public Threads)
* Invite RSVP avant un événement — un message « tu viens ? » avec boutons confirmer/décliner et un décompte en direct (timing configurable)
* Sélecteur de personnage à l'inscription — les joueurs ayant plusieurs personnages enregistrés choisissent celui qu'ils amènent après avoir choisi un rôle, chacun affiché avec son icône de classe Aion 2 ; `/profile set` restreint les personnages à la liste de classes connues
* Réordonnancement de la file par les admins — un bouton « Gérer la file » (admins uniquement) permet de faire monter ou descendre les inscriptions pour promouvoir des joueurs en attente ; les places par rôle restent respectées et tout joueur poussé dans la party est notifié
* Modifier un événement publié — un bouton « Modifier » (créateur ou modérateur) change le titre, l'heure ou la description ; replanifier ré-arme le rappel et l'invite RSVP et pingue la party
* Visibilité des places libres — un événement standard en cours affiche ses places vides par rôle et un résumé « Manque : 1 Tank, 2 DPS » jusqu'à ce qu'il soit complet

## ✅ Phase 1 — Meilleure organisation des groupes *(terminée)*

La création et la gestion des groupes sont désormais fluides : horaires
localisés, groupes par rôle, inscription par personnage, promotion automatique
de la file, réordonnancement admin, visibilité des places libres et édition
d'événement sont en place. Voir **Déjà livré** ci-dessus pour le détail.

## ✅ Phase 2 — Planification de légion *(terminée)*

L'organisation des activités récurrentes de la légion est désormais couverte :
événements récurrents, événements de siège découpés en groupes, salons vocaux
temporaires, export calendrier et tableau de disponibilités amélioré sont en
place.

* [x] Événements récurrents
* [x] Événements multi-groupes pour les sièges *(léger : un roster partagé affiché en groupes)*
* [x] Salons vocaux temporaires
* [x] Export calendrier (`.ics`)
* [x] Disponibilités hebdomadaires améliorées
* [x] Gestion de séries d'événements *(couvert par les événements récurrents)*

## ✅ Phase 3 — Formation intelligente des groupes *(terminée)*

La couche de visibilité dont une légion a vraiment besoin est en place : les
joueurs signalent ce qu'ils cherchent et qui est libre pour jouer maintenant, et
les organisateurs forment les groupes à partir de cette image en direct.

* [x] Système LFG *(pool + tableau par serveur, avec un bouton « Inviter LFG » sur les événements ouverts)*
* [x] Statut « disponible maintenant » *(présence sans activité, affichée en tête du tableau LFG)*

L'automatisation lourde du matchmaking a été envisagée puis **volontairement
écartée** : une légion est un groupe soudé qui forme ses parties socialement, pas
un pool d'inconnus à apparier par algorithme. Ces idées passent en **Exploration**.

## 🟠 Phase 4 — Outils de légion *(en cours)*

Donner aux organisateurs une vision plus claire de ce qui se passe.

* [x] Tableau de bord de légion *(une vue `/dashboard` auto-rafraîchie, dans Discord)*
* [ ] Interface web *(un saut de périmètre majeur — son propre brainstorming + spec avant tout code)*

## 💡 En exploration

Certaines idées sont intéressantes, mais ne sont pas prioritaires actuellement :

* Suggestions automatiques de groupes *(une légion forme ses parties socialement, pas par matchmaking)*
* Équilibrage rôle/classe
* Suggestions de remplaçants *(le bouton « Inviter LFG » couvre déjà une place libérée)*
* Meilleures préférences des joueurs
* Compositions de groupe plus flexibles (ratios de rôles personnalisés)
* Jets de butin (loot rolls)
* Anniversaires
* Hall of fame de screenshots
* Davantage d'intégrations Aion 2
* Outils communautaires supplémentaires

Kisk doit rester **utile plutôt que surchargé**.

Si une fonctionnalité n'aide pas une légion à s'organiser, communiquer ou jouer ensemble, elle n'a probablement pas sa place dans Kisk.

---

# 🧭 La vision

Les communautés Aion 2 ne devraient pas avoir besoin de tableurs, de calendriers externes et de dizaines de messages Discord juste pour organiser un groupe.

Kisk vise à simplifier le processus :

```text
Player
   │
   ├── Profile
   ├── Availability
   └── Preferences
          │
          ▼
       Kisk
          │
   ┌──────┼──────┐
   ▼      ▼      ▼
 Events  LFG   Legion
   │      │      │
   └──────┼──────┘
          ▼
    Group formation
          │
          ▼
       The fight
```

L'objectif à long terme est simple :

> **Kisk devrait savoir ce que fait votre légion, qui est disponible, quels groupes ont besoin de joueurs, et aider à préparer tout le monde au combat.**
