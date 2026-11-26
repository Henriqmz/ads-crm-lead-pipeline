from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from .config import AdAccountConfig, PipelineSettings
from .normalizer import normalize_lead
from .oauth import OAuthTokenManager
from .pipeline import LeadPipeline
from .providers import ConsoleNotifier, DemoAdsProvider, DemoCRMProvider
from .storage import LeadStorage

STUDIO_HTML = """<!doctype html>
<html lang="pt-BR" data-theme="dark">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Ads-to-CRM Lead Pipeline — OAuth 2.0 &amp; Idempotency Console</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet" />
  <style>
    :root, [data-theme="dark"] {
      --bg: #050a0f; --surface: #0b1219; --surface-2: #111b24; --surface-hover: #172430;
      --text: #f0f7fc; --muted: #9ab3c8; --accent: #d4f1ff; --accent-ink: #050a0f;
      --accent-soft: rgba(212, 241, 255, 0.11); --accent-border: rgba(212, 241, 255, 0.34);
      --border: rgba(212, 241, 255, 0.14);
      --ok-bg: rgba(52, 211, 153, 0.15); --ok-text: #6ee7b7;
      --warn-bg: rgba(251, 191, 36, 0.15); --warn-text: #fcd34d;
    }
    [data-theme="light"] {
      --bg: #f0f7fc; --surface: #ffffff; --surface-2: #e3eef6; --surface-hover: #d5e5f1;
      --text: #050a0f; --muted: #395064; --accent: #050a0f; --accent-ink: #f0f7fc;
      --accent-soft: rgba(5, 10, 15, 0.08); --accent-border: rgba(5, 10, 15, 0.3);
      --border: rgba(5, 10, 15, 0.14);
      --ok-bg: #ecfdf5; --ok-text: #047857;
      --warn-bg: #fffbeb; --warn-text: #b45309;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Plus Jakarta Sans", system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
    .shell-header {
      padding: 18px max(24px, calc((100% - 1180px) / 2)); border-bottom: 1px solid var(--border);
      background: var(--surface); display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 1rem;
    }
    .brand { display: flex; align-items: center; gap: 0.85rem; }
    .logo { width: 38px; height: 38px; border-radius: 10px; background: var(--accent); color: var(--accent-ink); display: grid; place-items: center; font-weight: 900; font-size: 0.86rem; }
    .brand-title { font-weight: 800; font-size: 1.08rem; }
    .brand-sub { font-size: 0.78rem; color: var(--muted); }
    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem;
      padding: 0.54rem 0.96rem; border-radius: 9px; border: 1px solid var(--border);
      background: var(--surface-2); color: var(--text); font: inherit; font-size: 0.82rem; font-weight: 700; cursor: pointer;
    }
    .btn:hover { background: var(--surface-hover); border-color: var(--accent-border); }
    .btn-primary { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
    .shell-body { width: min(1180px, calc(100% - 48px)); margin: 0 auto; padding: 26px 0 44px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.9rem; margin-bottom: 22px; }
    .kpi { background: var(--surface-2); border: 1px solid var(--border); border-left: 4px solid var(--accent); border-radius: 12px; padding: 0.95rem 1.1rem; }
    .kpi-label { font-size: 0.72rem; color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
    .kpi-val { font-size: 1.65rem; font-weight: 800; color: var(--accent); margin-top: 0.2rem; }
    .grid { display: grid; grid-template-columns: 1.45fr 0.85fr; gap: 20px; align-items: start; }
    .card { background: var(--surface-2); border: 1px solid var(--border); border-radius: 14px; padding: 1.25rem; }
    .card h2 { margin: 0 0 0.35rem; font-size: 1.04rem; }
    .sub { margin: 0 0 1rem; font-size: 0.82rem; color: var(--muted); }
    table { width: 100%; border-collapse: collapse; font-size: 0.84rem; }
    th, td { text-align: left; padding: 0.75rem 0.6rem; border-bottom: 1px solid var(--border); }
    th { font-size: 0.71rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
    .mono { font-family: "JetBrains Mono", monospace; font-size: 0.76rem; color: var(--muted); }
    .badge { display: inline-block; font-family: "JetBrains Mono", monospace; font-size: 0.7rem; font-weight: 700; padding: 0.2rem 0.58rem; border-radius: 999px; background: var(--ok-bg); color: var(--ok-text); }
    .input, select { width: 100%; padding: 0.58rem 0.8rem; border-radius: 9px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font: inherit; font-size: 0.85rem; margin-bottom: 0.75rem; }
    label { display: block; font-size: 0.78rem; font-weight: 600; color: var(--muted); margin-bottom: 0.25rem; }
    .toast { position: fixed; right: 24px; bottom: 24px; padding: 0.72rem 1.1rem; border-radius: 10px; background: var(--accent); color: var(--accent-ink); font-weight: 700; font-size: 0.83rem; opacity: 0; pointer-events: none; transition: opacity 0.2s; }
    .toast.show { opacity: 1; }
    @media (max-width: 920px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header class="shell-header">
    <div class="brand">
      <span class="logo">ADS</span>
      <div>
        <div class="brand-title">Ads-to-CRM Lead Pipeline</div>
        <div class="brand-sub">OAuth 2.0 Auto-Refresh (401) · Normalização E.164 · SQLite Idempotente</div>
      </div>
    </div>
    <div style="display:flex;gap:0.55rem;align-items:center">
      <button id="pollBtn" type="button" class="btn btn-primary">⚡ Executar Polling Ads API</button>
      <button id="themeToggle" type="button" class="btn" style="border-radius:999px">
        <span id="themeIcon">☀</span> <span id="themeLabel">Modo Claro</span>
      </button>
    </div>
  </header>

  <main class="shell-body">
    <section class="kpi-grid">
      <div class="kpi"><div class="kpi-label">Leads no CRM (SQLite)</div><div class="kpi-val" id="kSynced">--</div></div>
      <div class="kpi"><div class="kpi-label">Duplicados Bloqueados</div><div class="kpi-val" id="kDup">--</div></div>
      <div class="kpi"><div class="kpi-label">Forms Fora da Whitelist</div><div class="kpi-val" id="kIgnored">--</div></div>
      <div class="kpi"><div class="kpi-label">Auto-Refresh OAuth 2.0</div><div class="kpi-val" id="kOauth">--</div></div>
    </section>

    <div class="grid">
      <section class="card">
        <h2>Auditoria de Leads Injetados no CRM</h2>
        <p class="sub">Clique em "Executar Polling Ads API" novamente para comprovar a deduplicação idempotente (nenhum negócio duplicado é criado).</p>
        <div style="overflow-x:auto">
          <table>
            <thead><tr><th>Lead / Campanha</th><th>Contato Normalizado (E.164)</th><th>Form ID</th><th>Negócio CRM</th></tr></thead>
            <tbody id="leadsBody"></tbody>
          </table>
        </div>
      </section>

      <aside class="card">
        <h2>+ Simular Novo Lead de Mídia Paga</h2>
        <p class="sub">Teste a higienização de telefone brasileiro para E.164, filtro de formulário e deduplicação por <code>lead_id</code>.</p>
        <form id="simForm">
          <label>Lead ID (repita para testar idempotência)</label>
          <input id="fId" class="input" value="lead-custom-701" required />
          <label>Nome Completo</label>
          <input id="fName" class="input" value="Roberto Nogueira" required />
          <label>E-mail</label>
          <input id="fEmail" class="input" value="ROBERTO@HORIZONTE-DEMO.EXAMPLE" required />
          <label>Telefone Bruto (será convertido p/ E.164)</label>
          <input id="fPhone" class="input" value="(11) 99123-4567" required />
          <label>Formulário de Origem</label>
          <select id="fForm">
            <option value="form-b2b-enterprise-01">form-b2b-enterprise-01 (Autorizado)</option>
            <option value="form-unlisted-99">form-unlisted-99 (Não autorizado - Ignorar)</option>
          </select>
          <button type="submit" class="btn btn-primary" style="width:100%">Processar Lead no Pipeline</button>
        </form>
      </aside>
    </div>
  </main>

  <div id="toast" class="toast"></div>

  <script>
    const root = document.documentElement;
    function applyTheme(t) {
      root.setAttribute("data-theme", t);
      localStorage.setItem("ads-theme", t);
      document.getElementById("themeIcon").textContent = t === "light" ? "☾" : "☀";
      document.getElementById("themeLabel").textContent = t === "light" ? "Modo Escuro" : "Modo Claro";
    }
    applyTheme(localStorage.getItem("ads-theme") || "dark");
    document.getElementById("themeToggle").addEventListener("click", () => {
      applyTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
    });

    function toast(m) {
      const el = document.getElementById("toast");
      el.textContent = m; el.classList.add("show");
      setTimeout(() => el.classList.remove("show"), 2600);
    }

    async function loadState() {
      const data = await (await fetch("/api/state")).json();
      document.getElementById("kSynced").textContent = data.leads.length;
      document.getElementById("kDup").textContent = data.stats.skipped_duplicate;
      document.getElementById("kIgnored").textContent = data.stats.ignored_form;
      document.getElementById("kOauth").textContent = data.stats.oauth_refreshes;

      const tbody = document.getElementById("leadsBody");
      tbody.innerHTML = "";
      data.leads.forEach(item => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${item.norm.full_name}</strong><br/><span class="mono">${item.lead_id} · ${item.norm.campaign_name}</span></td>
          <td><span class="mono" style="color:var(--accent)">${item.norm.phone_e164}</span><br/><span class="mono">${item.norm.email}</span></td>
          <td class="mono">${item.form_id}</td>
          <td><span class="badge">${item.crm_deal_id}</span></td>
        `;
        tbody.appendChild(tr);
      });
    }

    document.getElementById("pollBtn").addEventListener("click", async () => {
      const r = await (await fetch("/api/poll", { method: "POST" })).json();
      toast(`Polling: +${r.injected} injetados, ${r.skipped_duplicate} duplicados ignorados`);
      loadState();
    });

    document.getElementById("simForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        id: document.getElementById("fId").value,
        full_name: document.getElementById("fName").value,
        email: document.getElementById("fEmail").value,
        phone: document.getElementById("fPhone").value,
        form_id: document.getElementById("fForm").value,
        campaign_name: "Inbound Web Demo",
        company: "Horizonte S.A.",
      };
      const res = await (await fetch("/api/inject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })).json();
      toast(res.message);
      loadState();
    });

    loadState();
  </script>
</body>
</html>
"""


class CustomMutableAdsProvider(DemoAdsProvider):
    def __init__(self) -> None:
        super().__init__(expire_first_token=True)
        self.extra_leads: list[dict[str, Any]] = []

    def fetch_leads(self, account_id: str, access_token: str) -> list[dict[str, Any]]:
        base = super().fetch_leads(account_id, access_token)
        return base + list(self.extra_leads)


def run_studio(port: int = 8021, host: str = "127.0.0.1") -> None:
    storage = LeadStorage(Path("data/studio_leads.db"))
    ads_provider = CustomMutableAdsProvider()
    crm_provider = DemoCRMProvider()
    token_mgr = OAuthTokenManager(
        access_token="expired-demo-token",
        refresh_token="demo-refresh-token",
        refresh_fn=lambda rt: ("fresh-demo-token", rt),
    )
    settings = PipelineSettings(
        allowed_form_ids=["form-b2b-enterprise-01", "form-saas-trial-02"],
        ad_accounts=[AdAccountConfig(name="Conta Principal B2B", account_id="acc-100")],
    )
    pipeline = LeadPipeline(
        settings=settings,
        ads_provider=ads_provider,
        crm_provider=crm_provider,
        notifier=ConsoleNotifier(),
        storage=storage,
        token_manager=token_mgr,
    )
    totals = {"skipped_duplicate": 0, "ignored_form": 0, "oauth_refreshes": 0}
    s0 = pipeline.run_once()
    totals["skipped_duplicate"] += s0.skipped_duplicate
    totals["ignored_form"] += s0.ignored_form
    totals["oauth_refreshes"] = s0.oauth_refreshes

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            pass

        def _json(self, obj: Any, status: int = 200) -> None:
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            if self.path == "/api/state":
                rows = storage.list_processed()
                enriched = []
                for r in rows:
                    norm = normalize_lead(r["payload"])
                    enriched.append(
                        {
                            "lead_id": r["lead_id"],
                            "form_id": r["form_id"],
                            "crm_deal_id": r["crm_deal_id"],
                            "norm": {
                                "full_name": norm.full_name,
                                "email": norm.email,
                                "phone_e164": norm.phone_e164,
                                "campaign_name": norm.campaign_name,
                            },
                        }
                    )
                self._json({"leads": enriched, "stats": totals})
                return
            raw = STUDIO_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self) -> None:
            if self.path == "/api/poll":
                st = pipeline.run_once()
                totals["skipped_duplicate"] += st.skipped_duplicate
                totals["ignored_form"] += st.ignored_form
                totals["oauth_refreshes"] = st.oauth_refreshes
                self._json(
                    {
                        "injected": st.injected,
                        "skipped_duplicate": st.skipped_duplicate,
                        "ignored_form": st.ignored_form,
                    }
                )
                return
            if self.path == "/api/inject":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                ads_provider.extra_leads = [payload]
                st = pipeline.run_once()
                ads_provider.extra_leads = []
                totals["skipped_duplicate"] += st.skipped_duplicate
                totals["ignored_form"] += st.ignored_form
                if st.injected:
                    msg = f"Lead {payload['id']} normalizado e injetado no CRM!"
                elif st.skipped_duplicate:
                    msg = f"Idempotência: {payload['id']} já existe no SQLite (ignorado)."
                else:
                    msg = f"Formulário {payload['form_id']} fora da whitelist (ignorado)."
                self._json({"message": msg})
                return
            self.send_error(404)

    httpd = HTTPServer((host, port), Handler)
    print(f"Ads-to-CRM Pipeline Console em http://{host}:{port}")
    httpd.serve_forever()
