<p align="center">
  🇬🇧 <a href="ROADMAP.md">English version</a> · ⬅️ <a href="README.fr.md">Retour au README</a>
</p>

# 🗺️ Feuille de route

Kisk commence volontairement petit.

L'objectif à long terme est d'évoluer d'un simple bot de groupe vers un **outil de coordination complet pour les légions Aion 2**.

La feuille de route est flexible et évoluera avec le jeu et la communauté.

## 🟢 Phase 1 — Meilleure organisation des groupes

Rendre la création et la gestion des groupes aussi fluides que possible.

* [ ] Ping de rôle Discord lors de la création d'un événement
* [ ] Fil de discussion automatique pour chaque événement
* [ ] Sélecteur de classe Aion 2 lors de l'inscription
* [ ] Confirmation de présence
* [ ] UX améliorée des événements et des groupes
* [ ] Meilleure gestion de la liste d'attente
* [ ] Compositions de groupe plus flexibles

## 🔵 Phase 2 — Planification de légion

Faciliter l'organisation des activités récurrentes de la légion.

* [ ] Événements récurrents
* [ ] Événements multi-groupes pour les sièges
* [ ] Salons vocaux temporaires
* [ ] Export calendrier (`.ics`)
* [ ] Disponibilités hebdomadaires améliorées
* [ ] Meilleure prise en charge des fuseaux horaires
* [ ] Gestion de séries d'événements

## 🟣 Phase 3 — Formation intelligente des groupes

Passer de l'organisation manuelle des groupes à une aide pour trouver automatiquement le bon groupe.

* [ ] Système LFG
* [ ] Statut « Disponible maintenant »
* [ ] Suggestions automatiques de groupe
* [ ] Équilibrage des rôles et des classes
* [ ] Promotion intelligente depuis la liste d'attente
* [ ] Suggestions de remplaçants
* [ ] Historique des groupes
* [ ] Meilleures préférences des joueurs

## 🟠 Phase 4 — Intelligence de légion

Donner aux organisateurs une meilleure visibilité sur leur communauté.

* [ ] Historique de présence
* [ ] Statistiques de participation
* [ ] Répartition des classes et des rôles
* [ ] Statistiques d'activité de la légion
* [ ] Tendances d'activité
* [ ] Tableau de bord de légion
* [ ] Interface web
* [ ] Prise en charge multi-serveurs

## 💡 En exploration

Certaines idées sont intéressantes, mais ne sont pas prioritaires actuellement :

* Jets de loot
* Anniversaires
* Panthéon des captures d'écran
* DKP
* Statistiques de présence avancées
* Plus d'intégrations Aion 2
* Outils communautaires supplémentaires

Kisk doit rester **utile plutôt que surchargé**.

Si une fonctionnalité n'aide pas une légion à s'organiser, à communiquer ou à jouer ensemble, elle n'a probablement pas sa place dans Kisk.

---

# 🧭 La vision

Les communautés Aion 2 ne devraient pas avoir besoin de tableurs, de calendriers externes et de dizaines de messages Discord juste pour organiser un groupe.

Kisk vise à rendre le processus simple :

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
