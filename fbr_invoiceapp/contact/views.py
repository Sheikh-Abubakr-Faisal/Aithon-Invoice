from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ContactMessage
from django.conf import settings

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # Save to database
        contact_message = ContactMessage.objects.create(
            name=name,
            phone=phone,
            subject=subject,
            message=message
        )

        messages.success(request, "Your message has been received. We will contact you soon!")
        return redirect('index')

    return render(request, 'index.html')
