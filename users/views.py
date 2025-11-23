from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! Please login.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def add_money(request):
    if request.method == 'POST':
        amount = float(request.POST.get('amount'))
        request.user.profile.balance = float(request.user.profile.balance) + amount
        request.user.profile.save()
        messages.success(request, f'Added ${amount} to wallet.')
        return redirect('dashboard')
    return render(request, 'users/add_money.html')