from datetime import datetime,date,timedelta
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.utils.dateparse import parse_date
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from decimal import Decimal
from django.utils import timezone
from .models import Category,Product,Variant,Variant_image,Banner
from products.models import ProductOffer,CategoryOffer
from coupon.models import Coupon
from .forms import CategoryForm
from checkout.models import Wallet,WalletHistory
import base64
from django.db.models.functions import Cast
from django.db.models.functions import TruncMonth, TruncYear, TruncDate
import re,json
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.core.serializers import serialize
from django.db.models import Count
from django.core.files.base import ContentFile
from django.urls import reverse
from django.db.models import *
from django.http import JsonResponse
from authentication.models import *
from authentication.models import Usermodels
from checkout.models import Order,OrderItem
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import cache_control,never_cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def is_superuser(user):
    return user.is_superuser



def adminlogin(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
                request.session.flush()
                login(request, user)
                return redirect('admin_dashboard')  
        else:
                return redirect('adminlogin')
    return render(request, 'admin/adminlogin.html')


@login_required(login_url='login')    
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def admin_dashboard(request):
    today = timezone.now().date()

    # Default filter is daily
    filter_type = request.GET.get('filter', 'daily')

    if filter_type == 'monthly':
        start_date = today.replace(day=1)
        end_date = (today.replace(day=1) + timezone.timedelta(days=31)).replace(day=1)
    elif filter_type == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = (today.replace(year=today.year + 1, month=1, day=1))
    else:  # Default to daily
        start_date = today
        end_date = today + timezone.timedelta(days=1)

    # Fetch all orders for the table
    orders_list = Order.objects.all()
    paginator = Paginator(orders_list, 5)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    
    # Fetch metrics
    user_count = Usermodels.objects.count()
    total_price = Order.objects.aggregate(Sum('total_price'))['total_price__sum']
    revenue_current = Order.objects.filter(order_date__date=start_date).aggregate(total_revenue=Sum('total_price'))['total_revenue'] or Decimal('0')
    daily_income = OrderItem.objects.filter(order__order_date__date=start_date).aggregate(
        total_income=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=FloatField()))
    )['total_income'] or Decimal('0')
    total_orders = Order.objects.count()

    # Previous metrics
    if filter_type == 'monthly':
        previous_start_date = (start_date - timezone.timedelta(days=30)).replace(day=1)
        previous_end_date = (end_date - timezone.timedelta(days=30)).replace(day=1)
    elif filter_type == 'yearly':
        previous_start_date = start_date - timezone.timedelta(days=365)
        previous_end_date = end_date - timezone.timedelta(days=365)
    else:
        previous_start_date = start_date - timezone.timedelta(days=1)
        previous_end_date = end_date - timezone.timedelta(days=1)

    revenue_previous = Order.objects.filter(order_date__date__range=(previous_start_date, previous_end_date)).aggregate(total_revenue=Sum('total_price'))['total_revenue'] or Decimal('0')
    daily_income_previous = OrderItem.objects.filter(order__order_date__date__range=(previous_start_date, previous_end_date)).aggregate(
        total_income=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=FloatField()))
    )['total_income'] or Decimal('0')
    total_orders_previous = Order.objects.filter(order_date__date__range=(previous_start_date, previous_end_date)).count()

    # Calculate percentage changes
    # revenue_change = ((float(revenue_current) - float(revenue_previous)) / float(revenue_previous) * 100) if revenue_previous else 0
    # income_change = ((float(daily_income) - float(daily_income_previous)) / float(daily_income_previous) * 100) if daily_income_previous else 0
    # orders_change = ((total_orders - total_orders_previous) / total_orders_previous * 100) if total_orders_previous else 0
    revenue_change = ((float(revenue_current) - float(revenue_previous)) / float(revenue_previous) * 100) if revenue_previous and float(revenue_previous) != 0 else 0
    income_change = ((float(daily_income) - float(daily_income_previous)) / float(daily_income_previous) * 100) if daily_income_previous and float(daily_income_previous) != 0 else 0
    orders_change = ((total_orders - total_orders_previous) / total_orders_previous * 100) if total_orders_previous != 0 else 0
    
    # Prepare data for the chart
    date_range = [start_date + timezone.timedelta(days=i) for i in range((end_date - start_date).days)]
    revenue_data = []
    income_data = []

    for date in date_range:
        daily_revenue = Order.objects.filter(order_date__date=date).aggregate(total_revenue=Sum('total_price'))['total_revenue'] or Decimal('0')
        daily_income = OrderItem.objects.filter(order__order_date__date=date).aggregate(
            total_income=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=FloatField()))
        )['total_income'] or Decimal('0')

        # Convert both to float for the arithmetic operation
        daily_revenue_float = float(daily_revenue)
        daily_income_float = float(daily_income)
        daily_profit = daily_income_float - daily_revenue_float

        revenue_data.append(daily_revenue_float)
        income_data.append(daily_profit)  # Convert Decimal to float

    # Prepare data for the pie chart
    status_counts = Order.objects.values('order_status').annotate(count=Count('id'))
    statuses = [status['order_status'] for status in status_counts]
    counts = [int(status['count']) for status in status_counts] 

    context = {
        'user_count': user_count,
        'revenue_current': float(revenue_current),
        'daily_income': float(daily_income),
        'total_orders': total_orders,
        'date_range': [d.strftime('%Y-%m-%d') for d in date_range],
        'revenue_data': json.dumps(revenue_data),
        'income_data': json.dumps(income_data),
        'statuses': json.dumps(statuses),
        'counts': json.dumps(counts),
        'filter_type': filter_type,
        'orders': orders,
        'total_price': float(total_price)
    }
    
    return render(request, 'admin/index.html', context)

@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def customers(request):
    users = Usermodels.objects.all().order_by('id') 
    query = request.GET.get('q', '')
    if query:
        users = users.filter(name=query) | users.filter(email=query) | users.filter(phone=query)
 
    paginator = Paginator(users, 5)  

    page = request.GET.get('page')
    try:
         users = paginator.page(page)
    except PageNotAnInteger:
         
         users = paginator.page(1)
    except EmptyPage:
        
         users = paginator.page(paginator.num_pages)

    return render(request,'admin/user.html', {'users':users})




@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def toggle_user_block(request, user_id):
     user = get_object_or_404(Usermodels, id=user_id)
     user.is_block = not user.is_block 
     user.save()
     return redirect('customers')



@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def category(request):
    categories = Category.objects.annotate(total_products=Count('product')).order_by('id')
    query = request.GET.get('q', '')
    if query:
        categories = categories.filter(category_name=query) 

     
    paginator = Paginator(categories, 5)  

    page = request.GET.get('page')
    try:
         users = paginator.page(page)
    except PageNotAnInteger:

         users = paginator.page(1)
    except EmptyPage:
         
         users = paginator.page(paginator.num_pages)
    return render(request,'admin/category.html', {'categories': categories, 'query': query})




@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
def toggle_category(request, category_id):
     category = get_object_or_404(Category, id=category_id)
     category.is_listed = not category.is_listed 
     category.save()
     return redirect('category')




@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def add_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        cropped_image_data = request.POST.get('cropped_image')
        image = None

       # Validate category name
        if not category_name or len(category_name) < 4 or not re.match("^[A-Za-z]+$", category_name):
            messages.error(request, 'Category name must be at least 4 characters long and contain only letters with no spaces.')
            return render(request, 'admin/addcategory.html')
        
        existing_category = Category.objects.filter(category_name__iexact=category_name).exists()
        
        if existing_category:
            messages.error(request, f'A category with the name "{category_name}" already exists.')
            return render(request, 'admin/addcategory.html', {'category_name': category_name})
        
        if not cropped_image_data:
            messages.error(request, 'An image must be uploaded.')
            return render(request, 'admin/addcategory.html', {'category_name': category_name})
        try:
            format, imgstr = cropped_image_data.split(';base64,')
            ext = format.split('/')[-1]
            img_data = ContentFile(base64.b64decode(imgstr), name=f'{category_name}.{ext}')
            image = img_data
        except (ValueError, TypeError):
            messages.error(request, 'Invalid image data.')
            return render(request, 'admin/addcategory.html', {'category_name': category_name}) 

        Category.objects.create(category_name=category_name, image=image)
        messages.success(request, f'Category "{category_name}" created successfully.')
        return render(request, 'admin/addcategory.html')
    
    return render(request, 'admin/addcategory.html')


@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.category_name = request.POST.get('category_name')
        cropped_image_data = request.POST.get('cropped_image')

        
        # Validate category name
        if category.category_name:
            if not re.match("^[A-Za-z]+$", category.category_name):
                messages.error(request, 'Category name must contain only alphabets and no spaces.')
                return render(request, 'admin/addcategory.html', {'category': category})

            existing_category = Category.objects.filter(category_name__iexact=category.category_name).exists()
            if existing_category and category.category_name.lower() != category.category_name.lower():
                messages.error(request, f'A category with the name "{category.category_name}" already exists.')
                return render(request, 'admin/addcategory.html', {'category_name': category.category_name, 'category': category})

            category.category_name = category.category_name
        
        if cropped_image_data:
            format, imgstr = cropped_image_data.split(';base64,')
            ext = format.split('/')[-1]
            img_data = ContentFile(base64.b64decode(imgstr), name=f'{category_id}.{ext}')
            category.image = img_data
        category.save()
        messages.success(request, f'Category "{category.category_name}" updated successfully.')
        return render('admin/addcategory.html') 
    return render(request, 'admin/addcategory.html', {'category': category})



@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def products(request):
    products = Product.objects.all().order_by('id')
    query = request.GET.get('q', '')
    if query:
        products = products.filter(name=query) | products.filter(category__category_name=query)

      #pagination
    paginator = Paginator(products, 5)  

    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
         
        products = paginator.page(1)
    except EmptyPage:
         
        products = paginator.page(paginator.num_pages)    
    return render(request,'admin/products.html', {'products': products,'query': query})



@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def toggle_product_active(request, product_id):
     product = get_object_or_404(Product, id=product_id)
     product.is_available = not product.is_available
     product.save()
     return redirect('products')


@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def add_products(request):
    if request.method == 'POST':
        name = request.POST.get('productName')
        category_id = request.POST.get('productCategory')
        description = request.POST.get('productDescription')
        product_detail = request.POST.get('productDetails')
        is_available = bool(request.POST.get('isAvailable', True))
        
        image= request.POST.get('croppedImageData')

        if not name or not name.strip() or not name.isalpha():
            messages.error(request, 'Product name must be a valid character string.')
            return render(request, 'admin/addproducts.html', {'categories': Category.objects.all()})
        elif not description or not description.strip():
            messages.error(request, 'Please provide a product description') 
            return render(request, 'admin/addproducts.html', {'categories': Category.objects.all()}) 
        elif not product_detail or not product_detail.strip():
            messages.error(request, 'Please provide product details.') 
            return render(request, 'admin/addproducts.html', {'categories': Category.objects.all()})     
        elif not image:
            messages.error(request, 'Please upload an image for the product.')
            return render(request, 'admin/addproducts.html', {'categories': Category.objects.all()})
            
        else:

            product = Product.objects.create(
                name = name,
                category_id = category_id,
                description = description,
                product_detail = product_detail,
                is_available = is_available, 
             
            )

            if image:
                format, imgstr = image.split(';base64,')
                ext = format.split('/')[-1]
                img_data = ContentFile(base64.b64decode(imgstr), name=f'{product.slug}.{ext}')
                product.image = img_data
                product.save()

        variant_color = request.POST.get('variantColor')
        variant_price = request.POST.get('variantPrice')
        variant_stock = request.POST.get('variantStock')
        

        if not variant_color or not variant_color.strip() or not variant_color.isalpha():
            messages.error(request, 'variant color must be a valid character string.')
            return render(request, 'admin/addproducts.html', {'categories': Category.objects.all()})
        elif not variant_price or not variant_price.strip() or not variant_price.isdigit() or int(variant_price) <= 0:
            messages.error(request, 'Price must be a positive integer.') 
            return render(request, 'admin/addproducts.html', {'categories': Category.objects.all()}) 
        elif not variant_stock or not variant_stock.strip() or not variant_stock.isdigit() or int(variant_stock) <= 0:
            messages.error(request, 'stock must be a positive integer.')
            return render(request, 'admin/addproducts.html', {'categories': Category.objects.all()})
       
        else:          

            # Check if variant with the same color already exists for this product
            existing_variant = Variant.objects.filter(product=product, color=variant_color).exists()
        
            if existing_variant:
                messages.error(request, f'A variant with color "{variant_color}" already exists for this product.')
                return render(request, 'admin/addproducts.html', {'categories': Category.objects.all()})
        

        variant = Variant.objects.create(
            product = product,
            color = variant_color,
            price = variant_price,
            stock = variant_stock
        )
        variant.save()  

        # Handle multiple variant images
        cropped_images = request.POST.get('cropped_images')
        if cropped_images:
            base64_images = cropped_images.split('###')
            for base64_image in base64_images:
                try:
                    # Splitting the base64 string
                    format, imgstr = base64_image.split(';base64,')
                    ext = format.split('/')[-1]  # Extract the file extension
                    image_data = ContentFile(base64.b64decode(imgstr), name=f"variant_image.{ext}")
                    Variant_image.objects.create(variant=variant, image=image_data) 
                except ValueError:
                    messages.error(request, 'Invalid base64 string for image.')
                    return render(request, 'admin/addproducts.html', {'product': product, 'categories': Category.objects.all()})

        messages.success(request, 'Product and variant added successfully.')
        return render(request, 'admin/addproducts.html', {'product': product, 'categories': Category.objects.all()})

       
     
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'admin/addproducts.html', context)



@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def edit_products(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all().order_by('id')

    if request.method == 'POST':
        product.name = request.POST.get('productName')
        product.category_id = request.POST.get('productCategory')
        product.description = request.POST.get('productDescription')
        product.product_detail = request.POST.get('productDetails')

        if request.FILES.get('img[]'):
            product.image = request.FILES.get('img[]')

        if not product.name or not product.name.strip() or not product.name.isalpha():
            messages.error(request, 'Product name must be a valid character string.')
            return render(request, 'admin/editproducts.html', {'product': product, 'categories': categories})

        elif not product.description or not product.description.strip():
            messages.error(request, 'Please provide a product description.')
            return render(request, 'admin/editproducts.html', {'product': product, 'categories': categories})

        elif not product.product_detail or not product.product_detail.strip():
            messages.error(request, 'Please provide product details.')
            return render(request, 'admin/editproducts.html', {'product': product, 'categories': categories})    

        product.save()


        for key, value in request.POST.items():
            if key.startswith('croppedImages_'):
                try:
                    format, imgstr = value.split(';base64,')
                    ext = format.split('/')[-1]
                    img_data = ContentFile(base64.b64decode(imgstr), name=f'{product.id}_{key}.{ext}')
                    Variant_image.objects.create(product=product, image=img_data)
                except ValueError:
                    messages.error(request, 'Invalid base64 string for image.')
                    return render(request, 'admin/editproducts.html', {'product': product, 'categories': categories})

        messages.success(request, 'Product updated successfully.')
        return render(request, 'admin/editproducts.html', {'product': product, 'categories': categories})

    context = {
        'product': product,
        'categories' : categories,
    }   
    return render(request,'admin/editproducts.html',context)         


@login_required(login_url='login')        
def edit_product_image(request, product_id):
    product = get_object_or_404(Product, id=product_id)     

    if request.method == 'POST':
        cropped_image_data = request.POST.get('cropped_image')
        if cropped_image_data:
            format, imgstr = cropped_image_data.split(';base64,')
            ext = format.split('/')[-1]
            img_data = ContentFile(base64.b64decode(imgstr), name=f'{product_id}.{ext}')
            product.image.save(f'{product_id}.{ext}', img_data, save=True)
            return redirect('products')

    context = {
        'product': product,
    }
    return render(request, 'admin/editimage.html', context)
                    
     

@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def variants(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.all().order_by('id')
    query = request.GET.get('q', '')
    if query:
        variants = variants.filter(color=query) 
    paginator = Paginator(variants, 10)

    page = request.GET.get('page')
    try:
        variant = paginator.page(page)
    except PageNotAnInteger:
        variant = paginator.page(1)
    except EmptyPage:
        variant = paginator.page(paginator.num_pages)        

    return render(request,'admin/variants.html',{'product': product, 'variants': variants, 'variant': variant})


@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def add_variant(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        variant_color = request.POST.get('variantColor')
        variant_price = request.POST.get('variantPrice')
        variant_stock = request.POST.get('variantStock')

        if not variant_color or not variant_color.strip() or not variant_color.isalpha():
                messages.error(request, 'Variant color must be a valid character string.')
                return render(request, 'admin/addvariance.html', {'product': product})
        elif not variant_price or not variant_price.strip() or not variant_price.isdigit() or int(variant_price) <= 0:
                messages.error(request, 'Price must be a positive integer.')
                return render(request, 'admin/addvariance.html', {'product': product})
        elif not variant_stock or not variant_stock.strip() or not variant_stock.isdigit() or int(variant_stock) <= 0:
                messages.error(request, 'Stock must be a positive integer.')
                return render(request, 'admin/addvariance.html', {'product': product})

       
        existing_variant = Variant.objects.filter(product=product, color=variant_color).exists()
        
        if existing_variant:
            messages.error(request, f'A variant with color "{variant_color}" already exists for this product.')
            return render(request, 'admin/addvariance.html', {'product': product})
        

        variant = Variant.objects.create(
            product = product,
            color = variant_color,
            price = variant_price,
            stock = variant_stock
        )
        variant.save()  

        
        cropped_images = request.POST.get('cropped_images')
        if cropped_images:
            base64_images = cropped_images.split('###')
            for base64_image in base64_images:
                try:
                    format, imgstr = base64_image.split(';base64,')
                    ext = format.split('/')[-1]  
                    image_data = ContentFile(base64.b64decode(imgstr), name=f"variant_image.{ext}")
                    Variant_image.objects.create(variant=variant, image=image_data) 
                except ValueError:
                    print("Invalid base64 string")
        return redirect('products')  
    
      


    return render(request, 'admin/addvariance.html', {'product': product})



@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def edit_variant(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id)

    if request.method == 'POST':
        variant.color = request.POST.get('variantColor')
        variant.price = request.POST.get('variantPrice')
        variant.stock = request.POST.get('variantStock')

        # Validate updated variant fields
        if not variant.color or not variant.color.strip() or not variant.color.isalpha():
            messages.error(request, 'Variant color must be a valid character string.')
            return render(request, 'admin/editvariant.html', {'variant': variant})

        elif not variant.price or not variant.price.strip() or not variant.price.isdigit() or int(variant.price) <= 0:
            messages.error(request, 'Price must be a positive integer.')
            return render(request, 'admin/editvariant.html', {'variant': variant})

        elif not variant.stock or not variant.stock.strip() or not variant.stock.isdigit() or int(variant.stock) <= 0:
            messages.error(request, 'Stock must be a positive integer.')
            return render(request, 'admin/editvariant.html', {'variant': variant})
        
        existing_variant = Variant.objects.filter(product=variant.product, color=variant.color).exclude(id=variant.id).exists()
        if existing_variant:
            messages.error(request, f'A variant with color "{variant.color}" already exists for this product.')
            return render(request, 'admin/editvariant.html', {'variant': variant})

        variant.save()
        return redirect('variants', product_id=variant.product_id)

    context = {
        'variant': variant,
    }
    return render(request, 'admin/editvariant.html', context)



@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def variant_image_view(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id)
    images = Variant_image.objects.filter(variant_id=variant_id)
    for image in images:
        print(image.image.url)
    
    return render(request,'admin/editvariantimage.html',{'variant':variant, 'images': images})



@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def edit_variantimage(request, variant_id):
    if request.method == 'POST' and request.FILES.get('croppedImage'):
        cropped_image = request.FILES['croppedImage']
        print(cropped_image,variant_id)
        variant = get_object_or_404(Variant, pk=variant_id)
        new_image=Variant_image.objects.create(variant=variant, image=cropped_image) 
        serialized_image = serialize('json', [new_image,])


        
        
        return JsonResponse({'message': 'Image uploaded successfully.', 'image': serialized_image})
    else:
        return JsonResponse({'error': 'No cropped image data found.'}, status=400)



@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def toggle_variant_active(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id)
    variant.is_available = not variant.is_available
    variant.save()
    return redirect('variants', product_id=variant.product_id)  


@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def toggle_variantimage_active(request, variantimage_id):
    variant_image = get_object_or_404(Variant_image, id=variantimage_id)
    variant_image.is_active = not variant_image.is_active
    variant_image.save()
    return redirect('variant_image_view', variant_id=variant_image.variant_id) 

def banner_list(request):
    query = request.GET.get('q', '')
    banners = Banner.objects.filter(title__icontains=query)
    
    paginator = Paginator(banners, 10)  # Show 10 banners per page
    page_number = request.GET.get('page')
    banners = paginator.get_page(page_number)
    
    return render(request, 'admin/banner.html', {'banners': banners, 'query': query})

def add_banner(request):
    if request.method == 'POST':
        title = request.POST.get('bannerTitle')
        subtitle = request.POST.get('bannerSubtitle')
        image = request.FILES.get('bannerImage')

        # Create and save the new banner
        banner = Banner(
            title=title,
            subtitle=subtitle,
            image=image
        )
        banner.save()
        
        messages.success(request, 'Banner added successfully.')
        return redirect('banner_list')  # Redirect to the list of banners or another appropriate page

    return render(request, 'admin/addbanner.html')


def edit_banner(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    
    if request.method == 'POST':
        title = request.POST.get('bannerTitle')
        subtitle = request.POST.get('bannerSubtitle')
        image = request.FILES.get('bannerImage')
        
        if title and subtitle:
            banner.title = title
            banner.subtitle = subtitle
            
            if image:
                banner.image = image
            
            banner.save()
            messages.success(request, 'Banner updated successfully!')
            return redirect('banner_list')
        else:
            messages.error(request, 'Please fill out all fields.')

    context = {
        'banner': banner
    }
    return render(request, 'admin/editbanner.html', context)

def toggle_banner_active(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    banner.is_active = not banner.is_active
    banner.save()
    return redirect('banner_list')

@login_required(login_url='login')   
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
@user_passes_test(is_superuser, login_url='adminlogin') 
def coupon(request):
    coupons = Coupon.objects.all()

    query = request.GET.get('q', '')
    if query:
        coupons = coupons.filter(coupon_code__icontains=query)

    paginator = Paginator(coupons, 10)
    page = request.GET.get('page')
    try:
        coupon = paginator.page(page)
    except PageNotAnInteger:
        coupon = paginator.page(1)
    except EmptyPage:
        coupon = paginator.page(paginator.num_pages)

    
    context ={
        'coupons':coupons,
        'coupon': coupon
    }
    return render(request, 'admin/coupon.html',context)


@login_required(login_url='login')   
def addcoupon(request):
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_name')
        valid_from = request.POST.get('coupon_validfrom')
        valid_to = request.POST.get('coupon_validto')
        discount_price = request.POST.get('coupon_discountamt')
        minimum_amount = request.POST.get('coupon_minamt')
        quantity = request.POST.get('coupon_qty')
        is_active = 'is_active' in request.POST


        # Validate coupon code format
        if not coupon_code or not coupon_code.isalnum():
            messages.error(request, 'Coupon code should only contain alphanumeric characters.')
            return render(request, 'admin/addcoupon.html')
        
        # Validate dates
        try:
            valid_from_date = datetime.strptime(valid_from, '%Y-%m-%d').date()
            valid_to_date = datetime.strptime(valid_to, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format. Use YYYY-MM-DD.')
            return render(request, 'admin/addcoupon.html')

        if valid_from_date >= valid_to_date:
            messages.error(request, 'Valid from date must be before valid to date.')
            return render(request, 'admin/addcoupon.html')
        
        # Validate discount price
        try:
            discount_price = int(discount_price)
            if discount_price < 100:
                messages.error(request, 'Discount price must be at least 100.')
                return render(request, 'admin/addcoupon.html')
        except (ValueError, TypeError):
            messages.error(request, 'Discount price must be a valid integer.')
            return render(request, 'admin/addcoupon.html')

        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity <= 0 or quantity > 100:
                messages.error(request, 'Quantity must be a positive integer between 1 and 100.')
                return render(request, 'admin/addcoupon.html')
        except (ValueError, TypeError):
            messages.error(request, 'Quantity must be a valid integer.')
            return render(request, 'admin/addcoupon.html')
        
        # Validate minimum amount
        try:
            minimum_amount = float(minimum_amount)
            if minimum_amount < 0:
                messages.error(request, 'Minimum amount must not be negative.')
                return render(request, 'admin/addcoupon.html')
        except (ValueError, TypeError):
            messages.error(request, 'Minimum amount must be a valid number.')
            return render(request, 'admin/addcoupon.html')
        
        if discount_price >= minimum_amount:
            messages.error(request, 'Discount price must be less than the minimum amount.')
            return render(request, 'admin/addcoupon.html')


        # Create a new Coupon object
        Coupon.objects.create(
            coupon_code=coupon_code,
            valid_from=valid_from,
            valid_to=valid_to,
            discount_price=discount_price,
            minimum_amount=minimum_amount,
            quantity=quantity,
            is_active=is_active
        )
        messages.success(request, 'Coupon added successfully.')
        return render(request, 'admin/addcoupon.html')
    return render(request,'admin/addcoupon.html')

@login_required(login_url='login')   
def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)

    if request.method == 'POST':
        coupon.coupon_code = request.POST.get('coupon_name')
        coupon.valid_from = request.POST.get('coupon_validfrom')
        coupon.valid_to = request.POST.get('coupon_validto')
        coupon.discount_price = request.POST.get('coupon_discountamt')
        coupon.minimum_amount = request.POST.get('coupon_minamt')
        coupon.quantity = request.POST.get('coupon_qty')
        
        # Validate coupon code format
        if not coupon.coupon_code or not coupon.coupon_code.isalnum():
            messages.error(request, 'Coupon code should only contain alphanumeric characters.')
            return render(request, 'admin/editcoupon.html', {'coupon': coupon})
        # Validate dates
        try:
            valid_from_date = datetime.strptime(coupon.valid_from, '%Y-%m-%d').date()
            valid_to_date = datetime.strptime(coupon.valid_to, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format. Use YYYY-MM-DD.')
            return render(request, 'admin/editcoupon.html', {'coupon': coupon})
        
        if valid_from_date >= valid_to_date:
            messages.error(request, 'Valid from date must be before valid to date.')
            return render(request, 'admin/editcoupon.html', {'coupon': coupon})

        # Validate discount price
        try:
            discount_price = int(coupon.discount_price)
            if discount_price < 100:
                messages.error(request, 'Discount price must be at least 100.')
                return render(request, 'admin/editcoupon.html', {'coupon': coupon})
        except (ValueError, TypeError):
            messages.error(request, 'Discount price must be a valid integer.')
            return render(request, 'admin/editcoupon.html', {'coupon': coupon})

        # Validate quantity
        try:
            quantity = int(coupon.quantity)
            if quantity <= 0 or quantity > 100:
                messages.error(request, 'Quantity must be a positive integer between 1 and 100.')
                return render(request, 'admin/editcoupon.html', {'coupon': coupon})
        except (ValueError, TypeError):
            messages.error(request, 'Quantity must be a valid integer.')
            return render(request, 'admin/editcoupon.html', {'coupon': coupon})

        # Validate minimum amount
        try:
            minimum_amount = float(coupon.minimum_amount)
            if minimum_amount < 0:
                messages.error(request, 'Minimum amount must not be negative.')
                return render(request, 'admin/editcoupon.html', {'coupon': coupon})
        except (ValueError, TypeError):
            messages.error(request, 'Minimum amount must be a valid number.')
            return render(request, 'admin/editcoupon.html', {'coupon': coupon})

        # Ensure discount price is less than minimum amount
        if discount_price >= minimum_amount:
            messages.error(request, 'Discount price must be less than the minimum amount.')
            return render(request, 'admin/editcoupon.html', {'coupon': coupon})

        coupon.save()
        messages.success(request, 'Coupon updated successfully.')
        return render(request, 'admin/editcoupon.html', {'coupon': coupon})
    
    context = {
        'coupon': coupon
    }
    return render(request, 'admin/editcoupon.html', context)
 



@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def toggle_coupon(request, coupon_id):
     coupon = get_object_or_404(Coupon, id=coupon_id)
     coupon.is_active = not coupon.is_active
     coupon.save()
     return redirect('coupon')



@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def orders(request):
    orders = Order.objects.order_by('-order_date')

    query = request.GET.get('q', '')
    if query:
        orders = orders.filter(id__icontains=query)

    paginator = Paginator(orders, 10)

    page = request.GET.get('page')
    try:
        order = paginator.page(page)
    except PageNotAnInteger:
        order = paginator.page(1)
    except EmptyPage:
        order = paginator.page(paginator.num_pages)        
    
    
    context ={
        'orders': orders,
        'order': order,
    }
    return render(request, 'admin/order.html',context)



@login_required(login_url='login')   
@user_passes_test(is_superuser, login_url='adminlogin') 
@cache_control(no_cache=True, must_revalidate=True, no_store=True,max_age=0)
def order_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    context = {
        'order': order
    }
    return render(request,'admin/orderdetails.html', context)


@login_required(login_url='login')   
def update_order_status(request):
    if request.method == "POST":
       
        order_id = request.POST.get('id')
        new_status = request.POST.get('status')
        try:
            order = Order.objects.get(id=order_id)
            if order.order_status in ['cancelled', 'delivered']:
               return JsonResponse({'error': 'Cannot update status of a cancelled or delivered order'}, status=403)
            order.order_status = new_status
            if new_status == 'delivered':
                order.delivered_date = timezone.now()
            order.save()
            return JsonResponse({'status': new_status})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status = 404)
    return JsonResponse({'error': 'Invalid request'}, status=400)


def sales_report(request):
    report_type = request.GET.get('report_type', 'daily')
    current_datetime = timezone.now()
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    cost_percentage = Decimal('0.20')  # 20% cost

    if report_type == 'monthly':
        # Monthly Sales Report
        sales_data = Order.objects.filter(order_date__year=current_datetime.year).annotate(
            month=TruncMonth('order_date')
        ).values('month').annotate(
            total_sales=Sum('total_price'),
            total_orders=Count('id'),
        ).values('month', 'total_sales', 'total_orders')
        
        total_products=OrderItem.objects.filter(order__order_date__year=current_datetime.year).annotate(month=TruncMonth('order__order_date')).values('month').annotate(
            total_quantity=Sum('quantity')
        ).values('month','total_quantity')

        combined_data = []
        grand_total_sales = 0
        grand_total_orders = 0
        grand_total_quantity = 0
        grand_total_profit =0

        for sale in sales_data:
            month = sale['month']
            total_sales = sale['total_sales']
            total_orders = sale['total_orders']
            
            # Find the corresponding product data
            product_info = next((item for item in total_products if item['month'] == month), {})
            total_quantity = product_info.get('total_quantity', 0)

            total_cost = total_sales * cost_percentage
            profit = total_cost

            formatted_month = month.strftime('%Y-%b').upper()
            
            combined_data.append({
                'month': formatted_month,
                'total_sales': total_sales,
                'total_orders': total_orders,
                'total_quantity': total_quantity,
                'profit': profit
            })

            grand_total_sales += total_sales
            grand_total_orders += total_orders
            grand_total_quantity += total_quantity
            grand_total_profit += profit

    elif report_type == 'yearly':
        # Yearly Sales Report
        sales_data = Order.objects.annotate(
            year=TruncYear('order_date')
        ).values('year').annotate(
            total_sales=Sum('total_price'),
            total_orders=Count('id')
        ).values('year', 'total_sales', 'total_orders')

        total_products = OrderItem.objects.annotate(
            year=TruncYear('order__order_date')
        ).values('year').annotate(
            total_quantity=Sum('quantity')
        ).values('year', 'total_quantity')

        combined_data = []
        grand_total_sales = 0
        grand_total_orders = 0
        grand_total_quantity = 0
        grand_total_profit =0

        for sale in sales_data:
            year = sale['year']
            total_sales = sale['total_sales']
            total_orders = sale['total_orders']
            
            # Find the corresponding product data
            product_info = next((item for item in total_products if item['year'] == year), {})
            total_quantity = product_info.get('total_quantity', 0)

            total_cost = total_sales * cost_percentage
            profit = total_cost

            formatted_year = year.strftime('%Y')
            
            combined_data.append({
                'year': formatted_year,
                'total_sales': total_sales,
                'total_orders': total_orders,
                'total_quantity': total_quantity,
                'profit': profit
            })

            grand_total_sales += total_sales
            grand_total_orders += total_orders
            grand_total_quantity += total_quantity
            grand_total_profit += profit

    elif report_type == 'daily':
        # Daily Sales Report
        sales_data = Order.objects.annotate(
            date=TruncDate('order_date')
        ).values('date').annotate(
            total_sales=Sum('total_price'),
            total_orders=Count('id')
        ).values('date', 'total_sales', 'total_orders')

        total_products = OrderItem.objects.annotate(
            date=TruncDate('order__order_date')
        ).values('date').annotate(
            total_quantity=Sum('quantity')
        ).values('date', 'total_quantity')

        combined_data = []
        grand_total_sales = 0
        grand_total_orders = 0
        grand_total_quantity = 0
        grand_total_profit =0

        for sale in sales_data:
            date = sale['date']
            total_sales = sale['total_sales']
            total_orders = sale['total_orders']
            
            # Find the corresponding product data
            product_info = next((item for item in total_products if item['date'] == date), {})
            total_quantity = product_info.get('total_quantity', 0)

            total_cost = total_sales * cost_percentage
            profit = total_cost

            formatted_date = date.strftime('%Y-%m-%d')
            
            combined_data.append({
                'date': formatted_date,
                'total_sales': total_sales,
                'total_orders': total_orders,
                'total_quantity': total_quantity,
                'profit': profit
            })

            grand_total_sales += total_sales
            grand_total_orders += total_orders
            grand_total_quantity += total_quantity
            grand_total_profit += profit

    elif report_type == 'custom':
        # Custom date range report
        if not start_date_str:
            start_date = timezone.now() - timedelta(days=30)  # Default to 30 days ago
        else:
            try:
                start_date = timezone.make_aware(datetime.combine(datetime.strptime(start_date_str, '%Y-%m-%d').date(), datetime.min.time()))
            except ValueError:
                start_date = timezone.now() - timedelta(days=30)  # Default to 30 days ago if parsing fails

        if not end_date_str:
            end_date = timezone.now()  # Default to current time
        else:
            try:
                end_date = timezone.make_aware(datetime.combine(datetime.strptime(end_date_str, '%Y-%m-%d').date(), datetime.max.time()))
            except ValueError:
                end_date = timezone.now()  # Default to current time if parsing fails

        sales_data = Order.objects.filter(order_date__range=[start_date, end_date]).annotate(
            date=TruncDate('order_date')
        ).values('date').annotate(
            total_sales=Sum('total_price'),
            total_orders=Count('id')
        ).values('date', 'total_sales', 'total_orders')

        total_products = OrderItem.objects.filter(
            order__order_date__range=[start_date, end_date]
        ).annotate(
            date=TruncDate('order__order_date')
        ).values('date').annotate(
            total_quantity=Sum('quantity')
        ).values('date', 'total_quantity')

        combined_data = []
        grand_total_sales = 0
        grand_total_orders = 0
        grand_total_quantity = 0
        grand_total_profit = 0

        for sale in sales_data:
            date = sale['date']
            total_sales = sale['total_sales']
            total_orders = sale['total_orders']
            
            # Find the corresponding product data
            product_info = next((item for item in total_products if item['date'] == date), {})
            total_quantity = product_info.get('total_quantity', 0)

            total_cost = total_sales * cost_percentage
            profit = total_cost

            formatted_date = date.strftime('%Y-%m-%d')
            
            combined_data.append({
                'date': formatted_date,
                'total_sales': total_sales,
                'total_orders': total_orders,
                'total_quantity': total_quantity,
                'profit': profit
            })

            grand_total_sales += total_sales
            grand_total_orders += total_orders
            grand_total_quantity += total_quantity
            grand_total_profit += profit

    context = {
        'sales_data': list(combined_data),
        'grand_total_sales': grand_total_sales,
        'grand_total_orders': grand_total_orders,
        'grand_total_quantity': grand_total_quantity,
        'grand_total_profit': grand_total_profit,
    }
    
    # Check if the request is an AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(context)
    
    return render(request, 'admin/sales.html', context)


def get_return_requested_items(request):
    if request.method == "GET":
        page_number = request.GET.get('page', 1)
        requested_items = OrderItem.objects.filter(return_status='requested').order_by('-id')
        paginator = Paginator(requested_items, 10)  # Show 10 items per page
        page_obj = paginator.get_page(page_number)

        
        items_data = list(page_obj.object_list.values(
            'id', 'order', 'product', 'variant', 'price', 'quantity', 'return_status'
        ))

        return render(request, 'admin/productreturn.html', {
            'page_obj': page_obj,
            'items_data': items_data
        })

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def update_return_status(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        return_status = data.get('return_status')
        

        try:
            item = OrderItem.objects.get(id=item_id)
            
            if item.order.order_status != 'delivered':
                return JsonResponse({'success': False, 'message': 'Order item cannot be returned as it is not delivered yet.'})

            original_total_price = sum([i.subtotal() for i in item.order.items.all()])

            if item.order.coupon:
                coupon_discount = item.order.coupon.discount_price
                discount_percentage = coupon_discount / original_total_price
            else:
                discount_percentage = 0

            item_discount_amount = item.subtotal() * discount_percentage
            amount_to_reduce = round(item.subtotal() - item_discount_amount)

            item.return_status = return_status
            item.save()

            # Adjust variant stock
            variant = item.variant
            with transaction.atomic():
                variant.stock += item.quantity  # Restore stock
                variant.save()

        
            wallet, created = Wallet.objects.get_or_create(user=item.order.user)
            wallet.balance += amount_to_reduce
            wallet.save()

            WalletHistory.objects.create(
                wallet=wallet,
                type=WalletHistory.CREDIT,
                amount=amount_to_reduce,
                new_balance=wallet.balance
            )

            return JsonResponse({'success': True})

        except OrderItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order item not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def category_offer_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        discount_percentage = request.POST.get('discount_percentage')
        start_date_str = request.POST.get('valid_from')
        end_date_str = request.POST.get('valid_to')

        errors = {}

        # Validate title
        if not title or not re.match(r'^[A-Za-z0-9]+$', title):
            errors['title'] = ['Title must contain only letters and numbers, and no spaces.']

        # Validate dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors['dates'] = ['Invalid date format. Use YYYY-MM-DD.']

        if start_date >= end_date:
            errors['dates'] = ['Start date must be before end date.']

        # Validate discount percentage
        try:
            discount_percentage = int(discount_percentage)
            if not (1 <= discount_percentage <= 100):
                raise ValueError
        except (ValueError, TypeError):
            errors['discount_percentage'] = ['Discount percentage must be a positive integer between 1 and 100.']

        # Validate category
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            errors['category'] = ['Selected category does not exist.']

        if errors:
            return JsonResponse({'errors': errors}, status=400)

        # Create a new CategoryOffer object
        CategoryOffer.objects.create(
            category=category,
            title=title,
            discount_percentage=discount_percentage,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        return JsonResponse({'message': 'Category offer added successfully.'})

    # GET request: Render the form with existing offers and available categories
    today = timezone.now().date()
    offers = CategoryOffer.objects.all()
    # Exclude categories with active offers only
    active_offer_categories = Category.objects.filter(
        categoryoffer__is_active=True,
        categoryoffer__end_date__gte=today
    ).distinct()
    categories = Category.objects.exclude(id__in=active_offer_categories)

    context = {
        'offers': offers,
        'categories': categories
    }

    return render(request, 'admin/category_offers.html', context)

def toggle_category_offer_active(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    offer.is_active = not offer.is_active
    offer.save()
    return redirect('category_offers')

def delete_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    offer.delete()
    messages.success(request, 'Category offer deleted successfully.')
    return redirect('category_offers')

def edit_category_offer_view(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        discount_percentage = request.POST.get('discount_percentage')
        start_date_str = request.POST.get('valid_from')
        end_date_str = request.POST.get('valid_to')

        errors = {}

        # Validate title
        if not title or not re.match(r'^[A-Za-z0-9]+$', title):
            errors['title'] = ['Title must contain only letters and numbers, and no spaces.']

        # Validate dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors['dates'] = ['Invalid date format. Use YYYY-MM-DD.']

        if start_date >= end_date:
            errors['dates'] = ['Start date must be before end date.']

        # Validate discount percentage
        try:
            discount_percentage = int(discount_percentage)
            if not (1 <= discount_percentage <= 100):
                raise ValueError
        except (ValueError, TypeError):
            errors['discount_percentage'] = ['Discount percentage must be a positive integer between 1 and 100.']


        # Validate category
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            errors['category'] = ['Selected category does not exist.']

        if errors:
            return JsonResponse({'errors': errors}, status=400)

        # Update the offer
        offer.title = title
        offer.category = category
        offer.discount_percentage = discount_percentage
        offer.start_date = start_date
        offer.end_date = end_date
        offer.save()

        return JsonResponse({'message': 'Category offer updated successfully.'})

    # GET request: Render the form with existing offer details
    context = {
        'offer': offer,
        'categories': Category.objects.all()
    }
    return render(request, 'admin/edit_category_offer.html', context)

def product_offer_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        product_id = request.POST.get('product')
        discount_percentage = request.POST.get('discount_percentage')
        start_date_str = request.POST.get('valid_from')
        end_date_str = request.POST.get('valid_to')

        errors = {}

        # Validate title
        if not title or not re.match(r'^[A-Za-z0-9]+$', title):
            errors['title'] = ['Title must contain only letters and numbers, and no spaces.']
        
        # Validate dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors['dates'] = ['Invalid date format. Use YYYY-MM-DD.']

        if start_date >= end_date:
            errors['dates'] = ['Start date must be before end date.']

        # Validate discount percentage
        try:
            discount_percentage = int(discount_percentage)
            if not (1 <= discount_percentage <= 100):
                raise ValueError
        except (ValueError, TypeError):
            errors['discount_percentage'] = ['Discount percentage must be a positive integer between 1 and 100.']

        # Validate product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            errors['product'] = ['Selected product does not exist.']

        if errors:
            return JsonResponse({'errors': errors}, status=400)

        # Create a new ProductOffer object
        ProductOffer.objects.create(
            product=product,
            title=title,
            discount_percentage=discount_percentage,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        return JsonResponse({'message': 'Product offer added successfully.'})


    # GET request
    today = timezone.now().date()
    offers = ProductOffer.objects.all()
    active_offer_products = Product.objects.filter(
        productoffer__is_active=True,
        productoffer__end_date__gte=today
    ).distinct()
    products = Product.objects.exclude(id__in=active_offer_products)

    context = {
        'offers': offers,
        'products': products
    }

    return render(request, 'admin/product_offer.html', context)

def toggle_offer_active(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    offer.is_active = not offer.is_active
    offer.save()
    return redirect('product_offers')

def delete_offer(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    offer.delete()
    messages.success(request, 'Offer deleted successfully.')
    return redirect('product_offers')


def edit_offer_view(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        product_id = request.POST.get('product')
        discount_percentage = request.POST.get('discount_percentage')
        start_date_str = request.POST.get('valid_from')
        end_date_str = request.POST.get('valid_to')

        errors = {}


        # Validate title
        if not title or not re.match(r'^[A-Za-z0-9]+$', title):
            errors['title'] = 'Title must contain only letters and numbers, and no spaces.'

        # Validate dates
        try:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if start_date >= end_date:
                errors['dates'] = 'Start date must be before end date.'
        except (ValueError, TypeError):
            errors['dates'] = 'Invalid date format. Use YYYY-MM-DD.'

        # Validate discount percentage
        try:
            discount_percentage = int(discount_percentage)
            if not (1 <= discount_percentage <= 100):
                raise ValueError
        except (ValueError, TypeError):
            errors['discount_percentage'] = 'Discount percentage must be a positive integer between 1 and 100.'


        # Validate product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            errors['product'] = 'Selected product does not exist.'

        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)


        # Update the offer
        offer.title = title
        offer.product = product
        offer.discount_percentage = discount_percentage
        offer.start_date = start_date
        offer.end_date = end_date
        offer.save()

        return JsonResponse({'status': 'success', 'message': 'Product offer updated successfully.'})

    # GET request: Render the form with existing offer details
    offer = get_object_or_404(ProductOffer, id=offer_id)
    context = {
        'offer': offer,
        'products': Product.objects.all()
    }
    return render(request, 'admin/edit_offer.html', context)

def bestseller(request):
    # Calculate best-selling categories
    category_sales = (
        OrderItem.objects
        .select_related('product')
        .values('product__category')
        .annotate(
            total_sales=Sum('quantity'),
            total_orders=Count('order'),
            total_amount=Sum(F('price') * F('quantity'))
        )
        .order_by('-total_sales')
    )

    # Fetch categories and attach sales data
    categories = []
    for sales in category_sales:
        category = Category.objects.get(id=sales['product__category'])
        categories.append({
            'category': category,
            'total_sales': sales['total_sales'],
            'total_orders': sales['total_orders'],
            'total_amount': sales['total_amount'],
        })

    # Calculate best-selling products
    product_sales = (
        OrderItem.objects
        .select_related('product')
        .values('product')
        .annotate(
            total_sales=Sum('quantity'),
            total_orders=Count('order'),
            total_amount=Sum(F('price') * F('quantity'))
        )
        .order_by('-total_sales')
    )

    # Fetch products and attach sales data
    products = []
    for sales in product_sales:
        product = Product.objects.get(id=sales['product'])
        products.append({
            'product': product,
            'total_sales': sales['total_sales'],
            'total_orders': sales['total_orders'],
            'total_amount': sales['total_amount'],
        })

    context = {
        'categories': categories,
        'products': products,
    }

    return render(request, 'admin/Bestsellers.html', context)


@user_passes_test(is_superuser)
def adminlogout(request):
    logout(request)
    login_url = reverse('adminlogin')  
    return redirect(login_url)






