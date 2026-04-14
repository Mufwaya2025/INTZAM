from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0002_loan_review_comments'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='odoo_partner_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text='Odoo res.partner ID synced from LMS client at disbursement.',
            ),
        ),
        migrations.AddField(
            model_name='loan',
            name='odoo_disbursement_move_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text='Odoo account.move ID for the disbursement journal entry.',
            ),
        ),
    ]
