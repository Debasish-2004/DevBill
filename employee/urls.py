from django.urls import path
from . import views

urlpatterns = [
    path("", views.employee_home, name="employee_home"),

    # Browse
    path("products/", views.product_categories, name="product_categories"),
    path("products/category/<int:pk>/", views.category_detail, name="category_detail"),
    path("products/subcategory/<int:pk>/", views.subcategory_detail, name="subcategory_detail"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),

    # Search
    path("api/search/", views.search_products, name="search_products"),

    # Billing
    path("billing/", views.billing, name="billing"),
    path("billing/add/<int:pk>/", views.add_to_bill, name="add_to_bill"),
    path("billing/update/", views.update_bill, name="update_bill"),
    path("checkout/", views.checkout, name="checkout"),
    path("receipt/<int:bill_id>/", views.receipt, name="receipt"),

    # Returns
    path("returns/", views.return_search, name="return_search"),
    path("returns/bill/<int:bill_id>/", views.return_bill, name="return_bill"),

    # Deposits (collect outstanding)
    path("deposit/", views.deposit_search, name="deposit_search"),
    path("deposit/<int:customer_id>/add/", views.add_deposit, name="add_deposit"),
]
