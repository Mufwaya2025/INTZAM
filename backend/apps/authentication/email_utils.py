from django.core.mail import get_connection, EmailMultiAlternatives
from django.conf import settings


def get_smtp_config():
    """Read SMTP config from SystemConfig DB, fall back to settings."""
    try:
        from apps.core.models import SystemConfig
        def cfg(key, default=''):
            try:
                return SystemConfig.objects.get(key=key).value or default
            except SystemConfig.DoesNotExist:
                return default

        return {
            'host': cfg('smtp_host', settings.EMAIL_HOST),
            'port': int(cfg('smtp_port', str(settings.EMAIL_PORT))),
            'username': cfg('smtp_username', settings.EMAIL_HOST_USER),
            'password': cfg('smtp_password', settings.EMAIL_HOST_PASSWORD),
            'use_tls': cfg('smtp_use_tls', 'true').lower() == 'true',
            'use_ssl': cfg('smtp_use_ssl', 'false').lower() == 'true',
            'from_email': cfg('smtp_from_email', settings.DEFAULT_FROM_EMAIL),
        }
    except Exception:
        return {
            'host': settings.EMAIL_HOST,
            'port': settings.EMAIL_PORT,
            'username': settings.EMAIL_HOST_USER,
            'password': settings.EMAIL_HOST_PASSWORD,
            'use_tls': settings.EMAIL_USE_TLS,
            'use_ssl': getattr(settings, 'EMAIL_USE_SSL', False),
            'from_email': settings.DEFAULT_FROM_EMAIL,
        }


def send_system_email(subject, text_body, html_body, recipient_list):
    cfg = get_smtp_config()
    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=cfg['host'],
        port=cfg['port'],
        username=cfg['username'],
        password=cfg['password'],
        use_tls=cfg['use_tls'],
        use_ssl=cfg['use_ssl'],
    )
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=cfg['from_email'],
        to=recipient_list,
        connection=connection,
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send()
