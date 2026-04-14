from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Client, KYCSubmission, QualifiedBase


def sync_client_profile_for_user(user):
    if not user or getattr(user, 'role', None) != 'CLIENT':
        return None

    existing_profile = Client.objects.filter(user=user).first()
    if existing_profile:
        return existing_profile

    full_name = (user.get_full_name() or user.username or 'Client').strip()
    email = (user.email or '').strip()
    phone = (user.phone or user.username or '').strip()

    matched_profile = Client.objects.filter(
        Q(phone=phone) | Q(email__iexact=email)
    ).first() if phone or email else None

    if matched_profile:
        updates = []
        if matched_profile.user_id != user.id:
            matched_profile.user = user
            updates.append('user')
        if not matched_profile.name:
            matched_profile.name = full_name
            updates.append('name')
        if not matched_profile.phone and phone:
            matched_profile.phone = phone
            updates.append('phone')
        if not matched_profile.email and email:
            matched_profile.email = email
            updates.append('email')
        if updates:
            matched_profile.save(update_fields=updates)
        return matched_profile

    if not phone:
        return None

    candidate_email = email or f"{phone}@example.com"
    if Client.objects.filter(email__iexact=candidate_email).exists():
        candidate_email = f"{phone}.{user.id}@example.com"

    return Client.objects.create(
        user=user,
        name=full_name,
        email=candidate_email,
        phone=phone,
        kyc_verified=False,
    )


def sync_all_client_profiles():
    User = get_user_model()
    for user in User.objects.filter(role='CLIENT'):
        sync_client_profile_for_user(user)


def ensure_pending_kyc_submission_for_client(client):
    if client is None:
        return None

    latest_submission = client.kyc_submissions.order_by('-created_at').first()
    if latest_submission:
        return latest_submission

    if client.kyc_verified:
        return None

    return KYCSubmission.objects.create(client=client, status='PENDING')


def ensure_pending_kyc_submissions_for_all_clients():
    for client in Client.objects.all():
        ensure_pending_kyc_submission_for_client(client)


def get_client_qualified_record(client):
    if client is None:
        return None

    filters = Q()
    phone = (client.phone or "").strip()
    nrc_number = (client.nrc_number or "").strip()

    if phone:
        filters |= Q(phone_number__iexact=phone)
    if nrc_number:
        filters |= Q(nrc_number__iexact=nrc_number)

    if not filters:
        return None

    return QualifiedBase.objects.filter(filters).order_by('-date_qualified').first()


def get_client_max_borrow_amount(client, product=None):
    amount = Decimal('0')
    qualified_record = get_client_qualified_record(client)

    if qualified_record:
        amount = qualified_record.amount_qualified_for

    if product is not None:
        amount = min(amount, product.max_amount)

    return max(amount, Decimal('0'))
