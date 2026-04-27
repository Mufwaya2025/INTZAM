from rest_framework.test import APITestCase

from apps.accounting.models import JournalEntry, LedgerAccount
from apps.authentication.models import User
from apps.core.models import Client, InterestType, LoanProduct
from apps.loans.models import Loan, LoanStatus


class AccountingRegressionTests(APITestCase):
    def setUp(self):
        self.accountant = User.objects.create_user(
            username='accounting-regression',
            password='secret123',
            role='ACCOUNTANT',
            email='accounting-regression@example.com',
        )
        self.asset = LedgerAccount.objects.create(
            code='1901',
            name='Regression Asset',
            account_type='ASSET',
            category='BS',
        )
        self.equity = LedgerAccount.objects.create(
            code='3901',
            name='Regression Equity',
            account_type='EQUITY',
            category='BS',
        )

    def _auth(self):
        self.client.force_authenticate(user=self.accountant)

    def test_account_balance_cannot_be_updated_directly(self):
        self._auth()

        response = self.client.patch(
            f'/api/v1/accounting/accounts/{self.asset.id}/',
            {'balance': '999999.00', 'name': 'Renamed Asset'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.name, 'Renamed Asset')
        self.assertEqual(self.asset.balance, 0)

    def test_unbalanced_journal_returns_400(self):
        self._auth()

        response = self.client.post(
            '/api/v1/accounting/journal/',
            {
                'reference_id': 'UNBALANCED-001',
                'description': 'Should be rejected',
                'date': '2026-04-27',
                'lines': [
                    {'account': self.asset.id, 'debit': '100.00'},
                    {'account': self.equity.id, 'credit': '90.00'},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('lines', response.data)
        self.asset.refresh_from_db()
        self.equity.refresh_from_db()
        self.assertEqual(self.asset.balance, 0)
        self.assertEqual(self.equity.balance, 0)

    def test_journal_line_cannot_have_debit_and_credit(self):
        self._auth()

        response = self.client.post(
            '/api/v1/accounting/journal/',
            {
                'reference_id': 'BAD-LINE-001',
                'description': 'Should be rejected',
                'date': '2026-04-27',
                'lines': [
                    {'account': self.asset.id, 'debit': '100.00', 'credit': '100.00'},
                    {'account': self.equity.id, 'credit': '100.00'},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('debit and credit', str(response.data))

    def test_balanced_journal_posts_and_uses_authenticated_user(self):
        self._auth()

        response = self.client.post(
            '/api/v1/accounting/journal/',
            {
                'reference_id': 'BALANCED-001',
                'description': 'Valid journal',
                'date': '2026-04-27',
                'posted_by': 'forged-user',
                'lines': [
                    {'account': self.asset.id, 'debit': '100.00'},
                    {'account': self.equity.id, 'credit': '100.00'},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.asset.refresh_from_db()
        self.equity.refresh_from_db()
        self.assertEqual(self.asset.balance, 100)
        self.assertEqual(self.equity.balance, -100)
        self.assertEqual(response.data['posted_by'], self.accountant.username)

    def test_reading_trial_balance_does_not_seed_opening_balance(self):
        self._auth()

        response = self.client.get('/api/v1/accounting/trial-balance/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(JournalEntry.objects.filter(reference_id='OPENING-BANK-BALANCE').exists())
        self.assertEqual(response.data['total_debit'], 0)
        self.assertEqual(response.data['total_credit'], 0)

    def test_monthly_report_par_ratio_uses_net_outstanding(self):
        client_user = User.objects.create_user(
            username='par-client',
            password='secret123',
            role='CLIENT',
            email='par-client@example.com',
        )
        client = Client.objects.create(
            user=client_user,
            name='PAR Client',
            email='par-client@example.com',
            phone='0979000001',
        )
        product = LoanProduct.objects.create(
            name='PAR Product',
            description='PAR reporting product',
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
        Loan.objects.create(
            client=client,
            product=product,
            amount=1000,
            purpose='Partially repaid overdue loan',
            term_months=1,
            interest_rate=25,
            total_repayable=1000,
            repaid_amount=400,
            monthly_payment=1000,
            status=LoanStatus.OVERDUE,
            days_overdue=40,
        )
        Loan.objects.create(
            client=client,
            product=product,
            amount=1000,
            purpose='Performing loan',
            term_months=1,
            interest_rate=25,
            total_repayable=1000,
            repaid_amount=0,
            monthly_payment=1000,
            status=LoanStatus.ACTIVE,
            days_overdue=0,
        )

        self._auth()
        response = self.client.get('/api/v1/accounting/odoo-monthly-report/?period=2026-04')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['total_net_outstanding'], 1600.0)
        self.assertEqual(response.data['par_ratio_pct'], 37.5)
