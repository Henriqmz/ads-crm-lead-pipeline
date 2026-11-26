from __future__ import annotations

import argparse
import logging
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> bool:
        return False

from .config import load_settings
from .oauth import OAuthTokenManager
from .pipeline import LeadPipeline
from .providers import (
    ConsoleNotifier,
    DemoAdsProvider,
    DemoCRMProvider,
    RestAdsProvider,
    WebhookCRMProvider,
)
from .server import run_studio
from .storage import LeadStorage


def main() -> None:
    parser = argparse.ArgumentParser(description="Ads-to-CRM Lead Pipeline")
    parser.add_argument("--demo", action="store_true", help="Executa em modo demonstração com dados sintéticos")
    parser.add_argument("--serve", action="store_true", help="Inicia o painel web interativo do pipeline")
    parser.add_argument("--port", type=int, default=8021, help="Porta do painel web (padrão: 8021)")
    args = parser.parse_args()

    if args.serve:
        run_studio(port=args.port)
        return

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    load_dotenv()

    settings = load_settings()

    if args.demo:
        storage = LeadStorage(Path("data/demo_leads.db"))
        token_mgr = OAuthTokenManager(
            access_token="expired-demo-token",
            refresh_token="demo-refresh-token",
            refresh_fn=lambda rt: ("fresh-demo-token", rt),
        )
        pipeline = LeadPipeline(
            settings=settings,
            ads_provider=DemoAdsProvider(expire_first_token=True),
            crm_provider=DemoCRMProvider(),
            notifier=ConsoleNotifier(),
            storage=storage,
            token_manager=token_mgr,
        )
    else:
        storage = LeadStorage(settings.db_path)
        token_mgr = OAuthTokenManager(
            access_token=settings.oauth_access_token,
            refresh_token=settings.oauth_refresh_token,
            refresh_fn=lambda rt: (settings.oauth_access_token, rt),
        )
        pipeline = LeadPipeline(
            settings=settings,
            ads_provider=RestAdsProvider(settings.ads_api_base_url),
            crm_provider=WebhookCRMProvider(settings.crm_webhook_url),
            notifier=ConsoleNotifier(),
            storage=storage,
            token_manager=token_mgr,
        )

    summary = pipeline.run_once()
    print(
        f"\nResumo: capturados={summary.fetched} | injetados={summary.injected} | "
        f"duplicados={summary.skipped_duplicate} | formulários_ignorados={summary.ignored_form} | "
        f"renovações_oauth={summary.oauth_refreshes}"
    )


if __name__ == "__main__":
    main()
