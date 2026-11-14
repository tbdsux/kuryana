from types import SimpleNamespace
from typing import Any

import pytest

from app import client as app_client


@pytest.fixture(autouse=True)
def block_mdl_unless_live(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only tests marked `live` may reach the real MyDramaList site.

    Everything else must fake it, so the offline suite (which gates deploys)
    can't start depending on MDL without anyone noticing.
    """
    if request.node.get_closest_marker("live"):
        return

    async def get(url: str, params: Any = None) -> None:
        raise RuntimeError(
            f"offline test tried to reach {url}; mark it @pytest.mark.live"
        )

    monkeypatch.setattr(app_client, "client", SimpleNamespace(get=get))
