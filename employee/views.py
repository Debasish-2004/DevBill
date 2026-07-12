import re
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.db import transaction

from owner.models import Category, SubCategory, Product, Customer, Bill, BillItem


# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────

def employee_home(request):
    context = {
        'categories_count': Category.objects.count(),
        'products_count': Product.objects.count(),
        'bill_count': _bill_item_count(request),
    }
    return render(request, "employee_home.html", context)


# ─────────────────────────────────────────────
# BROWSE: categories → subcategories → products
# ─────────────────────────────────────────────

def product_categories(request):
    """Landing: show every category as a card."""
    categories = Category.objects.prefetch_related('subcategories', 'products').all()
    return render(request, 'products.html', {
        'categories': categories,
        'bill_count': _bill_item_count(request),
    })


def category_detail(request, pk):
    """If the category uses subcategories, show them; otherwise show its products."""
    category = get_object_or_404(
        Category.objects.prefetch_related('subcategories'), pk=pk
    )

    if category.has_subcategories:
        subcategories = category.subcategories.all()
        return render(request, 'category_detail.html', {
            'category': category,
            'subcategories': subcategories,
            'bill_count': _bill_item_count(request),
        })

    products = category.products.select_related('category', 'subcategory').all()
    return render(request, 'product_list.html', {
        'category': category,
        'subcategory': None,
        'products': products,
        'bill_count': _bill_item_count(request),
    })


def subcategory_detail(request, pk):
    """Show the products inside a subcategory."""
    subcategory = get_object_or_404(
        SubCategory.objects.select_related('category'), pk=pk
    )
    products = subcategory.products.select_related('category', 'subcategory').all()
    return render(request, 'product_list.html', {
        'category': subcategory.category,
        'subcategory': subcategory,
        'products': products,
        'bill_count': _bill_item_count(request),
    })


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('category', 'subcategory'), pk=pk
    )
    return render(request, 'product_detail.html', {
        'product': product,
        'bill_count': _bill_item_count(request),
    })


# ─────────────────────────────────────────────
# SEARCH (autocomplete suggestions)
# ─────────────────────────────────────────────

def search_products(request):
    """AJAX endpoint for the header search bar. Returns product suggestions."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})

    products = (
        Product.objects
        .select_related('category', 'subcategory')
        .filter(name__icontains=q)[:8]
    )

    results = []
    for p in products:
        if p.subcategory:
            location = f"{p.category.name} → {p.subcategory.name}"
        else:
            location = p.category.name
        results.append({
            'id': p.id,
            'name': p.name,
            'category': location,
            'price': f"{p.current_price}",
            'image': p.image.url if p.image else '',
            'url': reverse('product_detail', args=[p.id]),
        })
    return JsonResponse({'results': results})


# ─────────────────────────────────────────────
# BILLING (session cart)
# ─────────────────────────────────────────────

def _get_bill(request):
    """Return the session bill dict, creating it if needed."""
    bill = request.session.get('bill')
    if not bill or 'items' not in bill:
        bill = {'items': {}, 'discount': '0'}
        request.session['bill'] = bill
    return bill


def _save_bill(request, bill):
    request.session['bill'] = bill
    request.session.modified = True


def _bill_item_count(request):
    bill = request.session.get('bill') or {}
    items = bill.get('items', {})
    return sum(int(i.get('qty', 0)) for i in items.values())


def add_to_bill(request, pk):
    product = get_object_or_404(Product, pk=pk)
    bill = _get_bill(request)
    items = bill['items']
    key = str(pk)

    if key in items:
        items[key]['qty'] = int(items[key]['qty']) + 1
    else:
        items[key] = {
            'qty': 1,
            'price': str(product.current_price),
        }

    _save_bill(request, bill)
    messages.success(request, f'"{product.name}" added to bill.')

    # Allow AJAX callers to get a fresh count without a redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'count': _bill_item_count(request)})

    return redirect('billing')


def _compute_bill(request):
    """Build line items + totals from the session cart, dropping deleted products
    and clamping any price below MSP. Returns a summary dict."""
    bill = _get_bill(request)
    items = bill['items']

    product_ids = [int(k) for k in items.keys()]
    products = Product.objects.select_related('category', 'subcategory').in_bulk(product_ids)

    line_items = []
    subtotal = Decimal('0')
    stale_keys = []
    dirty = False

    for key, entry in items.items():
        product = products.get(int(key))
        if product is None:
            stale_keys.append(key)
            continue

        qty = int(entry.get('qty', 1))
        try:
            price = Decimal(str(entry.get('price', product.current_price)))
        except (InvalidOperation, ValueError):
            price = product.current_price

        # Never allow a stored price below MSP
        if price < product.minimum_selling_price:
            price = product.minimum_selling_price
            entry['price'] = str(price)
            dirty = True

        line_total = (price * qty).quantize(Decimal('0.01'))
        subtotal += line_total
        line_items.append({
            'product': product,
            'qty': qty,
            'price': price,
            'msp': product.minimum_selling_price,
            'line_total': line_total,
        })

    # Drop any products that were deleted since being added
    if stale_keys:
        for k in stale_keys:
            items.pop(k, None)
        dirty = True
    if dirty:
        _save_bill(request, bill)

    try:
        discount = Decimal(str(bill.get('discount', '0')))
    except (InvalidOperation, ValueError):
        discount = Decimal('0')

    if discount < 0:
        discount = Decimal('0')
    if discount > subtotal:
        discount = subtotal

    total = (subtotal - discount).quantize(Decimal('0.01'))

    return {
        'line_items': line_items,
        'subtotal': subtotal.quantize(Decimal('0.01')),
        'discount': discount.quantize(Decimal('0.01')),
        'total': total,
    }


def billing(request):
    summary = _compute_bill(request)
    return render(request, 'billing.html', {
        **summary,
        'bill_count': _bill_item_count(request),
    })


def checkout(request):
    """Take the customer's phone + payment method, persist the bill, then print."""
    summary = _compute_bill(request)

    if not summary['line_items']:
        messages.warning(request, 'Your bill is empty.')
        return redirect('billing')

    if request.method == 'POST':
        phone_raw = request.POST.get('phone', '').strip()
        payment_method = request.POST.get('payment_method', '').strip()
        amount_paid_raw = request.POST.get('amount_paid', '').strip()

        # Normalise phone: keep leading + and digits
        digits = re.sub(r'[^0-9]', '', phone_raw)
        if len(digits) < 7 or len(digits) > 15:
            messages.error(request, 'Enter a valid phone number (7–15 digits).')
            return render(request, 'checkout.html', {
                **summary,
                'phone': phone_raw,
                'payment_method': payment_method,
                'bill_count': _bill_item_count(request),
            })
        phone = digits

        if payment_method not in dict(Bill.PAYMENT_CHOICES):
            messages.error(request, 'Choose a valid payment method.')
            return render(request, 'checkout.html', {
                **summary,
                'phone': phone_raw,
                'payment_method': payment_method,
                'bill_count': _bill_item_count(request),
            })

        total = summary['total']

        # Work out paid / due depending on method
        if payment_method == Bill.PAYMENT_PAYLATER:
            try:
                amount_paid = Decimal(amount_paid_raw or '0')
            except (InvalidOperation, ValueError):
                amount_paid = Decimal('0')
            if amount_paid < 0:
                amount_paid = Decimal('0')
            if amount_paid > total:
                amount_paid = total
            amount_paid = amount_paid.quantize(Decimal('0.01'))
            amount_due = (total - amount_paid).quantize(Decimal('0.01'))
        else:
            amount_paid = total
            amount_due = Decimal('0.00')

        # Persist customer + bill + items atomically
        with transaction.atomic():
            customer, _ = Customer.objects.get_or_create(phone=phone)
            new_bill = Bill.objects.create(
                customer=customer,
                subtotal=summary['subtotal'],
                discount=summary['discount'],
                total=total,
                payment_method=payment_method,
                amount_paid=amount_paid,
                amount_due=amount_due,
            )
            BillItem.objects.bulk_create([
                BillItem(
                    bill=new_bill,
                    product=li['product'],
                    product_name=li['product'].name,
                    unit_price=li['price'],
                    quantity=li['qty'],
                    line_total=li['line_total'],
                )
                for li in summary['line_items']
            ])

        # Empty the cart now that it's a real bill
        request.session['bill'] = {'items': {}, 'discount': '0'}
        request.session.modified = True

        return redirect('receipt', bill_id=new_bill.pk)

    return render(request, 'checkout.html', {
        **summary,
        'phone': '',
        'payment_method': Bill.PAYMENT_CASH,
        'bill_count': _bill_item_count(request),
    })


def receipt(request, bill_id):
    """Printable receipt for a completed bill."""
    bill = get_object_or_404(
        Bill.objects.select_related('customer').prefetch_related('items'),
        pk=bill_id,
    )
    return render(request, 'receipt.html', {
        'bill': bill,
        'items': bill.items.all(),
        # auto-open the print dialog unless suppressed with ?noprint=1
        'auto_print': request.GET.get('noprint') != '1',
    })


def update_bill(request):
    """Handle price edits, quantity changes, discount, and item removal."""
    if request.method != 'POST':
        return redirect('billing')

    bill = _get_bill(request)
    items = bill['items']
    action = request.POST.get('action')

    if action == 'remove':
        key = request.POST.get('product_id')
        items.pop(str(key), None)
        _save_bill(request, bill)
        messages.info(request, 'Item removed from bill.')
        return redirect('billing')

    if action == 'clear':
        bill['items'] = {}
        bill['discount'] = '0'
        _save_bill(request, bill)
        messages.info(request, 'Bill cleared.')
        return redirect('billing')

    if action == 'update':
        # Update quantities and prices for every line item
        for key in list(items.keys()):
            product = Product.objects.filter(pk=int(key)).first()
            if product is None:
                items.pop(key, None)
                continue

            # Quantity
            qty_raw = request.POST.get(f'qty_{key}')
            if qty_raw is not None:
                try:
                    qty = int(qty_raw)
                except (ValueError, TypeError):
                    qty = int(items[key].get('qty', 1))
                if qty <= 0:
                    items.pop(key, None)
                    continue
                items[key]['qty'] = qty

            # Price (clamped to MSP floor)
            price_raw = request.POST.get(f'price_{key}')
            if price_raw is not None and price_raw.strip() != '':
                try:
                    price = Decimal(price_raw.strip())
                except (InvalidOperation, ValueError):
                    price = product.current_price
                if price < product.minimum_selling_price:
                    price = product.minimum_selling_price
                    messages.warning(
                        request,
                        f'"{product.name}" cannot go below MSP ₹{product.minimum_selling_price}. '
                        'Price set to MSP.',
                    )
                items[key]['price'] = str(price.quantize(Decimal('0.01')))

        # Discount on the total bill
        discount_raw = request.POST.get('discount', '').strip()
        if discount_raw == '':
            bill['discount'] = '0'
        else:
            try:
                discount = Decimal(discount_raw)
                if discount < 0:
                    discount = Decimal('0')
                bill['discount'] = str(discount.quantize(Decimal('0.01')))
            except (InvalidOperation, ValueError):
                messages.error(request, 'Invalid discount value.')

        _save_bill(request, bill)

        # "Proceed to Payment" submits this same form, then continues to checkout
        if request.POST.get('next') == 'checkout':
            return redirect('checkout')

        messages.success(request, 'Bill updated.')

    return redirect('billing')
