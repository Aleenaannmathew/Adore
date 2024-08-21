from django.contrib import messages
from django.forms import ValidationError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect
from authentication.models import Usermodels
from products.models import Category,Product,Variant
from wishlist.models import Wishlist,WishlistItem
from .models import Cart, CartItems




def update_cart_items(request):
    if request.method == 'POST':
        cart_item_id = request.POST.get('cart_item_id')
        quantity = int(request.POST.get('quantity', 0))

        if not cart_item_id or quantity <= 0:
            return JsonResponse({'error': 'Invalid data'}, status=400)

        cart_item = get_object_or_404(CartItems, id=cart_item_id)
        variant = get_object_or_404(Variant, id=cart_item.product.id)
        
        if quantity > variant.stock :
            return JsonResponse({'success': False, 'error': 'Variant out of stock'}, status=400)

        max_quantity = 10
        if quantity > max_quantity:
            return JsonResponse({'success': False, 'error': f'Maximum quantity per person is {max_quantity}'}, status=400)

        # Calculate the difference in quantity
        quantity_difference = quantity - cart_item.quantity

        # Update the quantity and save the cart item
        cart_item.quantity = min(quantity, max_quantity)
        cart_item.save()

        # Update the variant stock accordingly
        # variant.stock -= quantity_difference
        # variant.save()

        sub_total = cart_item.get_item_price()
        total = cart_item.cart.get_total_price()

        return JsonResponse({
            'message': 'Cart item updated successfully',
            'sub_total': sub_total,
            'total': total
        })
    else:
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
 
def add_to_cart(request, variant_id):
    if request.method == 'GET':
        
        # check if the user is logged in 
        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'success': False, 'error': 'User not logged in'}, status = 401)
        
        user = get_object_or_404(Usermodels, email=user_email)
        if not user.is_verified:
            return JsonResponse({'success': False, 'error': 'User not verified'}, status=403)
        
        # Get the variant
        variant = get_object_or_404(Variant, id=variant_id)
        
        # Check variant stock
        if variant.stock <= 0:
            return JsonResponse({'success': False, 'error': 'Variant is out of stock'}, status=400)
        
        # Get or create the cart for the user
        cart, created = Cart.objects.get_or_create(user=user)
        
        # Get or create the cart item
        cart_item, created = CartItems.objects.get_or_create(cart=cart, product=variant)
        
        current_quantity = cart_item.quantity
        

        if current_quantity + 1 > variant.max_quantity_per_person:
            return JsonResponse({'success': False, 'error': f'Maximum quantity per person is {variant.max_quantity_per_person}'}, status=400)

        if current_quantity + 1 > variant.stock:
            return JsonResponse({'success': False, 'error': 'Variant out of stock'}, status=400)
            
        
        # Update the cart item quantity
        if created:
            cart_item.quantity = 1
        else:
            cart_item.quantity += 1
        cart_item.save()
        cart_count = CartItems.objects.filter(cart=cart).count()
        
        
        return JsonResponse({'success': True, 'cart_item_count': CartItems.objects.filter(cart=cart).count(),'cart_count': cart_count})
    
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
 
def shop_cart(request):
    user_email = request.session.get('email')
    if not user_email:
        return redirect('login')
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
            cart_items = CartItems.objects.filter(cart=cart)

    if not cart:
        return render(request, 'cart/shopcart.html', {'cart': None})
    
    return render(request, 'cart/shopcart.html', {'cart': cart, 'cart_id': cart.id,'wishlist_count': wishlist_count,'cart_count': cart_count,'cart_items': cart_items})


def remove_cart_item(request):
    if request.method == 'POST':
        cart_item_id = request.POST.get('cart_item_id')
        cart_item = get_object_or_404(CartItems, id=cart_item_id)
        variant = get_object_or_404(Variant, id=cart_item.product.id)
        # variant.stock += cart_item.quantity
        # variant.save()
        cart_item.delete()
        total = cart_item.cart.get_total_price()
        if 'email' in request.session:
            user_email = request.session['email']
            user = get_object_or_404(Usermodels, email=user_email)
            cart = Cart.objects.filter(user=user).first()
        if cart:
            cart_count = CartItems.objects.filter(cart=cart).count()
        return JsonResponse({'success': True, 'total': total,'cart_count':cart_count})
    return JsonResponse({'success': False, 'error':'Invalid request method'}, status=400)



