from django.contrib import admin
from .models import Category, SubCategory, Product


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
