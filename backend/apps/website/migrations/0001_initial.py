from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0005_client_registration_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebsiteAudience',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(blank=True, max_length=100, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('badge', models.CharField(blank=True, max_length=120)),
                ('description', models.TextField()),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='WebsiteFAQ',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255)),
                ('answer', models.TextField()),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='WebsiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_name', models.CharField(default='IntZam', max_length=100)),
                ('site_tagline', models.CharField(default='Smart Lending for Growing Communities', max_length=200)),
                ('country_name', models.CharField(default='Zambia', max_length=100)),
                ('hero_eyebrow', models.CharField(default='Fast. Clear. Human-centered lending.', max_length=200)),
                ('hero_title', models.CharField(default='Beautiful digital lending for everyday ambition.', max_length=255)),
                ('hero_description', models.TextField(default='IntZam helps individuals and growing businesses access flexible loans with transparent pricing, simple onboarding, and a modern mobile-first experience.')),
                ('hero_primary_cta_text', models.CharField(default='Start an application', max_length=100)),
                ('hero_primary_cta_url', models.CharField(default='/client-pwa/', max_length=255)),
                ('hero_secondary_cta_text', models.CharField(default='Explore products', max_length=100)),
                ('hero_secondary_cta_url', models.CharField(default='#products', max_length=255)),
                ('client_portal_url', models.CharField(default='/client-pwa/', max_length=255)),
                ('staff_portal_url', models.CharField(default='/admin-frontend/', max_length=255)),
                ('zambia_focus_copy', models.CharField(default="Designed for Zambia's civil servants, salaried professionals, and growing households.", max_length=255)),
                ('audience_intro', models.TextField(default='Especially relevant for civil servants, teachers, nurses, and other dependable earners who need a simpler, more respectful lending experience.')),
                ('lead_form_title', models.CharField(default='Talk to IntZam about the right loan for you.', max_length=255)),
                ('lead_form_description', models.TextField(default='Share a few details and our team can reach out, especially if you are a civil servant or salaried professional in Zambia.')),
                ('contact_email', models.EmailField(default='hello@intzam.com', max_length=254)),
                ('contact_phone', models.CharField(default='+260 000 000 000', max_length=30)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Website settings',
            },
        ),
        migrations.CreateModel(
            name='WebsiteTestimonial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('role', models.CharField(blank=True, max_length=120)),
                ('quote', models.TextField()),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='WebsiteLead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=30)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('segment', models.CharField(choices=[('CIVIL_SERVANT', 'Civil Servant'), ('TEACHER_OR_NURSE', 'Teacher or Nurse'), ('SALARIED_EMPLOYEE', 'Salaried Employee'), ('BUSINESS_OWNER', 'Business Owner'), ('OTHER', 'Other')], default='CIVIL_SERVANT', max_length=30)),
                ('employer_name', models.CharField(blank=True, max_length=200)),
                ('desired_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('desired_term_months', models.PositiveIntegerField(blank=True, null=True)),
                ('message', models.TextField(blank=True)),
                ('consent', models.BooleanField(default=False)),
                ('source_page', models.CharField(default='website', max_length=100)),
                ('status', models.CharField(choices=[('NEW', 'New'), ('CONTACTED', 'Contacted'), ('QUALIFIED', 'Qualified'), ('CONVERTED', 'Converted'), ('CLOSED', 'Closed')], default='NEW', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('converted_client', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='website_leads', to='core.client')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
