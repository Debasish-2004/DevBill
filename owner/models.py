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
