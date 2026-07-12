from django.contrib import admin
from .models import Category, SubCategory, Product, Customer, Bill, BillItem


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'has_subcategories', 'created_at']
    inlines = [SubCategoryInline]


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'created_at']
    list_filter = ['category']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'place', 'current_price', 'minimum_selling_price']
    list_filter = ['category', 'subcategory']
    search_fields = ['name', 'place']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['phone', 'name', 'created_at']
    search_fields = ['phone', 'name']


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'total', 'amount_paid', 'amount_due', 'payment_method', 'created_at']
    list_filter = ['payment_method', 'created_at']
    search_fields = ['customer__name', 'customer__phone']


@admin.register(BillItem)
class BillItemAdmin(admin.ModelAdmin):
    list_display = ['bill', 'product_name', 'quantity', 'unit_price', 'line_total']
    search_fields = ['product_name', 'bill__id']
