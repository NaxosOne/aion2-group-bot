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
* Pack d'emojis personnalisés (rôles et types d'événement)
* Rappels automatiques, clôture et annulation d'événement
* Multi-serveur — Kisk fonctionne indépendamment sur autant de serveurs que voulu
* Onboarding de profil guidé (`/onboard`) — les membres validés reçoivent un MP pour enregistrer leur main (et reroll), bilingue FR/EN, avec repli sur salon
* Gestion des profils — `/profile delete` (le tien, ou celui d'un membre pour les modérateurs) et nettoyage automatique au départ d'un membre du serveur

## 🟢 Phase 1 — Meilleure organisation des groupes

Rendre la création et la gestion des groupes aussi fluides que possible.

* [ ] Fil de discussion automatique pour chaque événement
* [ ] Sélecteur de classe Aion 2 lors de l'inscription
* [ ] Confirmation d'inscription avant l'événement (un rapide « tu viens ? »)
* [ ] UX améliorée des événements et des groupes
* [ ] Meilleure gestion de la liste d'attente (réorganisation manuelle, places par rôle)
* [ ] Compositions de groupe plus flexibles (ratios personnalisés)

## 🔵 Phase 2 — Planification de légion

Faciliter l'organisation des activités récurrentes de la légion.

* [ ] Événements récurrents
* [ ] Événements multi-groupes pour les sièges
* [ ] Salons vocaux temporaires
* [ ] Export calendrier (`.ics`)
* [ ] Disponibilités hebdomadaires améliorées
* [ ] Gestion de séries d'événements

## 🟣 Phase 3 — Formation intelligente des groupes

Passer de l'organisation manuelle des groupes à une aide automatique pour trouver le bon groupe.

* [ ] Système LFG
* [ ] Statut « disponible maintenant »
* [ ] Suggestions automatiques de groupes
* [ ] Équilibrage rôle/classe
* [ ] Promotion intelligente (selon les rôles) depuis la liste d'attente
* [ ] Suggestions de remplaçants
* [ ] Meilleures préférences des joueurs

## 🟠 Phase 4 — Outils de légion

Donner aux organisateurs une vision plus claire de ce qui se passe.

* [ ] Tableau de bord de légion
* [ ] Interface web

## 💡 En exploration

Certaines idées sont intéressantes, mais ne sont pas prioritaires actuellement :

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
