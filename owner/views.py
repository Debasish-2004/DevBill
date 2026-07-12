import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import redirect_to_login
from django.db.models import Sum, Count, Max, Q
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from PIL import Image, ImageOps

from .decorators import is_owner
from .models import Category, SubCategory, Product, Customer, Bill, BillItem


def compress_image_for_upload(uploaded_file, max_size_bytes=500 * 1024):
    if not uploaded_file:
        return uploaded_file

    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    if image.mode in {'RGBA', 'LA', 'P'}:
        image = image.convert('RGB')
    image = image.copy()

    original_name = uploaded_file.name or 'image.jpg'
    extension = Path(original_name).suffix.lower()
    if extension in {'.jpg', '.jpeg'}:
        save_format = 'JPEG'
        filename = f"{Path(original_name).stem}.jpg"
    elif extension == '.png':
        save_format = 'PNG'
        filename = f"{Path(original_name).stem}.png"
    else:
        save_format = 'JPEG'
        filename = f"{Path(original_name).stem}.jpg"

    quality = 95
    current_image = image
    while True:
        buffer = BytesIO()
        if save_format == 'JPEG':
            current_image.save(buffer, format='JPEG', quality=quality, optimize=True)
        else:
            current_image.save(buffer, format='PNG', optimize=True)

        if len(buffer.getvalue()) <= max_size_bytes or quality <= 20:
            break

        quality -= 5
        if quality < 20:
            quality = 20

        if current_image.width > 200 and current_image.height > 200:
            current_image = current_image.resize(
                (max(200, int(current_image.width * 0.9)), max(200, int(current_image.height * 0.9))),
                Image.LANCZOS,
            )
        else:
            break

    while len(buffer.getvalue()) > max_size_bytes and (current_image.width > 200 or current_image.height > 200):
        current_image = current_image.resize(
            (max(200, int(current_image.width * 0.9)), max(200, int(current_image.height * 0.9))),
            Image.LANCZOS,
        )
        buffer = BytesIO()
        if save_format == 'JPEG':
            current_image.save(buffer, format='JPEG', quality=max(20, quality), optimize=True)
        else:
            current_image.save(buffer, format='PNG', optimize=True)

    return ContentFile(buffer.getvalue(), name=filename)


def owner_login(request):
    if is_owner(request.user):
        return redirect('owner_home')

    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return render(request, 'login.html', {'next': next_url, 'username': username})

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, 'Invalid username or password.')
            return render(request, 'login.html', {'next': next_url, 'username': username})

        if not user.is_active:
            messages.error(request, 'This account is inactive.')
            return render(request, 'login.html', {'next': next_url, 'username': username})

        if user.is_staff:
            messages.error(request, 'Staff accounts must use the admin panel, not the owner portal.')
            return render(request, 'login.html', {'next': next_url, 'username': username})

        login(request, user)

        if next_url:
            return redirect(next_url)
        return redirect('owner_home')

    return render(request, 'login.html', {'next': next_url})


@require_POST
def owner_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('owner_login')


def owner_home(request):
    categories_count = Category.objects.count()
    products_count = Product.objects.count()
    context = {
        'categories_count': categories_count,
        'products_count': products_count,
    }
    return render(request, "owner_home.html", context)


# ─────────────────────────────────────────────
# CATEGORY
# ─────────────────────────────────────────────

def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        has_subcategories = request.POST.get('has_subcategories') == 'on'
        subcategory_names = request.POST.getlist('subcategory_names')

        if not name:
            messages.error(request, 'Category name is required.')
            return render(request, 'add_category.html')

        if Category.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Category "{name}" already exists.')
            return render(request, 'add_category.html')

        category = Category.objects.create(
            name=name,
            has_subcategories=has_subcategories,
        )

        if has_subcategories:
            for sub_name in subcategory_names:
                sub_name = sub_name.strip()
                if sub_name:
                    SubCategory.objects.get_or_create(
                        name=sub_name,
                        category=category,
                    )

        messages.success(request, f'Category "{name}" created successfully!')
        return redirect('add_category')

    return render(request, 'add_category.html')


def add_subcategory(request):
    categories = Category.objects.filter(has_subcategories=True)

    if request.method == 'POST':
        category_id = request.POST.get('category')
        name = request.POST.get('name', '').strip()

        if not category_id or not name:
            messages.error(request, 'Both category and subcategory name are required.')
            return render(request, 'add_category.html', {'categories': categories})

        category = get_object_or_404(Category, pk=category_id)
        if not category.has_subcategories:
            messages.error(request, f'Category "{category.name}" does not support subcategories.')
            return redirect('edit_category_list')

        if SubCategory.objects.filter(name__iexact=name, category=category).exists():
            messages.error(request, f'Subcategory "{name}" already exists in "{category.name}".')
        else:
            SubCategory.objects.create(name=name, category=category)
            messages.success(request, f'Subcategory "{name}" added to "{category.name}"!')

        return redirect('edit_category_list')

    return render(request, 'add_category.html', {'categories': categories})


def edit_category_list(request):
    categories = Category.objects.prefetch_related('subcategories', 'products').all()
    return render(request, 'edit_category_list.html', {'categories': categories})


def delete_category(request, pk):
    if request.method == 'POST':
        category = get_object_or_404(Category, pk=pk)
        product_count = category.products.count()
        name = category.name
        category.delete()
        messages.success(
            request,
            f'Category "{name}" deleted. {product_count} product(s) were removed.',
        )
    return redirect('edit_category_list')


def delete_subcategory(request, pk):
    if request.method == 'POST':
        sub = get_object_or_404(SubCategory, pk=pk)
        product_count = sub.products.count()
        name = str(sub)
        sub.delete()
        messages.success(
            request,
            f'Subcategory "{name}" deleted. {product_count} product(s) were removed.',
        )
    return redirect('edit_category_list')


# ─────────────────────────────────────────────
# PRODUCT
# ─────────────────────────────────────────────

def get_subcategories(request):
    """AJAX endpoint: returns subcategories + has_subcategories flag."""
    category_id = request.GET.get('category_id')
    if not category_id:
        return JsonResponse({'has_subcategories': False, 'subcategories': []})

    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return JsonResponse({'has_subcategories': False, 'subcategories': []})

    subs = list(
        category.subcategories.values('id', 'name').order_by('name')
    )
    return JsonResponse({
        'has_subcategories': category.has_subcategories,
        'subcategories': subs,
    })


def search_products(request):
    """AJAX endpoint for owner-side product suggestions on the edit page."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})

    products = (
        Product.objects
        .select_related('category', 'subcategory')
        .filter(name__icontains=q)[:8]
    )

    results = []
    for product in products:
        if product.subcategory:
            location = f"{product.category.name} → {product.subcategory.name}"
        else:
            location = product.category.name
        results.append({
            'id': product.id,
            'name': product.name,
            'category': location,
            'price': f"{product.current_price}",
            'image': product.image.url if product.image else '',
            'url': reverse('edit_product', args=[product.id]),
        })
    return JsonResponse({'results': results})


def add_product(request):
    categories = Category.objects.all()

    if request.method == 'POST':
        category_id = request.POST.get('category')
        subcategory_id = request.POST.get('subcategory') or None
        name = request.POST.get('name', '').strip()
        place = request.POST.get('place', '').strip()
        min_price = request.POST.get('minimum_selling_price', '').strip()
        cur_price = request.POST.get('current_price', '').strip()
        image = request.FILES.get('image')

        errors = []
        if not category_id:
            errors.append('Category is required.')
        if not name:
            errors.append('Product name is required.')
        if not place:
            errors.append('Place is required.')
        if not min_price:
            errors.append('Minimum selling price is required.')
        if not cur_price:
            errors.append('Current price is required.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'add_product.html', {'categories': categories})

        try:
            min_price = Decimal(min_price)
            cur_price = Decimal(cur_price)
        except (InvalidOperation, ValueError):
            messages.error(request, 'Invalid price values.')
            return render(request, 'add_product.html', {'categories': categories})

        category = get_object_or_404(Category, pk=category_id)

        # Enforce subcategory rule
        if category.has_subcategories:
            if not subcategory_id:
                messages.error(
                    request,
                    f'Category "{category.name}" has subcategories. You must select one.',
                )
                return render(request, 'add_product.html', {'categories': categories})
            subcategory = get_object_or_404(SubCategory, pk=subcategory_id, category=category)
        else:
            subcategory = None

        product = Product(
            name=name,
            category=category,
            subcategory=subcategory,
            place=place,
            minimum_selling_price=min_price,
            current_price=cur_price,
        )
        if image:
            product.image = compress_image_for_upload(image)

        product.full_clean()
        product.save()
        messages.success(request, f'Product "{name}" added successfully!')
        return redirect('add_product')

    return render(request, 'add_product.html', {'categories': categories})


def edit_product_list(request):
    products = Product.objects.select_related('category', 'subcategory').all()
    categories = Category.objects.all()

    # Filter by category if requested
    category_filter = request.GET.get('category')
    if category_filter:
        products = products.filter(category_id=category_filter)

    search_q = request.GET.get('q', '').strip()
    if search_q:
        products = products.filter(name__icontains=search_q)

    return render(request, 'edit_product_list.html', {
        'products': products,
        'categories': categories,
        'selected_category': category_filter,
        'search_q': search_q,
    })


def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    subcategories = SubCategory.objects.filter(category=product.category)

    if request.method == 'POST':
        category_id = request.POST.get('category')
        subcategory_id = request.POST.get('subcategory') or None
        name = request.POST.get('name', '').strip()
        place = request.POST.get('place', '').strip()
        min_price = request.POST.get('minimum_selling_price', '').strip()
        cur_price = request.POST.get('current_price', '').strip()
        image = request.FILES.get('image')

        if not all([category_id, name, place, min_price, cur_price]):
            messages.error(request, 'All fields are required.')
            return render(request, 'edit_product.html', {
                'product': product,
                'categories': categories,
                'subcategories': subcategories,
            })

        try:
            min_price = Decimal(min_price)
            cur_price = Decimal(cur_price)
        except (InvalidOperation, ValueError):
            messages.error(request, 'Invalid price values.')
            return render(request, 'edit_product.html', {
                'product': product,
                'categories': categories,
                'subcategories': subcategories,
            })

        category = get_object_or_404(Category, pk=category_id)

        if category.has_subcategories:
            if not subcategory_id:
                messages.error(
                    request,
                    f'Category "{category.name}" has subcategories. You must select one.',
                )
                return render(request, 'edit_product.html', {
                    'product': product,
                    'categories': categories,
                    'subcategories': subcategories,
                })
            subcategory = get_object_or_404(SubCategory, pk=subcategory_id, category=category)
        else:
            subcategory = None

        product.name = name
        product.category = category
        product.subcategory = subcategory
        product.place = place
        product.minimum_selling_price = min_price
        product.current_price = cur_price
        if image:
            product.image = compress_image_for_upload(image)

        product.full_clean()
        product.save()
        messages.success(request, f'Product "{name}" updated successfully!')
        return redirect('edit_product_list')

    return render(request, 'edit_product.html', {
        'product': product,
        'categories': categories,
        'subcategories': subcategories,
    })


def delete_product(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
    return redirect('edit_product_list')


# ─────────────────────────────────────────────
# BULK PRICE CHANGE
# ─────────────────────────────────────────────

def bulk_price_change(request):
    categories = Category.objects.prefetch_related('subcategories').all()

    if request.method == 'POST':
        category_id = request.POST.get('category')
        subcategory_id = request.POST.get('subcategory') or None
        percentage_str = request.POST.get('percentage', '').strip()

        if not category_id or not percentage_str:
            messages.error(request, 'Category and percentage are required.')
            return render(request, 'bulk_price_change.html', {'categories': categories})

        try:
            percentage = Decimal(percentage_str)
        except (InvalidOperation, ValueError):
            messages.error(request, 'Invalid percentage value.')
            return render(request, 'bulk_price_change.html', {'categories': categories})

        category = get_object_or_404(Category, pk=category_id)

        # Get the target products
        if subcategory_id:
            subcategory = get_object_or_404(SubCategory, pk=subcategory_id, category=category)
            products = Product.objects.filter(subcategory=subcategory)
            target_label = f"{category.name} → {subcategory.name}"
        else:
            products = Product.objects.filter(category=category)
            target_label = category.name

        if not products.exists():
            messages.warning(request, f'No products found in "{target_label}".')
            return render(request, 'bulk_price_change.html', {'categories': categories})

        # Apply percentage change
        multiplier = 1 + (percentage / 100)
        count = 0
        for product in products:
            new_price = (product.current_price * multiplier).quantize(Decimal('0.01'))
            # Don't allow price to go below minimum selling price
            if new_price < product.minimum_selling_price:
                new_price = product.minimum_selling_price
            product.current_price = new_price
            product.save(update_fields=['current_price', 'updated_at'])
            count += 1

        direction = "increased" if percentage > 0 else "decreased"
        messages.success(
            request,
            f'{count} product(s) in "{target_label}" {direction} by {abs(percentage)}%.',
        )
        return redirect('bulk_price_change')

    return render(request, 'bulk_price_change.html', {'categories': categories})

# ─────────────────────────────────────────────
# CUSTOMERS & BILLS
# ─────────────────────────────────────────────

def _period_start(period):
    """Return the datetime cutoff for a named period, or None for 'all'."""
    now = timezone.now()
    if period == 'week':
        return now - timedelta(days=7)
    if period == 'month':
        return now - timedelta(days=30)
    if period == 'year':
        return now - timedelta(days=365)
    return None


def customer_list(request):
    period = request.GET.get('period', 'all')
    start = _period_start(period)

    bill_filter = Q(bills__created_at__gte=start) if start else Q()

    customers = (
        Customer.objects
        .annotate(
            bill_count=Count('bills', filter=bill_filter),
            spent=Sum('bills__total', filter=bill_filter),
            due=Sum('bills__amount_due', filter=bill_filter),
            last_purchase=Max('bills__created_at', filter=bill_filter),
        )
        .filter(bill_count__gt=0)
        .order_by('-last_purchase')
    )

    return render(request, 'customer_list.html', {
        'customers': customers,
        'period': period,
        'period_options': [
            ('all', 'All time'),
            ('week', 'This week'),
            ('month', 'This month'),
            ('year', 'This year'),
        ],
    })


def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    bills = customer.bills.prefetch_related('items').all()
    totals = customer.bills.aggregate(
        spent=Sum('total'),
        paid=Sum('amount_paid'),
        due=Sum('amount_due'),
    )
    return render(request, 'customer_detail.html', {
        'customer': customer,
        'bills': bills,
        'spent': totals['spent'] or 0,
        'paid': totals['paid'] or 0,
        'due': totals['due'] or 0,
    })


def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        customer.name = name
        customer.save(update_fields=['name'])
        if name:
            messages.success(request, f'Customer name set to "{name}".')
        else:
            messages.info(request, 'Customer name cleared.')
    return redirect('customer_detail', pk=pk)


def paylater_list(request):
    sort = request.GET.get('sort', 'amount')   # amount | time

    customers = (
        Customer.objects
        .annotate(
            due=Sum('bills__amount_due'),
            last_purchase=Max('bills__created_at'),
        )
        .filter(due__gt=0)
    )

    if sort == 'time':
        customers = customers.order_by('-last_purchase')
    else:
        customers = customers.order_by('-due')

    total_outstanding = customers.aggregate(t=Sum('due'))['t'] or 0

    return render(request, 'paylater_list.html', {
        'customers': customers,
        'sort': sort,
        'total_outstanding': total_outstanding,
    })
