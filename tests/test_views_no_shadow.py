"""Guard against shadowing discord.py View internals. Run: pytest

`discord.ui.View._refresh(components)` is called by discord.py when Discord
refreshes a persistent view on a message update. Defining a method of the same
name on our views shadows it and crashes the gateway (TypeError), so our views
must never declare `_refresh` (nor other reserved internals).
"""

from bot.views import RSVPView, SignupView

RESERVED = {"_refresh", "_dispatch_item", "_scheduled_task"}


def test_our_views_do_not_shadow_discord_internals():
    for view_cls in (SignupView, RSVPView):
        clashes = RESERVED & set(vars(view_cls))
        assert not clashes, f"{view_cls.__name__} shadows discord.py View {clashes}"
