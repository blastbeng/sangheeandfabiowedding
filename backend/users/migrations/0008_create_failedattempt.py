# Generated migration to create FailedAttempt model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_create_cookieconsent'),
    ]

    operations = [
        migrations.CreateModel(
            name='FailedAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField()),
                ('endpoint', models.CharField(max_length=50)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['ip_address', 'endpoint', '-timestamp'], name='users_fail_ip_endpoi_idx'),
                ],
            },
        ),
    ]
