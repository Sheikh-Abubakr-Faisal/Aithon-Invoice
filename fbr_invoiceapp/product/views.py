from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from django.db.models import Q
from django.contrib import messages
from category.models import Category
from product.models import Product
import requests
from django.http import JsonResponse

@login_required(login_url='sign_in')
def all_products(request):
    company = request.user.company
    categories = Category.objects.filter(company=company)
    token = company.fbr_api_key

    # Fetch UOMs from FBR API
    try:
        uom_url = "https://gw.fbr.gov.pk/pdi/v1/uom"
        headers = {"Authorization": f"Bearer {token}"}
        uom_response = requests.get(uom_url, headers=headers, timeout=10)

        uoms = []
        if uom_response.status_code == 200:
            uoms = uom_response.json()  # [{"uoM_ID": 77, "description": "Square Metre"}, ...]
    except Exception as e:
        uoms = []

    # Fetch HS Codes from FBR API
    try:
        hs_url = "https://gw.fbr.gov.pk/pdi/v1/itemdesccode"
        headers = {"Authorization": f"Bearer {token}"}
        hs_response = requests.get(hs_url, headers=headers, timeout=10)

        hs_codes = []
        if hs_response.status_code == 200:
            hs_codes = hs_response.json()  # [{"hS_CODE": "8432.1010", "description": "NUCLEAR REACTOR..."}, ...]
    except Exception as e:
        hs_codes = []

    # Handle product create
    if request.method == 'POST':
        item_code = request.POST.get('item_code')
        item_name = request.POST.get('item_name')
        item_category = request.POST.get('item_category')
        item_uom = request.POST.get('item_uom')
        item_unit_price = request.POST.get('item_unit_price')
        item_type = request.POST.get('product_type')

        try:
            category = Category.objects.get(id=item_category, company=company)
            Product.objects.create(
                code=item_code,
                name=item_name,
                category=category,
                unit_of_measurement=item_uom,
                unit_price=item_unit_price,
                product_type=item_type,
                company=company
            )
            messages.success(request, f'Product "{item_name}" created successfully.')
            return redirect('all_products')
        except IntegrityError:
            messages.error(request, f"Product '{item_name}' already exists!")
            return redirect('all_products')
        except Exception as e:
            messages.error(request, f"Something went wrong: {e}")
            return redirect('all_products')
        
    # Search and list products
    products = Product.objects.filter(company=company)
    if request.GET.get('search'):
        search = request.GET.get('search')
        products = products.filter(Q(name__icontains=search) | Q(code__icontains=search))

    context = {
        'products': products,
        'categories': categories,
        'uoms': uoms,
        'hs_codes': hs_codes,
        'title': "All Products"
    }
    return render(request, 'all_products.html', context)

@login_required(login_url='sign_in')
def fetch_uom(request):
    hs_code = request.GET.get("hs_code")
    annexure_id = 3  # always 3 for Sales
    company=request.user.company
    token = company.fbr_api_key

    if not hs_code:
        return JsonResponse({"error": "HS Code is required"}, status=400)

    # Fetch UOMs from FBR API based on HS Code
    url = f"https://gw.fbr.gov.pk/pdi/v2/HS_UOM?hs_code={hs_code}&annexure_id={annexure_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return JsonResponse(response.json(), safe=False)  # return API data as JSON
        else:
            return JsonResponse({"error": response.text}, status=response.status_code)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required(login_url='sign_in')
def del_product(request, id):
    company = request.user.company
    product = get_object_or_404(Product, id=id, company=company)
    purchase_items = product.purchaseitem_set.all()
    sale_items = product.saleitem_set.all()

    if purchase_items.exists() or sale_items.exists():
        messages.error(
            request,
            f'Product "{product.name}" is assigned to {purchase_items.count()} purchase item(s) and '
            f'{sale_items.count()} sale item(s). Please delete or update those invoices before deleting this product.'
        )
        return redirect('all_products')
    product.delete()
    messages.success(request, f'Product "{product.name}" deleted successfully.')
    return redirect('all_products')

@login_required(login_url='sign_in')
def update_product(request, id):
    company = request.user.company
    product = get_object_or_404(Product, id=id, company=company)
    categories = Category.objects.filter(company=company)
    token = company.fbr_api_key

    # Fetch UOMs from FBR API
    try:
        uom_url = "https://gw.fbr.gov.pk/pdi/v1/uom"
        headers = {"Authorization": f"Bearer {token}"}
        uom_response = requests.get(uom_url, headers=headers, timeout=10)

        uoms = []
        if uom_response.status_code == 200:
            uoms = uom_response.json()
    except Exception:
        uoms = []

    # Fetch HS Codes from FBR API
    try:
        hs_url = "https://gw.fbr.gov.pk/pdi/v1/itemdesccode"
        headers = {"Authorization": f"Bearer {token}"}
        hs_response = requests.get(hs_url, headers=headers, timeout=10)

        hs_codes = []
        if hs_response.status_code == 200:
            hs_codes = hs_response.json()
    except Exception:
        hs_codes = []

    if request.method == 'POST':
        item_code = request.POST.get('item_code')
        item_name = request.POST.get('item_name')
        item_category = request.POST.get('item_category')
        item_uom = request.POST.get('item_uom')
        item_unit_price = request.POST.get('item_unit_price')

        try:
            category = get_object_or_404(Category, id=item_category, company=company)
            product.code = item_code
            product.name = item_name
            product.category = category
            product.unit_of_measurement = item_uom
            product.unit_price = item_unit_price
            product.save()
            messages.success(request, f'Product "{item_name}" updated successfully.')
            return redirect('all_products')
        except IntegrityError:
            messages.error(request, f"Product '{item_name}' already exists!")
        except Exception as e:
            messages.error(request, f"Something went wrong: {e}")
        return redirect('all_products')

    context = {
        'product': product,
        'categories': categories,
        'uoms': uoms,
        'hs_codes': hs_codes,
        'title': "Update Product"
    }

    return render(request, 'all_products.html', context)
