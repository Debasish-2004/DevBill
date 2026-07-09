from django.shortcuts import render

# Create your views here.
def owner_home(request):
    return render(request, "owner_home.html")