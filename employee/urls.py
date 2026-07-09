from django.urls import path
from . import views

urlpatterns = [
    path("", views.employee_home, name="employee_home"),
]