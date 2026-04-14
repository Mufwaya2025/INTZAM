# Odoo Integration Status Tracker
**Project**: IntZam Microfinance / CirclePay Zambia — LMS ↔ Odoo 17 XML-RPC Bridge
**Last updated**: 2026-03-17 (live disbursement + repayment tested, service account created, cron wired)
**Odoo target**: Community 17 at `http://localhost:8069`
**Database**: `odoo_lms_test` (dev) / `odoo_lms_production` (prod)

---

## Quick Status Summary

| Layer | Status |
|---|---|
| Django XML-RPC client (`odoo_client.py`) | **Done** |
| Disbursement hook (`on_loan_disbursed`) | **Done — wired** |
| Payment hook (`on_payment_received`) | **Done — wired** |
| Repayment-due hook (`on_repayment_due`) | **Done — wired** via `sync_odoo_repayment_invoices` command |
| `lms_bridge` Odoo custom module | **Done — Installed** (`odoo_lms_test`) |
| Odoo service | **Running** PID at `/tmp/odoo17.pid`, start: `bash ~/start_odoo.sh` |
| PostgreSQL | **Running** `:5432`, `odoo_user` / `odoo_pass_2025` confirmed |
| Odoo HTTP | **Up** `:8069` health `{"status":"pass"}` |
| `lms_bridge` DB install state | **Installed** — `lms.loan.event` accessible, 0 records |
| All 5 journals | **Present** LDIS(8), LRPY(9), LINT(10), LFEE(11), LPROV(12) |
| All 76 Section 7 COA accounts | **Present** 76/76 verified (2026-03-16) |
| 7-step connection test | **All pass** (2026-03-16) |
| Dedicated Odoo service account | **Done** — `lms_bridge` UID=6, `.env.local` + `.env` updated |
| Repayment-due management command | **Done** `sync_odoo_repayment_invoices` |
| Section 9 (Prompts 19–22) | **Done** — connection test, journal debugger, monthly report, MoMo webhook |
| Section 10 (Konse Konse, Prompts 23–29) | **Done** — full KK gateway layer, Odoo event router, model/migration, webhook, cron, 4 COA accounts, test suite |

---

## What's Already Built

### Django Side (`/mnt/f/LMS/backend/`)

| File | What it does |
|---|---|
| `apps/accounting/odoo_client.py` | Full XML-RPC client — auth, sync_borrower, post_disbursement, post_repayment, post_penalty, post_origination_fee, post_ecl_provision, post_writeoff, post_recovery, ping |
| `apps/accounting/on_loan_approved.py` | Hook: syncs borrower + posts disbursement journal. Called from `DisburseLoanView` (line 160) |
| `apps/accounting/on_payment_received.py` | Hook: splits principal/interest, posts repayment + penalty journals. Called from `RepaymentView` (lines 243-248) |
| `apps/accounting/on_repayment_due.py` | Hook: creates repayment invoice in Odoo for next due instalment. **Not yet called by any scheduler** |
| `apps/loans/migrations/0003_loan_odoo_fields.py` | Adds `odoo_partner_id` and `odoo_disbursement_move_id` to `Loan` model |
| `config/config_loader.py` | Multi-env `.env` loader (`APP_ENV=local/production/staging`) |
| `.env.example` | All `ODOO_*` vars documented (URL, DB, user, password, journal codes, account codes) |
| `test_odoo_connection.py` | 7-step connection test script (HTTP → XML-RPC → auth → partners → lms.loan.event → journals → ping) |

### Odoo Side (`/opt/odoo17/custom_addons/lms_bridge/`)

| File | What it does |
|---|---|
| `__manifest__.py` | Module descriptor — v17.0.1.0.0, depends on `base`, `account`, `contacts`, `mail` |
| `models/lms_loan_event.py` | `lms.loan.event` audit log model — idempotency ledger for all LMS→Odoo events |
| `models/lms_config.py` | `LmsBridgeConfig` — journal/account settings UI under Accounting → Configuration |
| `data/lms_bridge_data.xml` | Seeds `ir.config_parameter` records for journal codes (LDIS, LRPY, LINT, LFEE, LPROV) |
| `views/lms_loan_event_views.xml` | List/form views for the LMS Bridge → Loan Events menu |
| `views/lms_bridge_menu.xml` | Top-level menu entry in Odoo |
| `security/ir.model.access.csv` | Access rules for `lms.loan.event` |

### Tooling

| File | What it does |
|---|---|
| `export_odoo.sh` | Packages DB dump + filestore + lms_bridge + odoo17.conf into a dated `.zip` |
| `import_odoo.sh` | Restores that zip on a production server (with dry-run mode) |

---

## Missing / TODO

### P0 — Must do to get the bridge working at all

- [x] **Start Odoo service** *(2026-03-16)*
  Odoo not registered as systemd unit. Use `bash ~/start_odoo.sh` instead.
  PID stored at `/tmp/odoo17.pid`. Stop: `kill $(cat /tmp/odoo17.pid)`
  ```bash
  bash ~/start_odoo.sh
  ```

- [x] **Verify PostgreSQL `odoo_user` credentials** *(2026-03-16)*
  `odoo_user` / `odoo_pass_2025` (from `/etc/odoo17.conf`). Confirmed working.

- [x] **Verify lms_bridge is installed in `odoo_lms_test`** *(2026-03-16)*
  `lms.loan.event` accessible — module is installed.

- [x] **Run the full connection test** *(2026-03-16)*
  All 7 tests passed. Run with:
  ```bash
  source /home/mufwaya/lms-venv/bin/activate
  cd /mnt/f/LMS/backend && python test_odoo_connection.py
  ```
  > Note: the Windows venv at `/mnt/f/LMS/venv/` cannot be used in WSL.
  > Linux venv lives at `/home/mufwaya/lms-venv/`.

- [x] **Verify the 5 required journals exist in Odoo** *(2026-03-16)*
  LDIS(8), LRPY(9), LINT(10), LFEE(11), LPROV(12) — all present.

- [x] **Verify all 76 Section 7 COA accounts exist** *(2026-03-16)*
  Full Section 7 audit: 66/76 were already present. 10 were missing and created via XML-RPC:
  1104, 1311, 1321, 2110, 2203, 3003, 3005, 5203, 5214, 5251.
  > Note: `3003` (Current Year Profit/Loss) uses type `equity` — Odoo reserves
  > `equity_unaffected` for the system account `999999` (Undistributed Profits/Losses).
  > All 76/76 accounts confirmed present after remediation.

---

### Section 8 Event Mapping — Compliance Status *(updated 2026-03-16)*

| Event | Debit | Credit | Status |
|---|---|---|---|
| Loan Disbursed | 1111 | 1105 | **Wired** — `DisburseLoanView` → `on_loan_disbursed` |
| Repayment Principal | 1105 | 1111/1112/1113 | **Wired** — `RepaymentView` → `on_payment_received` |
| Repayment Interest | 1105 | 4101/4102/4103 | **Wired** — same hook, IFRS stage-aware |
| Repayment Penalty | 1105 | 4202 | **Wired** — same hook, `penalty_amount` param |
| Loan moves to S2 | 5102 | 1202 | **Wired** — `update_loan_statuses` → `on_stage_changed` |
| Loan moves to S3 | 5103 | 1203 | **Wired** — same command |
| Loan Written Off | 1204 | 1113 | **Wired** — `WriteOffLoanView` → `on_loan_written_off` *(was Dr 5104 — fixed)* |
| Recovery Post Write-off | 1105 | 4302 | **Wired** — new `RecoveryView` → `on_recovery_received` |
| Origination Fee | 1105 | 4201 | **Wired** — `on_loan_disbursed` (auto if `processing_fee > 0`) |
| VAT on Origination Fee | 2105 | 4201 | **Wired** — called alongside origination fee |
| Insurance Premium | 1105 | 4204 | **Built** — `post_insurance_premium()`. Call manually or wire via `RepaymentView` flag |
| Mobile Money Levy | 2109 | 1102/1103 | **Built** — `post_momo_levy()`. Wire when Konse Konse gateway integrated |
| VAT on Fees (general) | 2105 | 4201/4202 | **Built** — `post_vat_on_fees()`. Wire per-fee-type as needed |
| Interest Accrual (month-end) | 1120 | 4101/4102/4103 | **Wired** — `sync_odoo_interest_accrual` command |
| Provision Monthly Charge | 5101/5102/5103 | 1201/1202/1203 | **Wired** — `sync_odoo_ecl_provision` command |

---

### P1 — Required before any disbursement/payment events sync

- [x] **Confirm `.env` Odoo credentials work end-to-end** *(2026-03-17)*
  Switched to dedicated service account `lms_bridge` (UID=6). All 7 connection tests pass.

- [x] **Run a live disbursement test** *(2026-03-17)*
  Loan LN477208 (ZMW 5,000, 3 months). Results:
  - `odoo_partner_id=10`, `odoo_disbursement_move_id=5` stored on loan
  - Odoo journal entry: `LDIS/2026/03/0002`, state=posted, ZMW 5,000
  - Dr 1111 / Cr 1105 verified

- [x] **Run a live repayment test** *(2026-03-17)*
  ZMW 2,000 repayment on LN477208. Results:
  - Odoo journal entry: `LRPY/2026/00002`, state=posted, ZMW 2,000
  - Dr 1105 / Cr 1111 ZMW 1,600.01 principal / Cr 4101 ZMW 399.99 interest — split correct

---

### P2 — Required for full feature parity

- [x] **Build the repayment-due management command** *(2026-03-16)*
  Created: `backend/apps/core/management/commands/sync_odoo_repayment_invoices.py`
  Features: `--dry-run`, `--loan LOAN_NUMBER`, skips not-yet-due instalments.
  Dry-run tested and working (0 active loans in dev DB).
  Wire to cron once there are live loans (daily at 08:00 CAT):
  ```bash
  # crontab -e
  0 8 * * * /home/mufwaya/lms-venv/bin/python /mnt/f/LMS/backend/manage.py \
      sync_odoo_repayment_invoices >> /var/log/lms/odoo_repayment_sync.log 2>&1
  ```

- [x] **Create dedicated Odoo service account** *(2026-03-17)*
  - Name: `LMS Bridge Service`, login: `lms_bridge`, UID=6
  - Group: Full Accounting Features (id=24)
  - `.env` and `.env.local` updated with new credentials

- [x] **Wire up ECL provision posting** *(2026-03-16)*
  `sync_odoo_ecl_provision` management command created. Cron: 1st of month 07:00.

- [x] **Wire up write-off and recovery hooks** *(2026-03-16)*
  `on_loan_written_off.py` + `on_recovery_received.py` created and wired into `WriteOffLoanView` and new `RecoveryView`.

- [x] **Wire up origination/application fee posting** *(2026-03-16)*
  Called automatically from `on_loan_disbursed()` when `product.processing_fee > 0`. VAT posted alongside.

- [ ] **Wire up insurance premium posting**
  `post_insurance_premium()` exists in `odoo_client.py`. No caller yet — add `insurance_amount` param to `RepaymentView` when needed.

- [x] **Set up cron jobs** for all 5 management commands *(2026-03-17)* — installed in crontab, logs → `/home/mufwaya/logs/lms/`:
  ```bash
  # crontab -e  (use /home/mufwaya/lms-venv/bin/python)
  0  1 * * * python /mnt/f/LMS/backend/manage.py update_loan_statuses
  0  8 * * * python /mnt/f/LMS/backend/manage.py sync_odoo_repayment_invoices
  0  7 1 * * python /mnt/f/LMS/backend/manage.py sync_odoo_ecl_provision
  55 23 L * * python /mnt/f/LMS/backend/manage.py sync_odoo_interest_accrual
  * * * * *   python /mnt/f/LMS/backend/manage.py poll_konse_transactions
  ```

---

### P3 — Production deployment

- [ ] **Create `.env.production`** from `.env.example`
  - Set `ODOO_URL` to the production server IP/domain
  - Set `ODOO_DB=odoo_lms_production`
  - Set `ODOO_USER` to the dedicated service account (not admin)
  - Set `ODOO_ENABLED=true`

- [ ] **Run `export_odoo.sh`** to snapshot the dev Odoo environment
  ```bash
  bash /mnt/f/LMS/export_odoo.sh
  # Output: ~/odoo_exports/odoo_export_YYYYMMDD.zip
  ```

- [ ] **Transfer and run `import_odoo.sh`** on the production server
  ```bash
  bash import_odoo.sh --archive odoo_export_*.zip --target-db odoo_lms_production
  ```

- [x] **Konse Konse gateway integration** *(2026-03-16)*
  Full Section 10 layer complete:
  - `konse_konse_client.py` — API client with HMAC-SHA256 signing, retry/backoff, sandbox mode
  - `konse_events.py` — Odoo event router (disbursement, repayment, fee, agent collection)
  - `KonseTransaction` model + migration `0004_konse_transaction.py`
  - `KonseWebhookView` at `POST /api/accounting/konse-webhook/`
  - `poll_konse_transactions` management command (every-minute cron)
  - 4 new COA accounts in Odoo: 1107 KK Gateway Float, 1108 KK Disbursement Clearing, 2111 KK Fees Payable, 5223 KK Gateway Fees
  - `test_konse_odoo_flow.py` — 7-case integration test suite
  - **Pending**: real `KONSE_API_KEY` + `KONSE_SECRET` from Konse Konse sandbox; ngrok tunnel for `KONSE_CALLBACK_URL`

---

---

## Odoo 19 Upgrade Plan

**Current version**: Odoo 17 Community (LTS — supported through 2027)
**Target version**: Odoo 19 Community (released October 2025)
**Upgrade path**: 17 → 18 → 19 *(Odoo does not support skipping versions)*

**Recommendation**: Remain on Odoo 17 until the LMS is live and stable in production. Plan the migration for Q3/Q4 2027 or when Odoo 17 LTS support ends.

---

### Phase 1 — Odoo 17 → 18

| Task | Effort | Notes |
|---|---|---|
| Export dev DB snapshot | 30 min | `bash export_odoo.sh` |
| Install Odoo 18 Community in parallel WSL instance | 2 hrs | Do NOT overwrite the 17 install |
| Run Odoo built-in migration tool (`odoo-bin -d odoo_lms_test -u all`) | 1–2 hrs | Resolves model changes automatically |
| Rewrite `lms_bridge` module for Odoo 18 API | 1–2 days | See breaking changes below |
| Re-verify all 76 COA accounts and 5 journals | 1 hr | Some account types renamed in v18 |
| Re-run `test_odoo_connection.py` + `test_konse_odoo_flow.py` | 30 min | |

### Phase 2 — Odoo 18 → 19

| Task | Effort | Notes |
|---|---|---|
| Repeat migration process on the v18 DB | 1–2 hrs | |
| Update `lms_bridge` for any v19 API changes | 4–8 hrs | Smaller delta than 17→18 |
| Re-verify and re-test | 1 hr | |

---

### Known Breaking Changes to Address

#### `lms_bridge` module (`/opt/odoo17/custom_addons/lms_bridge/`)

| Change | Odoo 18/19 Impact |
|---|---|
| `__manifest__.py` version | Change `17.0.1.0.0` → `18.0.1.0.0` (then `19.0.1.0.0`) |
| `account_type` field values | Some internal codes renamed — re-verify all account types |
| `ir.actions.act_window` URL format | `/web#action=ID` → `/odoo/action-ID` (already broken in 17; use menu navigation) |
| `account.move` `move_type` field | Stable across 17/18/19 |
| XML-RPC endpoint | `/xmlrpc/2/common` and `/xmlrpc/2/object` — unchanged, fully stable |
| `mail.thread` mixin in models | May require updated `_inherit` declarations |

#### Django side (`odoo_client.py`)

| Change | Impact |
|---|---|
| XML-RPC calls | No changes needed — protocol is stable |
| `account_type` values in search filters | Update if Odoo 18/19 renames any (e.g. `asset_receivable` → check release notes) |
| Journal entry line structure | Stable — `account.move.line` with `debit`/`credit` unchanged |

---

### Pre-Migration Checklist

Before starting any upgrade:
- [ ] Full DB backup: `bash /mnt/f/LMS/export_odoo.sh`
- [ ] All LMS Django migrations up to date: `python manage.py migrate`
- [ ] All 5 cron jobs paused (stop `poll_konse_transactions` etc.)
- [ ] Test suite passing: `python test_odoo_connection.py` all 7 steps green
- [ ] Odoo 17 snapshot tagged in git: `git tag odoo17-pre-migration`

---

## Test Checklist (run after each change)

```bash
# 1. Full connection test
cd /mnt/f/LMS/backend && python test_odoo_connection.py

# 2. Django shell ping
python manage.py shell -c "
from apps.accounting.odoo_client import get_odoo_client
import json; print(json.dumps(get_odoo_client().ping(), indent=2))
"

# 3. After a disbursement — check Odoo IDs were stored
python manage.py shell -c "
from apps.loans.models import Loan
l = Loan.objects.filter(status='ACTIVE').last()
print('odoo_partner_id:', l.odoo_partner_id)
print('odoo_disbursement_move_id:', l.odoo_disbursement_move_id)
"

# 4. Odoo journal entries count
python manage.py shell -c "
from apps.accounting.odoo_client import get_odoo_client
c = get_odoo_client()
print('LDIS entries:', len(c._search('account.move', [['journal_id.code','=','LDIS']])))
print('LRPY entries:', len(c._search('account.move', [['journal_id.code','=','LRPY']])))
"
```

---

## Change Log

| Date | Change | Who |
|---|---|---|
| 2026-03-16 | Initial tracker created. Odoo service inactive, all Django-side code complete | — |
| 2026-03-16 | P0 complete: Odoo started via `~/start_odoo.sh`, all 7 connection tests pass, journals verified | — |
| 2026-03-16 | Full Section 7 COA audit: 66/76 present, created 10 missing accounts (1104, 1311, 1321, 2110, 2203, 3003, 3005, 5203, 5214, 5251). 76/76 confirmed | — |
| 2026-03-16 | Created Linux venv at `/home/mufwaya/lms-venv/` (Windows venv at `/mnt/f/LMS/venv/` unusable in WSL) | — |
| 2026-03-16 | Built `sync_odoo_repayment_invoices` management command (P2). Dry-run tested OK | — |
| 2026-03-16 | Section 9 Prompt 19: already done (`test_odoo_connection.py`). Prompts 20–22 implemented: journal imbalance debugger (`debug_journal_imbalance.py` + `debug_journal_lines()` method), monthly Odoo report endpoint (`GET /api/accounting/odoo-monthly-report/`), MoMo reconciliation module + webhook (`POST /api/accounting/momo-webhook/`) | — |
| 2026-03-16 | Section 8 full compliance pass: fixed `post_writeoff()` debit (5104→1204); added `post_stage_transfer`, `post_insurance_premium`, `post_momo_levy`, `post_vat_on_fees`, `post_interest_accrual` methods; created `on_loan_written_off.py`, `on_loan_stage_changed.py`; wired `WriteOffLoanView`; added `RecoveryView` + `RECOVERY` transaction type + `/loans/<pk>/recover/` endpoint; built `update_loan_statuses`, `sync_odoo_ecl_provision`, `sync_odoo_interest_accrual` management commands. All 15 Section 8 events now mapped | — |
| 2026-03-16 | Full COA re-audit: created 19 missing accounts, corrected 18 name/type mismatches, added `notes` field to `lms.loan.event`, fixed US taxes → Zambia. All 76 accounts now verified correct | — |
| 2026-03-16 | Section 10 (Konse Konse, Prompts 23–29) complete: `konse_konse_client.py`, `konse_events.py`, `KonseTransaction` model + migration, `KonseWebhookView`, `poll_konse_transactions` command, 4 new Odoo COA accounts (1107/1108/2111/5223 — shifted from guide's 1106/2110 to avoid COA conflicts), `test_konse_odoo_flow.py`. `manage.py check` clean. Pending: real sandbox credentials + ngrok | — |
| 2026-03-17 | P1 complete: live disbursement test (LN477208 ZMW 5k → LDIS/2026/03/0002), live repayment test (ZMW 2k → LRPY/2026/00002, correct principal/interest split). Dedicated service account `lms_bridge` (UID=6) created, `.env.local` and `.env` updated. All 5 cron jobs wired in crontab (logs: ~/logs/lms/). | — |

---

## Key File Paths Reference

| What | Path |
|---|---|
| XML-RPC client | `/mnt/f/LMS/backend/apps/accounting/odoo_client.py` |
| Disbursement hook | `/mnt/f/LMS/backend/apps/accounting/on_loan_approved.py` |
| Payment hook | `/mnt/f/LMS/backend/apps/accounting/on_payment_received.py` |
| Repayment-due hook | `/mnt/f/LMS/backend/apps/accounting/on_repayment_due.py` |
| Connection test | `/mnt/f/LMS/backend/test_odoo_connection.py` |
| Odoo custom module | `/opt/odoo17/custom_addons/lms_bridge/` |
| Odoo binary | `/opt/odoo17/odoo-bin` |
| Odoo config | `/etc/odoo17.conf` |
| Django `.env` | `/mnt/f/LMS/backend/.env` |
| Export script | `/mnt/f/LMS/export_odoo.sh` |
| Import script | `/mnt/f/LMS/import_odoo.sh` |
| Repayment-due command | `/mnt/f/LMS/backend/apps/core/management/commands/sync_odoo_repayment_invoices.py` |
| ECL provision command | `/mnt/f/LMS/backend/apps/core/management/commands/sync_odoo_ecl_provision.py` |
| Interest accrual command | `/mnt/f/LMS/backend/apps/core/management/commands/sync_odoo_interest_accrual.py` |
| Loan status update command | `/mnt/f/LMS/backend/apps/core/management/commands/update_loan_statuses.py` |
| Write-off hook | `/mnt/f/LMS/backend/apps/accounting/on_loan_written_off.py` |
| Stage change hook | `/mnt/f/LMS/backend/apps/accounting/on_loan_stage_changed.py` |
| MoMo reconciliation | `/mnt/f/LMS/backend/apps/accounting/momo_reconcile.py` |
| Journal debug script | `/mnt/f/LMS/backend/debug_journal_imbalance.py` |
| Monthly Odoo report | `GET /api/accounting/odoo-monthly-report/?period=YYYY-MM` |
| MoMo webhook | `POST /api/accounting/momo-webhook/` |
| Konse Konse client | `/mnt/f/LMS/backend/apps/accounting/konse_konse_client.py` |
| Konse Konse Odoo router | `/mnt/f/LMS/backend/apps/accounting/konse_events.py` |
| Konse Konse webhook | `POST /api/accounting/konse-webhook/` |
| KK transaction model | `/mnt/f/LMS/backend/apps/loans/models.py` (`KonseTransaction`) |
| KK migration | `/mnt/f/LMS/backend/apps/loans/migrations/0004_konse_transaction.py` |
| KK poll command | `/mnt/f/LMS/backend/apps/core/management/commands/poll_konse_transactions.py` |
| KK integration tests | `/mnt/f/LMS/backend/test_konse_odoo_flow.py` |
| Linux venv (WSL) | `/home/mufwaya/lms-venv/` |
