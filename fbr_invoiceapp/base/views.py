from django.shortcuts import render, redirect
from .models import *
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model, logout
User = get_user_model()
from django.contrib.auth.decorators import login_required

def index(request):
    return render(request, 'index.html')

def sign_in(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, "Both email and password are required.")
            return redirect('sign_in')
        
        if not CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Invalid Email')
            return redirect('/sign_in/')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            request.session['company_id'] = getattr(user, 'company_id', None)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password.")
            return redirect('sign_in')

    return render(request, 'signin.html')

@login_required(login_url='sign_in')
def user_logout(request):
    logout(request)
    return redirect('sign_in')
