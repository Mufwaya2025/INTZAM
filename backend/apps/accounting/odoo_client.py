# -*- coding: utf-8 -*-
"""
odoo_client.py
==============
XML-RPC integration client between the IntZam LMS (Django) and
Odoo 17 Community Accounting.

Responsibilities:
  - Authenticate to Odoo via XML-RPC v2
  - Sync borrowers (LMS Client → Odoo res.partner)
  - Post loan disbursement journal entries
  - Create customer invoices for repayment schedules
  - Post penalty, fee, provision, write-off, and recovery entries
  - Guarantee idempotency via lms_reference unique key

Usage:
    from apps.accounting.odoo_client import OdooLMSClient

    client = OdooLMSClient()           # loads from .env automatically
    client.authenticate()              # optional — auto-called on first use
    partner_id = client.sync_borrower(client_obj)
    move_id    = client.post_disbursement(loan_obj)

Environment variables (in backend/.env):
    ODOO_URL       http://localhost:8069
    ODOO_DB        odoo_lms_test
    ODOO_USER      admin
    ODOO_PASSWORD  admin1234
    ODOO_ENABLED   true   (set false to disable all Odoo calls — dry-run mode)
"""

from __future__ import annotations

import logging
import os
import xmlrpc.client
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
_ENV_PATH = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(_ENV_PATH, override=False)

_logger = logging.getLogger(__name__)

ZAMBIA_COUNTRY_ID = 248   # res.country id for Zambia in Odoo


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class OdooConnectionError(Exception):
    """Raised when Odoo authentication or connection fails."""


class OdooPostingError(Exception):
    """Raised when an Odoo write/create/post operation fails."""


class OdooDuplicateError(Exception):
    """Raised when a duplicate lms_reference is detected in Odoo."""


# ─────────────────────────────────────────────────────────────────────────────
# OdooLMSClient
# ─────────────────────────────────────────────────────────────────────────────

class OdooLMSClient:
    """
    Thread-safe XML-RPC client for Odoo 17.

    Lazy authentication — uid is fetched on the first actual RPC call.
    Account and journal IDs are resolved once per process and cached.
    """

    def __init__(
        self,
        url: str | None = None,
        db: str | None = None,
        username: str | None = None,
        password: str | None = None,
        enabled: bool | None = None,
    ):
        self.url      = (url      or os.getenv('ODOO_URL',      'http://localhost:8069')).rstrip('/')
        self.db       = db       or os.getenv('ODOO_DB',       'odoo_lms_test')
        self.username = username or os.getenv('ODOO_USER',     'admin')
        self.password = password or os.getenv('ODOO_PASSWORD', 'admin1234')

        _enabled_env  = os.getenv('ODOO_ENABLED', 'true').lower()
        self.enabled  = enabled if enabled is not None else (_enabled_env == 'true')

        self._uid: int | None = None
        self._common_proxy: xmlrpc.client.ServerProxy | None = None
        self._models_proxy: xmlrpc.client.ServerProxy | None = None

        # Account / journal ID caches
        self._account_ids: dict[str, int] = {}
        self._journal_ids: dict[str, int] = {}

    # ── Proxy properties ──────────────────────────────────────────────────────

    @property
    def _common(self) -> xmlrpc.client.ServerProxy:
        if self._common_proxy is None:
            self._common_proxy = xmlrpc.client.ServerProxy(
                f'{self.url}/xmlrpc/2/common',
                allow_none=True,
            )
        return self._common_proxy

    @property
    def _models(self) -> xmlrpc.client.ServerProxy:
        if self._models_proxy is None:
            self._models_proxy = xmlrpc.client.ServerProxy(
                f'{self.url}/xmlrpc/2/object',
                allow_none=True,
            )
        return self._models_proxy

    # ── Authentication ────────────────────────────────────────────────────────

    def authenticate(self) -> int:
        """
        Authenticate with Odoo and cache the user id (uid).
        Safe to call multiple times — returns cached uid after first call.

        Returns:
            int: Odoo user id

        Raises:
            OdooConnectionError: if credentials are invalid or Odoo is unreachable
        """
        if self._uid:
            return self._uid

        if not self.enabled:
            _logger.info('Odoo integration disabled (ODOO_ENABLED=false). Skipping auth.')
            return 0

        try:
            uid = self._common.authenticate(self.db, self.username, self.password, {})
        except Exception as exc:
            raise OdooConnectionError(
                f'Cannot reach Odoo at {self.url}: {exc}'
            ) from exc

        if not uid:
            raise OdooConnectionError(
                f'Odoo authentication failed: invalid credentials for '
                f'user {self.username!r} on db {self.db!r}.'
            )

        self._uid = uid
        _logger.info('Odoo authenticated: uid=%s url=%s db=%s', uid, self.url, self.db)
        return uid

    # ── Low-level RPC ─────────────────────────────────────────────────────────

    def _call(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        """
        Execute an XML-RPC call. Authenticates on first use.

        Args:
            model:   Odoo model name, e.g. 'account.move'
            method:  ORM method, e.g. 'create', 'write', 'search_read'
            args:    Positional arguments
            kwargs:  Keyword arguments (optional)

        Returns:
            Raw Odoo response

        Raises:
            OdooConnectionError: on auth failure
            OdooPostingError: on Odoo-side errors
        """
        if not self.enabled:
            _logger.debug('[DRY RUN] %s.%s(%s)', model, method, args)
            return None

        uid = self.authenticate()
        try:
            return self._models.execute_kw(
                self.db, uid, self.password,
                model, method, args, kwargs or {},
            )
        except xmlrpc.client.Fault as exc:
            raise OdooPostingError(
                f'Odoo RPC error on {model}.{method}: {exc.faultString}'
            ) from exc
        except Exception as exc:
            raise OdooConnectionError(
                f'Connection error on {model}.{method}: {exc}'
            ) from exc

    # ── Convenience helpers ───────────────────────────────────────────────────

    def _search(self, model: str, domain: list, **kw) -> list:
        return self._call(model, 'search', [domain], kw) or []

    def _search_read(self, model: str, domain: list, fields: list, **kw) -> list:
        return self._call(model, 'search_read', [domain], {'fields': fields, **kw}) or []

    def _create(self, model: str, vals: dict) -> int:
        return self._call(model, 'create', [vals])

    def _write(self, model: str, ids: list, vals: dict) -> bool:
        return self._call(model, 'write', [ids, vals])

    def _get_id(self, model: str, domain: list) -> int | None:
        ids = self._search(model, domain, limit=1)
        return ids[0] if ids else None

    def _exists(self, model: str, domain: list) -> bool:
        return bool(self._search(model, domain, limit=1))

    # ── Account / journal resolution ─────────────────────────────────────────

    def _account_id(self, code: str) -> int:
        """
        Resolve an account code (e.g. '1111') to its Odoo integer ID.
        Result is cached per process.

        Raises:
            OdooPostingError: if the account code does not exist in Odoo COA.
        """
        if code not in self._account_ids:
            result = self._search_read(
                'account.account', [['code', '=', code]], ['id', 'name']
            )
            if not result:
                raise OdooPostingError(
                    f'Account code {code!r} not found in Odoo Chart of Accounts. '
                    f'Run the COA setup script first.'
                )
            self._account_ids[code] = result[0]['id']
            _logger.debug('Account resolved: %s → id=%s (%s)',
                          code, self._account_ids[code], result[0]['name'])
        return self._account_ids[code]

    def _journal_id(self, code: str) -> int:
        """
        Resolve a journal code (e.g. 'LDIS') to its Odoo integer ID.
        Result is cached per process.

        Raises:
            OdooPostingError: if the journal code does not exist in Odoo.
        """
        if code not in self._journal_ids:
            result = self._search_read(
                'account.journal', [['code', '=', code]], ['id', 'name']
            )
            if not result:
                raise OdooPostingError(
                    f'Journal code {code!r} not found in Odoo. '
                    f'Create it under Accounting → Configuration → Journals.'
                )
            self._journal_ids[code] = result[0]['id']
            _logger.debug('Journal resolved: %s → id=%s (%s)',
                          code, self._journal_ids[code], result[0]['name'])
        return self._journal_ids[code]

    # ── Journal line builder ──────────────────────────────────────────────────

    @staticmethod
    def _line(
        account_id: int,
        debit: float = 0.0,
        credit: float = 0.0,
        name: str = '',
        partner_id: int | None = None,
    ) -> tuple:
        """Build an ORM (0, 0, vals) tuple for account.move line_ids."""
        vals: dict[str, Any] = {
            'account_id': account_id,
            'debit'     : round(float(debit), 2),
            'credit'    : round(float(credit), 2),
            'name'      : name,
        }
        if partner_id:
            vals['partner_id'] = partner_id
        return (0, 0, vals)

    # ── Idempotency check ─────────────────────────────────────────────────────

    def _is_duplicate(self, lms_reference: str) -> bool:
        """
        Return True if a posted journal entry with this reference already exists.
        Prevents double-posting on network retries.
        """
        return self._exists(
            'account.move',
            [['ref', '=', lms_reference], ['state', '=', 'posted']],
        )

    def _post_move(
        self,
        journal_code: str,
        lms_reference: str,
        move_date: str,
        lines: list[tuple],
        partner_id: int | None = None,
        narration: str = '',
    ) -> int:
        """
        Create and immediately post an account.move in Odoo.

        Args:
            journal_code:  e.g. 'LDIS'
            lms_reference: Unique idempotency key (stored in move.ref)
            move_date:     ISO date string 'YYYY-MM-DD'
            lines:         List of (0, 0, vals) tuples from _line()
            partner_id:    Optional Odoo partner id
            narration:     Internal memo / note

        Returns:
            int: account.move id

        Raises:
            OdooDuplicateError: if lms_reference already posted
            OdooPostingError:   on any Odoo-side error
        """
        if self._is_duplicate(lms_reference):
            raise OdooDuplicateError(
                f'Journal entry with ref {lms_reference!r} already posted. Skipping.'
            )

        vals: dict[str, Any] = {
            'journal_id': self._journal_id(journal_code),
            'ref'       : lms_reference,
            'date'      : move_date,
            'narration' : narration,
            'line_ids'  : lines,
        }
        if partner_id:
            vals['partner_id'] = partner_id

        move_id = self._create('account.move', vals)
        _logger.info(
            'Journal entry created: id=%s ref=%r journal=%s',
            move_id, lms_reference, journal_code,
        )

        # Post (confirm) the entry — moves it from Draft → Posted
        self._call('account.move', 'action_post', [[move_id]])
        _logger.info('Journal entry posted: id=%s', move_id)
        return move_id

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    # ── 1. sync_borrower ─────────────────────────────────────────────────────

    def sync_borrower(self, client) -> int:
        """
        Find or create an Odoo res.partner record for an LMS Client.

        Lookup order:
          1. By LMS ref field  (ref = 'LMS-<client.id>')
          2. By NRC number     (stored in comment field)
          3. By phone number
          4. Create new partner if none found

        Args:
            client: LMS Client model instance (apps.core.models.Client)

        Returns:
            int: Odoo res.partner id

        Raises:
            OdooPostingError: on Odoo write errors
        """
        lms_ref = f'LMS-{client.id}'

        # ── Search by LMS ref ───────────────────────────────────────────────
        partner_id = self._get_id(
            'res.partner',
            [['ref', '=', lms_ref], ['active', 'in', [True, False]]],
        )
        if partner_id:
            _logger.debug('Partner found by LMS ref: id=%s client=%s', partner_id, client.id)
            return partner_id

        # ── Search by NRC number ────────────────────────────────────────────
        if client.nrc_number:
            nrc_domain = [
                ['comment', 'ilike', client.nrc_number],
                ['active', 'in', [True, False]],
            ]
            partner_id = self._get_id('res.partner', nrc_domain)
            if partner_id:
                _logger.debug('Partner found by NRC: id=%s nrc=%s', partner_id, client.nrc_number)
                self._write('res.partner', [partner_id], {'ref': lms_ref})
                return partner_id

        # ── Search by phone ─────────────────────────────────────────────────
        if client.phone:
            partner_id = self._get_id(
                'res.partner',
                [['phone', '=', client.phone], ['active', 'in', [True, False]]],
            )
            if partner_id:
                _logger.debug('Partner found by phone: id=%s phone=%s', partner_id, client.phone)
                self._write('res.partner', [partner_id], {'ref': lms_ref})
                return partner_id

        # ── Create new partner ───────────────────────────────────────────────
        vals = {
            'name'          : client.name,
            'ref'           : lms_ref,
            'phone'         : client.phone or '',
            'email'         : client.email or '',
            'street'        : client.address or '',
            'country_id'    : ZAMBIA_COUNTRY_ID,
            'customer_rank' : 1,
            'comment'       : (
                f'NRC: {client.nrc_number or "—"}\n'
                f'LMS Client ID: {client.id}\n'
                f'Tier: {client.tier}\n'
                f'Employment: {client.employment_status}'
            ),
        }
        partner_id = self._create('res.partner', vals)
        _logger.info(
            'Partner created: id=%s name=%r lms_client=%s',
            partner_id, client.name, client.id,
        )
        return partner_id

    # ── 2. post_disbursement ──────────────────────────────────────────────────

    def post_disbursement(self, loan, partner_id: int | None = None) -> int:
        """
        Post a loan disbursement journal entry to Odoo.

        Journal: LDIS (Loan Disbursement — Miscellaneous)
        ─────────────────────────────────────────────────
        Dr  1111  Loan Receivable — Stage 1     (principal)
        Cr  1105  Bank — Main Clearing (ZMW)    (principal)

        Args:
            loan:       LMS Loan model instance
            partner_id: Odoo partner id (sync_borrower result)

        Returns:
            int: Odoo account.move id

        Raises:
            OdooDuplicateError: if already posted
            OdooPostingError:   on Odoo error
        """
        amount    = float(loan.amount)
        loan_ref  = f'DISB-{loan.loan_number}-{loan.disbursement_date or date.today()}'
        move_date = str(loan.disbursement_date or date.today())

        lines = [
            self._line(
                self._account_id('1111'), debit=amount,
                name=f'Loan disbursement — {loan.loan_number}',
                partner_id=partner_id,
            ),
            self._line(
                self._account_id('1105'), credit=amount,
                name=f'Loan disbursement — {loan.loan_number}',
                partner_id=partner_id,
            ),
        ]

        move_id = self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_DISBURSEMENT', 'LDIS'),
            lms_reference = loan_ref,
            move_date     = move_date,
            lines         = lines,
            partner_id    = partner_id,
            narration     = (
                f'Loan Disbursement\n'
                f'Loan #: {loan.loan_number}\n'
                f'Client: {loan.client.name}\n'
                f'Amount: ZMW {amount:,.2f}\n'
                f'Term: {loan.term_months} months\n'
                f'Rate: {loan.interest_rate}%'
            ),
        )
        _logger.info(
            'Disbursement posted: loan=%s amount=%.2f move_id=%s',
            loan.loan_number, amount, move_id,
        )
        return move_id

    # ── 3. create_repayment_invoice ───────────────────────────────────────────

    def create_repayment_invoice(
        self,
        loan,
        principal: float,
        interest: float,
        due_date: str,
        partner_id: int | None = None,
        invoice_ref: str | None = None,
    ) -> int:
        """
        Create a customer invoice (account.move, move_type='out_invoice') in Odoo
        for a loan repayment instalment — splitting principal and interest lines.

        Args:
            loan:        LMS Loan model instance
            principal:   Principal portion (ZMW)
            interest:    Interest (EIR) portion (ZMW)
            due_date:    ISO date string 'YYYY-MM-DD'
            partner_id:  Odoo partner id
            invoice_ref: Custom reference; defaults to LOAN-<loan_number>-<due_date>

        Returns:
            int: Odoo account.move id (invoice)

        Raises:
            OdooPostingError: on Odoo error
        """
        ref = invoice_ref or f'INV-{loan.loan_number}-{due_date}'

        # Resolve income accounts
        principal_account_id = self._account_id('1111')   # reduce loan receivable
        interest_account_id  = self._account_id('4101')   # interest income S1

        invoice_lines = []
        if principal > 0:
            invoice_lines.append((0, 0, {
                'name'      : f'Principal repayment — {loan.loan_number}',
                'account_id': principal_account_id,
                'quantity'  : 1,
                'price_unit': round(principal, 2),
            }))
        if interest > 0:
            invoice_lines.append((0, 0, {
                'name'      : f'Interest (EIR) — {loan.loan_number}',
                'account_id': interest_account_id,
                'quantity'  : 1,
                'price_unit': round(interest, 2),
            }))

        vals: dict[str, Any] = {
            'move_type'         : 'out_invoice',
            'journal_id'        : self._journal_id(
                                    os.getenv('ODOO_JOURNAL_REPAYMENT', 'LRPY')),
            'ref'               : ref,
            'invoice_date'      : str(date.today()),
            'invoice_date_due'  : due_date,
            'narration'         : (
                f'Loan repayment schedule\n'
                f'Loan #: {loan.loan_number}\n'
                f'Due: {due_date}'
            ),
            'invoice_line_ids'  : invoice_lines,
        }
        if partner_id:
            vals['partner_id'] = partner_id

        invoice_id = self._create('account.move', vals)
        _logger.info(
            'Repayment invoice created: loan=%s due=%s invoice_id=%s principal=%.2f interest=%.2f',
            loan.loan_number, due_date, invoice_id, principal, interest,
        )
        return invoice_id

    # ── 4. post_repayment ─────────────────────────────────────────────────────

    def post_repayment(
        self,
        loan,
        principal: float,
        interest: float,
        move_date: str | None = None,
        partner_id: int | None = None,
        reference: str | None = None,
        ifrs9_stage: str = '1',
    ) -> int:
        """
        Post a loan repayment journal entry (principal + interest split).

        Journal: LRPY (Loan Repayment — Bank)
        ──────────────────────────────────────
        Dr  1105  Bank — Main Clearing           (total received)
        Cr  1111  Loan Receivable — Stage 1/2/3  (principal)
        Cr  4101  Interest Income — Stage 1/2/3  (interest)

        Args:
            loan:        LMS Loan model instance
            principal:   Principal portion
            interest:    Interest portion
            move_date:   ISO date (defaults to today)
            partner_id:  Odoo partner id
            reference:   Custom ref; defaults to REPY-<loan_number>-<date>
            ifrs9_stage: '1', '2', or '3'

        Returns:
            int: Odoo account.move id
        """
        total     = principal + interest
        today     = str(date.today())
        move_date = move_date or today
        ref       = reference or f'REPY-{loan.loan_number}-{move_date}'

        stage_map = {
            '1': ('1111', '4101'),
            '2': ('1112', '4102'),
            '3': ('1113', '4103'),
        }
        rec_code, inc_code = stage_map.get(str(ifrs9_stage), ('1111', '4101'))

        lines = [
            self._line(
                self._account_id('1105'), debit=total,
                name=f'Repayment received — {loan.loan_number}',
                partner_id=partner_id,
            ),
        ]
        if principal > 0:
            lines.append(self._line(
                self._account_id(rec_code), credit=principal,
                name=f'Principal — {loan.loan_number}',
                partner_id=partner_id,
            ))
        if interest > 0:
            lines.append(self._line(
                self._account_id(inc_code), credit=interest,
                name=f'Interest (EIR) S{ifrs9_stage} — {loan.loan_number}',
                partner_id=partner_id,
            ))

        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_REPAYMENT', 'LRPY'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            partner_id    = partner_id,
            narration     = (
                f'Loan Repayment | Loan: {loan.loan_number} | '
                f'Stage {ifrs9_stage} | Principal: {principal:.2f} | '
                f'Interest: {interest:.2f}'
            ),
        )

    # ── 5. post_penalty ───────────────────────────────────────────────────────

    def post_penalty(
        self,
        loan,
        amount: float,
        move_date: str | None = None,
        partner_id: int | None = None,
        reference: str | None = None,
    ) -> int:
        """
        Post a penalty / late fee collection.

        Journal: LFEE (Penalty & Fees — Miscellaneous)
        ───────────────────────────────────────────────
        Dr  1105  Bank — Main Clearing
        Cr  4202  Penalty & Late Fees
        """
        move_date = move_date or str(date.today())
        ref       = reference or f'PEN-{loan.loan_number}-{move_date}'

        lines = [
            self._line(self._account_id('1105'), debit=amount,
                       name=f'Penalty — {loan.loan_number}', partner_id=partner_id),
            self._line(self._account_id('4202'), credit=amount,
                       name=f'Penalty income — {loan.loan_number}', partner_id=partner_id),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_FEES', 'LFEE'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            partner_id    = partner_id,
            narration     = f'Penalty | Loan: {loan.loan_number} | Amount: {amount:.2f}',
        )

    # ── 6. post_origination_fee ────────────────────────────────────────────────

    def post_origination_fee(
        self,
        loan,
        amount: float,
        fee_type: str = 'origination',
        move_date: str | None = None,
        partner_id: int | None = None,
        reference: str | None = None,
    ) -> int:
        """
        Post origination or application fee.

        Journal: LFEE
        ─────────────
        Dr  1105  Bank — Main Clearing
        Cr  4201  Loan Origination Fees   (or 4203 Application Fees)

        Args:
            fee_type: 'origination' (→ 4201) or 'application' (→ 4203)
        """
        move_date   = move_date or str(date.today())
        income_code = '4203' if fee_type == 'application' else '4201'
        label       = 'Application fee' if fee_type == 'application' else 'Origination fee'
        ref         = reference or f'FEE-{loan.loan_number}-{fee_type.upper()}-{move_date}'

        lines = [
            self._line(self._account_id('1105'), debit=amount,
                       name=f'{label} — {loan.loan_number}', partner_id=partner_id),
            self._line(self._account_id(income_code), credit=amount,
                       name=f'{label} income — {loan.loan_number}', partner_id=partner_id),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_FEES', 'LFEE'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            partner_id    = partner_id,
            narration     = f'{label} | Loan: {loan.loan_number} | Amount: {amount:.2f}',
        )

    # ── 7. post_ecl_provision ─────────────────────────────────────────────────

    def post_ecl_provision(
        self,
        loan_id: str,
        ecl_amount: float,
        stage: str,
        move_date: str | None = None,
        reference: str | None = None,
    ) -> int:
        """
        Post an IFRS 9 ECL provision journal entry (monthly batch).

        Journal: LPROV (Loan Loss Provision — Miscellaneous)
        ─────────────────────────────────────────────────────
        Dr  5101/5102/5103  Provision Expense — Stage X
        Cr  1201/1202/1203  Provision for Loan Losses — Stage X
        """
        move_date = move_date or str(date.today())
        ref       = reference or f'ECL-{loan_id}-S{stage}-{move_date}'

        exp_map  = {'1': '5101', '2': '5102', '3': '5103'}
        prov_map = {'1': '1201', '2': '1202', '3': '1203'}
        exp_code  = exp_map.get(str(stage), '5101')
        prov_code = prov_map.get(str(stage), '1201')

        lines = [
            self._line(self._account_id(exp_code),  debit=ecl_amount,
                       name=f'ECL provision S{stage} — {loan_id}'),
            self._line(self._account_id(prov_code), credit=ecl_amount,
                       name=f'Loan loss provision S{stage} — {loan_id}'),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_PROVISION', 'LPROV'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            narration     = f'IFRS9 ECL Provision | Loan: {loan_id} | Stage {stage} | Amount: {ecl_amount:.2f}',
        )

    # ── 8. post_writeoff ──────────────────────────────────────────────────────

    def post_writeoff(
        self,
        loan,
        amount: float,
        move_date: str | None = None,
        partner_id: int | None = None,
        reference: str | None = None,
    ) -> int:
        """
        Post a loan write-off journal entry (Section 8 mapping).

        Journal: LPROV
        ──────────────
        Dr  1204  Write-off Reserve        (draws down the provision already built)
        Cr  1113  Loan Receivable — Stage 3
        """
        move_date = move_date or str(date.today())
        ref       = reference or f'WO-{loan.loan_number}-{move_date}'

        lines = [
            self._line(self._account_id('1204'), debit=amount,
                       name=f'Write-off reserve — {loan.loan_number}', partner_id=partner_id),
            self._line(self._account_id('1113'), credit=amount,
                       name=f'Loan written off — {loan.loan_number}', partner_id=partner_id),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_PROVISION', 'LPROV'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            partner_id    = partner_id,
            narration     = f'Write-off | Loan: {loan.loan_number} | Amount: {amount:.2f}',
        )

    # ── 9. post_recovery ─────────────────────────────────────────────────────

    def post_recovery(
        self,
        loan,
        amount: float,
        move_date: str | None = None,
        partner_id: int | None = None,
        reference: str | None = None,
    ) -> int:
        """
        Post a cash recovery on a written-off loan.

        Journal: LRPY
        ─────────────
        Dr  1105  Bank — Main Clearing
        Cr  4302  Recovery on Written-off Loans
        """
        move_date = move_date or str(date.today())
        ref       = reference or f'REC-{loan.loan_number}-{move_date}'

        lines = [
            self._line(self._account_id('1105'), debit=amount,
                       name=f'Recovery — {loan.loan_number}', partner_id=partner_id),
            self._line(self._account_id('4302'), credit=amount,
                       name=f'Recovery income — {loan.loan_number}', partner_id=partner_id),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_REPAYMENT', 'LRPY'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            partner_id    = partner_id,
            narration     = f'Recovery | Loan: {loan.loan_number} | Amount: {amount:.2f}',
        )

    # ── 10. post_stage_transfer ───────────────────────────────────────────────

    def post_stage_transfer(
        self,
        loan,
        from_stage: str,
        to_stage: str,
        ecl_amount: float,
        move_date: str | None = None,
        reference: str | None = None,
    ) -> int:
        """
        Post an IFRS 9 stage transition provision entry (Section 8 mapping).

        S1 → S2:  Dr 5102 Provision Exp S2 / Cr 1202 Provision S2
        S2 → S3:  Dr 5103 Provision Exp S3 / Cr 1203 Provision S3
        S3 → S2:  Dr 1203 Provision S3    / Cr 5103 Provision Exp S3  (cure reversal)
        S2 → S1:  Dr 1202 Provision S2    / Cr 5102 Provision Exp S2  (cure reversal)

        Journal: LPROV
        """
        move_date = move_date or str(date.today())
        ref       = reference or f'STG-{loan.loan_number}-S{from_stage}S{to_stage}-{move_date}'

        stage_map = {
            ('1', '2'): ('5102', '1202'),
            ('2', '3'): ('5103', '1203'),
            ('3', '2'): ('1203', '5103'),  # cure — reverse the S3 provision
            ('2', '1'): ('1202', '5102'),  # cure — reverse the S2 provision
        }
        key = (str(from_stage), str(to_stage))
        if key not in stage_map:
            raise OdooPostingError(
                f'Unsupported stage transition: S{from_stage} → S{to_stage}. '
                f'Supported: {list(stage_map.keys())}'
            )
        debit_code, credit_code = stage_map[key]
        label = f'Stage {from_stage}→{to_stage}'

        lines = [
            self._line(self._account_id(debit_code), debit=ecl_amount,
                       name=f'{label} ECL — {loan.loan_number}'),
            self._line(self._account_id(credit_code), credit=ecl_amount,
                       name=f'{label} provision — {loan.loan_number}'),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_PROVISION', 'LPROV'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            narration     = (
                f'IFRS9 Stage Transfer | Loan: {loan.loan_number} | '
                f'S{from_stage}→S{to_stage} | ECL: {ecl_amount:.2f}'
            ),
        )

    # ── 11. post_insurance_premium ────────────────────────────────────────────

    def post_insurance_premium(
        self,
        loan,
        amount: float,
        move_date: str | None = None,
        partner_id: int | None = None,
        reference: str | None = None,
    ) -> int:
        """
        Post a credit life insurance premium collection (Section 8 mapping).

        Journal: LFEE
        ─────────────
        Dr  1105  Bank — Main Clearing
        Cr  4204  Insurance Premium Income
        """
        move_date = move_date or str(date.today())
        ref       = reference or f'INS-{loan.loan_number}-{move_date}'

        lines = [
            self._line(self._account_id('1105'), debit=amount,
                       name=f'Insurance premium — {loan.loan_number}', partner_id=partner_id),
            self._line(self._account_id('4204'), credit=amount,
                       name=f'Credit life insurance — {loan.loan_number}', partner_id=partner_id),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_FEES', 'LFEE'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            partner_id    = partner_id,
            narration     = f'Insurance Premium | Loan: {loan.loan_number} | Amount: {amount:.2f}',
        )

    # ── 12. post_momo_levy ────────────────────────────────────────────────────

    def post_momo_levy(
        self,
        loan,
        levy_amount: float,
        float_account: str = '1102',
        move_date: str | None = None,
        reference: str | None = None,
    ) -> int:
        """
        Post the Mobile Money Transaction Levy (Act No. 25 of 2024, Section 8 mapping).

        Journal: LFEE
        ─────────────
        Dr  2109  Mobile Money Levy Payable
        Cr  1102  MTN MoMo Float  (or 1103 Airtel Float — pass float_account)

        Args:
            float_account: '1102' (MTN) or '1103' (Airtel) or '1104' (Zamtel)
        """
        move_date = move_date or str(date.today())
        ref       = reference or f'LEVY-{loan.loan_number}-{move_date}'

        lines = [
            self._line(self._account_id('2109'), debit=levy_amount,
                       name=f'MoMo Levy payable — {loan.loan_number}'),
            self._line(self._account_id(float_account), credit=levy_amount,
                       name=f'MoMo float deducted — {loan.loan_number}'),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_FEES', 'LFEE'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            narration     = (
                f'MoMo Levy Act 25/2024 | Loan: {loan.loan_number} | '
                f'Float: {float_account} | Amount: {levy_amount:.2f}'
            ),
        )

    # ── 13. post_vat_on_fees ──────────────────────────────────────────────────

    def post_vat_on_fees(
        self,
        loan,
        fee_amount: float,
        fee_account: str = '4201',
        move_date: str | None = None,
        partner_id: int | None = None,
        reference: str | None = None,
        vat_rate: float = 0.16,
    ) -> int:
        """
        Post ZRA VAT (16%) on fee income (Section 8 mapping).

        Journal: LFEE
        ─────────────
        Dr  2105  VAT Payable (ZRA)
        Cr  4201  Loan Origination Fees  (or 4202 Penalty — pass fee_account)

        The VAT amount is calculated as fee_amount * vat_rate.

        Args:
            fee_account: '4201' (origination) or '4202' (penalty)
            vat_rate:    0.16 (ZRA standard rate)
        """
        vat_amount = round(fee_amount * vat_rate, 2)
        move_date  = move_date or str(date.today())
        ref        = reference or f'VAT-{loan.loan_number}-{fee_account}-{move_date}'

        lines = [
            self._line(self._account_id('2105'), debit=vat_amount,
                       name=f'VAT payable (ZRA) — {loan.loan_number}', partner_id=partner_id),
            self._line(self._account_id(fee_account), credit=vat_amount,
                       name=f'VAT on fee income — {loan.loan_number}', partner_id=partner_id),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_FEES', 'LFEE'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            partner_id    = partner_id,
            narration     = (
                f'ZRA VAT {int(vat_rate*100)}% | Loan: {loan.loan_number} | '
                f'Fee account: {fee_account} | VAT: {vat_amount:.2f}'
            ),
        )

    # ── 14. post_interest_accrual ─────────────────────────────────────────────

    def post_interest_accrual(
        self,
        loan,
        accrual_amount: float,
        period: str,
        ifrs9_stage: str = '1',
        move_date: str | None = None,
        reference: str | None = None,
    ) -> int:
        """
        Post a month-end interest accrual journal entry (Section 8 mapping).

        Journal: LINT
        ─────────────
        Dr  1120  Interest Receivable
        Cr  4101  Interest Income — Stage 1  (or 4102/4103 based on stage)

        Args:
            period:      YYYY-MM string identifying the accrual period
            ifrs9_stage: '1', '2', or '3'
        """
        move_date = move_date or str(date.today())
        ref       = reference or f'ACC-{loan.loan_number}-{period}'

        inc_map   = {'1': '4101', '2': '4102', '3': '4103'}
        inc_code  = inc_map.get(str(ifrs9_stage), '4101')

        lines = [
            self._line(self._account_id('1120'), debit=accrual_amount,
                       name=f'Interest accrual {period} — {loan.loan_number}'),
            self._line(self._account_id(inc_code), credit=accrual_amount,
                       name=f'Interest income S{ifrs9_stage} {period} — {loan.loan_number}'),
        ]
        return self._post_move(
            journal_code  = os.getenv('ODOO_JOURNAL_INTEREST', 'LINT'),
            lms_reference = ref,
            move_date     = move_date,
            lines         = lines,
            narration     = (
                f'Interest Accrual | Loan: {loan.loan_number} | '
                f'Period: {period} | Stage {ifrs9_stage} | Amount: {accrual_amount:.2f}'
            ),
        )

    # ── 15. debug_journal_lines ───────────────────────────────────────────────

    def debug_journal_lines(self, lines: list[tuple], label: str = '') -> dict:
        """
        Debug a set of account.move line tuples BEFORE posting.

        Checks for balance, prints each line's debit/credit, and flags
        the most common causes of 'Journal Entry is not balanced' errors.

        Args:
            lines: List of (0, 0, vals) tuples as returned by _line()
            label: Optional description for the output header

        Returns:
            dict with keys: balanced (bool), total_debit, total_credit,
            diff, issues (list of str), lines (list of dicts)

        Usage:
            lines = [
                self._line(self._account_id('1111'), debit=1000),
                self._line(self._account_id('1105'), credit=999),  # imbalanced!
            ]
            result = client.debug_journal_lines(lines, label='Disbursement test')
            if not result['balanced']:
                print(result['issues'])
        """
        total_debit  = 0.0
        total_credit = 0.0
        parsed       = []
        issues       = []

        header = f'  ─── Journal Line Debug: {label or "unnamed"} ───'
        _logger.info(header)
        print(header)

        for i, entry in enumerate(lines):
            if not (isinstance(entry, (list, tuple)) and len(entry) == 3):
                issues.append(f'Line {i}: invalid ORM tuple structure (expected (0, 0, {{vals}}))')
                continue

            vals = entry[2]
            if not isinstance(vals, dict):
                issues.append(f'Line {i}: vals is not a dict')
                continue

            debit  = round(float(vals.get('debit',  0) or 0), 2)
            credit = round(float(vals.get('credit', 0) or 0), 2)
            acc_id = vals.get('account_id', '?')
            name   = vals.get('name', '')

            total_debit  += debit
            total_credit += credit

            row = {'line': i, 'account_id': acc_id, 'name': name,
                   'debit': debit, 'credit': credit}
            parsed.append(row)

            line_str = (
                f'  [{i:02d}] account={acc_id:<6}  '
                f'Dr {debit:>12.2f}  Cr {credit:>12.2f}  "{name}"'
            )
            _logger.info(line_str)
            print(line_str)

            # Per-line checks
            if debit > 0 and credit > 0:
                issues.append(
                    f'Line {i} ("{name}"): both debit and credit are non-zero — '
                    f'a line must have only one side populated.'
                )
            if debit == 0 and credit == 0:
                issues.append(
                    f'Line {i} ("{name}"): both debit and credit are zero — '
                    f'line will be ignored by Odoo.'
                )
            if not acc_id or acc_id == '?':
                issues.append(
                    f'Line {i} ("{name}"): missing account_id — '
                    f'call _account_id() before building the line.'
                )

        diff      = round(abs(total_debit - total_credit), 2)
        balanced  = diff == 0.0

        summary = (
            f'  TOTAL  Dr {total_debit:>12.2f}  Cr {total_credit:>12.2f}  '
            f'diff={diff:.2f}  balanced={balanced}'
        )
        _logger.info(summary)
        print(summary)

        if not balanced:
            issues.append(
                f'Entry is UNBALANCED by {diff:.2f} ZMW. '
                f'Common causes: rounding (use round(x,2) on every amount), '
                f'fee/tax split not included in all legs, '
                f'currency conversion applied to only one side.'
            )
            print(f'  ⚠ IMBALANCED by {diff:.2f}')
        else:
            print('  ✓ Balanced')

        if issues:
            print('  Issues found:')
            for issue in issues:
                print(f'    - {issue}')

        return {
            'balanced':     balanced,
            'total_debit':  round(total_debit, 2),
            'total_credit': round(total_credit, 2),
            'diff':         diff,
            'issues':       issues,
            'lines':        parsed,
        }

    # ── 16. ping (health check) ───────────────────────────────────────────────

    def ping(self) -> dict:
        """
        Test the Odoo connection and return version info.

        Returns:
            dict with keys: server_version, server_version_info, etc.
            Empty dict if ODOO_ENABLED=false.
        """
        if not self.enabled:
            return {'status': 'disabled', 'message': 'ODOO_ENABLED=false'}
        try:
            info = self._common.version()
            self.authenticate()
            info['auth_status'] = 'ok'
            info['uid'] = self._uid
            _logger.info('Odoo ping OK: %s', info.get('server_version'))
            return info
        except Exception as exc:
            _logger.error('Odoo ping failed: %s', exc)
            return {'status': 'error', 'message': str(exc)}

    def __repr__(self):
        status = f'uid={self._uid}' if self._uid else 'unauthenticated'
        return f'OdooLMSClient(url={self.url!r}, db={self.db!r}, {status})'


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton (import and use directly)
# ─────────────────────────────────────────────────────────────────────────────

_client_instance: OdooLMSClient | None = None


def get_odoo_client() -> OdooLMSClient:
    """
    Return the module-level singleton OdooLMSClient.
    Creates it on first call. Safe to call repeatedly.

    Usage:
        from apps.accounting.odoo_client import get_odoo_client
        client = get_odoo_client()
        client.post_disbursement(loan)
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = OdooLMSClient()
    return _client_instance
