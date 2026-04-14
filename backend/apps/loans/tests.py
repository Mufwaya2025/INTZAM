from datetime import date

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.authentication.models import User
from apps.accounting.models import JournalEntry, LedgerAccount
from apps.accounting.services import ensure_opening_bank_balance, post_journal_entry, sync_loan_disbursement_journal
from apps.core.models import Client, InterestType, LoanProduct
from .models import Loan, LoanStatus, TransactionType
from .services import calculate_loan_terms
from .views import ApproveLoanView, DisburseLoanView, LoanCalculatorView, ReturnToUnderwriterView


class LoanCalculationTests(SimpleTestCase):
    def test_flat_calculation_includes_fees_and_nominal_interest(self):
        result = calculate_loan_terms(
            principal=1000,
            interest_rate=25,
            term_months=1,
            interest_type='FLAT',
            nominal_interest_rate=18,
            credit_facilitation_fee=5,
            processing_fee=2,
        )

        self.assertEqual(result['finance_interest'], 180.0)
        self.assertEqual(result['credit_facilitation_fee_amount'], 50.0)
        self.assertEqual(result['processing_fee_amount'], 20.0)
        self.assertEqual(result['total_interest'], 250.0)
        self.assertEqual(result['total_repayable'], 1250.0)
        self.assertEqual(result['monthly_payment'], 1250.0)

    def test_flat_calculation_uses_total_rate_when_component_rates_are_unavailable(self):
        result = calculate_loan_terms(
            principal=1000,
            interest_rate=25,
            term_months=3,
            interest_type='FLAT',
        )

        self.assertEqual(result['finance_interest'], 250.0)
        self.assertEqual(result['total_interest'], 250.0)
        self.assertEqual(result['total_repayable'], 1250.0)
        self.assertEqual(result['monthly_payment'], 416.67)

    def test_reducing_calculation_spreads_one_time_fees(self):
        result = calculate_loan_terms(
            principal=1000,
            interest_rate=7,
            term_months=12,
            interest_type='REDUCING',
            nominal_interest_rate=0,
            credit_facilitation_fee=5,
            processing_fee=2,
        )

        self.assertEqual(result['total_interest'], 70.0)
        self.assertEqual(result['total_repayable'], 1070.0)
        self.assertEqual(result['monthly_payment'], 89.17)


class LoanCalculatorViewTests(TestCase):
    def test_calculator_uses_product_configuration(self):
        user = User.objects.create_user(
            username='client-user',
            password='secret',
            role='CLIENT',
        )
        product = LoanProduct.objects.create(
            name='Configured Product',
            description='Uses configured rates',
            interest_type=InterestType.FLAT,
            interest_rate=25,
            nominal_interest_rate=18,
            credit_facilitation_fee=5,
            processing_fee=2,
            min_amount=500,
            max_amount=5000,
            min_term=1,
            max_term=12,
        )

        request = APIRequestFactory().post(
            '/calculator/',
            {'product': product.id, 'principal': 1000, 'term_months': 1},
            format='json',
        )
        force_authenticate(request, user=user)

        response = LoanCalculatorView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_interest'], 250.0)
        self.assertEqual(response.data['total_repayable'], 1250.0)
        self.assertEqual(response.data['monthly_payment'], 1250.0)

    def test_underwriter_can_approve_with_comments(self):
        underwriter = User.objects.create_user(
            username='underwriter-user',
            password='secret',
            role='UNDERWRITER',
            first_name='Under',
            last_name='Writer',
        )
        client_user = User.objects.create_user(
            username='client-approval',
            password='secret',
            role='CLIENT',
            email='approval@example.com',
        )
        client = Client.objects.create(
            user=client_user,
            name='Approval Client',
            email='approval@example.com',
            phone='0970000001',
        )
        product = LoanProduct.objects.create(
            name='Approval Product',
            description='For underwriting comments',
            interest_type=InterestType.FLAT,
            interest_rate=25,
            nominal_interest_rate=18,
            credit_facilitation_fee=5,
            processing_fee=2,
            min_amount=500,
            max_amount=5000,
            min_term=1,
            max_term=12,
        )
        loan = Loan.objects.create(
            client=client,
            product=product,
            amount=1000,
            purpose='School fees',
            term_months=1,
            interest_rate=25,
            total_repayable=1250,
            monthly_payment=1250,
            status=LoanStatus.PENDING_APPROVAL,
            disbursement_comments='Old disbursement feedback',
        )

        request = APIRequestFactory().post(
            f'/loans/{loan.id}/approve/',
            {'comments': 'Payslips verified and customer is eligible.'},
            format='json',
        )
        force_authenticate(request, user=underwriter)

        response = ApproveLoanView.as_view()(request, pk=loan.id)
        loan.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(loan.status, LoanStatus.APPROVED)
        self.assertEqual(loan.approved_by, 'Under Writer')
        self.assertEqual(loan.underwriter_comments, 'Payslips verified and customer is eligible.')
        self.assertEqual(loan.disbursement_comments, '')

    def test_accountant_can_disburse_approved_loan(self):
        accountant = User.objects.create_user(
            username='finance-user',
            password='secret',
            role='ACCOUNTANT',
        )
        client_user = User.objects.create_user(
            username='client-borrower',
            password='secret',
            role='CLIENT',
            email='client@example.com',
        )
        client = Client.objects.create(
            user=client_user,
            name='Client Borrower',
            email='client@example.com',
            phone='0970000000',
        )
        product = LoanProduct.objects.create(
            name='Disbursement Product',
            description='Approved loans can be disbursed by accountant',
            interest_type=InterestType.FLAT,
            interest_rate=25,
            nominal_interest_rate=18,
            credit_facilitation_fee=5,
            processing_fee=2,
            min_amount=500,
            max_amount=5000,
            min_term=1,
            max_term=12,
        )
        loan = Loan.objects.create(
            client=client,
            product=product,
            amount=1000,
            purpose='Business stock',
            term_months=1,
            interest_rate=25,
            total_repayable=1250,
            monthly_payment=1250,
            status=LoanStatus.APPROVED,
        )

        request = APIRequestFactory().post(f'/loans/{loan.id}/disburse/', {}, format='json')
        force_authenticate(request, user=accountant)

        response = DisburseLoanView.as_view()(request, pk=loan.id)
        loan.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(loan.status, LoanStatus.ACTIVE)
        self.assertIsNotNone(loan.disbursement_date)
        self.assertEqual(loan.transactions.count(), 1)
        self.assertEqual(loan.transactions.first().transaction_type, TransactionType.DISBURSEMENT)
        self.assertEqual(JournalEntry.objects.count(), 2)
        self.assertTrue(JournalEntry.objects.filter(reference_id='OPENING-BANK-BALANCE').exists())
        self.assertTrue(JournalEntry.objects.filter(reference_id=f'LOAN-DISBURSEMENT-{loan.loan_number}').exists())
        self.assertEqual(LedgerAccount.objects.get(code='1001').balance, 19000)
        self.assertEqual(LedgerAccount.objects.get(code='1100').balance, 1000)
        self.assertEqual(LedgerAccount.objects.get(code='1200').balance, 250)
        self.assertEqual(LedgerAccount.objects.get(code='4001').balance, -180)
        self.assertEqual(LedgerAccount.objects.get(code='4100').balance, -70)
        self.assertEqual(LedgerAccount.objects.get(code='3001').balance, -20000)

    def test_disbursement_fails_when_bank_balance_is_insufficient(self):
        accountant = User.objects.create_user(
            username='finance-user-low-balance',
            password='secret',
            role='ACCOUNTANT',
        )
        client_user = User.objects.create_user(
            username='client-borrower-large',
            password='secret',
            role='CLIENT',
            email='client-large@example.com',
        )
        client = Client.objects.create(
            user=client_user,
            name='Client Borrower Large',
            email='client-large@example.com',
            phone='0970000003',
        )
        product = LoanProduct.objects.create(
            name='Large Disbursement Product',
            description='Should be blocked if bank funds are insufficient',
            interest_type=InterestType.FLAT,
            interest_rate=25,
            nominal_interest_rate=18,
            credit_facilitation_fee=5,
            processing_fee=2,
            min_amount=500,
            max_amount=50000,
            min_term=1,
            max_term=12,
        )
        loan = Loan.objects.create(
            client=client,
            product=product,
            amount=25000,
            purpose='Large stock purchase',
            term_months=1,
            interest_rate=25,
            total_repayable=31250,
            monthly_payment=31250,
            status=LoanStatus.APPROVED,
        )

        request = APIRequestFactory().post(f'/loans/{loan.id}/disburse/', {}, format='json')
        force_authenticate(request, user=accountant)

        response = DisburseLoanView.as_view()(request, pk=loan.id)
        loan.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Insufficient bank balance for disbursement.')
        self.assertEqual(loan.status, LoanStatus.APPROVED)
        self.assertIsNone(loan.disbursement_date)
        self.assertEqual(loan.transactions.count(), 0)
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(LedgerAccount.objects.get(code='1001').balance, 20000)

    def test_existing_disbursement_entry_can_be_synced_with_receivable_lines(self):
        accountant = User.objects.create_user(
            username='finance-user-sync',
            password='secret',
            role='ACCOUNTANT',
        )
        client_user = User.objects.create_user(
            username='client-borrower-sync',
            password='secret',
            role='CLIENT',
            email='client-sync@example.com',
        )
        client = Client.objects.create(
            user=client_user,
            name='Client Borrower Sync',
            email='client-sync@example.com',
            phone='0970000004',
        )
        product = LoanProduct.objects.create(
            name='Sync Product',
            description='Existing entries should be upgraded with receivables',
            interest_type=InterestType.FLAT,
            interest_rate=25,
            nominal_interest_rate=18,
            credit_facilitation_fee=5,
            processing_fee=2,
            min_amount=500,
            max_amount=5000,
            min_term=1,
            max_term=12,
        )
        loan = Loan.objects.create(
            client=client,
            product=product,
            amount=1000,
            purpose='Existing loan sync',
            term_months=1,
            interest_rate=25,
            total_repayable=1250,
            monthly_payment=1250,
            status=LoanStatus.ACTIVE,
            disbursement_date=date(2026, 3, 13),
        )

        accounts = ensure_opening_bank_balance(posted_by='System')
        post_journal_entry(
            reference_id=f'LOAN-DISBURSEMENT-{loan.loan_number}',
            description=f'Loan disbursement for {loan.loan_number}',
            posted_by=accountant.username,
            entry_date=loan.disbursement_date,
            lines=[
                {'account': accounts['1100'], 'debit': 1000, 'description': 'Principal advanced'},
                {'account': accounts['1001'], 'credit': 1000, 'description': 'Cash released'},
            ],
        )

        sync_loan_disbursement_journal(loan=loan, posted_by=accountant.username)

        entry = JournalEntry.objects.get(reference_id=f'LOAN-DISBURSEMENT-{loan.loan_number}')

        self.assertEqual(JournalEntry.objects.count(), 2)
        self.assertEqual(entry.lines.count(), 5)
        self.assertEqual(LedgerAccount.objects.get(code='1001').balance, 19000)
        self.assertEqual(LedgerAccount.objects.get(code='1100').balance, 1000)
        self.assertEqual(LedgerAccount.objects.get(code='1200').balance, 250)
        self.assertEqual(LedgerAccount.objects.get(code='4001').balance, -180)
        self.assertEqual(LedgerAccount.objects.get(code='4100').balance, -70)

    def test_accountant_can_return_approved_loan_to_underwriter(self):
        accountant = User.objects.create_user(
            username='finance-return-user',
            password='secret',
            role='ACCOUNTANT',
        )
        client_user = User.objects.create_user(
            username='client-return-borrower',
            password='secret',
            role='CLIENT',
            email='client-return@example.com',
        )
        client = Client.objects.create(
            user=client_user,
            name='Return Client',
            email='client-return@example.com',
            phone='0970000002',
        )
        product = LoanProduct.objects.create(
            name='Return Product',
            description='Approved loans can be returned to underwriting',
            interest_type=InterestType.FLAT,
            interest_rate=25,
            nominal_interest_rate=18,
            credit_facilitation_fee=5,
            processing_fee=2,
            min_amount=500,
            max_amount=5000,
            min_term=1,
            max_term=12,
        )
        loan = Loan.objects.create(
            client=client,
            product=product,
            amount=1000,
            purpose='Inventory',
            term_months=1,
            interest_rate=25,
            total_repayable=1250,
            monthly_payment=1250,
            status=LoanStatus.APPROVED,
            approved_by='Under Writer',
            underwriter_comments='Approved after verifying client documents.',
        )

        request = APIRequestFactory().post(
            f'/loans/{loan.id}/return-to-underwriter/',
            {'comments': 'NRC attachment is blurry. Please re-check the client documents.'},
            format='json',
        )
        force_authenticate(request, user=accountant)

        response = ReturnToUnderwriterView.as_view()(request, pk=loan.id)
        loan.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(loan.status, LoanStatus.PENDING_APPROVAL)
        self.assertEqual(loan.approved_by, '')
        self.assertEqual(loan.disbursement_comments, 'NRC attachment is blurry. Please re-check the client documents.')
        self.assertEqual(loan.underwriter_comments, 'Approved after verifying client documents.')
