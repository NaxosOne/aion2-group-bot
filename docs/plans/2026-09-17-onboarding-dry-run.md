# Dry run — phase finale de l'onboarding (post-correctif #recruit-role-fix)

**Méthode.** Aucun interpréteur Python n'est disponible dans cet environnement
(`pytest` non exécutable ici), donc ce dry run est une **relecture statique
tracée** : chaque étape cite le fichier et la ligne exacts, l'état avant/après,
et ce qu'un membre/officier voit réellement dans Discord. Objectif : vérifier
que le parcours candidat → membre → profil fonctionne de bout en bout après le
correctif du 2026-09-17 sur `Recruitment._accept`.

**Scénario.** Légion « Dexterity France ». Configuration existante :

| Réglage | Valeur |
|---|---|
| `recruit_channel_id` | #officiers-recrutement |
| `member_role_id` | `@Dexterity France` |
| `admin_role_id` | `@Officier` |
| Rôle du bot Kisk | positionné **au-dessus** de `@Dexterity France` dans la hiérarchie, permission **Gérer les rôles** ✅ |

Candidate : **Nova**, a postulé comme Templar/Tank.

---

## Étape 0 — Rappel : où en est Nova avant la phase finale

Nova a déjà cliqué **Postuler**, rempli le formulaire (`ApplicationModal.on_submit`,
`bot/cogs/recruitment.py:159-161`), et sa fiche est postée dans le salon
officiers avec les boutons **✅ Accepter** / **❌ Refuser**
(`submit_application`, `bot/cogs/recruitment.py:321-387`). État en base :
`applications.status = "pending"`.

## Étape 1 — Un officier clique « Accepter »

`DecisionButton.callback` → `Recruitment.decide` (`bot/cogs/recruitment.py:201-408`).

1. `member_is_admin(db, interaction.user)` (`bot/utils/permissions.py:28-36`) —
   vérifie que le cliqueur a `admin_role_id` ou `Manage Server`. Si non :
   message `recruit.not_officer`, **fin** (Nova ne bouge pas).
2. `app = db.get_application(app_id)` → statut `"pending"` → on continue.
3. `action == "accept"` → `Recruitment._accept(interaction, app, lang)`.

## Étape 2 — Résolution du rôle et du membre (`_accept`, ligne 410)

```
settings.member_role_id = <id de @Dexterity France>
role = guild.get_role(role_id)          # non None : le rôle existe
member = guild.get_member(app.user_id)  # Nova est toujours dans le serveur
```

Les deux gardes-fous (`role is None`, `member is None`,
lignes 416-428) sont franchis sans déclenchement.

## Étape 3 — Marquage en base **avant** l'action Discord

```
db.set_application_status(app.id, "accepted", reviewer_id=<officier>, reason=None)
```

Ceci réussit (retourne `True`, la candidature était bien `"pending"`) — le
statut passe à `"accepted"` **avant** que le rôle soit réellement accordé.
C'est le point exact où l'ancien bug pouvait diverger de la réalité : la
DB/la fiche annoncent un succès avant même la tentative Discord. Le correctif
ne change pas cet ordre (il reste nécessaire pour éviter un double-clic
concurrent) — il corrige ce qui se passe **après**.

## Étape 4 — Octroi du rôle (le cœur du correctif, lignes 436-466)

```python
role_granted = True
try:
    await member.add_roles(role, reason="Recruitment: application accepted")
except discord.HTTPException:
    role_granted = False
    log.warning(...)
```

**Branche nominale (ce scénario) :** hiérarchie OK, permission OK →
`add_roles` réussit. Discord émet un `on_member_update` pour Nova avec
`before.roles` sans `@Dexterity France`, `after.roles` avec.

**Branche défaillante (l'ancien bug, testée pour mémoire) :** si le rôle du
bot avait été sous `@Dexterity France`, `add_roles` aurait levé
`discord.Forbidden` (sous-classe de `HTTPException`). Avant le correctif :
avalé silencieusement, tout continuait comme si de rien n'était. Après le
correctif : `role_granted = False` propage jusqu'aux lignes 449-466 →
la fiche est tamponnée `recruit.accepted_role_failed_fiche` (⚠️ au lieu de
✅) et l'officier reçoit un followup ephemeral `recruit.role_grant_failed`
citant le nom du rôle. Vérifié statiquement : les deux clés résolvent dans
les deux catalogues (`node` a chargé `en.json`/`fr.json`, 348 clés de chaque
côté, aucune clé orpheline).

Pour ce dry run (branche nominale), on continue avec `role_granted = True`.

## Étape 5 — DM de confirmation, nettoyage, fiche (lignes 444-452)

- `member.send(i18n.t("recruit.dm_accepted", ...))` → Nova reçoit en MP :
  *« 🎉 Ta candidature à Dexterity France a été acceptée — bienvenue parmi
  nous ! »*
- `_teardown_channel` supprime le salon privé `#cand-templar-nova`.
- `_stamp_fiche(..., "recruit.accepted_fiche", ...)` → la fiche dans le salon
  officiers affiche désormais `✅ Accepté par @Officier`, boutons retirés.

À cet instant, côté candidat : Nova a le rôle `@Dexterity France`, mais **pas
encore de profil**. C'est la jonction exacte entre `recruitment.py` et
`onboarding.py`.

## Étape 6 — `on_member_update` déclenche l'onboarding (`bot/cogs/onboarding.py:337-342`)

Discord notifie le bot du changement de rôle de Nova. Le listener :

```python
if before.roles == after.roles: return          # False ici, on continue
role_id = settings.member_role_id               # @Dexterity France
role_just_added(role_id, before_ids, after_ids) # True (utils/onboarding.py:15-17)
has_profile = db.has_main_profile(guild_id, nova.id)  # False : aucun perso encore
should_onboard(member_role_added=True, has_main_profile=False, is_bot=False)  # True
```

→ `self._onboard(after, settings)` (ligne 359).

## Étape 7 — Le MP d'onboarding

`_onboard` tente `member.send(embed=welcome_embed, view=OnboardButton)`. MP de
Nova ouverts → succès, **fin de la branche** (pas de repli salon). Nova reçoit
un embed *« Bienvenue sur Dexterity France ! 🎉 »* avec un bouton
**Configurer mon profil**, dont le `custom_id` encode le `guild_id`
(`onboard_custom_id`, `bot/utils/onboarding.py:6-12`) — persistant, donc
cliquable même après un redémarrage du bot.

## Étape 8 — Nova clique « Configurer mon profil » (`OnboardButton.callback`, ligne 281)

```python
has_main_profile(guild_id, nova.id)  # toujours False → on continue
view = ProfileSetupView(guild_id, "Dexterity France", ephemeral=False, lang)
```

Nova voit deux menus déroulants (**Classe** — Templar 🛡️ déjà pré-rempli côté
candidature, mais ici c'est un formulaire neuf donc rien n'est présélectionné
— et **Rôle**), puis un bouton **Continuer** sur sa propre ligne (régression
testée par `test_recruitment_views.py`/`test_onboarding.py` sur le
chevauchement de lignes : 2 selects + 1 bouton, aucun conflit de row).

## Étape 9 — Sélection + modal (`ClassSelect`, `RoleSelect`, `ProfileNameModal`)

Nova choisit **Templar** 🛡️, **Tank**, clique Continuer → modal avec le champ
**Nom du personnage**. Elle tape « Novastrike » → `on_submit`
(`bot/cogs/onboarding.py:197-227`) :

```python
characters = db.get_profiles(guild_id, nova.id)      # []
len(characters) >= MAX_CHARACTERS                     # 0 >= 10 : False
db.add_character(guild_id, nova.id, "Novastrike", "Templar", "tank")
```

`add_character` (`bot/db_profiles.py:91-…`) : premier personnage → devient
automatiquement `is_main = 1`, quel que soit `make_main`. Nova reçoit la
confirmation `onboard.added_main` avec un bouton **Ajouter un personnage**
(`AddAltView`, puisque `1 < MAX_CHARACTERS`).

## Étape 10 — État final vérifié

```
db.has_main_profile(guild_id, nova.id)  → True
db.get_profiles(guild_id, nova.id)      → [{char_name: "Novastrike", char_class: "Templar", role: "tank", is_main: 1}]
```

Un officier lançant `/roster` ou `/profile show member:@Nova` verrait
désormais `⭐ 🛡️ **Novastrike** (🛡️ Templar)` sous Nova. Le parcours
candidature → rôle → profil est complet, sans intervention manuelle.

---

## Checklist de vérification

- [x] Le clic Accepter est bien restreint aux Kisk-admins (`member_is_admin`)
- [x] Le rôle est résolu et le membre existe avant tout effet de bord
- [x] Branche nominale : rôle accordé → DM → salon supprimé → fiche ✅
- [x] Branche défaillante (corrigée) : rôle refusé par Discord → fiche ⚠️ +
      alerte officier au lieu d'un échec silencieux (clés i18n résolues dans
      les deux langues, testé statiquement)
- [x] `on_member_update` détecte la transition et ne s'onboarde qu'un humain
      sans profil (`should_onboard`, couvert par `test_onboarding.py`)
- [x] Le bouton d'onboarding est persistant (`add_dynamic_items`, `bot/main.py:58`)
      donc réutilisable après un redémarrage ou si Nova revient plus tard
- [x] Premier personnage toujours promu `main` (`db_profiles.py`), donc
      `has_main_profile` passe à `True` dès la première soumission

## Ce que ce dry run NE couvre PAS

- Comportement réel de l'API Discord (rate limits, latence, permissions
  réellement appliquées côté serveur) — nécessite un smoke test sur un
  serveur de test avec le bot connecté.
- Les chemins de repli MP fermés (`_invite_in_channel`, `_onboard_in_channel`)
  n'ont pas été exercés dans ce scénario (Nova a ses MP ouverts) ; leur code
  est lu mais non simulé ici.
- Exécution effective de la suite `pytest` (aucun interpréteur Python présent
  dans cet environnement) — à lancer localement :
  ```
  pytest tests/test_onboarding.py tests/test_onboarding_i18n_keys.py \
         tests/test_recruitment_i18n_keys.py tests/test_recruitment_views.py \
         tests/test_recruitment_db.py
  ```
