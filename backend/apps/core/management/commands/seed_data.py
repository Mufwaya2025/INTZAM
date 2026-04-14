"""
Management command to seed the database with initial data.
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models import LoanProduct, TierConfig, KYCSection, KYCField
from apps.accounting.models import LedgerAccount
from apps.accounting.services import ensure_opening_bank_balance

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with initial demo data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        self.create_users()
        self.create_products()
        self.create_kyc_sections()
        self.create_chart_of_accounts()
        ensure_opening_bank_balance(posted_by='Seed Data')
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

    def create_users(self):
        users_data = [
            {'username': 'admin',       'email': 'admin@intzam.com',       'password': 'admin123',  'role': 'ADMIN',               'first_name': 'System',     'last_name': 'Admin'},
            {'username': 'portfolio',   'email': 'portfolio@intzam.com',   'password': 'staff123',  'role': 'PORTFOLIO_MANAGER',   'first_name': 'Portfolio',  'last_name': 'Manager'},
            {'username': 'collections', 'email': 'collections@intzam.com', 'password': 'staff123',  'role': 'COLLECTIONS_OFFICER', 'first_name': 'Collections','last_name': 'Officer'},
            {'username': 'finance',     'email': 'finance@intzam.com',     'password': 'staff123',  'role': 'ACCOUNTANT',          'first_name': 'Finance',    'last_name': 'Officer'},
            {'username': 'underwriter', 'email': 'underwriter@intzam.com', 'password': 'staff123',  'role': 'UNDERWRITER',         'first_name': 'Under',      'last_name': 'Writer'},
        ]
        for data in users_data:
            if not User.objects.filter(username=data['username']).exists():
                User.objects.create_user(**data)
                self.stdout.write(f"  Created user: {data['username']}")

    def create_products(self):
        products_data = [
            {
                'name': 'IntZam Personal',
                'description': 'Unsecured personal loan for salaried individuals',
                'interest_type': 'FLAT',
                'interest_rate': 25,
                'nominal_interest_rate': 18,
                'credit_facilitation_fee': 5,
                'processing_fee': 2,
                'min_amount': 500,
                'max_amount': 50000,
                'min_term': 1,
                'max_term': 24,
                'penalty_rate': 5,
                'grace_period_days': 3,
                'rollover_interest_rate': 4,
                'max_rollovers': 2,
                'rollover_min_principal_paid_percent': 30,
                'rollover_extension_days': 14,
                'required_documents': ['NRC Front', 'NRC Back', 'Pay Slip', 'Bank Statement'],
                'tiers': [
                    {'tier': 'BRONZE', 'interest_rate': 25, 'max_limit_multiplier': 1.0},
                    {'tier': 'SILVER', 'interest_rate': 20, 'max_limit_multiplier': 1.3},
                    {'tier': 'GOLD', 'interest_rate': 15, 'max_limit_multiplier': 1.5},
                    {'tier': 'PLATINUM', 'interest_rate': 12, 'max_limit_multiplier': 2.0},
                ]
            },
            {
                'name': 'SME Growth',
                'description': 'Working capital for small businesses',
                'interest_type': 'REDUCING',
                'interest_rate': 30,
                'nominal_interest_rate': 22,
                'credit_facilitation_fee': 6,
                'processing_fee': 2,
                'min_amount': 2000,
                'max_amount': 100000,
                'min_term': 6,
                'max_term': 36,
                'penalty_rate': 7,
                'grace_period_days': 5,
                'rollover_interest_rate': 5,
                'max_rollovers': 3,
                'rollover_min_principal_paid_percent': 25,
                'rollover_extension_days': 30,
                'required_documents': ['Business License', 'Bank Statement 6 months', 'NRC', 'Business Plan'],
                'tiers': [
                    {'tier': 'BRONZE', 'interest_rate': 30, 'max_limit_multiplier': 1.0},
                    {'tier': 'SILVER', 'interest_rate': 25, 'max_limit_multiplier': 1.3},
                    {'tier': 'GOLD', 'interest_rate': 20, 'max_limit_multiplier': 1.5},
                    {'tier': 'PLATINUM', 'interest_rate': 15, 'max_limit_multiplier': 2.0},
                ]
            },
        ]
        for data in products_data:
            tiers = data.pop('tiers')
            product, created = LoanProduct.objects.get_or_create(name=data['name'], defaults=data)
            if created:
                for tier in tiers:
                    TierConfig.objects.create(product=product, **tier)
                self.stdout.write(f"  Created product: {product.name}")

    def create_kyc_sections(self):
        """Create KYC sections and fields"""
        sections_data = [
            {
                'name': 'Personal Information',
                'description': 'Basic personal details',
                'order': 1,
                'is_active': True,
                'fields': [
                    {'name': 'full_name', 'label': 'Full Name', 'field_type': 'TEXT', 'required': True, 'order': 1},
                    {'name': 'date_of_birth', 'label': 'Date of Birth', 'field_type': 'DATE', 'required': True, 'order': 2},
                    {'name': 'nrc_number', 'label': 'NRC Number', 'field_type': 'TEXT', 'required': True, 'order': 3},
                    {'name': 'phone_number', 'label': 'Phone Number', 'field_type': 'TEXT', 'required': True, 'order': 4},
                    {'name': 'email', 'label': 'Email Address', 'field_type': 'TEXT', 'required': True, 'order': 5},
                    {'name': 'residential_address', 'label': 'Residential Address', 'field_type': 'LONG_TEXT', 'required': True, 'order': 6},
                ]
            },
            {
                'name': 'Employment Information',
                'description': 'Details about your employment status',
                'order': 2,
                'is_active': True,
                'fields': [
                    {'name': 'employment_status', 'label': 'Employment Status', 'field_type': 'SELECT', 'required': True, 'order': 1, 'options': ['Employed', 'Self-Employed', 'Business Owner', 'Unemployed']},
                    {'name': 'employer_name', 'label': 'Employer Name', 'field_type': 'TEXT', 'required': False, 'order': 2},
                    {'name': 'job_title', 'label': 'Job Title/Position', 'field_type': 'TEXT', 'required': False, 'order': 3},
                    {'name': 'monthly_income', 'label': 'Monthly Income (ZMW)', 'field_type': 'NUMBER', 'required': True, 'order': 4},
                    {'name': 'years_employed', 'label': 'Years at Current Employment', 'field_type': 'NUMBER', 'required': False, 'order': 5},
                ]
            },
            {
                'name': 'Document Upload',
                'description': 'Upload required documents',
                'order': 3,
                'is_active': True,
                'fields': [
                    {'name': 'nrc_front', 'label': 'NRC Front Side', 'field_type': 'FILE', 'required': True, 'order': 1},
                    {'name': 'nrc_back', 'label': 'NRC Back Side', 'field_type': 'FILE', 'required': True, 'order': 2},
                    {'name': 'proof_of_income', 'label': 'Proof of Income (Payslip/Bank Statement)', 'field_type': 'FILE', 'required': True, 'order': 3},
                    {'name': 'proof_of_residence', 'label': 'Proof of Residence', 'field_type': 'FILE', 'required': False, 'order': 4},
                ]
            },
            {
                'name': 'Next of Kin',
                'description': 'Emergency contact information',
                'order': 4,
                'is_active': True,
                'fields': [
                    {'name': 'kin_name', 'label': 'Next of Kin Full Name', 'field_type': 'TEXT', 'required': True, 'order': 1},
                    {'name': 'kin_relationship', 'label': 'Relationship', 'field_type': 'TEXT', 'required': True, 'order': 2},
                    {'name': 'kin_phone', 'label': 'Phone Number', 'field_type': 'TEXT', 'required': True, 'order': 3},
                    {'name': 'kin_address', 'label': 'Address', 'field_type': 'LONG_TEXT', 'required': False, 'order': 4},
                ]
            },
        ]

        for section_data in sections_data:
            fields_data = section_data.pop('fields')
            section, created = KYCSection.objects.get_or_create(
                name=section_data['name'],
                defaults=section_data
            )
            if created:
                for field_data in fields_data:
                    KYCField.objects.create(section=section, **field_data)
                self.stdout.write(f"  Created KYC section: {section.name}")
            else:
                self.stdout.write(f"  KYC section already exists: {section.name}")



    def create_chart_of_accounts(self):
        accounts = [
            ('1001', 'Cash and Bank', 'ASSET', 'BS'),
            ('1100', 'Loan Portfolio', 'ASSET', 'BS'),
            ('1200', 'Interest Receivable', 'ASSET', 'BS'),
            ('1300', 'Provision for Loan Losses', 'ASSET', 'BS'),
            ('2001', 'Customer Deposits', 'LIABILITY', 'BS'),
            ('2100', 'Borrowings', 'LIABILITY', 'BS'),
            ('3001', 'Share Capital', 'EQUITY', 'BS'),
            ('3100', 'Retained Earnings', 'EQUITY', 'BS'),
            ('4001', 'Interest Income', 'INCOME', 'PL'),
            ('4100', 'Fee Income', 'INCOME', 'PL'),
            ('4200', 'Penalty Income', 'INCOME', 'PL'),
            ('5001', 'Interest Expense', 'EXPENSE', 'PL'),
            ('5100', 'Operating Expenses', 'EXPENSE', 'PL'),
            ('5200', 'Loan Loss Provision', 'EXPENSE', 'PL'),
        ]
        for code, name, acc_type, category in accounts:
            LedgerAccount.objects.get_or_create(
                code=code,
                defaults={'name': name, 'account_type': acc_type, 'category': category}
            )
        self.stdout.write(f"  Created {len(accounts)} ledger accounts")
