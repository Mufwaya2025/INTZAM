from django.db import models
from django.conf import settings
import uuid


class ClientTier(models.TextChoices):
    BRONZE = 'BRONZE', 'Bronze'
    SILVER = 'SILVER', 'Silver'
    GOLD = 'GOLD', 'Gold'
    PLATINUM = 'PLATINUM', 'Platinum'


class Gender(models.TextChoices):
    MALE   = 'MALE',   'Male'
    FEMALE = 'FEMALE', 'Female'
    OTHER  = 'OTHER',  'Other'


class EmploymentStatus(models.TextChoices):
    EMPLOYED = 'EMPLOYED', 'Employed'
    SELF_EMPLOYED = 'SELF_EMPLOYED', 'Self Employed'
    BUSINESS_OWNER = 'BUSINESS_OWNER', 'Business Owner'
    UNEMPLOYED = 'UNEMPLOYED', 'Unemployed'
    RETIRED = 'RETIRED', 'Retired'


class Client(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='client_profile'
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)
    nrc_number = models.CharField(max_length=50, blank=True, unique=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    kyc_verified = models.BooleanField(default=False)
    credit_score = models.IntegerField(default=0)
    monthly_income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.EMPLOYED
    )
    employer_name = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    next_of_kin_name = models.CharField(max_length=200, blank=True)
    next_of_kin_phone = models.CharField(max_length=20, blank=True)
    next_of_kin_relation = models.CharField(max_length=100, blank=True)
    tier = models.CharField(max_length=10, choices=ClientTier.choices, default=ClientTier.BRONZE)
    completed_loans = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.email})"

    def update_tier(self):
        """Auto-update tier based on completed loans."""
        if self.completed_loans >= 8:
            self.tier = ClientTier.PLATINUM
        elif self.completed_loans >= 5:
            self.tier = ClientTier.GOLD
        elif self.completed_loans >= 2:
            self.tier = ClientTier.SILVER
        else:
            self.tier = ClientTier.BRONZE
        self.save()


class InterestType(models.TextChoices):
    FLAT = 'FLAT', 'Flat Rate'
    REDUCING = 'REDUCING', 'Reducing Balance'
    DAILY = 'DAILY', 'Daily Rate'
    MONTHLY = 'MONTHLY', 'Monthly Rate'


class RepaymentFrequency(models.TextChoices):
    WEEKLY = 'WEEKLY', 'Weekly'
    BIWEEKLY = 'BIWEEKLY', 'Bi-Weekly (Every 2 Weeks)'
    MONTHLY = 'MONTHLY', 'Monthly'


class LoanProduct(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    interest_type = models.CharField(
        max_length=10,
        choices=InterestType.choices,
        default=InterestType.FLAT
    )
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2)  # Total rate
    nominal_interest_rate = models.DecimalField(max_digits=6, decimal_places=2)
    credit_facilitation_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    processing_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    min_amount = models.DecimalField(max_digits=15, decimal_places=2)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2)
    min_term = models.IntegerField()  # months
    max_term = models.IntegerField()  # months
    penalty_rate = models.DecimalField(max_digits=6, decimal_places=2, default=5)
    grace_period_days = models.IntegerField(default=3)
    # Rollover configuration
    rollover_interest_rate = models.DecimalField(max_digits=6, decimal_places=2, default=4)
    max_rollovers = models.IntegerField(default=2)
    rollover_min_principal_paid_percent = models.IntegerField(default=30)
    rollover_extension_days = models.IntegerField(default=14)
    repayment_frequency = models.CharField(
        max_length=10,
        choices=RepaymentFrequency.choices,
        default=RepaymentFrequency.MONTHLY,
    )
    required_documents = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class TierConfig(models.Model):
    product = models.ForeignKey(LoanProduct, on_delete=models.CASCADE, related_name='tiers')
    tier = models.CharField(max_length=10, choices=ClientTier.choices)
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2)
    max_limit_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)

    class Meta:
        unique_together = ['product', 'tier']

    def __str__(self):
        return f"{self.product.name} - {self.tier}"

class QualifiedBase(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, unique=True)
    nrc_number = models.CharField(max_length=50, unique=True)
    date_qualified = models.DateField(auto_now_add=True)
    amount_qualified_for = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        ordering = ['-date_qualified']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.nrc_number})"

class SystemLog(models.Model):
    action = models.CharField(max_length=200)
    details = models.TextField()
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} by {self.performed_by} at {self.created_at}"

class KYCSection(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

class FieldType(models.TextChoices):
    TEXT = 'TEXT', 'Short Text'
    LONG_TEXT = 'LONG_TEXT', 'Long Text'
    NUMBER = 'NUMBER', 'Number'
    DATE = 'DATE', 'Date'
    SELECT = 'SELECT', 'Dropdown Select'
    FILE = 'FILE', 'File Upload'
    BOOLEAN = 'BOOLEAN', 'Yes/No'

class KYCField(models.Model):
    section = models.ForeignKey(KYCSection, on_delete=models.CASCADE, related_name='fields')
    name = models.CharField(max_length=50) # machine name
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.TEXT)
    required = models.BooleanField(default=True)
    options = models.JSONField(default=list, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.label} ({self.section.name})"

class KYCSubmissionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Review'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'

class KYCSubmission(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='kyc_submissions')
    status = models.CharField(max_length=20, choices=KYCSubmissionStatus.choices, default=KYCSubmissionStatus.PENDING)
    reviewer_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.name} - {self.status}"

class KYCFieldValue(models.Model):
    submission = models.ForeignKey(KYCSubmission, on_delete=models.CASCADE, related_name='field_values')
    field = models.ForeignKey(KYCField, on_delete=models.PROTECT)
    value_text = models.TextField(blank=True)
    value_file = models.FileField(upload_to='kyc_documents/', null=True, blank=True)

    class Meta:
        unique_together = ['submission', 'field']


class SystemConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_config'

    def __str__(self):
        return self.key
