from __future__ import annotations

import logging
from typing import Any, Protocol

import requests

from .normalizer import NormalizedLead

logger = logging.getLogger(__name__)


class UnauthorizedError(RuntimeError):
    """Raised when the upstream Ads API responds with HTTP 401."""


class AdsProvider(Protocol):
    def fetch_leads(self, account_id: str, access_token: str) -> list[dict[str, Any]]: ...


class CRMProvider(Protocol):
    def create_deal(self, lead: NormalizedLead, stage: str) -> str: ...


class Notifier(Protocol):
    def notify_new_lead(self, lead: NormalizedLead, deal_id: str) -> None: ...


class RestAdsProvider:
    """Generic REST client for Ads Lead Gen APIs."""

    def __init__(self, base_url: str, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_leads(self, account_id: str, access_token: str) -> list[dict[str, Any]]:
        url = f"{self.base_url}/adAccounts/{account_id}/leadResponses"
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=self.timeout,
        )
        if resp.status_code == 401:
            raise UnauthorizedError("Access token expirado (HTTP 401).")
        resp.raise_for_status()
        return list(resp.json().get("elements", []))


class WebhookCRMProvider:
    """Injects normalized leads into any REST/Webhook-enabled CRM."""

    def __init__(self, webhook_url: str, timeout: int = 15) -> None:
        self.webhook_url = webhook_url.rstrip("/")
        self.timeout = timeout

    def create_deal(self, lead: NormalizedLead, stage: str) -> str:
        payload = {
            "title": f"[{lead.campaign_name}] {lead.full_name}",
            "stage": stage,
            "contact": {
                "name": lead.full_name,
                "email": lead.email,
                "phone": lead.phone_e164,
                "company": lead.company,
            },
            "metadata": lead.custom_answers,
        }
        resp = requests.post(f"{self.webhook_url}/deals", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return str(resp.json().get("deal_id", "unknown"))


class DemoAdsProvider:
    """In-memory Ads simulator that exercises OAuth 401 expiry and form filtering."""

    def __init__(self, expire_first_token: bool = True) -> None:
        self._expired_once = not expire_first_token

    def fetch_leads(self, account_id: str, access_token: str) -> list[dict[str, Any]]:
        if not self._expired_once and access_token == "expired-demo-token":
            self._expired_once = True
            raise UnauthorizedError("Token de demonstração expirado; acionando refresh.")
        return [
            {
                "id": "lead-demo-001",
                "form_id": "form-b2b-enterprise-01",
                "campaign_name": "SaaS Enterprise Q4",
                "first_name": "Marina",
                "last_name": "Alves",
                "email": "MARINA.ALVES@ACME-DEMO.EXAMPLE",
                "phone": "(11) 98765-4321",
                "company": "Acme Logística Ltda (Demo)",
                "answers": {"Tamanho do Time": "50-200", "Interesse": "Automação CRM"},
            },
            {
                "id": "lead-demo-002",
                "form_id": "form-saas-trial-02",
                "campaign_name": "Trial Inbound",
                "full_name": "Lucas Pereira",
                "email": "lucas@vortex-demo.example",
                "phone": "21999887766",
                "company": "Vortex Tech (Demo)",
                "answers": {"Cargo": "Head de Operações"},
            },
            {
                "id": "lead-demo-ignored",
                "form_id": "form-unlisted-99",
                "campaign_name": "Campanha Institucional",
                "full_name": "Contato Ignorado",
                "email": "ignorado@demo.example",
                "phone": "11900000000",
            },
        ]


class DemoCRMProvider:
    """In-memory CRM sink used in --demo mode and automated tests."""

    def __init__(self) -> None:
        self.created_deals: list[dict[str, Any]] = []

    def create_deal(self, lead: NormalizedLead, stage: str) -> str:
        deal_id = f"DEAL-{len(self.created_deals) + 1001}"
        self.created_deals.append({"deal_id": deal_id, "stage": stage, "lead": lead})
        return deal_id


class ConsoleNotifier:
    """Prints structured notifications for demo/local execution."""

    def __init__(self) -> None:
        self.sent_messages: list[str] = []

    def notify_new_lead(self, lead: NormalizedLead, deal_id: str) -> None:
        msg = (
            f"[ALERTA NOVO LEAD] {lead.full_name} ({lead.company or 'N/A'}) | "
            f"Tel: {lead.phone_e164} | Campanha: {lead.campaign_name} | CRM: {deal_id}"
        )
        self.sent_messages.append(msg)
        logger.info(msg)
