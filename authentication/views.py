from django.contrib.auth import logout
from django.contrib import messages
from django.forms import ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from .models import Usermodels,Referral
from adminpanel.models import Banner
from checkout.models import Wallet,WalletHistory
from products.models import Category,CategoryOffer,Product,ProductOffer
from django.views.decorators.cache import cache_control
from django.http import JsonResponse
from django.urls import reverse
from wishlist.models import Wishlist,WishlistItem
from cart.models import Cart,CartItems
from django.db.models import Q
from django.db.models import OuterRef, Subquery, Q,Avg,Count
from decimal import Decimal
from django.utils import timezone




# Create your views here.


@cache_control(no_cache=True,must_revalidate=True,no_store=True)
def home(request):
    categories = Category.objects.filter(is_listed=True).all()
    products = Product.objects.filter(is_available=True).prefetch_related('variants__images')
    
    search_query = request.GET.get('s','')

    wishlist_count = 0
    cart_count = 0
    if search_query:
        return redirect(reverse('showproducts') + '?s=' + search_query)

    if search_query:
        products = products.filter(Q(name__icontains=search_query))

    offers = ProductOffer.objects.filter(product=OuterRef('pk'), is_active=True)
    products = products.annotate(
        offer_exists=Subquery(offers.values('id')[:1]),
        discount_percentage=Subquery(offers.values('discount_percentage')[:1]),
        average_rating=Avg('review__rating'),  
        review_count=Count('review') 
    )

    for product in products:
        if product.offer_exists and ProductOffer.objects.get(id=product.offer_exists).is_valid():
            original_price = product.variants.first().price
            discount_percentage = Decimal(product.discount_percentage)  # Convert to Decimal
            discounted_price = original_price - (original_price * (discount_percentage / Decimal(100)))
            product.discounted_price = discounted_price
        else:
            product.discounted_price = product.variants.first().price if product.variants.exists() else None

    products = products.distinct()
    

    if 'email' in request.session:
        user_email = request.session['email']
        user = get_object_or_404(Usermodels, email=user_email)
        
        wishlist= Wishlist.objects.filter(user=user).first()
        if wishlist:
            wishlist_count = wishlist.items.count()
        
        cart = Cart.objects.filter(user=user).first()
        if cart:
            cart_count = CartItems.objects.filter(cart=cart).count()

    banners = Banner.objects.filter(is_active=True)

    # Get category offers
    today = timezone.now().date()
    # Annotate categories with category offers
    category_offers_subquery = CategoryOffer.objects.filter(
        category=OuterRef('pk'),
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).values('discount_percentage')[:1]

    categories = categories.annotate(
        discount_percentage=Subquery(category_offers_subquery)
    )

    # Compute the discounted price if needed (not required for categories, but for consistency in approach)
    for category in categories:
        if category.discount_percentage:
            discount_percentage = Decimal(category.discount_percentage)  # Convert to Decimal
          

    context = {
        'categories': categories,
        'products': products,
        'wishlist_count': wishlist_count,
        'cart_count': cart_count,
        'banners': banners,
        
        
    }
    return render(request, 'authentication/home.html', context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def user_login(request):
    if "email" in request.session:
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = Usermodels.objects.get(email=email,password1=password)
        except Usermodels.DoesNotExist:
            user = None

        if user is not None :  # Assuming you're using Django's built-in User model
            if user.is_block:
                messages.error(request, "Your account is blocked")
                return redirect("login")

            if user.is_verified:
                request.session.flush()
                request.session["email"] = email
                return redirect("home")
            else:
                messages.error(request, "Account not verified. Please check your email for the OTP.")
                return redirect("login")
        else:
            messages.error(request, "Invalid email or password")
            return redirect("login")

    return render(request, 'authentication/login.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def forget_pass(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        #check if the email exists in the database
        if Usermodels.objects.filter(email=email).exists():
            #Generate and send OTP
            otp = generate_otp(request)
            send_otp_email(otp,email)
            #Redirect to OTP page with user ID
            user = Usermodels.objects.get(email=email)
            return HttpResponseRedirect(reverse('otp', args=[user.id, 'password_reset']))
        else:
            messages.error(request, "Email not registered.Please register.")
            return redirect('register') # Redirect to register page if email not found
        
    return render(request,'authentication/forget_pass.html')    
    


def register(request):  
    if "email" in request.session:
        return redirect("home")
    
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        pass1 = request.POST.get('password1')
        pass2 = request.POST.get('password2')
        referral_code = request.POST.get('referral_code')
        
        #name validation
        if not name.replace(" "," ").isalpha():
            messages.error(request,"username must contain only alphabets")
            return redirect('register')
        
        #phone number validation
        if not phone.isdigit() or len(phone) != 10:
            messages.error(request, "Phone number must contain 10 digits")
            return render(request, 'authentication/register.html')
        
        #password validation
        if not pass1.isdigit():
            messages.error(request,"password must contain only numbers")
            return redirect('register')
        #email validation
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request,"Invalid email address")
            return redirect('register')    
        
        if pass1 != pass2:
            messages.error(request, "Passwords do not match")
            return redirect('register')
        

        elif Usermodels.objects.filter(email=email).exists():
            messages.error(request, "This Email address already exists")
            return render(request, 'authentication/register.html')

        else:
            myuser = Usermodels(
                name=name,
                email=email,
                phone=phone,
                password1=pass1,
                password2=pass2,
            )
            myuser.save()

            if referral_code:
                try:
                    referred_by = Referral.objects.get(referral_code=referral_code).user
                   
                    referral = Referral.objects.get(user=myuser)
                    referral.referred_by=referred_by
                    referral.save()
                    # Add ₹100 to the wallet of the user who referred
                    wallet, created = Wallet.objects.get_or_create(user=referred_by)
                    wallet.balance += 100
                    wallet.save()
                    WalletHistory.objects.create(wallet=wallet, type=WalletHistory.CREDIT, amount=100, new_balance=wallet.balance)
                    messages.success(request, "Referral successful! ₹100 added to the referrer's wallet.")
                except Referral.DoesNotExist:
                    messages.error(request, "Invalid referral code")

                    
            otp = generate_otp(request)  # Generate and save OTP in session
            print(otp)
            send_otp_email(otp, myuser.email)
            return HttpResponseRedirect(reverse('otp', args=[myuser.id,'registration']))

    return render(request, 'authentication/register.html')


@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def otp(request, id, purpose):
    user = get_object_or_404(Usermodels, id=id)
    if request.method == "POST":
        # Capture the individual OTP inputs and concatenate them
        otp1 = request.POST.get("otp1")
        otp2 = request.POST.get("otp2")
        otp3 = request.POST.get("otp3")
        otp4 = request.POST.get("otp4")
        entered_otp = f"{otp1}{otp2}{otp3}{otp4}"
      
        session_otp = request.session.get('otp')
        if entered_otp == session_otp:
            user.is_verified = True
            user.save()
            if purpose == 'registration':  
                return redirect("login")
            elif purpose == 'password_reset':
                return redirect("change_password", id=user.id)
        else: 
            messages.error(request, "OTP you entered is not correct")
            return redirect("otp", id=id, purpose=purpose)

    return render(request, "authentication/otp.html", {"id": id, "purpose": purpose})

def generate_otp(request):
    otp = get_random_string(length=4, allowed_chars="1234567890")
    request.session['otp'] = otp
    return otp

def send_otp_email(otp, email):
    subject = "Your OTP for Signup"
    message = f"Your OTP is {otp}. Enter this code to complete your signup."
    from_email = "aleenamathewinformal@gmail.com"
    to_email = [email]
    send_mail(subject, message, from_email, to_email)


def resend_otp(request,id):
    # Get the user object based on the provided id
    user = get_object_or_404(Usermodels,id=id)
    otp = generate_otp(request)
   
    send_otp_email(otp, user.email)
    return JsonResponse({"message": "OTP resent succesfully."})

@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def change_password(request, id):
    user = get_object_or_404(Usermodels, id=id)
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        #password validation
        if not password1.isdigit():
            messages.error(request,"password must contain only numbers")
            return redirect('change_password', id=id)

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect('change_password', id=id)
        
        user.password1 = password1
        user.password2 = password2
        user.save()
        messages.success(request, "Password changed successfully")
        return redirect('login')
    
    return render(request, 'authentication/change_pass.html', {"id":id})


def user_logout(request):
    try:
        del request.session["email"]
        logout(request)
    except KeyError:
        pass
    messages.success(request, "You have logged out successfully.")
    return redirect("login") 

def contact(request):

    return render(request, 'user/contactus.html')


def faq(request):

    return render(request,'user/faq.html')

def about(request):
    return render(request, 'user/aboutus.html')