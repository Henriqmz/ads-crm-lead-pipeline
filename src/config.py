from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AdAccountConfig:
    name: str
    account_id: str


@dataclass(frozen=True)
class PipelineSettings:
    allowed_form_ids: list[str]
    ad_accounts: list[AdAccountConfig]
    default_pipeline_stage: str = "NEW_LEAD"
    db_path: Path = Path("data/leads.db")
    ads_api_base_url: str = "https://api.example-ads.com/v2"
    crm_webhook_url: str = ""
    notify_webhook_url: str = ""
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_access_token: str = ""
    oauth_refresh_token: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def load_settings(config_file: Path | None = None) -> PipelineSettings:
    """Loads pipeline settings from config.json (or config.example.json) and environment."""
    target = config_file or (
        Path("config.json") if Path("config.json").exists() else Path("config.example.json")
    )
    raw = json.loads(target.read_text(encoding="utf-8"))
    accounts = [
        AdAccountConfig(name=item["name"], account_id=str(item["account_id"]))
        for item in raw.get("ad_accounts", [])
    ]
    return PipelineSettings(
        allowed_form_ids=[str(fid) for fid in raw.get("allowed_form_ids", [])],
        ad_accounts=accounts,
        default_pipeline_stage=raw.get("default_pipeline_stage", "NEW_LEAD"),
        db_path=Path(os.getenv("DB_PATH", "data/leads.db")),
        ads_api_base_url=os.getenv("ADS_API_BASE_URL", "https://api.example-ads.com/v2"),
        crm_webhook_url=os.getenv("CRM_WEBHOOK_URL", ""),
        notify_webhook_url=os.getenv("NOTIFY_WEBHOOK_URL", ""),
        oauth_client_id=os.getenv("ADS_CLIENT_ID", ""),
        oauth_client_secret=os.getenv("ADS_CLIENT_SECRET", ""),
        oauth_access_token=os.getenv("ADS_ACCESS_TOKEN", ""),
        oauth_refresh_token=os.getenv("ADS_REFRESH_TOKEN", ""),
    )
