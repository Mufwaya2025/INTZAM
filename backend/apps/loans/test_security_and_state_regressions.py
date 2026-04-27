from rest_framework.test import APITestCase

from apps.accounting.models import LedgerAccount
from apps.authentication.models import User
from apps.core.models import (
    Client,
    FieldType,
    InterestType,
    KYCField,
    KYCSection,
    KYCSubmission,
    LoanProduct,
    QualifiedBase,
)
from apps.loans.models import Loan, LoanStatus


class SecurityRegressionTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client-sec-1',
            password='secret123',
            role='CLIENT',
            email='client-sec-1@example.com',
            phone='0972000001',
        )
        self.other_user = User.objects.create_user(
            username='client-sec-2',
            password='secret123',
            role='CLIENT',
            email='client-sec-2@example.com',
            phone='0972000002',
        )
        self.admin = User.objects.create_user(
            username='admin-sec',
            password='secret123',
            role='ADMIN',
            email='admin-sec@example.com',
        )
        self.accountant = User.objects.create_user(
            username='accountant-sec',
            password='secret123',
            role='ACCOUNTANT',
            email='accountant-sec@example.com',
        )

        self.client_profile = Client.objects.create(
            user=self.client_user,
            name='Client One',
            email='client-sec-1@example.com',
            phone='0972000001',
            nrc_number='SEC-NRC-001',
            kyc_verified=True,
        )
        self.other_profile = Client.objects.create(
            user=self.other_user,
            name='Client Two',
            email='client-sec-2@example.com',
            phone='0972000002',
            nrc_number='SEC-NRC-002',
            kyc_verified=True,
        )
        QualifiedBase.objects.create(
            first_name='Client',
            last_name='One',
            phone_number=self.client_profile.phone,
            nrc_number=self.client_profile.nrc_number,
            amount_qualified_for=3000,
        )
        QualifiedBase.objects.create(
            first_name='Client',
            last_name='Two',
            phone_number=self.other_profile.phone,
            nrc_number=self.other_profile.nrc_number,
            amount_qualified_for=3000,
        )
        self.product = LoanProduct.objects.create(
            name='Security Product',
            description='Security regression product',
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
        self.other_loan = Loan.objects.create(
            client=self.other_profile,
            product=self.product,
            amount=1000,
            purpose='Other client loan',
            term_months=1,
            interest_rate=25,
            total_repayable=1250,
            monthly_payment=1250,
            status=LoanStatus.ACTIVE,
        )
        section = KYCSection.objects.create(name='Security KYC', is_active=True)
        KYCField.objects.create(
            section=section,
            name='id_number',
            label='ID Number',
            field_type=FieldType.TEXT,
            required=True,
        )
        self.other_submission = KYCSubmission.objects.create(client=self.other_profile)

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_client_cannot_create_privileged_user(self):
        self._auth(self.client_user)
        response = self.client.post(
            '/api/v1/auth/users/',
            {
                'username': 'evil-admin',
                'password': 'secret123',
                'role': 'ADMIN',
                'custom_permissions': ['manage_users'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='evil-admin').exists())

    def test_client_cannot_promote_own_account(self):
        self._auth(self.client_user)
        response = self.client.patch(
            f'/api/v1/auth/users/{self.client_user.id}/',
            {'role': 'ADMIN', 'custom_permissions': ['manage_users'], 'is_active': False},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.role, 'CLIENT')
        self.assertEqual(self.client_user.custom_permissions, [])
        self.assertTrue(self.client_user.is_active)

    def test_client_cannot_apply_for_another_client(self):
        self._auth(self.client_user)
        response = self.client.post(
            '/api/v1/loans/',
            {
                'client': self.other_profile.id,
                'product': self.product.id,
                'amount': '1000',
                'purpose': 'Attempted cross-client application',
                'term_months': 1,
                'documents': [],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        loan = Loan.objects.get(purpose='Attempted cross-client application')
        self.assertEqual(loan.client_id, self.client_profile.id)

    def test_client_cannot_view_other_client_loan_or_kyc_submission(self):
        self._auth(self.client_user)

        loan_response = self.client.get(f'/api/v1/loans/{self.other_loan.id}/')
        kyc_response = self.client.get(f'/api/v1/kyc/submissions/{self.other_submission.id}/')

        self.assertEqual(loan_response.status_code, 404)
        self.assertEqual(kyc_response.status_code, 404)

    def test_client_cannot_post_accounting_journal(self):
        LedgerAccount.objects.create(code='1999', name='Test Asset', account_type='ASSET', category='BS')
        LedgerAccount.objects.create(code='3999', name='Test Equity', account_type='EQUITY', category='BS')
        self._auth(self.client_user)

        response = self.client.post(
            '/api/v1/accounting/journal/',
            {
                'reference_id': 'CLIENT-JOURNAL-ATTEMPT',
                'description': 'Client should not post journal',
                'date': '2026-04-27',
                'posted_by': 'client',
                'is_posted': True,
                'lines': [
                    {'account': LedgerAccount.objects.get(code='1999').id, 'debit': '10.00', 'credit': '0.00'},
                    {'account': LedgerAccount.objects.get(code='3999').id, 'debit': '0.00', 'credit': '10.00'},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 403)


class LoanStateMachineRegressionTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client-state',
            password='secret123',
            role='CLIENT',
            email='client-state@example.com',
            phone='0973000001',
        )
        self.underwriter = User.objects.create_user(
            username='underwriter-state',
            password='secret123',
            role='UNDERWRITER',
            email='underwriter-state@example.com',
        )
        self.accountant = User.objects.create_user(
            username='accountant-state',
            password='secret123',
            role='ACCOUNTANT',
            email='accountant-state@example.com',
        )
        self.admin = User.objects.create_user(
            username='admin-state',
            password='secret123',
            role='ADMIN',
            email='admin-state@example.com',
        )
        self.client_profile = Client.objects.create(
            user=self.client_user,
            name='State Client',
            email='client-state@example.com',
            phone='0973000001',
            nrc_number='STATE-NRC-001',
            kyc_verified=True,
        )
        self.product = LoanProduct.objects.create(
            name='State Product',
            description='State regression product',
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

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _loan(self, status):
        return Loan.objects.create(
            client=self.client_profile,
            product=self.product,
            amount=1000,
            purpose=f'{status} loan',
            term_months=1,
            interest_rate=25,
            total_repayable=1250,
            monthly_payment=1250,
            status=status,
        )

    def test_invalid_underwriting_and_disbursement_transitions_are_blocked(self):
        active_loan = self._loan(LoanStatus.ACTIVE)

        self._auth(self.underwriter)
        approve_response = self.client.post(f'/api/v1/loans/{active_loan.id}/approve/', {}, format='json')
        reject_response = self.client.post(
            f'/api/v1/loans/{active_loan.id}/reject/',
            {'reason': 'Should not reject active loan'},
            format='json',
        )
        active_loan.refresh_from_db()

        self.assertEqual(approve_response.status_code, 400)
        self.assertEqual(reject_response.status_code, 400)
        self.assertEqual(active_loan.status, LoanStatus.ACTIVE)

        pending_loan = self._loan(LoanStatus.PENDING_APPROVAL)
        self._auth(self.accountant)
        disburse_response = self.client.post(f'/api/v1/loans/{pending_loan.id}/disburse/', {}, format='json')
        self.assertEqual(disburse_response.status_code, 404)

    def test_repay_settle_and_rollover_require_valid_states(self):
        self._auth(self.client_user)
        for invalid_status in [
            LoanStatus.PENDING_APPROVAL,
            LoanStatus.APPROVED,
            LoanStatus.CLOSED,
            LoanStatus.REJECTED,
            LoanStatus.WRITTEN_OFF,
        ]:
            loan = self._loan(invalid_status)
            response = self.client.post(
                f'/api/v1/loans/{loan.id}/repay/',
                {'amount': '1'},
                format='json',
            )
            self.assertEqual(response.status_code, 400, invalid_status)
            self.assertIn('active or overdue', response.data['error'])

        active_loan = self._loan(LoanStatus.ACTIVE)
        self._auth(self.admin)
        settle_response = self.client.post(
            f'/api/v1/loans/{active_loan.id}/settle/',
            {'amount': '1'},
            format='json',
        )
        self.assertEqual(settle_response.status_code, 400)
        self.assertIn('payoff quote', settle_response.data['error'])

        closed_loan = self._loan(LoanStatus.CLOSED)
        self._auth(self.client_user)
        rollover_response = self.client.post(
            f'/api/v1/loans/{closed_loan.id}/rollover/',
            {'extension_days': 14},
            format='json',
        )
        self.assertEqual(rollover_response.status_code, 400)
        self.assertIn('active or overdue', rollover_response.data['error'])
