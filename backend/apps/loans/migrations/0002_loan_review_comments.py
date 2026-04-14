from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='disbursement_comments',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='loan',
            name='underwriter_comments',
            field=models.TextField(blank=True),
        ),
    ]
