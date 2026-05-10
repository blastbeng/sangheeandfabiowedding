# Generated migration to add OAuth, Nextcloud, and SMTP fields to SiteSettings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='google_client_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='google_client_secret',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='facebook_app_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='facebook_app_secret',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='instagram_app_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='instagram_app_secret',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='nextcloud_url',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='nextcloud_username',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='nextcloud_password',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='nextcloud_folder',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='email_host',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='email_port',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='email_use_tls',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='email_host_user',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='email_host_password',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='default_from_email',
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),
    ]
