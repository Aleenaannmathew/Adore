# your_app/pipeline.py
from django.contrib.auth import get_user_model, login as auth_login
from django.shortcuts import redirect
from .models import Usermodels

def save_user_data(strategy, details, response, *args, **kwargs):
    User = Usermodels  # Use your custom User model

    if response:
        user_data = {
            'email': details.get('email'),
            'name': details.get('fullname'),
            'is_verified':True
             # Get profile photo if available
        }

        user, created = User.objects.get_or_create(email=user_data['email'], defaults=user_data)
        
        if not created:
            # Update user details if already exists
            if user_data.get('name'):
                user.name = user_data['name']
            user.save()
            
        # Optionally, set the user as logged in
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        

        # Store email in session
        strategy.request.session['email'] = user.email
        
        # Redirect to a specific view after login
        return redirect('/')  # Ensure this matches your view URL pattern