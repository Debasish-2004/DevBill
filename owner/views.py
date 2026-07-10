import json
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages

from .models import Category, SubCategory, Product


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
            product.image = image

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
            product.image = image

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