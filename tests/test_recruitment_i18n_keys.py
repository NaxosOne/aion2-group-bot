"""Every recruitment string resolves in both catalogs with the params the cog
passes — a renamed or half-translated key fails here, not in front of players."""

import pytest

from bot import i18n

RECRUIT_KEYS = {
    "recruit.dm_title": {"guild": "Kisk"},
    "recruit.dm_body": {},
    "recruit.dm_fallback_prefix": {},
    "recruit.apply_button": {},
    "recruit.already_pending": {},
    "recruit.setup_title": {"guild": "Kisk"},
    "recruit.summary_body": {"class_line": "x", "role_line": "y"},
    "recruit.continue": {},
    "recruit.pick_first": {},
    "recruit.modal_title": {},
    "recruit.name_label": {},
    "recruit.level_label": {},
    "recruit.exp_label": {},
    "recruit.avail_label": {},
    "recruit.motivation_label": {},
    "recruit.submitted": {},
    "recruit.no_channel": {},
    "recruit.missing_perm": {},
    "recruit.channel_welcome": {"mention": "@x"},
    "recruit.fiche_title": {"name": "Kratos"},
    "recruit.fiche_class_role": {"emoji": "🔥", "cls": "Sorcerer", "role": "DPS"},
    "recruit.fiche_level": {},
    "recruit.fiche_exp": {},
    "recruit.fiche_avail": {},
    "recruit.fiche_motivation": {},
    "recruit.fiche_pending": {"mention": "@x"},
    "recruit.btn_accept": {},
    "recruit.btn_reject": {},
    "recruit.btn_discuss": {},
    "recruit.not_officer": {},
    "recruit.already_decided": {},
    "recruit.no_member_role": {},
    "recruit.applicant_gone": {},
    "recruit.accepted_fiche": {"who": "@x"},
    "recruit.rejected_fiche": {"who": "@x"},
    "recruit.reject_modal_title": {},
    "recruit.reject_reason_label": {},
    "recruit.dm_accepted": {"guild": "Kisk"},
    "recruit.dm_rejected": {"guild": "Kisk"},
    "recruit.dm_rejected_reason": {"guild": "Kisk", "reason": "low"},
    "recruit.cmd_on": {},
    "recruit.cmd_off": {},
    "recruit.desk_title": {"guild": "Kisk"},
    "recruit.desk_body": {},
    "recruit.desk_footer": {"guild": "Kisk"},
    "recruit.posted": {"link": "https://discord.com/x"},
    "recruit.post_needs_channel": {},
    "recruit.save_failed": {},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(RECRUIT_KEYS.items()))
def test_recruit_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    assert out != key
    assert "{" not in out
