from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


class TokenRefreshError(RuntimeError):
    """Raised when an OAuth 2.0 refresh token flow fails."""


@dataclass
class OAuthTokenState:
    access_token: str
    refresh_token: str
    refresh_count: int = 0


class OAuthTokenManager:
    """Manages OAuth 2.0 access/refresh tokens with automatic renewal on HTTP 401."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        refresh_fn: Callable[[str], tuple[str, str]],
        persist_fn: Callable[[str, str], None] | None = None,
    ) -> None:
        self.state = OAuthTokenState(access_token=access_token, refresh_token=refresh_token)
        self._refresh_fn = refresh_fn
        self._persist_fn = persist_fn

    @property
    def current_token(self) -> str:
        return self.state.access_token

    def renew(self) -> str:
        if not self.state.refresh_token:
            raise TokenRefreshError("Refresh token ausente; autenticação interativa necessária.")
        new_access, new_refresh = self._refresh_fn(self.state.refresh_token)
        if not new_access:
            raise TokenRefreshError("Provedor OAuth não retornou novo access_token.")
        self.state.access_token = new_access
        if new_refresh:
            self.state.refresh_token = new_refresh
        self.state.refresh_count += 1
        if self._persist_fn:
            self._persist_fn(self.state.access_token, self.state.refresh_token)
        logger.info("Token OAuth 2.0 renovado com sucesso (renovação #%d).", self.state.refresh_count)
        return self.state.access_token
