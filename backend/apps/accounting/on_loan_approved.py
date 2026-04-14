# -*- coding: utf-8 -*-
"""
on_loan_approved.py
===================
Event hook called by DisburseLoanView immediately after a loan transitions
to ACTIVE status.  "Approved" in this context means approved-for-disbursement
— the financial event that warrants posting to Odoo.

Responsibilities
----------------
1. Sync the borrower → Odoo res.partner (get_or_create by NRC / phone / LMS ref).
2. Post the disbursement journal entry to Odoo (Dr 1111 / Cr 1105).
3. Store the returned Odoo IDs back on the Loan record so they are available
   to later hooks (on_payment_received, on_repayment_due).

Error policy
------------
All Odoo errors are caught and logged as ERROR.  They do NOT propagate back
to the caller — the LMS disbursement is already committed in the DB and must
not be rolled back because Odoo is temporarily unavailable.
"""

from __future__ import annotations

import logging

from apps.accounting.odoo_client import (
    OdooConnectionError,
    OdooDuplicateError,
    OdooPostingError,
    get_odoo_client,
)

# ZRA VAT rate — update if rate changes
_VAT_RATE = 0.16

_logger = logging.getLogger(__name__)


def on_loan_disbursed(loan) -> None:
    """
    Called synchronously inside DisburseLoanView after the DB transaction
    for the disbursement has been committed.

    Args:
        loan: apps.loans.models.Loan instance (status already set to ACTIVE,
              disbursement_date and maturity_date already populated).

    Side-effects:
        - Sets loan.odoo_partner_id
        - Sets loan.odoo_disbursement_move_id
        - Saves those two fields back to the database.
        - Logs success or failure at INFO / ERROR level.
    """
    client = get_odoo_client()

    if not client.enabled:
        _logger.info(
            '[Odoo disabled] Skipping disbursement sync for loan %s.',
            loan.loan_number,
        )
        return

    # ── Step 1: Sync borrower → Odoo res.partner ──────────────────────────────
    partner_id: int | None = None
    try:
        partner_id = client.sync_borrower(loan.client)
        _logger.info(
            'Borrower synced: loan=%s client=%s odoo_partner_id=%s',
            loan.loan_number, loan.client.id, partner_id,
        )
    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error(
            'Odoo sync_borrower failed for loan %s (client %s): %s',
            loan.loan_number, loan.client.id, exc,
        )
        # Continue — we can still try to post the disbursement without a partner link.

    # ── Step 2: Post disbursement journal entry ────────────────────────────────
    move_id: int | None = None
    try:
        move_id = client.post_disbursement(loan, partner_id=partner_id)
        _logger.info(
            'Disbursement posted to Odoo: loan=%s move_id=%s',
            loan.loan_number, move_id,
        )
    except OdooDuplicateError:
        # Already posted on a previous attempt — find the existing move_id.
        _logger.warning(
            'Disbursement already posted in Odoo for loan %s. Fetching existing move_id.',
            loan.loan_number,
        )
        try:
            ref = f'DISB-{loan.loan_number}-{loan.disbursement_date}'
            records = client._search_read(
                'account.move',
                [['ref', '=', ref], ['state', '=', 'posted']],
                ['id'],
                limit=1,
            )
            move_id = records[0]['id'] if records else None
        except Exception as lookup_exc:
            _logger.error(
                'Could not retrieve existing Odoo move for loan %s: %s',
                loan.loan_number, lookup_exc,
            )
    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error(
            'Odoo post_disbursement failed for loan %s: %s',
            loan.loan_number, exc,
        )

    # ── Step 3: Post origination fee (processing_fee % of principal) ──────────
    processing_fee_rate = float(getattr(loan.product, 'processing_fee', 0) or 0)
    if processing_fee_rate > 0:
        fee_amount = round(float(loan.amount) * processing_fee_rate / 100, 2)
        try:
            client.post_origination_fee(
                loan=loan, amount=fee_amount, fee_type='origination',
                partner_id=partner_id,
            )
            _logger.info('Origination fee posted: loan=%s fee=%.2f', loan.loan_number, fee_amount)
            # Post VAT on origination fee
            client.post_vat_on_fees(
                loan=loan, fee_amount=fee_amount, fee_account='4201',
                partner_id=partner_id, vat_rate=_VAT_RATE,
            )
        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.error('Odoo origination fee failed for loan %s: %s', loan.loan_number, exc)

    # ── Step 4: Persist Odoo IDs on the loan record ───────────────────────────
    if partner_id is not None or move_id is not None:
        update_fields = []
        if partner_id is not None:
            loan.odoo_partner_id = partner_id
            update_fields.append('odoo_partner_id')
        if move_id is not None:
            loan.odoo_disbursement_move_id = move_id
            update_fields.append('odoo_disbursement_move_id')
        try:
            loan.save(update_fields=update_fields)
            _logger.info(
                'Loan %s updated with Odoo IDs: partner=%s move=%s',
                loan.loan_number, partner_id, move_id,
            )
        except Exception as save_exc:
            _logger.error(
                'Failed to save Odoo IDs on loan %s: %s',
                loan.loan_number, save_exc,
            )
