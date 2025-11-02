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

#         # Compose email
#         full_message = f"""
# New contact message from your website:

# Name: {name}
# Phone: {phone}
# Subject: {subject}

# Message:
# {message}
#         """

#         try:
#             send_mail(
#                 subject=f"[Contact Form] {subject}",
#                 message=full_message,
#                 from_email=settings.EMAIL_HOST_USER,  # use your server email
#                 recipient_list=['abubakrsheikh44@gmail.com'],
#                 fail_silently=False,
#             )
#             messages.success(request, '✅ Your message has been sent successfully!')
#         except Exception as e:
#             messages.error(request, f"⚠️ Error sending email: {str(e)}")

#         return redirect('index')

    return render(request, 'index.html')
