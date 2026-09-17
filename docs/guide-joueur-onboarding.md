# Tu as été accepté mais tu n'as pas encore configuré ton profil ?

Ce guide est pour toi si : tu as postulé, un officier t'a accepté (tu as
normalement reçu un message privé de confirmation), mais tu n'as jamais
terminé — ou jamais reçu — le formulaire pour enregistrer ton personnage.
Pas de panique, ça se règle en moins d'une minute.

## Étape 1 — Vérifie que tu as bien ton rôle de membre

Regarde la liste des membres du serveur (clic droit sur le nom du serveur →
« Voir les membres », ou le panneau latéral) : si tu apparais avec un rôle du
type `@Dexterity France` (le nom exact dépend du serveur), c'est bon, tu es
bien membre validé. Si tu ne l'as pas du tout, préviens un officier — c'est
un problème différent (l'acceptation elle-même n'a pas abouti) et il devra le
régler avant que la suite ne fonctionne.

## Étape 2 — Cherche le message privé « Bienvenue »

Kisk (le bot du serveur) t'envoie normalement un message privé avec un
bouton **📝 Configurer mon profil** dès que tu reçois ton rôle. Regarde dans
tes messages privés (icône Discord en haut à gauche) une conversation avec le
bot.

- **Tu le retrouves ?** Clique sur le bouton, choisis ta **classe** et ton
  **rôle** dans les menus, clique **Continuer**, puis tape le nom de ton
  personnage. C'est fini — passe directement à l'étape 4.
- **Tu ne le retrouves pas** (supprimé, jamais reçu parce que tes MP étaient
  fermés, etc.) ? Passe à l'étape 3, ça marche tout aussi bien.

## Étape 3 — Configure ton profil directement avec une commande

Tape la commande suivante **dans un salon du serveur** (pas en MP) — Discord
te proposera de la compléter automatiquement :

```text
/profile set name: TonPersonnage class: TaClasse role: Tank
```

- `name` : le nom de ton personnage en jeu.
- `class` : ta classe (Gladiator, Templar, Assassin, Ranger, Sorcerer,
  Spiritmaster, Cleric, Chanter…) — un menu déroulant te propose les choix
  disponibles.
- `role` : `Tank`, `Heal` ou `DPS`.

Ton premier personnage devient automatiquement ton personnage **principal** —
pas besoin de cocher quoi que ce soit de plus. La réponse n'est visible que
par toi.

## Étape 4 — Vérifie que c'est bien enregistré

```text
/profile show
```

Tu dois voir ton personnage listé avec une ⭐ (ton principal). Si oui, c'est
terminé — tu es pleinement configuré.

## Tu as plusieurs personnages ?

Relance `/profile set` autant de fois que tu veux avec un nom différent à
chaque fois (jusqu'à 10 personnages). Pour changer lequel est ton
« principal » :

```text
/profile main character: TonAutrePersonnage
```

## Ça ne marche toujours pas ?

Si `/profile set` répond quelque chose d'inattendu, ou si tu n'as toujours
pas ton rôle de membre à l'étape 1, contacte simplement un officier de la
légion en lui expliquant où tu bloques — c'est probablement un réglage côté
serveur à ajuster de son côté, rien que tu puisses corriger toi-même.
