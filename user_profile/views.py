from django.http import JsonResponse
import json,re
from django.contrib import messages
from django.shortcuts import render, redirect,get_object_or_404
from .models import UserAddress,Usermodels
from checkout.models import Order,OrderItem
from cart.models import Cart,CartItems
from wishlist.models import Wishlist
from checkout.models import Wallet,WalletHistory
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.forms.models import model_to_dict

def is_valid_indian_pincode(pincode):
    return re.match(r'^\d{6}$', pincode) is not None

def is_valid_indian_phone(phone):
    return re.match(r'^[789]\d{9}$', phone) is not None

def is_valid_name(name):
    return re.match(r'^[A-Za-z][A-Za-z\s]*$', name) is not None

@never_cache
def profile(request):
    user_email = request.session.get('email')
    if not user_email:
        return redirect('login')
    
    user = get_object_or_404(Usermodels, email=user_email)
    user_address = UserAddress.objects.filter(user=user, is_active=True).all()
    orders = Order.objects.filter(user=user).order_by('-order_date') 
    order_items = OrderItem.objects.filter(order__in=orders)

    wishlist_count = 0
    wishlist = Wishlist.objects.filter(user=user).first()
    if wishlist:
        wishlist_count = wishlist.items.count()

    cart_count = 0
    cart = Cart.objects.filter(user=user).first()
    if cart:
        cart_count = CartItems.objects.filter(cart=cart).count()

    total_orders = orders.count()    

    context = {
        'user': user,
        'user_address': user_address,
        'orders': orders,
        'order_items': order_items,
        'wishlist_count': wishlist_count,
        'cart_count': cart_count,
        'total_orders': total_orders, 
        'referral_code': user.referral_code,
        'id': user.id
    }
    return render(request, 'user_profile/profile.html',context)

def edit_user_details(request):
    if request.method == 'POST':
        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'success': False, 'error': 'User not logged in. '})
        user = get_object_or_404(Usermodels, email=user_email)
        user.name = request.POST.get('modal-full-name')
        user.phone = request.POST.get('modal-contact-number')
        user.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})  
            
def change_profile(request):
    user_email = request.session.get('email')
    if not user_email:
        return JsonResponse({'error': 'User not logged in'}, status=401)  # Unauthorized

    user = get_object_or_404(Usermodels, email=user_email)

    if request.method == 'POST':
        if 'profile_photo' in request.FILES:
            user.profile_photo = request.FILES['profile_photo']
            user.save()

            profile_photo_url = user.profile_photo.url if user.profile_photo else None

            return JsonResponse({
                'message': 'Profile picture updated successfully',
                'profile_photo_url': profile_photo_url
            })

        return JsonResponse({'error': 'No file uploaded'}, status=400)  # Bad Request

    return JsonResponse({'error': 'Invalid request method'}, status=405)  # Method Not Allowed

def remove_profile_picture(request):
    user_email = request.session.get('email')
    if not user_email:
        return JsonResponse({'error': 'User not logged in'}, status=401)  # Unauthorized

    user = get_object_or_404(Usermodels, email=user_email)

    if request.method == 'POST':
        if user.profile_photo:
            user.profile_photo = None
            user.save()
            return JsonResponse({'message': 'Profile picture removed successfully'})
        else:
            return JsonResponse({'error': 'No profile picture to remove'}, status=400)  # Bad Request

    return JsonResponse({'error': 'Invalid request method'}, status=405)  # Method Not Allowed 

   
@never_cache
def get_address(request):
    address_id = request.GET.get('id')
    address = UserAddress.objects.get(id=address_id, user=request.user, is_active=True)
    data = {
        'first_name': address.first_name,
        'last_name': address.last_name,
        'phone_number': address.phone_number,
        'address_line': address.address_line,
        'email': address.email,
        'city': address.city,
        'district': address.district,
        'state': address.state,
        'postal_code': address.postal_code,
        'country': address.country,
        
    }
    return JsonResponse(data)

def get_edit_address(request, address_id):
    try:
        address = UserAddress.objects.get(id=address_id)
        data = {
            'id': address.id,
            'fullname': address.fullname,
            'country': address.country,
            'street': address.street,
            'apartment': address.apartment,
            'city': address.city,
            'district': address.district,
            'state': address.state,
            'zip': address.zip_code,
            'phone': address.phone,
            'type': address.type  # Include other fields as needed
        }
        return JsonResponse(data)
    except UserAddress.DoesNotExist:
        return JsonResponse({'error': 'Address not found'}, status=404)
   
@never_cache
def save_address(request):
    if request.method == 'POST':
        user_email = request.session.get('email')

        if not user_email:
            return JsonResponse({'success': False, 'error': 'User not logged in'}, status = 401)
        
        user = get_object_or_404(Usermodels, email=user_email)
        address_count = UserAddress.objects.filter(user=user).count()
        address_type = 'main' if address_count == 0 else 'secondary'    

        if not user.is_verified:
            return JsonResponse({'success': False, 'error': 'User not verified'}, status=403)
        
        data = json.loads(request.body.decode('utf-8'))
        fullname = data.get('fullname')
        country = data.get('country')
        street = data.get('street')
        apartment = data.get('apartment', '')
        city = data.get('city')
        district = data.get('district')
        state = data.get('state')
        zip_code = data.get('zip')
        phone = data.get('phone')

        if not is_valid_indian_pincode(zip_code):
            return JsonResponse({'success': False, 'error': 'Invalid Indian pincode'}, status=400)

        if not is_valid_indian_phone(phone):
            return JsonResponse({'success': False, 'error': 'Invalid Indian phone number'}, status=400)
        
        if not is_valid_name(fullname):
            return JsonResponse({'success': False, 'error': 'Full name must contain only letters and no spaces at the start or special characters.'}, status=400)

        if not is_valid_name(country):
            return JsonResponse({'success': False, 'error': 'Country must contain only letters and no spaces at the start.'}, status=400)

        if not is_valid_name(district):
            return JsonResponse({'success': False, 'error': 'District must contain only letters and no spaces at the start.'}, status=400)

        if not is_valid_name(state):
            return JsonResponse({'success': False, 'error': 'State must contain only letters and no spaces at the start.'}, status=400)


        address = UserAddress(user=user, fullname=fullname, phone=phone, street=street, apartment=apartment, city=city, district=district, state=state, zip_code=zip_code, country=country, type=address_type)
        address.save()

        address_data = model_to_dict(address)

        return JsonResponse({'success': True,"address": address_data})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'})


  
@never_cache  
def update_address(request, address_id):
            if request.method == 'PUT':
                try:
                    data = json.loads(request.body)
                    address = get_object_or_404(UserAddress, id=address_id)
                    address.fullname = data.get('fullname', address.fullname)
                    address.country = data.get('country', address.country)
                    address.street = data.get('street', address.street)
                    address.apartment = data.get('apartment', address.apartment)
                    address.city = data.get('city', address.city)
                    address.district = data.get('district', address.district)
                    address.state = data.get('state', address.state)
                    address.zip_code = data.get('zip', address.zip_code)
                    address.phone = data.get('phone', address.phone)

                    if not is_valid_indian_pincode(address.zip_code):
                        return JsonResponse({'success': False, 'error': 'Invalid Indian pincode'}, status=400)

                    if not is_valid_indian_phone(address.phone):
                        return JsonResponse({'success': False, 'error': 'Invalid Indian phone number'}, status=400)
                    
                    if not is_valid_name(address.fullname):
                        return JsonResponse({'success': False, 'error': 'Full name must contain only letters and no spaces at the start or special characters.'}, status=400)

                    if not is_valid_name(address.country):
                        return JsonResponse({'success': False, 'error': 'Country must contain only letters and no spaces at the start.'}, status=400)

                    if not is_valid_name(address.district):
                        return JsonResponse({'success': False, 'error': 'District must contain only letters and no spaces at the start.'}, status=400)

                    if not is_valid_name(address.state):
                        return JsonResponse({'success': False, 'error': 'State must contain only letters and no spaces at the start.'}, status=400)

                    
                    
                    address.save()

                    
                    
                    address_data = model_to_dict(address)
                
                    
                    return JsonResponse({'success': True,'address':address_data})
                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)})
            return JsonResponse({'success': False, 'error': 'Invalid request method.'})   



   
@never_cache
def delete_address(request, address_id):
    if request.method == 'GET':
        try:
            user_email = request.session.get('email')
            if not user_email:
                return JsonResponse({'success': False, 'error': 'User not logged in'}, status=401)
            
            user = get_object_or_404(Usermodels, email=user_email)
            address = get_object_or_404(UserAddress, id=address_id, user=user)
            address.is_active = False
            address.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)


def password_change(request, id):
    user = get_object_or_404(Usermodels, id=id)
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('password1')  # Rename 'password1' for clarity
        confirm_password = request.POST.get('password2') 

        if current_password != user.password1:
            messages.error(request, "Current password is incorrect")
            return redirect('password_change', id=id)
        
        if not new_password.isdigit():
            messages.error(request, "Password must contain only numbers")
            return redirect('password_change', id=id)

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('password_change', id=id)
        
        user.password1 = new_password
        user.password2 = confirm_password
        user.save()
        messages.success(request, "Password changed successfully")
        return redirect('profile')
    
    return render(request, 'user_profile/profile.html',{'user': user})

def get_wallet_data(request):
    user_email = request.session.get('email')
    user = get_object_or_404(Usermodels, email=user_email)
    wallet = Wallet.objects.get(user=user)
    transactions = WalletHistory.objects.filter(wallet=wallet).order_by('-updated_date')

    transactions_data = [
        {
            'amount': txn.amount,
            'transaction_type': txn.type,
            'new_balance': txn.new_balance,
            'updated_date': txn.updated_date.strftime('%B %d, %Y')
        }
        for txn in transactions
    ]

    data = {
        'balance': wallet.balance,
        'transactions': transactions_data
    }

    return JsonResponse(data)