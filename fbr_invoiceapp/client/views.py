from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Client
from company.models import CompanyInfo
import requests
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from purchase_inv.models import PurchaseInvoice
from sale_inv.models import SaleInvoice
from django.contrib.auth.decorators import login_required

@login_required(login_url='sign_in')
def client_list(request):
    # Search filter
    search_query = request.GET.get("search", "")
    if search_query:
        clients = Client.objects.filter(name__icontains=search_query)
    else:
        clients = Client.objects.all().order_by("-id")  # newest first

    context = {
        "clients": clients,
        "total_clients": clients.count(),
    }
    return render(request, "client.html", context)

@login_required(login_url='sign_in')
def client_create(request):
    company = request.user.company
    token = company.fbr_api_key
    provinces = []

    # Fetch provinces from FBR API
    try:
        province_url = "https://gw.fbr.gov.pk/pdi/v1/provinces"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(province_url, headers=headers, timeout=10)
        if response.status_code == 200:
            provinces = response.json()
    except Exception:
        provinces = []

    if request.method == "POST":
        name = request.POST.get("name")
        ntn = request.POST.get("ntn")
        registration_type = request.POST.get("registration_type")  # from input (auto-filled by AJAX)
        province_code = request.POST.get("province_code")
        province_name = request.POST.get("province_name")
        address = request.POST.get("address")
        client_type = request.POST.get("client_type")

        # Validate NTN/CNIC length
        if ntn and len(ntn) not in [7, 13]:
            messages.error(request, "NTN/CNIC must be 7 or 13 digits only.")
            return redirect("client_create")

        # If 7-digit NTN → verify with FBR STATL API
        if ntn and len(ntn) == 7:
            statl_url = "https://gw.fbr.gov.pk/dist/v1/statl"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            today_date = datetime.today().strftime("%Y-%m-%d")
            params = {"regno": ntn, "date": today_date}

            try:
                response = requests.get(statl_url, headers=headers, params=params, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    status_text = result.get('status', '')
                    if status_text.lower() != 'active':
                        messages.error(request, f"NTN {ntn} is In-Active according to FBR.")
                        return redirect("client_create")
                else:
                    messages.error(request, "Could not verify NTN with FBR. Try again later.")
                    return redirect("client_create")
            except Exception as e:
                messages.error(request, f"Error checking NTN: {e}")
                return redirect("client_create")

        # Save client
        try:
            client = Client.objects.create(
                name=name,
                ntn=ntn,
                registration_type=registration_type,
                province_code=province_code,
                province_name=province_name,
                address=address,
                client_type=client_type,
                company=company,
            )
            messages.success(request, f"Client '{client.name}' created successfully!")
            return redirect("client_list")
        except Exception as e:
            messages.error(request, f"Error creating client: {e}")
            return redirect("client_list")

    return render(request, "add_client.html", {
        "provinces": provinces,
        "is_edit": False,
        "client": None,
    })

def check_registration_type(request):
    company = request.user.company
    token = company.fbr_api_key
    reg_no = request.GET.get("regno")

    # If user left NTN/CNIC blank → unregistered
    if not reg_no:
        return JsonResponse({
            "statuscode": "01",
            "registration_type": "Unregistered"
        })

    # If provided but invalid length
    if len(reg_no) not in [7, 13]:
        return JsonResponse({"error": "NTN/CNIC must be 7 or 13 digits."}, status=400)

    try:
        url = "https://gw.fbr.gov.pk/dist/v1/Get_Reg_Type"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"Registration_No": reg_no}
        print("FBR Request Payload:", payload)


        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            print("FBR Response:", result)
            return JsonResponse({
                "statuscode": result.get("statuscode"),
                "registration_type": result.get("REGISTRATION_TYPE", "").capitalize() or "Unregistered"
            })
        else:
            return JsonResponse({"error": "FBR server error"}, status=500)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@login_required(login_url='sign_in')
def client_edit(request, client_id):
    company = request.user.company
    client = get_object_or_404(Client, id=client_id, company=request.user.company)
    token = company.fbr_api_key
    provinces = []

    # Fetch provinces from FBR API
    try:
        province_url = "https://gw.fbr.gov.pk/pdi/v1/provinces"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(province_url, headers=headers, timeout=10)
        if response.status_code == 200:
            provinces = response.json()
    except Exception:
        provinces = []

    if request.method == "POST":
        client.name = request.POST.get("name")
        client.ntn = request.POST.get("ntn")
        client.registration_type = request.POST.get("registration_type")
        client.province_code = request.POST.get("province_code")
        client.province_name = request.POST.get("province_name")
        client.address = request.POST.get("address")
        client.client_type = request.POST.get("client_type")
        client.save()

        messages.success(request, f"Client '{client.name}' updated successfully!")
        return redirect("client_list")

    return render(request, "add_client.html", {
        "provinces": provinces,
        "client": client,
        "is_edit": True,   # tells template it's edit mode
    })

@login_required(login_url='sign_in')
def client_delete(request, client_id):
    """
    Delete a client if it is not used in any SaleInvoice or PurchaseInvoice.
    """
    company = request.user.company
    client = get_object_or_404(Client, id=client_id, company=company)

    # Check if client is used in SaleInvoice or PurchaseInvoice
    sale_invoices = SaleInvoice.objects.filter(buyer=client).exists()
    purchase_invoices = PurchaseInvoice.objects.filter(supplier=client).exists()

    if sale_invoices or purchase_invoices:
        messages.error(
            request,
            f"Client '{client.name}' cannot be deleted because it is used in an invoice."
        )
        return redirect("client_list")

    try:
        client.delete()
        messages.success(request, f"Client '{client.name}' deleted successfully!")
    except Exception as e:
        messages.error(request, f"Error deleting client: {e}")

    return redirect("client_list")