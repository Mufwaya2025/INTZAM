# -*- coding: utf-8 -*-
"""
poll_konse_transactions.py
==========================
Django management command that polls the Konse Konse gateway for the status
of all PENDING KonseTransaction records and triggers the appropriate
accounting event handlers.

Purpose
-------
The Konse Konse platform notifies the LMS via webhook for most events, but
webhooks can be missed due to:
  - Network timeouts during delivery
  - Temporary LMS downtime
  - Konse Konse gateway retries exhausted

This command acts as a safety net, resolving PENDING transactions by polling
the KK REST API directly.

Scheduling recommendation
-------------------------
Run via cron every minute — the command itself processes all PENDING rows,
so running it twice per minute effectively achieves a ~30-second polling
interval without needing a persistent process:

    # /etc/cron.d/lms-konse-poll
    * * * * * lms-user cd /mnt/f/LMS/backend && /home/mufwaya/lms-venv/bin/python manage.py poll_konse_transactions >> /var/log/lms/konse_poll.log 2>&1

Usage
-----
    python manage.py poll_konse_transactions
    python manage.py poll_konse_transactions --dry-run
    python manage.py poll_konse_transactions --limit 50

Flags
-----
--dry-run   Print which transactions would be processed but do not call
            the KK API or update any records.
--limit N   Maximum number of PENDING transactions to process per run
            (default: 100).
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.loans.models import (
    KonseTransaction,
    KonseTransactionStatus,
    KonseTransactionType,
)

_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Poll Konse Konse gateway for PENDING transaction statuses and '
        'trigger accounting event handlers for confirmed/failed transactions.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Simulate polling without calling KK API or updating records.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of PENDING transactions to poll per run (default: 100).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit   = options['limit']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] No records will be updated.\n'))

        # ── Load KK client lazily to avoid import errors if not configured ──────
        try:
            from apps.accounting.konse_konse_client import (
                KonseKonseClient,
                KonseConnectionError,
                KonseAPIError,
                KonseAuthError,
            )
            from apps.accounting import konse_events
        except ImportError as exc:
            raise CommandError(f'Could not import KK modules: {exc}') from exc

        # ── Query PENDING transactions ─────────────────────────────────────────
        pending_qs = (
            KonseTransaction.objects
            .filter(status=KonseTransactionStatus.PENDING)
            .select_related('loan', 'loan__client', 'loan__product')
            .order_by('created_at')
            [:limit]
        )

        pending_count = pending_qs.count()
        self.stdout.write(
            f'Found {pending_count} PENDING KonseTransaction(s) '
            f'(limit={limit}, dry_run={dry_run}).\n'
        )

        if pending_count == 0:
            self.stdout.write(self.style.SUCCESS('Nothing to do.\n'))
            return

        if dry_run:
            for txn in pending_qs:
                self.stdout.write(
                    f'  [DRY RUN] Would poll: ref={txn.transaction_reference} '
                    f'type={txn.transaction_type} loan={txn.loan_id} '
                    f'amount={txn.amount} created={txn.created_at:%Y-%m-%d %H:%M}\n'
                )
            self.stdout.write(self.style.WARNING(
                f'\n[DRY RUN] {pending_count} transaction(s) listed — no changes made.\n'
            ))
            return

        # ── Initialise KK client ───────────────────────────────────────────────
        try:
            kk_client = KonseKonseClient()
        except KonseAuthError as exc:
            raise CommandError(f'Cannot initialise KK client: {exc}') from exc

        # ── Process each PENDING transaction ──────────────────────────────────
        confirmed_count = 0
        failed_count    = 0
        error_count     = 0

        for txn in pending_qs:
            ref  = txn.transaction_reference
            loan = txn.loan

            self.stdout.write(
                f'  Polling ref={ref} type={txn.transaction_type} '
                f'loan={getattr(loan, "loan_number", "None")} ...',
                ending='',
            )

            try:
                result = kk_client.get_transaction_status(ref)
            except KonseConnectionError as exc:
                self.stdout.write(self.style.ERROR(f' CONNECTION ERROR: {exc}\n'))
                error_count += 1
                _logger.error('poll_konse_transactions: connection error for ref %s: %s', ref, exc)
                continue
            except (KonseAPIError, KonseAuthError) as exc:
                self.stdout.write(self.style.ERROR(f' API ERROR: {exc}\n'))
                error_count += 1
                _logger.error('poll_konse_transactions: API error for ref %s: %s', ref, exc)
                continue

            kk_status = result.get('status', '')

            if kk_status == KonseTransactionStatus.CONFIRMED:
                # Route to appropriate handler
                move_id = None
                if loan is not None:
                    try:
                        if txn.transaction_type == KonseTransactionType.DISBURSEMENT:
                            move_id = konse_events.handle_disbursement_confirmed(
                                kk_ref=ref,
                                loan=loan,
                                amount=float(txn.amount),
                            )
                        elif txn.transaction_type == KonseTransactionType.REPAYMENT:
                            move_id = konse_events.handle_repayment_received(
                                kk_ref=ref,
                                loan=loan,
                                amount=float(txn.amount),
                            )
                        elif txn.transaction_type == KonseTransactionType.FEE:
                            raw    = txn.konse_raw_payload or {}
                            fee_tp = raw.get('feeType', raw.get('fee_type', 'origination')).lower()
                            move_id = konse_events.handle_fee_collected(
                                kk_ref=ref,
                                loan=loan,
                                amount=float(txn.amount),
                                fee_type=fee_tp,
                            )
                        elif txn.transaction_type == KonseTransactionType.AGENT_COLLECTION:
                            raw        = txn.konse_raw_payload or {}
                            agent_code = raw.get('agentCode', raw.get('agent_code', ''))
                            move_id = konse_events.handle_agent_collection(
                                kk_ref=ref,
                                loan=loan,
                                amount=float(txn.amount),
                                agent_code=agent_code,
                            )
                    except Exception as exc:
                        _logger.error(
                            'poll_konse_transactions: event handler error for ref %s: %s',
                            ref, exc,
                        )
                        error_count += 1
                        self.stdout.write(self.style.ERROR(f' HANDLER ERROR: {exc}\n'))
                        continue

                txn.status       = KonseTransactionStatus.CONFIRMED
                txn.odoo_move_id = move_id
                txn.processed_at = timezone.now()
                txn.save(update_fields=['status', 'odoo_move_id', 'processed_at', 'updated_at'])

                confirmed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f' CONFIRMED (move_id={move_id})\n')
                )

            elif kk_status == KonseTransactionStatus.FAILED:
                txn.status       = KonseTransactionStatus.FAILED
                txn.processed_at = timezone.now()
                txn.save(update_fields=['status', 'processed_at', 'updated_at'])

                failed_count += 1
                self.stdout.write(self.style.ERROR(' FAILED\n'))
                _logger.warning('poll_konse_transactions: ref %s marked FAILED by KK.', ref)

            else:
                # Still PENDING or REVERSED — leave as-is
                self.stdout.write(f' still {kk_status}\n')

        # ── Summary ────────────────────────────────────────────────────────────
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone: {confirmed_count} confirmed, '
                f'{failed_count} failed, '
                f'{error_count} errors '
                f'(of {pending_count} polled).\n'
            )
        )
