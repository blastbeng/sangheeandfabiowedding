# Generated migration to alter CookieConsent.user from ForeignKey to OneToOneField

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_add_media_content_hash'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cookieconsent',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cookie_consent', to='users.customuser'),
        ),
    ]
