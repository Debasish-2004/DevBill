from django.shortcuts import render

# Create your views here.
def employee_home(request):
    return render(request, "employee_home.html")