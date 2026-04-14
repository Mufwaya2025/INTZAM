# -*- coding: utf-8 -*-
"""
on_loan_written_off.py
======================
Event hooks for write-off and post-write-off cash recovery events.

Section 8 mapping
-----------------
Write-off:  Dr 1204 Write-off Reserve / Cr 1113 Loan Rec S3
Recovery:   Dr 1105 Bank             / Cr 4302 Recovery Income

Error policy
------------
Odoo errors are caught and logged. They do NOT propagate — the LMS
database transaction is already committed.
"""

from __future__ import annotations

import logging

from apps.accounting.odoo_client import (
    OdooConnectionError,
    OdooDuplicateError,
    OdooPostingError,
    get_odoo_client,
)

_logger = logging.getLogger(__name__)


def on_loan_written_off(loan, amount: float | None = None) -> int | None:
    """
    Post a write-off journal entry to Odoo.

    Called from WriteOffLoanView after the loan status is set to WRITTEN_OFF
    and the Transaction record is committed.

    Args:
        loan:   Loan instance (status already WRITTEN_OFF).
        amount: Write-off amount. Defaults to outstanding balance
                (total_repayable - repaid_amount).

    Returns:
        int: Odoo account.move id, or None on failure / disabled.
    """
    client = get_odoo_client()

    if not client.enabled:
        _logger.info('[Odoo disabled] Skipping write-off sync for loan %s.', loan.loan_number)
        return None

    if amount is None:
        amount = float(loan.total_repayable) - float(loan.repaid_amount)

    if amount <= 0:
        _logger.info('Write-off amount is zero for loan %s — skipping.', loan.loan_number)
        return None

    # Resolve partner
    partner_id: int | None = getattr(loan, 'odoo_partner_id', None)
    if partner_id is None:
        try:
            partner_id = client.sync_borrower(loan.client)
        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.warning('Could not sync borrower for write-off loan %s: %s', loan.loan_number, exc)

    try:
        move_id = client.post_writeoff(loan=loan, amount=amount, partner_id=partner_id)
        _logger.info('Write-off posted to Odoo: loan=%s amount=%.2f move_id=%s',
                     loan.loan_number, amount, move_id)
        return move_id
    except OdooDuplicateError:
        _logger.warning('Write-off already posted in Odoo for loan %s. Skipping.', loan.loan_number)
        return None
    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error('Odoo post_writeoff failed for loan %s: %s', loan.loan_number, exc)
        return None


def on_recovery_received(
    loan,
    amount: float,
    move_date: str | None = None,
    transaction_reference: str | None = None,
) -> int | None:
    """
    Post a cash recovery entry to Odoo when payment is received on a
    written-off loan.

    Called from RecoveryView after the Transaction record is committed.

    Args:
        loan:                  Loan instance (status WRITTEN_OFF).
        amount:                Cash amount recovered.
        move_date:             ISO date string; defaults to today.
        transaction_reference: Optional LMS transaction id for idempotency.

    Returns:
        int: Odoo account.move id, or None on failure / disabled.
    """
    client = get_odoo_client()

    if not client.enabled:
        _logger.info('[Odoo disabled] Skipping recovery sync for loan %s.', loan.loan_number)
        return None

    partner_id: int | None = getattr(loan, 'odoo_partner_id', None)
    if partner_id is None:
        try:
            partner_id = client.sync_borrower(loan.client)
        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.warning('Could not sync borrower for recovery loan %s: %s', loan.loan_number, exc)

    from datetime import date as _date
    ref = None
    if transaction_reference:
        ref = f'REC-{loan.loan_number}-{transaction_reference}'

    try:
        move_id = client.post_recovery(
            loan=loan, amount=amount,
            move_date=move_date or str(_date.today()),
            partner_id=partner_id, reference=ref,
        )
        _logger.info('Recovery posted to Odoo: loan=%s amount=%.2f move_id=%s',
                     loan.loan_number, amount, move_id)
        return move_id
    except OdooDuplicateError:
        _logger.warning('Recovery entry already posted in Odoo for loan %s. Skipping.', loan.loan_number)
        return None
    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error('Odoo post_recovery failed for loan %s: %s', loan.loan_number, exc)
        return None
