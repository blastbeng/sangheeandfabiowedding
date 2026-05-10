# Generated migration to create CookieConsent model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_add_sitesettings_frontend_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='CookieConsent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('analytics', models.BooleanField(default=False)),
                ('marketing', models.BooleanField(default=False)),
                ('necessary', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cookie_consent', to='users.customuser')),
            ],
            options={
                'db_table': 'users_cookieconsent',
            },
        ),
    ]
