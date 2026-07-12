from django.urls import path
from . import views
from .decorators import owner_required

urlpatterns = [
    path("login/", views.owner_login, name="owner_login"),
    path("logout/", views.owner_logout, name="owner_logout"),

    path("", owner_required(views.owner_home), name="owner_home"),

    # Category
    path("add-category/", owner_required(views.add_category), name="add_category"),
    path("categories/", owner_required(views.edit_category_list), name="edit_category_list"),
    path("delete-category/<int:pk>/", owner_required(views.delete_category), name="delete_category"),
    path("delete-subcategory/<int:pk>/", owner_required(views.delete_subcategory), name="delete_subcategory"),
    path("add-subcategory/", owner_required(views.add_subcategory), name="add_subcategory"),

    # Product
    path("add-product/", owner_required(views.add_product), name="add_product"),
    path("edit-products/", owner_required(views.edit_product_list), name="edit_product_list"),
    path("edit-product/<int:pk>/", owner_required(views.edit_product), name="edit_product"),
    path("delete-product/<int:pk>/", owner_required(views.delete_product), name="delete_product"),

    # AJAX
    path("api/subcategories/", owner_required(views.get_subcategories), name="get_subcategories"),
    path("api/search/", owner_required(views.search_products), name="owner_search_products"),

    # Bulk pricing
    path("bulk-price-change/", owner_required(views.bulk_price_change), name="bulk_price_change"),

    # Customers & billing
    path("customers/", owner_required(views.customer_list), name="customer_list"),
    path("customers/<int:pk>/", owner_required(views.customer_detail), name="customer_detail"),
    path("customers/<int:pk>/edit/", owner_required(views.customer_edit), name="customer_edit"),
    path("pay-later/", owner_required(views.paylater_list), name="paylater_list"),
]
