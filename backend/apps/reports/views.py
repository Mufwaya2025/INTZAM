from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from apps.authentication.permission_utils import user_has_permission
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import date, timedelta
from apps.loans.models import Loan, Transaction, LoanStatus, TransactionType
from apps.core.models import Client, LoanProduct


def loan_outstanding(loan):
    return max(float(loan.total_repayable) - float(loan.repaid_amount), 0.0)


def loan_expected_interest(loan):
    return max(float(loan.total_repayable) - float(loan.amount), 0.0)


def loan_interest_ratio(loan):
    total_repayable = float(loan.total_repayable)
    return loan_expected_interest(loan) / total_repayable if total_repayable else 0.0


def loan_interest_component(loan, amount):
    return round(float(amount) * loan_interest_ratio(loan), 2)


class ReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, report_type):
        if not user_has_permission(request.user, f'report:{report_type}'):
            return Response({'error': 'You do not have permission to view this report.'}, status=403)
        today = date.today()
        handlers = {
            'disbursement-register': self.disbursement_register,
            'active-loan-portfolio': self.active_loan_portfolio,
            'aging-par-report': self.aging_par_report,
            'income-statement': self.income_statement,
            'daily-cash-flow': self.daily_cash_flow,
            'daily-recovery-manifest': self.daily_recovery_manifest,
            'expected-collection': self.expected_collection,
            'ptp-performance': self.ptp_performance,
            'master-loan-tape': self.master_loan_tape,
            'vintage-analysis': self.vintage_analysis,
            'ifrs9-expected-loss': self.ifrs9_expected_loss,
            'write-off-register': self.write_off_register,
        }
        handler = handlers.get(report_type)
        if not handler:
            return Response({'error': f'Unknown report type: {report_type}'}, status=404)
        return Response(handler(request, today))

    def disbursement_register(self, request, today):
        def ifrs9_stage(days):
            if days <= 29: return 1
            if days <= 90: return 2
            return 3

        def loan_classification(days):
            if days == 0:   return 'Pass'
            if days <= 30:  return 'Watch'
            if days <= 90:  return 'Substandard'
            if days <= 180: return 'Doubtful'
            return 'Loss'

        def age_group(dob):
            if not dob:
                return 'Unknown'
            age = (today - dob).days // 365
            return 'Adult' if age > 35 else 'Youth'

        disbursable = [
            LoanStatus.ACTIVE, LoanStatus.OVERDUE,
            LoanStatus.CLOSED, LoanStatus.WRITTEN_OFF,
        ]
        status_filter = request.query_params.get('status')
        qs = Loan.objects.filter(
            status__in=[status_filter] if status_filter else disbursable
        ).select_related('client', 'product').order_by('disbursement_date')

        data = []
        total_disbursed = total_outstanding = total_expected_interest = par30_amount = 0.0
        par30_count = 0

        for i, loan in enumerate(qs, start=1):
            outstanding = loan_outstanding(loan)
            expected_interest = loan_expected_interest(loan)
            days = loan.days_overdue
            monthly_income = float(loan.client.monthly_income)
            dti = round(float(loan.monthly_payment) / monthly_income * 100, 1) if monthly_income else None
            # loan cycle = completed loans + 1 if still active/overdue, else completed count
            loan_cycle = loan.client.completed_loans + (
                1 if loan.status in [LoanStatus.ACTIVE, LoanStatus.OVERDUE] else 0
            )

            total_disbursed  += float(loan.amount)
            total_outstanding += outstanding
            total_expected_interest += expected_interest
            if days > 30:
                par30_count  += 1
                par30_amount += outstanding

            data.append({
                'no':                    i,
                'loan_number':           loan.loan_number,
                'client_name':           loan.client.name,
                'client_nrc':            loan.client.nrc_number or '',
                'client_phone':          loan.client.phone,
                'gender':                loan.client.gender or '',
                'age_group':             age_group(loan.client.date_of_birth),
                'employment_status':     loan.client.employment_status.replace('_', ' ').title(),
                'monthly_income':        float(loan.client.monthly_income),
                'loan_cycle':            loan_cycle,
                'client_tier':           loan.client.tier,
                'product':               loan.product.name,
                'interest_type':         loan.product.interest_type,
                'repayment_frequency':   loan.product.repayment_frequency,
                'purpose':               loan.purpose,
                'disbursed_amount':      float(loan.amount),
                'total_repayable':       float(loan.total_repayable),
                'expected_interest':     round(expected_interest, 2),
                'monthly_payment':       float(loan.monthly_payment),
                'term_months':           loan.term_months,
                'interest_rate':         float(loan.interest_rate),
                'disbursement_date':     str(loan.disbursement_date) if loan.disbursement_date else '',
                'maturity_date':         str(loan.maturity_date) if loan.maturity_date else '',
                'repaid_amount':         float(loan.repaid_amount),
                'outstanding_balance':   round(outstanding, 2),
                'days_overdue':          days,
                'approved_by':           loan.approved_by,
                'rollover_count':        loan.rollover_count,
                'status':                loan.status,
                'loan_classification':   loan_classification(days),
                'ifrs9_stage':           ifrs9_stage(days),
                'par_flag':              days > 30,
                'dti_ratio':             dti,
            })

        par30_ratio = round(par30_amount / total_outstanding * 100, 1) if total_outstanding else 0.0

        return {
            'report': 'Disbursement Register',
            'summary': {
                'total_loans':      len(data),
                'total_disbursed':  round(total_disbursed, 2),
                'total_expected_interest': round(total_expected_interest, 2),
                'total_outstanding': round(total_outstanding, 2),
                'par30_count':      par30_count,
                'par30_amount':     round(par30_amount, 2),
                'par30_ratio':      par30_ratio,
            },
            'data': data,
            'generated_at': str(today),
        }

    def active_loan_portfolio(self, request, today):
        loans = Loan.objects.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]
        ).select_related('product')
        by_product_map = {}
        total_disbursed = total_outstanding = total_expected_interest = 0.0

        for loan in loans:
            product_name = loan.product.name
            outstanding = loan_outstanding(loan)
            expected_interest = loan_expected_interest(loan)
            total_disbursed += float(loan.amount)
            total_outstanding += outstanding
            total_expected_interest += expected_interest

            if product_name not in by_product_map:
                by_product_map[product_name] = {
                    'product': product_name,
                    'count': 0,
                    'total_disbursed': 0.0,
                    'expected_interest': 0.0,
                    'total_outstanding': 0.0,
                }
            row = by_product_map[product_name]
            row['count'] += 1
            row['total_disbursed'] += float(loan.amount)
            row['expected_interest'] += expected_interest
            row['total_outstanding'] += outstanding

        return {
            'report': 'Active Loan Portfolio',
            'summary': {
                'total_loans': loans.count(),
                'total_disbursed': round(total_disbursed, 2),
                'total_expected_interest': round(total_expected_interest, 2),
                'total_outstanding': round(total_outstanding, 2),
            },
            'by_product': [
                {
                    **row,
                    'total_disbursed': round(row['total_disbursed'], 2),
                    'expected_interest': round(row['expected_interest'], 2),
                    'total_outstanding': round(row['total_outstanding'], 2),
                }
                for row in by_product_map.values()
            ],
            'generated_at': str(today)
        }

    def aging_par_report(self, request, today):
        BUCKETS = [
            ('current',    0,    0),
            ('1_30',       1,   30),
            ('31_60',     31,   60),
            ('61_90',     61,   90),
            ('91_120',    91,  120),
            ('121_150',  121,  150),
            ('151_180',  151,  180),
            ('above_180', 181, 99999),
        ]
        PD = {
            'current':   0.10,
            '1_30':      0.25,
            '31_60':     0.65,
            '61_90':     0.85,
            '91_120':    1.00,
            '121_150':   1.00,
            '151_180':   1.00,
            'above_180': 1.00,
        }

        loans = Loan.objects.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]
        ).select_related('product')

        products = {}
        totals = {b[0]: 0.0 for b in BUCKETS}
        totals['total'] = 0.0

        for loan in loans:
            name = loan.product.name
            outstanding = loan_outstanding(loan)
            days = loan.days_overdue

            if name not in products:
                products[name] = {b[0]: 0.0 for b in BUCKETS}
                products[name]['total'] = 0.0

            for bucket_key, low, high in BUCKETS:
                if low <= days <= high:
                    products[name][bucket_key] += outstanding
                    totals[bucket_key] += outstanding
                    break

            products[name]['total'] += outstanding
            totals['total'] += outstanding

        rows = [{'product': name, **buckets} for name, buckets in products.items()]

        provision = {}
        total_provision = 0.0
        for bucket_key, _, _ in BUCKETS:
            prov = totals[bucket_key] * PD[bucket_key]
            provision[bucket_key] = round(prov, 2)
            total_provision += prov
        provision['total'] = round(total_provision, 2)

        total_portfolio = totals['total']
        par_30_amount = sum(totals[b[0]] for b in BUCKETS if b[1] > 30)
        par_90_amount = sum(totals[b[0]] for b in BUCKETS if b[1] > 90)
        par_30_ratio = round((par_30_amount / total_portfolio * 100), 1) if total_portfolio else 0
        par_90_ratio = round((par_90_amount / total_portfolio * 100), 1) if total_portfolio else 0

        return {
            'report': 'Aging PAR Report',
            'report_date': today.strftime('%d %B %Y'),
            'rows': rows,
            'totals': totals,
            'pd_rates': PD,
            'provision': provision,
            'par_30_ratio': par_30_ratio,
            'par_90_ratio': par_90_ratio,
            'generated_at': str(today),
            # legacy fields
            'par_ratio': par_30_ratio,
            'par_amount': par_30_amount,
        }

    def income_statement(self, request, today):
        start = today.replace(day=1)
        transactions = Transaction.objects.filter(
            created_at__date__gte=start,
            created_at__date__lte=today
        )
        repayment_transactions = transactions.filter(
            transaction_type=TransactionType.REPAYMENT
        ).select_related('loan')
        interest_income = sum(
            loan_interest_component(t.loan, t.amount)
            for t in repayment_transactions
        )
        repayment_principal_component = round(
            sum(float(t.amount) for t in repayment_transactions) - interest_income,
            2
        )

        penalty_income = transactions.filter(
            transaction_type=TransactionType.PENALTY
        ).aggregate(total=Sum('amount'))['total'] or 0

        disbursements = transactions.filter(
            transaction_type=TransactionType.DISBURSEMENT
        ).aggregate(total=Sum('amount'))['total'] or 0

        return {
            'report': 'Income Statement',
            'period': f"{start} to {today}",
            'income': {
                'interest_income': float(interest_income),
                'penalty_income': float(penalty_income),
                'total_income': float(interest_income) + float(penalty_income),
                'repayment_principal_component': repayment_principal_component,
            },
            'disbursements': float(disbursements),
            'generated_at': str(today)
        }

    def daily_cash_flow(self, request, today):
        transactions = Transaction.objects.filter(created_at__date=today)
        inflows = transactions.filter(
            transaction_type__in=[TransactionType.REPAYMENT, TransactionType.PENALTY, TransactionType.ROLLOVER_FEE]
        ).aggregate(total=Sum('amount'))['total'] or 0
        outflows = transactions.filter(
            transaction_type=TransactionType.DISBURSEMENT
        ).aggregate(total=Sum('amount'))['total'] or 0

        return {
            'report': 'Daily Cash Flow',
            'date': str(today),
            'inflows': float(inflows),
            'outflows': float(outflows),
            'net': float(inflows) - float(outflows),
            'generated_at': str(today)
        }

    def daily_recovery_manifest(self, request, today):
        overdue = Loan.objects.filter(status=LoanStatus.OVERDUE).select_related('client')
        data = [{
            'loan_number': l.loan_number,
            'client': l.client.name,
            'phone': l.client.phone,
            'outstanding': loan_outstanding(l),
            'days_overdue': l.days_overdue,
            'ptp_status': l.ptp_status,
        } for l in overdue]
        return {'report': 'Daily Recovery Manifest', 'data': data, 'generated_at': str(today)}

    def expected_collection(self, request, today):
        try:
            window = int(request.query_params.get('days', 30))
        except (ValueError, TypeError):
            window = 30
        window = max(7, min(window, 90))
        cutoff = today + timedelta(days=window)

        active = Loan.objects.filter(
            status=LoanStatus.ACTIVE
        ).select_related('client', 'product')

        rows = []
        for l in active:
            due_date = l.next_due_date
            if due_date is None:
                continue
            # Include overdue loans and loans due within the window
            if due_date > cutoff:
                continue

            days_until_due = (due_date - today).days  # negative = overdue
            outstanding = loan_outstanding(l)
            installment_amount = float(l.next_payment_due)
            interest_ratio = loan_interest_ratio(l)

            # Arrears: overdue installments not yet paid
            # If days_overdue > 0 and there's more than 1 installment missed,
            # the arrears = outstanding - current installment scheduled.
            # Simpler: arrears = total overdue = days_overdue-based instalments missed
            monthly = float(l.monthly_payment)
            missed = max(0, -days_until_due // 30) if days_until_due < 0 else 0
            arrears = round(min(missed * monthly, outstanding - installment_amount), 2) if missed > 0 and monthly > 0 else 0.0
            total_expected = round(installment_amount + arrears, 2)
            expected_interest = round(total_expected * interest_ratio, 2)

            paid_count = int(float(l.repaid_amount) / monthly) if monthly > 0 else 0
            installment_no = f"{min(paid_count + 1, l.term_months)} of {l.term_months}"

            if l.days_overdue > 30:
                priority = 'High'
            elif l.days_overdue > 0:
                priority = 'Medium'
            else:
                priority = 'Low'

            rows.append({
                'loan_number': l.loan_number,
                'client_name': l.client.name,
                'client_phone': l.client.phone,
                'product': l.product.name,
                'installment_no': installment_no,
                'due_date': str(due_date),
                'days_until_due': days_until_due,
                'installment_amount': installment_amount,
                'arrears': arrears,
                'total_expected': total_expected,
                'expected_interest': expected_interest,
                'outstanding_balance': round(outstanding, 2),
                'days_overdue': l.days_overdue,
                'ptp_status': l.ptp_status,
                'ptp_date': str(l.ptp_date) if l.ptp_date else None,
                'ptp_amount': float(l.ptp_amount) if l.ptp_amount else None,
                'collection_priority': priority,
            })

        # Sort: overdue first (highest DPD), then by due date ascending
        rows.sort(key=lambda r: (r['days_until_due'] >= 0, r['days_until_due']))

        total_expected = round(sum(r['total_expected'] for r in rows), 2)
        total_expected_interest = round(sum(r['expected_interest'] for r in rows), 2)
        total_overdue = [r for r in rows if r['days_overdue'] > 0]
        total_overdue_amount = round(sum(r['arrears'] for r in total_overdue), 2)
        ptp_expected = round(sum(
            r['ptp_amount'] for r in rows
            if r['ptp_status'] == 'ACTIVE' and r['ptp_amount']
        ), 2)

        summary = {
            'window_days': window,
            'total_loans_due': len(rows),
            'total_expected': total_expected,
            'total_expected_interest': total_expected_interest,
            'overdue_loans': len(total_overdue),
            'total_arrears': total_overdue_amount,
            'ptp_pipeline': ptp_expected,
        }

        return {
            'report': 'Expected Collection',
            'summary': summary,
            'data': rows,
            'generated_at': str(today),
        }

    def ptp_performance(self, request, today):
        from apps.loans.models import PTPStatus
        active_ptp = Loan.objects.filter(ptp_status=PTPStatus.ACTIVE).count()
        broken_ptp = Loan.objects.filter(ptp_status=PTPStatus.BROKEN).count()
        fulfilled_ptp = Loan.objects.filter(ptp_status=PTPStatus.FULFILLED).count()
        total = active_ptp + broken_ptp + fulfilled_ptp
        return {
            'report': 'PTP Performance',
            'active': active_ptp,
            'broken': broken_ptp,
            'fulfilled': fulfilled_ptp,
            'total': total,
            'fulfillment_rate': round(fulfilled_ptp / total * 100, 2) if total else 0,
            'generated_at': str(today)
        }

    def master_loan_tape(self, request, today):
        loans = Loan.objects.all().select_related('client', 'product')
        data = [{
            'loan_number': l.loan_number,
            'client': l.client.name,
            'product': l.product.name,
            'amount': float(l.amount),
            'total_repayable': float(l.total_repayable),
            'expected_interest': round(loan_expected_interest(l), 2),
            'repaid': float(l.repaid_amount),
            'outstanding': loan_outstanding(l),
            'status': l.status,
            'term_months': l.term_months,
            'interest_rate': float(l.interest_rate),
            'disbursement_date': str(l.disbursement_date) if l.disbursement_date else None,
            'maturity_date': str(l.maturity_date) if l.maturity_date else None,
        } for l in loans]
        return {'report': 'Master Loan Tape', 'data': data, 'total': len(data), 'generated_at': str(today)}

    def vintage_analysis(self, request, today):
        from collections import defaultdict

        product_filter = request.query_params.get('product')
        qs = Loan.objects.filter(disbursement_date__isnull=False).select_related('client', 'product')
        if product_filter:
            qs = qs.filter(product__name=product_filter)

        cohort_map = defaultdict(list)
        for l in qs:
            key = l.disbursement_date.strftime('%Y-%m')
            cohort_map[key].append(l)

        rows = []
        for cohort_key in sorted(cohort_map.keys()):
            cl = cohort_map[cohort_key]
            count = len(cl)
            disbursed = sum(float(l.amount) for l in cl)
            repaid = sum(float(l.repaid_amount) for l in cl)
            total_repayable = sum(float(l.total_repayable) for l in cl)
            expected_interest = sum(loan_expected_interest(l) for l in cl)
            outstanding = sum(loan_outstanding(l) for l in cl)

            active_count     = sum(1 for l in cl if l.status == LoanStatus.ACTIVE)
            closed_count     = sum(1 for l in cl if l.status == LoanStatus.CLOSED)
            written_off_count= sum(1 for l in cl if l.status == LoanStatus.WRITTEN_OFF)

            par30_bal = sum(
                loan_outstanding(l)
                for l in cl if l.days_overdue > 30
            )
            par90_bal = sum(
                loan_outstanding(l)
                for l in cl if l.days_overdue > 90
            )
            written_off_amt = sum(float(l.amount) for l in cl if l.status == LoanStatus.WRITTEN_OFF)

            # MOB from first day of the cohort month to today
            cohort_date = cl[0].disbursement_date
            mob = (today.year - cohort_date.year) * 12 + (today.month - cohort_date.month)

            avg_loan  = round(disbursed / count, 2) if count else 0
            avg_term  = round(sum(l.term_months for l in cl) / count, 1) if count else 0
            avg_rate  = round(sum(float(l.interest_rate) for l in cl) / count, 2) if count else 0

            collection_rate = round(repaid / total_repayable * 100, 1) if total_repayable else 0
            par30_rate = round(par30_bal / disbursed * 100, 1) if disbursed else 0
            par90_rate = round(par90_bal / disbursed * 100, 1) if disbursed else 0
            loss_rate  = round(written_off_amt / disbursed * 100, 1) if disbursed else 0
            default_rate = round((par90_bal + written_off_amt) / disbursed * 100, 1) if disbursed else 0

            if all(l.status in (LoanStatus.CLOSED, LoanStatus.WRITTEN_OFF) for l in cl):
                status = 'Mature'
            elif mob >= 12:
                status = 'Seasoned'
            else:
                status = 'Active'

            rows.append({
                'vintage': cohort_key,
                'mob': mob,
                'vintage_status': status,
                'count': count,
                'disbursed': round(disbursed, 2),
                'expected_interest': round(expected_interest, 2),
                'avg_loan_size': avg_loan,
                'avg_term_months': avg_term,
                'avg_interest_rate': avg_rate,
                'active': active_count,
                'closed': closed_count,
                'written_off': written_off_count,
                'repaid': round(repaid, 2),
                'outstanding': round(outstanding, 2),
                'par30_rate': par30_rate,
                'par90_rate': par90_rate,
                'collection_rate': collection_rate,
                'loss_rate': loss_rate,
                'default_rate': default_rate,
            })

        all_products = list(LoanProduct.objects.values_list('name', flat=True).order_by('name'))
        total_disbursed = sum(r['disbursed'] for r in rows)
        total_expected_interest = sum(r['expected_interest'] for r in rows)
        total_repaid    = sum(r['repaid'] for r in rows)
        avg_collection  = round(sum(r['collection_rate'] for r in rows) / len(rows), 1) if rows else 0

        return {
            'report': 'Vintage Analysis',
            'summary': {
                'total_vintages': len(rows),
                'total_loans': sum(r['count'] for r in rows),
                'total_disbursed': round(total_disbursed, 2),
                'total_expected_interest': round(total_expected_interest, 2),
                'total_repaid': round(total_repaid, 2),
                'avg_collection_rate': avg_collection,
            },
            'cohorts': rows,
            'products': all_products,
            'generated_at': str(today),
        }

    def ifrs9_expected_loss(self, request, today):
        stages = {
            'Stage 1': {'days': (0, 30), 'pd': 0.02, 'lgd': 0.45},
            'Stage 2': {'days': (31, 90), 'pd': 0.15, 'lgd': 0.55},
            'Stage 3': {'days': (91, 9999), 'pd': 0.80, 'lgd': 0.75},
        }
        result = []
        total_ecl = 0
        for stage, config in stages.items():
            loans = Loan.objects.filter(
                status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE],
                days_overdue__gte=config['days'][0],
                days_overdue__lte=config['days'][1],
            )
            exposure = sum(loan_outstanding(loan) for loan in loans)
            ecl = float(exposure) * config['pd'] * config['lgd']
            total_ecl += ecl
            result.append({
                'stage': stage,
                'loan_count': loans.count(),
                'exposure': float(exposure),
                'pd': config['pd'],
                'lgd': config['lgd'],
                'ecl': ecl,
            })
        return {'report': 'IFRS 9 Expected Loss', 'stages': result, 'total_ecl': total_ecl, 'generated_at': str(today)}

    def write_off_register(self, request, today):
        loans = Loan.objects.filter(status=LoanStatus.WRITTEN_OFF).select_related('client', 'product')
        data = [{
            'loan_number': l.loan_number,
            'client': l.client.name,
            'product': l.product.name,
            'amount': float(l.amount),
            'outstanding': loan_outstanding(l),
            'write_off_date': str(l.updated_at.date()),
        } for l in loans]
        total = sum(d['outstanding'] for d in data)
        return {'report': 'Write-off Register', 'data': data, 'total_written_off': total, 'generated_at': str(today)}


class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()
        loans = Loan.objects.all()
        clients = Client.objects.all()

        active_loans = loans.filter(status=LoanStatus.ACTIVE)
        overdue_loans = loans.filter(status=LoanStatus.OVERDUE)
        pending_loans = loans.filter(status=LoanStatus.PENDING_APPROVAL)

        total_portfolio = active_loans.aggregate(total=Sum('amount'))['total'] or 0
        total_outstanding = sum(loan_outstanding(loan) for loan in active_loans)
        total_repaid = active_loans.aggregate(total=Sum('repaid_amount'))['total'] or 0

        # Monthly disbursements
        month_start = today.replace(day=1)
        monthly_disbursed = Transaction.objects.filter(
            transaction_type=TransactionType.DISBURSEMENT,
            created_at__date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        monthly_collected = Transaction.objects.filter(
            transaction_type=TransactionType.REPAYMENT,
            created_at__date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        par_amount = sum(
            float(l.total_repayable) - float(l.repaid_amount)
            for l in overdue_loans
        )
        par_ratio = (par_amount / float(total_outstanding) * 100) if total_outstanding else 0

        # Monthly performance for last 5 months
        monthly_performance = []
        for i in range(4, -1, -1):
            month_date = today.replace(day=1) - timedelta(days=i * 30)
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
            
            disbursed = Transaction.objects.filter(
                transaction_type=TransactionType.DISBURSEMENT,
                created_at__date__gte=month_start,
                created_at__date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            collected = Transaction.objects.filter(
                transaction_type=TransactionType.REPAYMENT,
                created_at__date__gte=month_start,
                created_at__date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_performance.append({
                'month': month_date.strftime('%b'),
                'disbursed': float(disbursed),
                'collected': float(collected),
            })

        return Response({
            'total_clients': clients.count(),
            'active_loans': active_loans.count(),
            'overdue_loans': overdue_loans.count(),
            'pending_loans': pending_loans.count(),
            'total_portfolio': float(total_portfolio),
            'total_outstanding': float(total_outstanding),
            'total_repaid': float(total_repaid),
            'monthly_disbursed': float(monthly_disbursed),
            'monthly_collected': float(monthly_collected),
            'par_ratio': round(par_ratio, 2),
            'par_amount': par_amount,
            'monthly_performance': monthly_performance,
        })
