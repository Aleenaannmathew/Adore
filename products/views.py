from django.contrib import messages
import json
from django.forms import ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from .models import Product
from django.utils import timezone
from django.db.models import OuterRef, Subquery, Q
from authentication.models import Usermodels
from wishlist.models import Wishlist, WishlistItem 
from django.db.models import Count,Avg,Q
from products.models import Category,CategoryOffer,Product,Variant,Variant_image,ProductOffer,Review
from checkout.models import Order,OrderItem
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.http import JsonResponse
from django.urls import reverse
from cart.models import Cart,CartItems
from wishlist.models import Wishlist
from decimal import Decimal


# Create your views here.


def show_allproducts(request):
    category_slug = request.GET.get('category', None)
    sort_by = request.GET.get('sort_by', 'default')
    price_ranges = request.GET.getlist('price-range')
    colors = request.GET.getlist('color')
    search_query = request.GET.get('s','')
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_listed=True)
        products = Product.objects.prefetch_related('variants__images').filter(category=category, is_available=True)
    else:
        products = Product.objects.prefetch_related('variants__images').filter(is_available=True)

    if price_ranges:
        price_filter = Q()
        for price_range in price_ranges:
            if price_range == '0-500':
                price_filter |= Q(variants__price__gte=0, variants__price__lt=500)
            elif price_range == '500-1000':
                price_filter |= Q(variants__price__gte=500, variants__price__lt=1000)
            elif price_range == '1000-2000':
                price_filter |= Q(variants__price__gte=1000, variants__price__lt=2000)
            elif price_range == '2000-3000':
                price_filter |= Q(variants__price__gte=2000, variants__price__lt=3000)
            elif price_range == '3000-and-above':
                price_filter |= Q(variants__price__gte=3000)
        products = products.filter(price_filter)

     # Apply color filter
    if colors:
        color_filter = Q()
        for color in colors:
            color_filter |= Q(variants__color__iexact=color)
        products = products.filter(color_filter)    

    if search_query:
        products = products.filter(Q(name__icontains=search_query))

    products = products.annotate(
        average_rating=Avg('review__rating'),
        review_count=Count('review')
    )

    if sort_by == 'popularity':
        products = products.annotate(num_wishlist=Count('wishlistitem')).order_by('-num_wishlist')
    elif sort_by == 'average_rating':
        products = products.order_by('average_rating')
    elif sort_by == 'latest':
        products = products.order_by('-id')
    elif sort_by == 'price_low_to_high':
        products = products.order_by('variants__price')
    elif sort_by == 'price_high_to_low':
        products = products.order_by('-variants__price')  
    else:
        products = products.order_by('id')    

     
    
    # Annotate with current valid offers
    today = timezone.now().date()
    active_product_offers = ProductOffer.objects.filter(
        product=OuterRef('pk'),
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    )
    products = products.annotate(
        offer_exists=Subquery(active_product_offers.values('id')[:1]),
        discount_percentage=Subquery(active_product_offers.values('discount_percentage')[:1])
    )
    
    # Annotate with current valid category offers
    category_offers = CategoryOffer.objects.filter(
        category=OuterRef('category'),
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    )
    products = products.annotate(
        category_offer_exists=Subquery(category_offers.values('id')[:1]),
        category_discount_percentage=Subquery(category_offers.values('discount_percentage')[:1])
    )
    
    # Calculate discounted prices
    for product in products:
        original_price = None
        discounted_price = None

        if product.offer_exists:
            original_price = product.variants.first().price
            discount_percentage = Decimal(product.discount_percentage)
            discounted_price = original_price - (original_price * (discount_percentage / Decimal('100')))
        elif product.category_offer_exists:
            original_price = product.variants.first().price
            discount_percentage = Decimal(product.category_discount_percentage)
            discounted_price = original_price - (original_price * (discount_percentage / Decimal('100')))
        else:
            discounted_price = product.variants.first().price if product.variants.exists() else None

        product.discounted_price = discounted_price
        print(f"Product: {product.name}, Original Price: {original_price}, Discounted Price: {discounted_price}")

    products = products.distinct()


    categories = Category.objects.annotate(total_products=Count('product')).filter(is_listed=True).order_by('id')  # Ensure consistent ordering (Change 2)
    variants = Variant.objects.filter(is_available=True).order_by('color').distinct('color')  # Ensure consistent ordering (Change 3)
    products_count = Product.objects.prefetch_related('variants__images').filter(is_available=True).count()
    
    
    wishlist_count = 0
    cart_count = 0
    if 'email' in request.session:
        user_email = request.session.get('email')
        if user_email:
            
            user = get_object_or_404(Usermodels, email=user_email)
            wishlist, created = Wishlist.objects.get_or_create(user=user)
            wishlist_count = wishlist.items.count()

        cart = Cart.objects.filter(user=user).first()
        if cart:
            cart_count = CartItems.objects.filter(cart=cart).count()    

    paginator = Paginator(products, 9)  # Show 9 products per page
    page = request.GET.get('page')
    
    try:
        products_paginated = paginator.page(page)
    except PageNotAnInteger:
        products_paginated = paginator.page(1)
    except EmptyPage:
        products_paginated = paginator.page(paginator.num_pages)

    context = {
        'categories': categories,
        'products': products_paginated,
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'variants': variants,
        'current_category': category if category_slug else None,
        'paginator': paginator,
        'products_count': products_count,
        'page_obj': products_paginated,
        'sort_by': sort_by,
        'price_ranges': price_ranges,
        'selected_colors': colors,
        'search_query': search_query,
    }
    
    return render(request, 'user/allproducts.html', context)

def round_to_nearest_half(value):
    if value is None:
        return 0  # or some other default value if needed
    return round(value * 2) / 2

def shop_details(request, product_slug):
    user_email = request.session.get('email')
    product = get_object_or_404(Product, slug=product_slug)
    review = False
    variants = product.variants.prefetch_related('images').all()
    first_variant = variants.first()

    offers = ProductOffer.objects.filter(product=OuterRef('pk'), is_active=True)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id).prefetch_related('variants__images').annotate(
        offer_exists=Subquery(offers.values('id')[:1]),
        discount_percentage=Subquery(offers.values('discount_percentage')[:1])
    )

    for related_product in related_products:
        if related_product.offer_exists and ProductOffer.objects.get(id=related_product.offer_exists).is_valid():
            original_price = related_product.variants.first().price
            discount_percentage = Decimal(related_product.discount_percentage)  # Convert to Decimal
            discounted_price = original_price - (original_price * (discount_percentage / Decimal(100)))
            related_product.discounted_price = discounted_price
        else:
            related_product.discounted_price = related_product.variants.first().price if related_product.variants.exists() else None

    related_products = related_products.distinct()

    if user_email:
        user = get_object_or_404(Usermodels, email=user_email)
        order_item = OrderItem.objects.filter(order__user=user, product=product, order__order_status="delivered").first()

        # Check if the user has already reviewed the product
        current_review = Review.objects.filter(user=user, product=product).first()
        if current_review:
            review = False
        elif order_item:
            review = True  # Set review to True if no review found
    product_reviews = Review.objects.filter(product=product)
    average_rating =product_reviews.aggregate(
    average_rating=Avg('rating')
     )['average_rating']
    rounded_rating = round_to_nearest_half(average_rating)
    print( "hiiiii",  rounded_rating)
    variants = product.variants.prefetch_related('images').all()
    first_variant = variants.first()
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]


    wishlist_count = 0
    cart_count = 0


    if 'email' in request.session:
        user_email = request.session['email']
        user = get_object_or_404(Usermodels, email=user_email)

        wishlist = Wishlist.objects.filter(user=user).first()
        if wishlist:
            wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()

        cart = Cart.objects.filter(user=user).first()
        if cart:
            cart_count = CartItems.objects.filter(cart=cart).count()

    user_email = request.session.get('email')
    wishlist_products = []
    if user_email:
        user = get_object_or_404(Usermodels, email=user_email)
        wishlist = Wishlist.objects.filter(user=user).first()
        if wishlist:
            wishlist_products = [item.product for item in wishlist.items.all()]
            print(wishlist_products)


    context = {
        'product':product,
        'variants':variants,
        'first_variant':first_variant,
        'related_products':related_products,
        'wishlist_products': wishlist_products,
        'wishlist_count':  wishlist_count,
        'cart_count':cart_count,
        'review': review,
        'product_review':product_reviews,
        'rounded_rating':rounded_rating
    }
    return render(request,'user/shop-details.html', context)

def variant_images_ajax(request, variant_id):
    images = Variant_image.objects.filter(variant_id=variant_id, is_active=True)
    image_urls = [image.image.url for image in images]
    variant_quantity=get_object_or_404(Variant,id=variant_id)
    return JsonResponse({'images':image_urls,'quantity':variant_quantity.stock})

def get_variants(request):
    product_id = request.GET.get('product_id')
    if product_id:
        try:
            product = get_object_or_404(Product, id=product_id)
            # Query variants based on product_id
            variants = Variant.objects.filter(product=product)
            variant_list = []
            
            for variant in variants:
                # Calculate discounted price
                discounted_price = int(product.get_discounted_price() or variant.price)
                
                variant_data = {
                    'id': variant.id,
                    'color': variant.color,
                    'price': discounted_price,  # Use discounted price if available
                    'stock': variant.stock,
                    'is_available': variant.is_available,
                }
                variant_list.append(variant_data)
                
            return JsonResponse({'variants': variant_list}, safe=False)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Product ID not provided'}, status=400)


def submit_comment(request):
    if request.method == 'POST':
        try:
            user_email = request.session.get('email')
            if not user_email:
                return JsonResponse({'status': 'error', 'message': 'User not logged in'}, status=401)
           
            data = json.loads(request.body)
            product_name = data.get('product_name')
            rating = data.get('rating')
            comment = data.get('comment')
            print(product_name)
            
            if not product_name or rating is None or comment is None:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
            
            rating = float(rating)
            if rating < 0.5 or rating > 5:
                return JsonResponse({'status': 'error', 'message': 'Invalid rating value'}, status=400)

            user = get_object_or_404(Usermodels, email=user_email)
            print(user)
            product = get_object_or_404(Product, name__iexact=product_name)
            print(f"Product: {product}")
            

            if Review.objects.filter(user=user, product=product).exists():
                return JsonResponse({'status': 'error', 'message': 'Review already exists'}, status=400)
            
            order_item = OrderItem.objects.filter(
                order__user=user,
                product=product,
                order__order_status='delivered'
            ).order_by('-order__delivered_date').first()
            if not order_item:
                return JsonResponse({'status': 'error', 'message': 'No matching order item found'}, status=400)

            order = order_item.order
            order_status = order.order_status
            print(f"Order Item: {order_item}")
            print(f"Order Status: {order_status}")

            if order_status.lower() != "delivered":
                return JsonResponse({'status': 'error', 'message': 'Order not delivered yet'}, status=400)

            
            

            Review.objects.create(
                user=user,
                product=product,
                rating=rating,
                comment=comment
            )

            return JsonResponse({'status': 'success', 'product_name': product_name})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)

    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
