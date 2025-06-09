"""
Signals for user models.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomUser, RiderProfile, DriverProfile, UserPreferences


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create user profile based on user type when a new user is created.
    """
    if created:
        # Create user preferences
        UserPreferences.objects.create(user=instance)
        
        # Create profile based on user type
        if instance.user_type == CustomUser.UserType.RIDER:
            RiderProfile.objects.create(user=instance)
        elif instance.user_type == CustomUser.UserType.DRIVER:
            DriverProfile.objects.create(user=instance)
