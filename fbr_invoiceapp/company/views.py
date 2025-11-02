from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required(login_url='sign_in')
def company_info(request):
    company = request.user.company
    context = {
        'company_info': {
            'name': company.name,
            'address': company.address,
            'ntn': company.ntn,
            'strn': company.strn,
            'phone': company.phone,
            'email': company.email,
        }
    }
    return render(request, 'company_info.html', context)