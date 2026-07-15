from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError


class Category(models.Model):
    name = models.CharField(max_length=200, unique=True)
    has_subcategories = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Sub Categories"
        ordering = ['name']
        unique_together = ['name', 'category']

    def __str__(self):
        return f"{self.category.name} → {self.name}"


class Product(models.Model):
    name = models.CharField(max_length=300)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
    )
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True,
    )
    place = models.CharField(
        max_length=300,
        help_text="Location/place where this product is stored",
    )
    minimum_selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'subcategory', 'name']

    def __str__(self):
        if self.subcategory:
            return f"{self.name} ({self.category} → {self.subcategory.name})"
        return f"{self.name} ({self.category})"

    def clean(self):
        """Enforce: if category has subcategories enabled, product MUST have one."""
        super().clean()
        if self.category_id:
            try:
                category = Category.objects.get(pk=self.category_id)
            except Category.DoesNotExist:
                return
            if category.has_subcategories and not self.subcategory_id:
                raise ValidationError({
                    'subcategory': (
                        f'Category "{category.name}" has subcategories enabled. '
                        'You must select a subcategory.'
                    ),
                })
            if not category.has_subcategories and self.subcategory_id:
                raise ValidationError({
                    'subcategory': (
                        f'Category "{category.name}" does not use subcategories. '
                        'Remove the subcategory selection.'
                    ),
                })
            # Ensure subcategory belongs to the selected category
            if self.subcategory_id and self.subcategory:
                if self.subcategory.category_id != self.category_id:
                    raise ValidationError({
                        'subcategory': 'Subcategory does not belong to the selected category.',
                    })


# ─────────────────────────────────────────────
# CUSTOMERS & BILLING
# ─────────────────────────────────────────────

class Customer(models.Model):
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name or self.phone

    @property
    def display_name(self):
        return self.name if self.name else "Unnamed"

    @property
    def outstanding(self):
        """Total amount still owed across all this customer's bills."""
        agg = self.bills.aggregate(due=models.Sum('amount_due'))
        return agg['due'] or 0

    def apply_payment(self, amount):
        """Apply `amount` toward this customer's outstanding bills, oldest first.

        Increases amount_paid / decreases amount_due on each due bill until the
        money runs out. Returns the amount actually applied — never more than the
        total outstanding, so any excess is left for the caller to handle (e.g.
        a cash refund).
        """
        remaining = Decimal(amount)
        applied = Decimal('0')
        if remaining <= 0:
            return applied

        bills = self.bills.filter(amount_due__gt=0).order_by('created_at')
        for bill in bills:
            if remaining <= 0:
                break
            take = min(bill.amount_due, remaining)
            bill.amount_paid += take
            bill.amount_due -= take
            bill.save(update_fields=['amount_paid', 'amount_due'])
            remaining -= take
            applied += take

        return applied.quantize(Decimal('0.01'))


class Bill(models.Model):
    PAYMENT_CASH = 'cash'
    PAYMENT_UPI = 'upi'
    PAYMENT_PAYLATER = 'pay_later'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_UPI, 'UPI'),
        (PAYMENT_PAYLATER, 'Pay Later'),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='bills',
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CASH,
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Bill #{self.pk} — {self.customer}"

    @property
    def is_paid(self):
        return self.amount_due <= 0

    @property
    def item_count(self):
        return sum(i.quantity for i in self.items.all())


class BillItem(models.Model):
    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE, related_name='items',
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bill_items',
    )
    product_name = models.CharField(max_length=300)   # snapshot at sale time
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def returned_quantity(self):
        """How many units of this line item have already been returned."""
        agg = self.return_items.aggregate(q=models.Sum('quantity'))
        return agg['q'] or 0

    @property
    def returnable_quantity(self):
        """Units still available to return."""
        return self.quantity - self.returned_quantity


# ─────────────────────────────────────────────
# RETURNS
# ─────────────────────────────────────────────

class Return(models.Model):
    """A return raised against a single bill by the employee."""
    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE, related_name='returns',
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='returns',
    )
    total_refund = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Portion of the refund used to reduce the customer's outstanding balance.
    applied_to_outstanding = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Return #{self.pk} — Bill #{self.bill_id}"

    @property
    def item_count(self):
        return sum(i.quantity for i in self.items.all())

    @property
    def cash_refund(self):
        """Refund handed back as cash after settling any outstanding balance."""
        return self.total_refund - self.applied_to_outstanding


class ReturnItem(models.Model):
    ret = models.ForeignKey(
        Return, on_delete=models.CASCADE, related_name='items',
    )
    bill_item = models.ForeignKey(
        BillItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='return_items',
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='return_items',
    )
    product_name = models.CharField(max_length=300)   # snapshot at return time
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} × {self.quantity} (returned)"


# ─────────────────────────────────────────────
# DEPOSITS (outstanding collections)
# ─────────────────────────────────────────────

class Deposit(models.Model):
    """Money collected from a customer by an employee against their outstanding
    balance. Recording a deposit reduces the customer's due amount."""
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='deposits',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Deposit ₹{self.amount} — {self.customer}"
