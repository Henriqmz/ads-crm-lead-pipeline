from pathlib import Path

from src.config import AdAccountConfig, PipelineSettings
from src.normalizer import normalize_phone_br
from src.oauth import OAuthTokenManager
from src.pipeline import LeadPipeline
from src.providers import ConsoleNotifier, DemoAdsProvider, DemoCRMProvider
from src.storage import LeadStorage


def test_normalize_phone_br():
    assert normalize_phone_br("(11) 98765-4321") == "+5511987654321"
    assert normalize_phone_br("21999887766") == "+5521999887766"
    assert normalize_phone_br("+1 415 555 0199") == "+14155550199"
    assert normalize_phone_br("") == ""


def test_pipeline_oauth_refresh_filter_and_idempotency(tmp_path: Path):
    settings = PipelineSettings(
        allowed_form_ids=["form-b2b-enterprise-01", "form-saas-trial-02"],
        ad_accounts=[AdAccountConfig(name="Demo Account", account_id="100000001")],
        db_path=tmp_path / "leads.db",
    )
    crm = DemoCRMProvider()
    notifier = ConsoleNotifier()
    storage = LeadStorage(settings.db_path)
    token_mgr = OAuthTokenManager(
        access_token="expired-demo-token",
        refresh_token="refresh-ok",
        refresh_fn=lambda rt: ("renewed-token", "refresh-ok-2"),
    )
    pipeline = LeadPipeline(
        settings=settings,
        ads_provider=DemoAdsProvider(expire_first_token=True),
        crm_provider=crm,
        notifier=notifier,
        storage=storage,
        token_manager=token_mgr,
    )

    first = pipeline.run_once()
    assert first.fetched == 3
    assert first.injected == 2
    assert first.ignored_form == 1
    assert first.oauth_refreshes == 1
    assert len(crm.created_deals) == 2
    assert len(notifier.sent_messages) == 2

    # Second run must be 100% idempotent
    second = pipeline.run_once()
    assert second.injected == 0
    assert second.skipped_duplicate == 2
    assert storage.count() == 2
