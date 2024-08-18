from django.shortcuts import render,redirect,get_object_or_404
from cart.models import Cart,CartItems
from django.contrib import messages
from products.models import Product, Variant
from authentication.models import Usermodels
from checkout.models import Order,OrderItem,Wallet,WalletHistory
from user_profile.models import UserAddress
from coupon.models import Coupon
from django.utils import timezone
from django.http import JsonResponse
import json
from django.views.decorators.cache import never_cache
from wishlist.models import Wishlist, WishlistItem 
import razorpay
from django.conf import settings
from django.db import transaction
from datetime import timedelta
from django.http import HttpResponse
from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa
# Create your views here.
@never_cache
def checkout(request):
   
    cart_id = request.GET.get('cart_id')
    user_email = request.session.get('email')
    if not user_email:
        return redirect('login')
    
    user = get_object_or_404(Usermodels, email=user_email)
    wishlist = Wishlist.objects.filter(user=user).first()
    if wishlist:
       wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()
    cart = get_object_or_404(Cart, id=cart_id, user=user)
    if cart:
       cart_count = CartItems.objects.filter(cart=cart).count()

    cart_items = CartItems.objects.filter(cart=cart)
    if not cart_items:
        messages.error(request, "No products in cart")
        return redirect("showcart")
    
    addresses = UserAddress.objects.filter(user=user, is_active=True)

    cart_subtotal = sum(item.get_item_price() for item in cart_items)
    shipping_charge = 40


    now = timezone.now()
    available_coupons = Coupon.objects.filter(valid_from__lte=now, valid_to__gte=now, minimum_amount__lte=cart_subtotal,is_active=True)

    coupon_discount = 0
    coupon_id = request.GET.get('coupon_id')
    if coupon_id:
        coupon = get_object_or_404(Coupon, id=coupon_id)
        if coupon.is_valid() and cart_subtotal >= coupon.minimum_amount:
            coupon_discount = coupon.discount_price

    order_total = cart_subtotal + shipping_charge - coupon_discount        


    
    context = {
        'cart_id': cart_id,
        'cart_items': cart_items,
        'addresses' : addresses,
        'cart_subtotal' : cart_subtotal,
        'shipping_charge': shipping_charge,
        'coupon_discount': coupon_discount,
        'order_total': order_total,
        'available_coupons' : available_coupons,
        'coupon_id': coupon_id,
        'wishlist_count': wishlist_count,
        'cart_count':cart_count
    }
    

    return render(request, 'checkout/checkout.html', context)



@never_cache
def place_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        cart_items = data.get('cartItems')
        address_id = data.get('addressId')
        payment_method = data.get('paymentMethod')
        shipping_amount = data.get('shippingAmount', 0)
        coupon_code = data.get('couponCode')
        cartId = data.get('cartId')
        

        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'success': False, 'message': 'User not logged in'}, status=403)

        user = get_object_or_404(Usermodels, email=user_email)
        address = get_object_or_404(UserAddress, id=address_id, is_active=True, user=user)
        cart = get_object_or_404(Cart, id=cartId, user=user)
        cart_items_PRODUCTS = CartItems.objects.filter(cart=cart)
        if not cart_items_PRODUCTS:
            return JsonResponse({'success': False, 'message': 'no productts available'}, status=403)
        coupon = None
        discount_amount = 0

        if coupon_code:
            try:
                coupon = Coupon.objects.get( coupon_code=coupon_code, is_active=True)
                discount_amount = coupon.discount_price  # Assuming the coupon has a discount_value field
            except Coupon.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Invalid coupon code'}, status=400)

        total_price = 0
        order_items = []

        for item in cart_items:
            variant_id = item.get('variant_id')
            quantity = int(item.get('quantity'))
            variant = get_object_or_404(Variant, id=variant_id)

            # Check stock availability
            if variant.stock < quantity:
                return JsonResponse({'success': False, 'message': f'Insufficient stock for {variant.product.name} ({variant.color})'}, status=400)
            
            product = variant.product
            price = product.get_discounted_price() or variant.price  # Assuming each variant has a price field
            
            total_price += price * quantity
            
            order_item = OrderItem(
                product=product,
                variant=variant,
                price=price,
                quantity=quantity
            )
            order_items.append(order_item)

        total_price = total_price - discount_amount + shipping_amount

        # Restrict COD for orders above ₹1000
        if payment_method == 'cod' and total_price > 1000:
            return JsonResponse({'success': False, 'message': 'COD is not allowed for orders above ₹1000, Please choose other payment method'}, status=400)

        order = Order(
            user=user,
            address=address,
            total_price=total_price,
            payment_method=payment_method,
            shipping_charge=shipping_amount,
            coupon=coupon,
            payment_status='completed',
            order_status='ordered',
            order_date=timezone.now()
        )
        order.save()

        for order_item in order_items:
            order_item.order = order
            order_item.save()
        
            # Update stock after order creation
            variant.stock -= order_item.quantity
            variant.save()

           
        cart_items_PRODUCTS .delete()
        

        return JsonResponse({'success': True, 'message': 'Order placed successfully', 'order_id': order.id})


    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

@never_cache
def order_success(request,order_id):
    user_email = request.session.get('email')
    if not user_email:
        return redirect('login')
    user = get_object_or_404(Usermodels, email=user_email)

    wishlist = Wishlist.objects.filter(user=user).first()
    if wishlist:
       wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()

    cart = Cart.objects.filter(user=user).first()
   
    if cart:
       cart_count = CartItems.objects.filter(cart=cart).count()

    order=get_object_or_404(Order, id=order_id)
    return render(request, 'checkout/ordersuccess.html', {'order':order,'wishlist_count': wishlist_count,'cart_count':cart_count})



def order_details(request, order_id):
    user_email = request.session.get('email')
    if not user_email:
        return redirect('login')
    user = get_object_or_404(Usermodels, email=user_email)
    wishlist = Wishlist.objects.filter(user=user).first()
    if wishlist:
       wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()
    cart = get_object_or_404(Cart, user=user)
    if cart:
       cart_count = CartItems.objects.filter(cart=cart).count()
    order = get_object_or_404(Order, id=order_id, user=user)
    address = UserAddress.objects.filter(user=user)
    
    context = {
        'order': order,
        'order_items': order.items.all(),
        'address': address,
        'wishlist_count':wishlist_count,
        'cart_count':cart_count

    }

    return render(request, 'checkout/orderdetails.html', context)


def create_razorpay_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        cart_items = data.get('cartItems')
        address_id = data.get('addressId')
        payment_method = data.get('paymentMethod')
        shipping_amount = data.get('shippingAmount', 0)
        coupon_code = data.get('couponCode')
        cartId = data.get('cartId')
        

        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'success': False, 'message': 'User not logged in'}, status=403)

        user = get_object_or_404(Usermodels, email=user_email)
        address = get_object_or_404(UserAddress, id=address_id, is_active=True, user=user)
        cart = get_object_or_404(Cart, id=cartId, user=user)
        cart_items_PRODUCTS = CartItems.objects.filter(cart=cart)
        if not cart_items_PRODUCTS:
            return JsonResponse({'success': False, 'message': 'no productts available'}, status=403)
        coupon = None
        discount_amount = 0

        if coupon_code:
            try:
                coupon = Coupon.objects.get( coupon_code=coupon_code, is_active=True)
                discount_amount = coupon.discount_price  # Assuming the coupon has a discount_value field
            except Coupon.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Invalid coupon code'}, status=400)

        total_price = 0
        order_items = []

        for item in cart_items:
            variant_id = item.get('variant_id')
            quantity = int(item.get('quantity'))
            variant = get_object_or_404(Variant, id=variant_id)
            product = variant.product
            price = product.get_discounted_price() or variant.price # Assuming each variant has a price field
            
            total_price += price * quantity
            
            order_item = OrderItem(
                product=product,
                variant=variant,
                price=price,
                quantity=quantity
            )
            order_items.append(order_item)

        total_price = total_price - discount_amount + shipping_amount
        amount_in_paise = int(total_price * 100)
        # Calculate the order amount
      
        
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment = client.order.create({
            "amount":amount_in_paise,  # Convert amount to paise
            "currency": "INR",
            "payment_capture": 1
        })

        return JsonResponse({
            'success': True,
            'amount':amount_in_paise,
            'order_id': payment['id']
        })
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def verify_razorpay_payment(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            params_dict = {
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            }

            client.utility.verify_payment_signature(params_dict)
            order_data = data.get('orderData')  # Correctly access orderData from JSON data
            print("hiiiiiiiii",order_data )
            cart_items = order_data.get('cartItems')
            address_id = order_data.get('addressId')
            payment_method = order_data.get('paymentMethod')
            shipping_amount = order_data.get('shippingAmount', 0)
            coupon_code = order_data.get('couponCode')
            cart_id = order_data.get('cartId')

            user_email = request.session.get('email')
            if not user_email:
                return JsonResponse({'success': False, 'message': 'User not logged in'}, status=403)

            user = get_object_or_404(Usermodels, email=user_email)
            address = get_object_or_404(UserAddress, id=address_id, is_active=True, user=user)
            cart = get_object_or_404(Cart, id=cart_id, user=user)
            cart_items_PRODUCTS = CartItems.objects.filter(cart=cart)
            if not cart_items_PRODUCTS:
                return JsonResponse({'success': False, 'message': 'No products available in the cart'}, status=403)

            coupon = None
            discount_amount = 0

            if coupon_code:
                try:
                    coupon = Coupon.objects.get(coupon_code=coupon_code, is_active=True)
                    discount_amount = coupon.discount_price  # Assuming the coupon has a discount_price field
                except Coupon.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Invalid coupon code'}, status=400)

            total_price = 0
            order_items = []

            for item in cart_items:
                variant_id = item.get('variant_id')
                quantity = int(item.get('quantity'))
                variant = get_object_or_404(Variant, id=variant_id)

                # Check stock availability
                if variant.stock < quantity:
                    return JsonResponse({'success': False, 'message': f'Insufficient stock for {variant.product.name} ({variant.color})'}, status=400)
            
                product = variant.product
                price = product.get_discounted_price() or variant.price   # Assuming each variant has a price field

                total_price += price * quantity

                order_item = OrderItem(
                    product=product,
                    variant=variant,
                    price=price,
                    quantity=quantity
                )
                order_items.append(order_item)

            total_price = total_price - discount_amount + shipping_amount

            order = Order(
                user=user,
                address=address,
                total_price=total_price,
                payment_method=payment_method,
                shipping_charge=shipping_amount,
                coupon=coupon,
                payment_status='completed',
                order_status='ordered',
                order_date=timezone.now(),
                razorpay_payment_id=data['razorpay_payment_id'],
                razorpay_order_id=data['razorpay_order_id'],
                razorpay_signature=data['razorpay_signature']
            )
            order.save()

            for order_item in order_items:
                order_item.order = order
                order_item.save()

                # Update stock after order creation
                variant.stock -= order_item.quantity
                variant.save()

            cart_items_PRODUCTS.delete()

            # Your order placement code here

            return JsonResponse({'success': True, 'order_id': order.id})  # Return the actual order ID
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'success': False, 'message': 'Payment verification failed.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def create_wallet_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        cart_items = data.get('cartItems')
        address_id = data.get('addressId')
        payment_method = data.get('paymentMethod')
        shipping_amount = data.get('shippingAmount', 0)
        coupon_code = data.get('couponCode')
        cart_id = data.get('cartId')

        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'success': False, 'message': 'User not logged in'}, status=403)

        user = get_object_or_404(Usermodels, email=user_email)
        address = get_object_or_404(UserAddress, id=address_id, is_active=True, user=user)
        cart = get_object_or_404(Cart, id=cart_id, user=user)
        cart_items_PRODUCTS = CartItems.objects.filter(cart=cart)
        if not cart_items_PRODUCTS:
            return JsonResponse({'success': False, 'message': 'No products available in the cart'}, status=403)

        coupon = None
        discount_amount = 0

        if coupon_code:
            try:
                coupon = Coupon.objects.get(coupon_code=coupon_code, is_active=True)
                discount_amount = coupon.discount_price  # Assuming the coupon has a discount_price field
            except Coupon.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Invalid coupon code'}, status=400)

        total_price = 0
        order_items = []

        for item in cart_items:
            variant_id = item.get('variant_id')
            quantity = int(item.get('quantity'))
            variant = get_object_or_404(Variant, id=variant_id)

            # Check stock availability
            if variant.stock < quantity:
                return JsonResponse({'success': False, 'message': f'Insufficient stock for {variant.product.name} ({variant.color})'}, status=400)
            
            product = variant.product
            price = product.get_discounted_price() or variant.price   # Assuming each variant has a price field

            total_price += price * quantity

            order_item = OrderItem(
                product=product,
                variant=variant,
                price=price,
                quantity=quantity
            )
            order_items.append(order_item)

        total_price = total_price - discount_amount + shipping_amount

        # Check if the user has sufficient balance in wallet
        user_wallet = get_object_or_404(Wallet, user=user)
        if user_wallet.balance < total_price:
            return JsonResponse({'success': False, 'message': 'Insufficient balance in wallet'}, status=400)

        with transaction.atomic():
            order = Order(
                user=user,
                address=address,
                total_price=total_price,
                payment_method=payment_method,
                shipping_charge=shipping_amount,
                coupon=coupon,
                payment_status='completed',
                order_status='ordered',
                order_date=timezone.now()
            )
            order.save()

            for order_item in order_items:
                order_item.order = order
                order_item.save()

                # Update stock after order creation
                variant.stock -= order_item.quantity
                variant.save()

            # Deduct the order total from user's wallet balance
            user_wallet.balance -= total_price
            user_wallet.save()

            # Record wallet history
            WalletHistory.objects.create(
                wallet=user_wallet,
                type=WalletHistory.DEBIT,
                amount=total_price,
                new_balance=user_wallet.balance
            )

            cart_items_PRODUCTS.delete()

            return JsonResponse({'success': True, 'message': 'Order placed successfully', 'order_id': order.id})

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def handle_failed_payment(request):
    if request.method == 'POST':
   
        data = json.loads(request.body)

        cart_items = data.get('cartItems')
        address_id = data.get('addressId')
        payment_method = data.get('paymentMethod')
        shipping_amount = data.get('shippingAmount', 0)
        coupon_code = data.get('couponCode')
        cartId = data.get('cartId')
        

        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({'success': False, 'message': 'User not logged in'}, status=403)

        user = get_object_or_404(Usermodels, email=user_email)
        address = get_object_or_404(UserAddress, id=address_id, is_active=True, user=user)
        cart = get_object_or_404(Cart, id=cartId, user=user)
        cart_items_PRODUCTS = CartItems.objects.filter(cart=cart)
        if not cart_items_PRODUCTS:
            return JsonResponse({'success': False, 'message': 'no productts available'}, status=403)
        coupon = None
        discount_amount = 0

        if coupon_code:
            try:
                coupon = Coupon.objects.get( coupon_code=coupon_code, is_active=True)
                discount_amount = coupon.discount_price  # Assuming the coupon has a discount_value field
            except Coupon.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Invalid coupon code'}, status=400)

        total_price = 0
        order_items = []

        for item in cart_items:
            variant_id = item.get('variant_id')
            quantity = int(item.get('quantity'))
            variant = get_object_or_404(Variant, id=variant_id)
            product = variant.product
            price = product.get_discounted_price() or variant.price  # Assuming each variant has a price field
            
            total_price += price * quantity
            
            order_item = OrderItem(
                product=product,
                variant=variant,
                price=price,
                quantity=quantity
            )
            order_items.append(order_item)

        total_price = total_price - discount_amount + shipping_amount

        order = Order(
            user=user,
            address=address,
            total_price=total_price,
            
            shipping_charge=shipping_amount,
            coupon=coupon,
            order_date=timezone.now()
        )
        order.save()

        for order_item in order_items:
            order_item.order = order
            order_item.save()

           
        cart_items_PRODUCTS .delete()

        return JsonResponse({'success': True, 'message': 'payment failed handled', 'order_id': order.id})


    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def order_failed(request,order_id):
    user_email = request.session.get('email')
    if not user_email:
        return redirect('login')
    user = get_object_or_404(Usermodels, email=user_email)

    wishlist = Wishlist.objects.filter(user=user).first()
    if wishlist:
       wishlist_count = WishlistItem.objects.filter(wishlist=wishlist).count()

    cart = Cart.objects.filter(user=user).first()
   
    if cart:
       cart_count = CartItems.objects.filter(cart=cart).count()

    order=get_object_or_404(Order, id=order_id)

    return render(request, 'checkout/orderfail.html', {'order':order,'wishlist_count': wishlist_count,'cart_count':cart_count})

def get_order_details(request, order_id):
    if request.method == 'GET':
        order = get_object_or_404(Order, id=order_id)
        
        # Check if payment status is 'pending'
        if order.payment_status != 'pending':
            return JsonResponse({'success': False, 'message': 'Invalid request: Payment is not pending'}, status=400)
        
        # Create a new Razorpay order if payment is pending
        amount_in_paise = int(order.total_price * 100)  # Convert amount to paise
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": 1
        })
        
        # Serialize the Order object into a dictionary
        order_data = {
            'id': order.id,
            'total_price':amount_in_paise,  # Convert Decimal to float
            'user_name': order.user.name,
            'user_email': order.user.email,
            'user_contact': order.user.phone,  # Adjust if you have a different field
            'razorpay_order_id': razorpay_order['id']  # Include Razorpay order ID
        }
        
        return JsonResponse({'success': True, 'order': order_data})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def handle_payment_success(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')

            # Get the order object
            order = get_object_or_404(Order, id=order_id)

            # Verify payment signature (optional but recommended)
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            payment = client.payment.fetch(razorpay_payment_id)
            if payment['status'] == 'captured':
                # Update the order with payment details and status
                order.razorpay_payment_id = razorpay_payment_id
                order.razorpay_order_id = razorpay_order_id
                order.razorpay_signature = razorpay_signature
                order.order_status='ordered'
                order.payment_status = 'completed'
                order.payment_method='online'
                order.save()

                return JsonResponse({'success': True, 'message': 'Payment successfully processed'})
            else:
                return JsonResponse({'success': False, 'message': 'Payment not captured'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


def cancel_order(request, order_id):
    user_email = request.session.get('email')
    user = get_object_or_404(Usermodels, email=user_email)
    order = get_object_or_404(Order, id=order_id, user=user)

    if order.order_status in ['cancelled', 'delivered']:
        messages.error(request, "This order cannot be cancelled")
        return redirect('order_details', order_id=order.id)
    
    if order.order_status == 'delivered' and timezone.now() > (order.delivery_date + timedelta(days=2)):
        messages.error(request, "The return period for this order has expired.")
        return redirect('order_details', order_id=order.id)
    
    with transaction.atomic():
        order.order_status = 'cancelled'
        order.save()

        # Recredit stock
        for order_item in order.items.all():  # Assuming `order.items.all()` retrieves items
            variant = order_item.variant
            variant.stock += order_item.quantity
            variant.save()

        if order.payment_method in ['online']:
            refund_to_wallet(order)

        messages.success(request, "Order has been cancelled successfully.")
        return redirect('order_details', order_id=order.id)

def refund_to_wallet(order):
    user_wallet, created = Wallet.objects.get_or_create(user=order.user)  

    new_balance = user_wallet.balance + order.total_price

    user_wallet.balance = new_balance
    user_wallet.save()

    WalletHistory.objects.create(
        wallet=user_wallet,
        type=WalletHistory.CREDIT,
        amount=order.total_price,
        new_balance=new_balance
    )      

def return_order_item(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        item = get_object_or_404(OrderItem, id=item_id)
        
        if item.order.order_status != 'delivered':
            return JsonResponse({'success': False, 'message': 'Order item cannot be returned as it is not delivered yet.'})
        
        if item.productReturn:
            return JsonResponse({'success': False, 'message': 'Order item has already been returned.'})
        
        item.return_status = 'requested'

        item.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})    


def download_invoice(request, order_id):
    # Fetch order and related order items using filter
    try:
        order = Order.objects.get(id=order_id)
        order_items = OrderItem.objects.filter(order=order)  # Assuming 'order' is a ForeignKey in OrderItem model
    except Order.DoesNotExist:
        return HttpResponse("Order not found.", status=404)
    except OrderItem.DoesNotExist:
        return HttpResponse("Order items not found.", status=404)
    
    context = {
        'order': order,
        'order_items': order_items,
    }

    # Render HTML template with context
    html_string = render_to_string('checkout/invoice.html', context)
    
    # Convert HTML to PDF
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html_string.encode('UTF-8')), dest=result)
    
    # Check for errors
    if pdf.err:
        return HttpResponse("Error generating PDF.", status=500)
    
    # Return PDF as HTTP response
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
    return response