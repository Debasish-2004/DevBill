from django.urls import path
from . import views

urlpatterns = [
    path("", views.owner_home, name="owner_home"),

    # Category
    path("add-category/", views.add_category, name="add_category"),
    path("categories/", views.edit_category_list, name="edit_category_list"),
    path("delete-category/<int:pk>/", views.delete_category, name="delete_category"),
    path("delete-subcategory/<int:pk>/", views.delete_subcategory, name="delete_subcategory"),
    path("add-subcategory/", views.add_subcategory, name="add_subcategory"),

    # Product
    path("add-product/", views.add_product, name="add_product"),
    path("edit-products/", views.edit_product_list, name="edit_product_list"),
    path("edit-product/<int:pk>/", views.edit_product, name="edit_product"),
    path("delete-product/<int:pk>/", views.delete_product, name="delete_product"),

    # AJAX
    path("api/subcategories/", views.get_subcategories, name="get_subcategories"),

    # Bulk pricing
    path("bulk-price-change/", views.bulk_price_change, name="bulk_price_change"),

    # Customers & billing
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("pay-later/", views.paylater_list, name="paylater_list"),
]