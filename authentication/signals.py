from django.db.models.signals import post_save
from django.dispatch import receiver
from social_django.models import UserSocialAuth
from .models import Usermodels  # Ensure you import your user model

@receiver(post_save, sender=UserSocialAuth)
def save_profile(sender, instance, created, **kwargs):
    if created and instance.provider == 'google-oauth2':
        user = instance.user
        extra_data = instance.extra_data

        user.email = extra_data.get('email')
        user.username = extra_data.get('name')
        # user.profile_photo = extra_data.get('picture')
        user.save()

