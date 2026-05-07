from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
import os


class Command(BaseCommand):
    help = 'Create social applications for Facebook and Instagram'

    def handle(self, *args, **kwargs):
        site = Site.objects.get_current()

        # Facebook
        fb_app_id = os.environ.get('FACEBOOK_APP_ID')
        fb_app_secret = os.environ.get('FACEBOOK_APP_SECRET')
        if fb_app_id and fb_app_secret:
            app, created = SocialApp.objects.get_or_create(
                provider='facebook',
                defaults={
                    'name': 'Facebook',
                    'client_id': fb_app_id,
                    'secret': fb_app_secret,
                }
            )
            if created:
                app.sites.add(site)
                self.stdout.write(self.style.SUCCESS('Facebook social app created'))
            else:
                # Update credentials if they changed
                if app.client_id != fb_app_id or app.secret != fb_app_secret:
                    app.client_id = fb_app_id
                    app.secret = fb_app_secret
                    app.save()
                    self.stdout.write(self.style.SUCCESS('Facebook social app updated'))
                if not app.sites.filter(pk=site.pk).exists():
                    app.sites.add(site)
        else:
            self.stdout.write(self.style.WARNING('Facebook app credentials not set'))

        # Instagram
        ig_app_id = os.environ.get('INSTAGRAM_APP_ID')
        ig_app_secret = os.environ.get('INSTAGRAM_APP_SECRET')
        if ig_app_id and ig_app_secret:
            app, created = SocialApp.objects.get_or_create(
                provider='instagram',
                defaults={
                    'name': 'Instagram',
                    'client_id': ig_app_id,
                    'secret': ig_app_secret,
                }
            )
            if created:
                app.sites.add(site)
                self.stdout.write(self.style.SUCCESS('Instagram social app created'))
            else:
                if app.client_id != ig_app_id or app.secret != ig_app_secret:
                    app.client_id = ig_app_id
                    app.secret = ig_app_secret
                    app.save()
                    self.stdout.write(self.style.SUCCESS('Instagram social app updated'))
                if not app.sites.filter(pk=site.pk).exists():
                    app.sites.add(site)
        else:
            self.stdout.write(self.style.WARNING('Instagram app credentials not set'))
