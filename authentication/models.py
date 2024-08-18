import random
import string
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MaxValueValidator,MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

# Create your models here.

def generate_referral_code(length=10):
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(length))
    print(f"Generated code: {code}")  # Debugging line
    return code

class Usermodels(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=254, unique=True)
    phone = models.CharField(max_length=15, validators=[
        MinValueValidator(1000000000, message='Phone number must be at least 10 digits.'),
        MaxValueValidator(9999999999, message='Phone number must be at most 10 digits.')
    ])
    password1 = models.CharField(max_length=128)  
    password2 = models.CharField(max_length=128)  
    is_verified = models.BooleanField(default=False)
    is_block = models.BooleanField(default=False)
    join_date = models.DateTimeField(null=True, blank=True)  

    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    referral_code = models.CharField(max_length=10, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.join_date:
            self.join_date = timezone.now()
        if not self.referral_code:
            self.referral_code = generate_referral_code()
        
        super(Usermodels, self).save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Referral(models.Model):
        user = models.OneToOneField(Usermodels, on_delete=models.CASCADE)
        referral_code = models.CharField(max_length=10, unique=True)
        referred_by = models.ForeignKey(Usermodels, related_name='referrals', null=True, blank=True, on_delete=models.SET_NULL)
    
        def __str__(self):
            return f"{self.user.name}'s Referral: {self.referral_code} Referred: {self.referred_by}"

        @receiver(post_save, sender=Usermodels)
        def create_user_referral(sender, instance, created, **kwargs):
            if created:
                Referral.objects.create(user=instance, referral_code=instance.referral_code)


 



    