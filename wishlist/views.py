from django.shortcuts import render,get_object_or_404,redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from authentication.models import Usermodels
from products.models import Product
from .models import Wishlist, WishlistItem
from cart.models import Cart, CartItems



def add_to_wishlist(request, product_id):
    user_email = request.session.get('email')
    if not user_email:
        return JsonResponse({'error': 'User not logged in'}, status=403)

    user = get_object_or_404(Usermodels, email=user_email)
    product = get_object_or_404(Product, id=product_id)
    
    wishlist, created = Wishlist.objects.get_or_create(user=user)
    
    # Check if the product is already in the wishlist
    wishlist_item = WishlistItem.objects.filter(wishlist=wishlist, product=product).first()
    if wishlist_item:
        wishlist_item.delete()
        message = 'Product removed from wishlist'
        status = 'removed'
    
    else:
        WishlistItem.objects.create(wishlist=wishlist, product=product)
        message = 'Product added to wishlist'
        status = 'added'
    if wishlist:
            wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()        
    
    return JsonResponse({'message': message, 'status': status,'wishlist_count': wishlist_count})


@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def wishlist(request):
    user_email = request.session.get('email')
    if not user_email:
        return redirect('login')

    user = get_object_or_404(Usermodels, email=user_email)
    wishlist, created = Wishlist.objects.get_or_create(user=user)
    items = wishlist.items.all()
    wishlist_products = [item.product for item in items]
    for product in wishlist_products:
    # Get the discounted price using the method defined in the Product model
        discounted_price = product.get_discounted_price()
    if wishlist:
            wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()
    cart = Cart.objects.filter(user=user).first()
    if cart:
        cart_count = CartItems.objects.filter(cart=cart).count()

    context = {
        'wishlist': wishlist,
        'items': items,
        'wishlist_products': wishlist_products,
        'wishlist_count': wishlist_count,
        'cart_count' : cart_count
    }
    return render(request, 'wishlist/wishlist.html', context)

def remove_from_wishlist(request, item_id):
    user_email = request.session.get('email')
    if not user_email:
        return JsonResponse({'error': 'User not logged in'}, status=403)

    user = get_object_or_404(Usermodels, email=user_email)
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=user)
    
    wishlist_item.delete()
    wishlist = Wishlist.objects.filter(user=user).first()
    if wishlist:
            wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()
    
    return JsonResponse({'message': 'Product removed from wishlist','wishlist_count': wishlist_count})