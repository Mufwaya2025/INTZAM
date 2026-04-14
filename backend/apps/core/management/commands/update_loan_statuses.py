# -*- coding: utf-8 -*-
"""
update_loan_statuses
====================
Daily management command that:
  1. Recalculates days_overdue for all ACTIVE/OVERDUE loans.
  2. Marks loans as OVERDUE when past maturity.
  3. Detects IFRS 9 stage transitions and posts the provision entry to Odoo.

Run daily:
    python manage.py update_loan_statuses
    python manage.py update_loan_statuses --dry-run

Cron (daily at 01:00 CAT):
    0 1 * * * /home/mufwaya/lms-venv/bin/python /mnt/f/LMS/backend/manage.py \
        update_loan_statuses >> /var/log/lms/loan_status_update.log 2>&1
"""

from datetime import date

from django.core.management.base import BaseCommand

from apps.accounting.on_loan_stage_changed import on_stage_changed, _ifrs9_stage
from apps.loans.models import Loan, LoanStatus


class Command(BaseCommand):
    help = 'Recalculate days_overdue, update OVERDUE status, post IFRS 9 stage transitions to Odoo'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Compute changes but do not save or post to Odoo')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today   = date.today()

        qs = Loan.objects.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]
        )

        total = qs.count()
        updated = stage_changes = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n  update_loan_statuses  [{"DRY RUN" if dry_run else "LIVE"}]  {today}'
        ))
        self.stdout.write(f'  Processing {total} loan(s)...\n')

        for loan in qs:
            if not loan.maturity_date:
                continue

            # ── 1. Compute days overdue ────────────────────────────────────
            delta = (today - loan.maturity_date).days
            new_days_overdue = max(0, delta)
            old_stage = _ifrs9_stage(loan.days_overdue or 0)
            new_stage = _ifrs9_stage(new_days_overdue)

            # ── 2. Update status ───────────────────────────────────────────
            new_status = loan.status
            if new_days_overdue > 0 and loan.status == LoanStatus.ACTIVE:
                new_status = LoanStatus.OVERDUE

            if dry_run:
                if old_stage != new_stage or new_days_overdue != (loan.days_overdue or 0):
                    self.stdout.write(
                        f'  [DRY]  {loan.loan_number}  days_overdue {loan.days_overdue}→{new_days_overdue}'
                        f'  stage S{old_stage}→S{new_stage}  status {loan.status}→{new_status}'
                    )
                continue

            # ── 3. Save ────────────────────────────────────────────────────
            changed = False
            if new_days_overdue != (loan.days_overdue or 0):
                loan.days_overdue = new_days_overdue
                changed = True
            if new_status != loan.status:
                loan.status = new_status
                changed = True
            if changed:
                loan.save(update_fields=['days_overdue', 'status'])
                updated += 1

            # ── 4. Post stage transition to Odoo ──────────────────────────
            if old_stage != new_stage:
                on_stage_changed(loan, from_stage=old_stage, to_stage=new_stage)
                stage_changes += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  [STAGE] {loan.loan_number}  S{old_stage}→S{new_stage}'
                    f'  days_overdue={new_days_overdue}'
                ))

        self.stdout.write(
            f'\n  Done.  loans_updated={updated}  stage_transitions={stage_changes}  total={total}\n'
        )
