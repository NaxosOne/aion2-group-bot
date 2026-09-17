# Guide officier — Recrutement & onboarding avec Kisk

Ce guide s'adresse aux officiers/modérateurs de la légion. Il couvre la
configuration initiale (à faire une seule fois), le déroulé au quotidien
quand un nouveau joueur arrive, et les cas où quelque chose se passe mal.

## 1. Configuration initiale (une seule fois par serveur)

Trois réglages doivent être en place **avant** que le recrutement fonctionne
correctement.

### a. Le salon de revue des candidatures

```text
/recruit channel action: Enable in this channel
```

À lancer dans le salon réservé aux officiers. C'est là que les fiches de
candidature arriveront avec les boutons **Accepter** / **Refuser**.

### b. Le rôle « membre validé »

```text
/onboard role role: @Dexterity France
```

C'est le rôle que **Accepter** attribue automatiquement, et qui déclenche le
MP d'onboarding du profil. Kisk vérifie immédiatement s'il peut réellement
l'attribuer et t'avertit sinon (voir section 4 — c'est le point qui a cassé
le recrutement précédemment).

### c. Qui peut décider (Accepter / Refuser)

Par défaut, seuls les membres avec **Gérer le serveur** peuvent cliquer
Accepter/Refuser. Pour l'ouvrir à un rôle « Officier » dédié sans donner
Gérer le serveur :

```text
/settings admin-role role: @Officier
```

### d. Permissions à donner au bot Kisk

| Permission Discord | Pourquoi |
|---|---|
| **Gérer les salons** | crée/supprime le salon privé de chaque candidat |
| **Gérer les rôles** | attribue le rôle `@Dexterity France` à l'acceptation |
| Rôle de Kisk **au-dessus** de `@Dexterity France` dans la hiérarchie | Discord refuse silencieusement d'attribuer un rôle situé au-dessus du rôle du bot — place le rôle de Kisk tout en haut, ou juste au-dessus des rôles qu'il doit gérer |

### Optionnel

```text
/recruit post          → poste un panneau "Postuler" permanent dans un salon
/welcome action: on     → tableau de bienvenue automatique à la validation
/language choice: Français
```

## 2. Le parcours complet d'un nouveau joueur

```
Arrivée sur le serveur
        │
        ▼
Kisk envoie un MP avec un bouton "📝 Postuler"
(repli dans le salon d'accueil si ses MP sont fermés)
        │
        ▼
Le joueur choisit Classe + Rôle, puis remplit un formulaire
(nom du perso, niveau/CP, expérience, disponibilités, motivation)
        │
        ▼
Kisk crée un salon privé "cand-<classe>-<nom>" (candidat + officiers)
et poste une fiche dans le salon officiers avec ✅ Accepter / ❌ Refuser
        │
        ▼
   Un officier décide
        │
   ┌────┴─────┐
   ▼          ▼
Accepter   Refuser (motif optionnel, envoyé en MP)
   │          │
   ▼          ▼
Rôle @Dexterity France attribué   Salon + fiche nettoyés
Salon supprimé, fiche → ✅         MP de refus envoyé
   │
   ▼
Kisk détecte le nouveau rôle → MP avec bouton
"📝 Configurer mon profil"
   │
   ▼
Le joueur choisit Classe + Rôle + nom de perso
→ profil enregistré, visible dans /roster
```

## 3. Au quotidien : traiter une candidature

1. Une fiche apparaît dans le salon officiers : classe, rôle, niveau/CP,
   expérience, disponibilités, motivation, et un lien vers le salon privé du
   candidat pour discuter/poser des questions avant de trancher.
2. **✅ Accepter** : attribue le rôle de membre validé, DM le candidat, ferme
   son salon privé, tamponne la fiche `✅ Accepté par @toi`.
3. **❌ Refuser** : ouvre une fenêtre pour un motif optionnel (envoyé en MP au
   candidat), ferme le salon, tamponne la fiche `❌ Refusé par @toi`.
4. Si le candidat quitte le serveur avant votre décision, sa fiche, son salon
   et ses données sont supprimés automatiquement — rien à faire.

> Seuls les Kisk-admins (rôle configuré via `/settings admin-role`, ou
> **Gérer le serveur**) voient leur clic pris en compte ; les autres reçoivent
> un message leur indiquant qu'ils ne sont pas habilités.

## 4. Symptômes et dépannage

### « J'ai accepté quelqu'un mais il n'a pas le rôle »

Depuis le correctif du 2026-09-17, ce cas n'est plus silencieux :

- **La fiche** affiche `⚠️ Accepté par @toi — l'attribution du rôle a échoué,
  ajoute-le manuellement` au lieu du `✅` habituel.
- **Toi** reçois un message privé (visible seulement par toi, dans le salon)
  du type *« Candidature acceptée, mais je n'ai pas pu attribuer
  **@Dexterity France** — vérifie que mon rôle est bien au-dessus dans la
  hiérarchie et que j'ai la permission Gérer les rôles, puis ajoute-le
  manuellement. »*

Cause quasi systématique : le rôle de Kisk est positionné **en dessous** du
rôle `@Dexterity France` dans **Paramètres du serveur → Rôles**, ou Kisk n'a
pas (ou plus) la permission **Gérer les rôles**. Corrige la hiérarchie/la
permission, puis attribue le rôle au joueur manuellement (Discord → fiche du
membre → Rôles).

Pour éviter que ça se reproduise : à chaque fois que tu relances
`/onboard role`, Kisk vérifie la hiérarchie et t'avertit tout de suite si ça
ne passera pas — pas besoin d'attendre qu'un candidat en fasse les frais.

### « Le joueur a le rôle mais n'a jamais reçu le MP d'onboarding, ou n'a pas de profil »

Voir le [guide dédié au joueur](guide-joueur-onboarding.md) — tu peux le lui
transmettre directement. En résumé, deux façons de le débloquer :

1. **Le plus simple, sans rien changer côté rôle** : dis-lui d'utiliser
   directement `/profile set` (voir le guide joueur) — ça fonctionne dans
   tous les cas, avec ou sans le bouton MP.
2. **Renvoyer le MP** : retire-lui puis redonne-lui le rôle
   `@Dexterity France` (deux actions séparées, pas un clic annulé) — Kisk
   détecte la ré-attribution et renvoie le MP d'onboarding automatiquement,
   à condition qu'il n'ait pas déjà de personnage principal enregistré.

### « Le bouton Postuler répond que le recrutement n'est pas configuré »

`/recruit channel` n'a pas été lancé (ou le salon configuré a été supprimé).
Relance la commande dans le salon voulu.

### « Impossible d'accepter, message "définis d'abord le rôle de membre" »

`/onboard role` n'a pas encore été configuré, ou le rôle choisi a été
supprimé depuis. Relance `/onboard role` avec un rôle valide.

## 5. Aide-mémoire des commandes

| Commande | Effet |
|---|---|
| `/recruit channel action: on/off` | Active/désactive la revue des candidatures dans ce salon |
| `/recruit post` | Poste un panneau "Postuler" permanent |
| `/onboard role role: @…` | Définit le rôle de membre validé (attribué à l'acceptation) |
| `/settings admin-role role: @…` | Définit qui peut Accepter/Refuser sans Gérer le serveur |
| `/welcome action: on/off` | Active le tableau de bienvenue automatique |
| `/language choice: …` | Langue du serveur (FR/EN/Auto) pour tout le parcours candidat/membre |
| `/roster` | Liste tous les personnages enregistrés de la légion |
| `/profile show member: @…` | Voir le profil d'un membre en particulier |
| `/profile delete member: @…` | (modérateurs) Supprimer le profil d'un membre |
