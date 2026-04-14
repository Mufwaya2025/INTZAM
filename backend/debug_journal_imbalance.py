#!/usr/bin/env python3
"""
debug_journal_imbalance.py  (Prompt 20)
========================================
Run from /mnt/f/LMS/backend/ to diagnose 'Journal Entry is not balanced'
errors when posting from the LMS to Odoo 17 via XML-RPC.

Usage:
    source /home/mufwaya/lms-venv/bin/activate
    python debug_journal_imbalance.py

The script:
  1. Connects to Odoo and resolves a real set of account IDs.
  2. Builds a deliberately imbalanced entry to show the debugger output.
  3. Builds a correctly balanced entry and confirms it passes.
  4. Queries the last 5 DRAFT journal entries in Odoo and checks their balance.
  5. Explains the 6 most common causes of imbalance.
"""
import os
import sys
import xmlrpc.client
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except ImportError:
    pass

ODOO_URL      = os.getenv('ODOO_URL',      'http://localhost:8069')
ODOO_DB       = os.getenv('ODOO_DB',       'odoo_lms_test')
ODOO_USER     = os.getenv('ODOO_USER',     'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin1234')

PASS  = '\033[92m✓\033[0m'
FAIL  = '\033[91m✗\033[0m'
WARN  = '\033[93m⚠\033[0m'
INFO  = '\033[94m→\033[0m'
BOLD  = '\033[1m'
RESET = '\033[0m'

sep   = lambda t='': print(f'\n{"─"*60}\n  {t}') if t else print('─'*60)
ok    = lambda m: print(f'  {PASS} {m}')
err   = lambda m: print(f'  {FAIL} {m}')
warn  = lambda m: print(f'  {WARN} {m}')
info  = lambda m: print(f'  {INFO} {m}')

# ── Connect ────────────────────────────────────────────────────────────────────
sep('Connecting to Odoo')
try:
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        err('Authentication failed'); sys.exit(1)
    ok(f'Authenticated as UID {uid}')
except Exception as e:
    err(f'Cannot connect: {e}'); sys.exit(1)


def call(model, method, args, kwargs=None):
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                             model, method, args, kwargs or {})


def resolve_account(code):
    rows = call('account.account', 'search_read',
                [[['code', '=', code]]], {'fields': ['id', 'name'], 'limit': 1})
    if not rows:
        raise ValueError(f'Account {code!r} not found in COA')
    return rows[0]['id'], rows[0]['name']


def check_lines(lines, label=''):
    """Print debit/credit totals and flag any imbalance or bad structure."""
    sep(f'BALANCE CHECK: {label}')
    total_dr = total_cr = 0.0
    issues = []

    for i, entry in enumerate(lines):
        vals   = entry[2]
        dr     = round(float(vals.get('debit',  0) or 0), 2)
        cr     = round(float(vals.get('credit', 0) or 0), 2)
        acc_id = vals.get('account_id', '?')
        name   = vals.get('name', '')
        total_dr += dr
        total_cr += cr

        row = f'  [{i:02d}] acct={acc_id:<5} Dr {dr:>12.2f}  Cr {cr:>12.2f}  "{name}"'
        print(row)

        if dr > 0 and cr > 0:
            issues.append(f'Line {i}: both Dr and Cr non-zero — pick one side only')
        if dr == 0 and cr == 0:
            issues.append(f'Line {i}: both zero — Odoo will ignore this line')

    diff = round(abs(total_dr - total_cr), 2)
    print(f'\n  TOTALS  Dr {total_dr:>12.2f}  Cr {total_cr:>12.2f}  diff={diff:.2f}')

    if diff == 0:
        ok('Entry is BALANCED')
    else:
        err(f'Entry is UNBALANCED by {diff:.2f} ZMW')
        issues.append(f'Imbalance of {diff:.2f}')

    for issue in issues:
        warn(issue)
    return diff == 0


# ── Step 1: Show a deliberately imbalanced entry ───────────────────────────────
sep('STEP 1 — Imbalanced entry (for demonstration)')
bank_id,   bank_name   = resolve_account('1105')
loan_s1_id, loan_s1_name = resolve_account('1111')

bad_lines = [
    (0, 0, {'account_id': loan_s1_id, 'debit':  1000.00, 'credit': 0.0,
            'name': 'Loan disbursement (Dr)'}),
    (0, 0, {'account_id': bank_id,    'debit':  0.0,     'credit': 999.00,
            'name': 'Bank clearing (Cr) — WRONG AMOUNT'}),
]
check_lines(bad_lines, 'Disbursement — amount mismatch')

# ── Step 2: Show a correct entry ───────────────────────────────────────────────
sep('STEP 2 — Correctly balanced entry')
good_lines = [
    (0, 0, {'account_id': loan_s1_id, 'debit':  1000.00, 'credit': 0.0,
            'name': 'Loan disbursement (Dr)'}),
    (0, 0, {'account_id': bank_id,    'debit':  0.0,     'credit': 1000.00,
            'name': 'Bank clearing (Cr)'}),
]
check_lines(good_lines, 'Disbursement — correct')

# ── Step 3: Multi-leg with rounding error ─────────────────────────────────────
sep('STEP 3 — Multi-leg rounding error (common with fee splits)')
int_id, _  = resolve_account('4101')
fee_id, _  = resolve_account('4201')

principal = 1000.00
interest  = 83.33
fee       = 50.00
total_in  = principal + interest + fee  # 1133.33

rounding_lines = [
    (0, 0, {'account_id': bank_id,   'debit': total_in, 'credit': 0.0,
            'name': 'Total received'}),
    (0, 0, {'account_id': loan_s1_id,'debit': 0.0,  'credit': principal,
            'name': 'Principal'}),
    (0, 0, {'account_id': int_id,    'debit': 0.0,  'credit': 83.34,   # off by 0.01
            'name': 'Interest (rounded up accidentally)'}),
    (0, 0, {'account_id': fee_id,    'debit': 0.0,  'credit': fee,
            'name': 'Fee'}),
]
check_lines(rounding_lines, 'Multi-leg with rounding error')

# ── Step 4: Check last 5 draft moves in Odoo ─────────────────────────────────
sep('STEP 4 — Last 5 DRAFT journal entries in Odoo (imbalance check)')
drafts = call('account.move', 'search_read',
              [[['state', '=', 'draft']]],
              {'fields': ['id', 'ref', 'date', 'journal_id'], 'limit': 5,
               'order': 'id desc'})

if not drafts:
    info('No draft journal entries found.')
else:
    for move in drafts:
        move_id  = move['id']
        lines_data = call('account.move.line', 'search_read',
                          [[['move_id', '=', move_id]]],
                          {'fields': ['account_id', 'debit', 'credit', 'name']})
        total_dr = round(sum(l['debit']  for l in lines_data), 2)
        total_cr = round(sum(l['credit'] for l in lines_data), 2)
        diff     = round(abs(total_dr - total_cr), 2)
        symbol   = PASS if diff == 0 else FAIL
        print(f'  {symbol} id={move_id}  ref={move.get("ref","—"):<30}  '
              f'Dr={total_dr:.2f}  Cr={total_cr:.2f}  diff={diff:.2f}')

# ── Step 5: Common causes reference ──────────────────────────────────────────
sep('STEP 5 — Common causes of Journal Entry is not balanced')
causes = [
    ('Rounding mismatch',
     'Use round(x, 2) on EVERY amount. Never use float arithmetic directly on '
     'Decimal model fields — cast with float() first, then round.'),
    ('Wrong amount on one leg',
     'Total received ≠ sum of all credit/debit lines. Print each leg before posting.'),
    ('Multi-currency entry without FX rate',
     'If one line uses USD and another ZMW, Odoo needs an FX rate set on the company.'),
    ('Both Dr and Cr set on same line',
     'Each account.move.line must have debit=X, credit=0  OR  debit=0, credit=Y.'),
    ('Zero-amount lines included',
     'Odoo ignores zero lines in validation but some versions treat them as errors. '
     'Filter them out: [l for l in lines if l[2]["debit"] or l[2]["credit"]].'),
    ('Account currency ≠ company currency',
     'Some accounts are pinned to USD. A ZMW debit against a USD-only account '
     'will fail balance checks. Check account.account.currency_id.'),
]
for i, (title, detail) in enumerate(causes, 1):
    print(f'\n  {BOLD}{i}. {title}{RESET}')
    print(f'     {detail}')

print('\n')
