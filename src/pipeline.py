from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from .config import PipelineSettings
from .normalizer import normalize_lead
from .oauth import OAuthTokenManager
from .providers import AdsProvider, CRMProvider, Notifier, UnauthorizedError
from .storage import LeadStorage

logger = logging.getLogger(__name__)


@dataclass
class RunSummary:
    fetched: int = 0
    ignored_form: int = 0
    skipped_duplicate: int = 0
    injected: int = 0
    oauth_refreshes: int = 0


class LeadPipeline:
    """Coordinates fetching, OAuth refresh, filtering, deduplication, and CRM injection."""

    def __init__(
        self,
        settings: PipelineSettings,
        ads_provider: AdsProvider,
        crm_provider: CRMProvider,
        notifier: Notifier,
        storage: LeadStorage,
        token_manager: OAuthTokenManager,
        max_retries: int = 3,
        retry_delay_sec: float = 0.2,
    ) -> None:
        self.settings = settings
        self.ads_provider = ads_provider
        self.crm_provider = crm_provider
        self.notifier = notifier
        self.storage = storage
        self.token_manager = token_manager
        self.max_retries = max_retries
        self.retry_delay_sec = retry_delay_sec

    def _fetch_with_oauth_refresh(self, account_id: str) -> list[dict]:
        try:
            return self.ads_provider.fetch_leads(account_id, self.token_manager.current_token)
        except UnauthorizedError:
            new_token = self.token_manager.renew()
            return self.ads_provider.fetch_leads(account_id, new_token)

    def _inject_with_retry(self, lead) -> str:
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return self.crm_provider.create_deal(lead, self.settings.default_pipeline_stage)
            except Exception as exc:
                last_err = exc
                logger.warning("Falha ao enviar lead %s (tentativa %d/%d): %s", lead.lead_id, attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_sec * attempt)
        assert last_err is not None
        raise last_err

    def run_once(self) -> RunSummary:
        summary = RunSummary()
        allowed = set(self.settings.allowed_form_ids)

        for account in self.settings.ad_accounts:
            raw_leads = self._fetch_with_oauth_refresh(account.account_id)
            summary.fetched += len(raw_leads)

            for raw in raw_leads:
                lead = normalize_lead(raw)
                if allowed and lead.form_id not in allowed:
                    summary.ignored_form += 1
                    continue
                if self.storage.already_processed(lead.lead_id):
                    summary.skipped_duplicate += 1
                    continue

                deal_id = self._inject_with_retry(lead)
                self.storage.mark_processed(
                    lead_id=lead.lead_id,
                    account_id=account.account_id,
                    form_id=lead.form_id,
                    crm_deal_id=deal_id,
                    status="SYNCED",
                    payload=raw,
                )
                self.notifier.notify_new_lead(lead, deal_id)
                summary.injected += 1

        summary.oauth_refreshes = self.token_manager.state.refresh_count
        return summary
