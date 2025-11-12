from django.template.loader import get_template, render_to_string
import weasyprint
from weasyprint import HTML, CSS
import requests
import json
from django.http import JsonResponse, HttpResponse
from .models import SaleInvoice, SaleItem
from product.models import Product
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import IntegrityError
from num2words import num2words 
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.auth.decorators import login_required
from datetime import datetime, timezone
from django.views.decorators.http import require_POST
from django.contrib.staticfiles import finders
from purchase_inv.models import PurchaseItem
from client.models import Client
from decimal import Decimal
import qrcode
import base64
import json
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils.dateparse import parse_datetime

@login_required(login_url='sign_in')
def sale_invoice_details(request, invoice_id=None):
    company = request.user.company
    token = company.fbr_api_key
    document_types = []

    try:
        doc_url = "https://gw.fbr.gov.pk/pdi/v1/doctypecode"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(doc_url, headers=headers, timeout=10)
        if response.status_code == 200:
            document_types = response.json()
    except Exception:
        document_types = []

    clients = Client.objects.filter(company=request.user.company, client_type__in=["Buyer", "Both"])

    if request.method == 'POST':
        invoice_number = request.POST.get('invoice_number')
        date = request.POST.get('date')
        buyer_id = request.POST.get('buyer')
        doc_type_id = request.POST.get('doc_type_id')
        doc_type_description = request.POST.get('doc_type_description')

        try:
            buyer = get_object_or_404(Client, id=buyer_id, company=request.user.company)
        except Client.DoesNotExist:
            messages.error(request, "Selected buyer does not exist.")
            return redirect('sale_invoice_details')
        
        buyer_ntn = buyer.ntn or ""

        if len(buyer_ntn) == 7:
            statl_url = "https://gw.fbr.gov.pk/dist/v1/statl"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            params = {"regno": buyer_ntn, "date": date}

            try:
                response = requests.get(statl_url, headers=headers, params=params, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    status_text = result.get('status', '')  # Only use 'status' to check Active/Inactive

                    if status_text.lower() != 'active':
                        messages.error(request, f"Buyer NTN {buyer_ntn} is In-Active according to FBR.")
                        return redirect('sale_invoice_details')
                    # If "Active", proceed normally
                else:
                    messages.error(request, "Could not verify NTN with FBR. Try again later.")
                    return redirect('sale_invoice_details')
            except Exception as e:
                messages.error(request, f"Error checking NTN: {e}")
                return redirect('sale_invoice_details')


        # Save the invoice if validation passed
        try:
            company = request.user.company
            invoice = SaleInvoice.objects.create(
                company=company,
                invoice_number=invoice_number,
                date=date,
                doc_type_id=doc_type_id,
                doc_type_description=doc_type_description,
                buyer=buyer
            )
            messages.success(request, f'Sale Invoice "{invoice_number}" created successfully.')
            return redirect('sale_invoice', invoice_id=invoice.id)
        except IntegrityError:
            messages.success(request, f"Invoice '{invoice_number}' already exists!")
        except Exception as e:
            messages.success(request, f"Something went wrong: {e}")

        return redirect('sale_invoice_details')

    return render(request, 'sale_invoice_details.html', {
        'title': 'Sale Invoice Details',
        'clients': clients,
        'document_types': document_types
    })

@login_required(login_url='sign_in')
def sale_invoice(request, invoice_id):
    company = request.user.company
    products = Product.objects.filter(company=company)
    invoice = get_object_or_404(SaleInvoice, id=invoice_id, company=company)
    item = SaleItem.objects.filter(invoice=invoice)

    # Fetch from FBR API
    sro_items, transaction_types, sro_schedule, rates = [], [], [], []

    token = company.fbr_api_key
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # --- Get Transaction Types ---
        transtype_url = "https://gw.fbr.gov.pk/pdi/v1/transtypecode"
        response = requests.get(transtype_url, headers=headers, timeout=10)
        if response.status_code == 200:
            transaction_types = response.json()

    except Exception as e:
        messages.warning(request, f"Could not fetch data from FBR API: {e}")

    if request.method == 'POST':
        item_id = request.POST.get('item')
        item_quantity = request.POST.get('item_quantity')
        item_unit_price = request.POST.get('item_unit_price')
        retailPrice = request.POST.get('retailPrice')
        rate = request.POST.get('rate')
        rate_id = request.POST.get("rateId")  
        salesTaxWithheldAtSource = request.POST.get('salesTaxWithheldAtSource', 0)
        extraTax = request.POST.get('extraTax', 0)
        furtherTax = request.POST.get('furtherTax', 0)
        fedPayable = request.POST.get('fedPayable', 0)
        discount = request.POST.get('discount', 0)

        # user selections
        saleType = request.POST.get('saleType')  
        saleTypeDesc = request.POST.get('saleTypeDesc')
        sroScheduleNo = request.POST.get('sroScheduleNo')
        sro_schedule_desc = request.POST.get('sro_schedule_desc')
        sroItemSerialNo = request.POST.get('sroItemSerialNo')
        action = request.POST.get("action")

        if not item_id or not item_quantity or not item_unit_price or not rate:
            messages.error(request, "All required fields must be filled.")
            return redirect("sale_invoice", invoice_id=invoice.id)

        try:
            product = Product.objects.get(id=item_id, company=company)
            quantity = Decimal(item_quantity)
            unit_price = float(item_unit_price)
            rate = Decimal(rate)

            if quantity <= 0:
                messages.error(request, "Quantity must be at least 1.")
                return redirect("sale_invoice", invoice_id=invoice.id)

            # Stock validation
            # --- Stock validation (skip for services) ---
            if product.product_type == 'good':
                purchased_stock = PurchaseItem.objects.filter(
                    product=product, invoice__company=company
                ).aggregate(total_qty=Sum("quantity"))["total_qty"] or 0

                sold_stock = SaleItem.objects.filter(
                    product=product, invoice__company=company
                ).aggregate(total_qty=Sum("quantity"))["total_qty"] or 0

                available_stock = purchased_stock - sold_stock

                if available_stock <= 0:
                    messages.error(request, f"Item '{product.name}' is out of stock.")
                    return redirect("sale_invoice", invoice_id=invoice.id)

                if quantity > available_stock:
                    messages.error(
                        request,
                        f"Not enough stock for '{product.name}'. "
                        f"Available: {available_stock}, Tried: {quantity}."
                    )
                    return redirect("sale_invoice", invoice_id=invoice.id)
            else:
                # Services don’t need stock checking
                available_stock = None


            # GST rate validation
            existing_items = SaleItem.objects.filter(invoice=invoice)
            if existing_items.exists():
                existing_rate = int(existing_items.first().rate)
                if existing_rate != rate:
                    messages.error(
                        request,
                        f"All items in invoice must have the same GST Rate ({existing_rate}%)."
                    )
                    return redirect("sale_invoice", invoice_id=invoice.id)
                
                # --- Add transaction type validation ---
                existing_sale_type = existing_items.first().saleTypeDesc
                if existing_sale_type != saleTypeDesc:
                    messages.error(
                        request,
                        f"All items in invoice must have the same Transaction Type."
                    )
                    return redirect("sale_invoice", invoice_id=invoice.id)

            # Add new sale item
            if action == "add_item":
                SaleItem.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    retailPrice=retailPrice, 
                    rate=rate,
                    rate_id=rate_id,
                    salesTaxWithheldAtSource=salesTaxWithheldAtSource,
                    extraTax=extraTax,
                    furtherTax=furtherTax,
                    fedPayable=fedPayable,
                    discount=discount,
                    saleType=saleType,  
                    saleTypeDesc=saleTypeDesc,
                    sroScheduleNo=sroScheduleNo,
                    sro_schedule_desc=sro_schedule_desc,
                    sroItemSerialNo=sroItemSerialNo,
                )
                print("SALETYPE:", saleType)
                print("SALETYPE DESC:", saleTypeDesc)

                messages.success(request, f'Item "{product.name}" added successfully.')

        except IntegrityError:
            messages.error(request, f"Item '{product.name}' already exists!")
        except Product.DoesNotExist:
            messages.error(request, "Selected product does not exist.")
        except Exception as e:
            messages.error(request, f"Something went wrong: {e}")

        return redirect('sale_invoice', invoice_id=invoice.id)
    
    default_trans_type_id = 75
    date_str = invoice.date.strftime("%d-%b-%Y").upper()
    rate_url = f"https://gw.fbr.gov.pk/pdi/v2/SaleTypeToRate?date={date_str}&transTypeId={default_trans_type_id}&originationSupplier={invoice.buyer.province_code}"
    response = requests.get(rate_url, headers=headers, timeout=20)
    if response.status_code == 200:
        rates = response.json()
    else:
        messages.warning(request, f"FBR API error {response.status_code} while fetching rates.")

    context = {
        'products': products,
        'item': item,
        'invoice': invoice,
        'sro_items': sro_items,
        'transaction_types': transaction_types,
        'sro_schedule': sro_schedule,
        'rates': rates,   
        'selected_rate': None,
        'title': 'Add Sale Items',
    }

    return render(request, 'sale_invoice.html', context)

@login_required
def get_rates(request):
    trans_id = request.GET.get("transTypeId")
    invoice_id = request.GET.get("invoiceId")  # send this from frontend

    if not trans_id or not invoice_id:
        return JsonResponse([], safe=False)

    # Get invoice from DB
    invoice = get_object_or_404(
        SaleInvoice, id=invoice_id, company=request.user.company
    )

    # province_code is already stored in DB (coming from FBR)
    province_id = invoice.buyer.province_code  

    company = request.user.company
    token = company.fbr_api_key
    headers = {"Authorization": f"Bearer {token}"}

    # Format date for API
    date_str = invoice.date.strftime("%d-%b-%Y").upper()

    # Build FBR API URL
    url = (
        f"https://gw.fbr.gov.pk/pdi/v2/SaleTypeToRate?date={date_str}&transTypeId={trans_id}&originationSupplier={province_id}"
    )

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return JsonResponse(response.json(), safe=False)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse([], safe=False)

@login_required
def get_sro_schedule(request):
    rate_id = request.GET.get("rateId")
    print(rate_id)

    if not rate_id:
        return JsonResponse([], safe=False)

    invoice_id = request.GET.get("invoiceId")  # optional: if you want to use invoice date
    invoice = None
    if invoice_id:
        invoice = get_object_or_404(SaleInvoice, id=invoice_id, company=request.user.company)

    company = request.user.company
    token = company.fbr_api_key
    headers = {"Authorization": f"Bearer {token}"}

    # Use invoice date if available, else today
    if invoice:
        date_str = invoice.date.strftime("%d-%b-%Y").upper()
    else:
        from datetime import datetime
        date_str = datetime.now().strftime("%d-%b-%Y").upper()

    url = f"https://gw.fbr.gov.pk/pdi/v1/SroSchedule?rate_id={rate_id}&date={date_str}&origination_supplier_csv={invoice.buyer.province_code}"
    print("FBR URL:", url)

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # --- Debug prints ---
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)
        print("Response JSON:", response.json())
        # -------------------

        if response.status_code == 200:
            return JsonResponse(response.json(), safe=False)
    except requests.RequestException as e:
        print("Request Exception:", e)  # Debug
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse([], safe=False)


@login_required
def get_hs_uom(request):
    hs_code = request.GET.get("hs_code")
    annexure_id = request.GET.get("annexure_id")

    if not hs_code or not annexure_id:
        return JsonResponse({"error": "Missing parameters"}, status=400)

    company = request.user.company
    token = company.fbr_api_key
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch HS UOM from FBR API
    url = f"https://gw.fbr.gov.pk/pdi/v2/HS_UOM?hs_code={hs_code}&annexure_id={annexure_id}"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return JsonResponse(response.json(), safe=False)
        else:
            return JsonResponse(
                {"error": f"FBR API error {response.status_code}"}, 
                status=response.status_code
            )
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def get_sro_items(request):
    sro_id = request.GET.get("sro_id")
    invoice_id = request.GET.get("invoiceId")

    if not sro_id:
        return JsonResponse({"error": "Missing sro_id"}, status=400)

    invoice = None
    if invoice_id:
        invoice = get_object_or_404(SaleInvoice, id=invoice_id, company=request.user.company)

    company = request.user.company
    token = company.fbr_api_key
    headers = {"Authorization": f"Bearer {token}"}

    # Use invoice date if available, otherwise today
    if invoice:
        date_str = invoice.date.strftime("%Y-%m-%d")  # required format: YYYY-MM-DD
    else:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")

    url = f"https://gw.fbr.gov.pk/pdi/v2/SROItem?date={date_str}&sro_id={sro_id}"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return JsonResponse(response.json(), safe=False)
        else:
            return JsonResponse(
                {"error": f"FBR API error {response.status_code}"},
                status=response.status_code
            )
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required(login_url='sign_in')
def sale_invoice_view(request, invoice_id):
    company = request.user.company
    invoice = get_object_or_404(SaleInvoice, id=invoice_id, company=company)
    items = SaleItem.objects.filter(invoice=invoice)

    subtotal = sum(i.total_price() for i in items) # subtotal = sum of all item total_price
    gst_total = subtotal * (invoice.gst_rate / 100) # gst_total = gst on subtotal
    grand_total = subtotal + gst_total # grand_total = Sum of subtotal and gst_total

    in_words = num2words(grand_total, to= 'cardinal', lang='en')

    company_info = {
        'name': invoice.company.name,
        'address': invoice.company.address,
        'ntn': invoice.company.ntn,
        'strn': invoice.company.strn,
        'phone': invoice.company.phone,
        'email': invoice.company.email,
    }
    

    context = {
        'invoice': invoice,
        'items': items,
        'title': 'Sale Invoice View',
        'subtotal': subtotal,
        'gst_total': gst_total,
        'grand_total': grand_total,
        'in_words': in_words,
        'company_info': company_info,
    }
    return render(request, "sale_invoice_pdf.html", context)

@login_required(login_url='sign_in')
def sale_inv_product_update(request, invoice_id, item_id):
    company = request.user.company
    products = Product.objects.filter(company=company)
    invoice = get_object_or_404(SaleInvoice, id=invoice_id, company=company)
    item = get_object_or_404(SaleItem, id=item_id, invoice=invoice) 

    token = company.fbr_api_key
    headers = {"Authorization": f"Bearer {token}"}

    transaction_types, rates, sro_schedule = [], [], []

    try:
        transtype_url = "https://gw.fbr.gov.pk/pdi/v1/transtypecode"
        response = requests.get(transtype_url, headers=headers, timeout=10)
        if response.status_code == 200:
            transaction_types = response.json()
    except Exception as e:
        messages.warning(request, f"Could not fetch transaction types: {e}")

    # --- Fetch rates same as in sale_invoice view ---
    default_trans_type_id = 75
    date_str = invoice.date.strftime("%d-%b-%Y").upper()
    rate_url = f"https://gw.fbr.gov.pk/pdi/v2/SaleTypeToRate?date={date_str}&transTypeId={default_trans_type_id}&originationSupplier={invoice.buyer.province_code}"
    try:
        rate_response = requests.get(rate_url, headers=headers, timeout=10)
        if rate_response.status_code == 200:
            rates = rate_response.json()
    except Exception as e:
        messages.warning(request, f"Could not fetch rates: {e}")


    if request.method == "POST":
        quantity = request.POST.get("item_quantity")
        unit_price = request.POST.get("item_unit_price")
        rate = request.POST.get('rate')
        retailPrice = request.POST.get('retailPrice')
        salesTaxWithheldAtSource = request.POST.get('salesTaxWithheldAtSource')
        extraTax = request.POST.get('extraTax')
        furtherTax = request.POST.get('furtherTax')
        fedPayable = request.POST.get('fedPayable')
        discount = request.POST.get('discount')
        saleType = request.POST.get('saleType')
        sroScheduleNo = request.POST.get('sroScheduleNo')
        sroItemSerialNo = request.POST.get('sroItemSerialNo')
        action = request.POST.get("action")

        if not quantity or not unit_price:
            messages.error(request, "All fields are required.")
            return redirect("sale_inv_product_update", invoice_id=invoice.id, item_id=item.id)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                messages.error(request, "Quantity must be at least 1.")
                return redirect("sale_inv_product_update", invoice_id=invoice.id, item_id=item.id)

            product = item.product  

                        # calculate stock again
                        # --- Stock validation (skip for services) ---
            if product.product_type == 'good':
                purchased_stock = PurchaseItem.objects.filter(
                    product=product, product__company=company
                ).aggregate(total_qty=Sum("quantity"))["total_qty"] or 0

                sold_stock = (
                    SaleItem.objects.filter(product=product, product__company=company)
                    .exclude(id=item.id)
                    .aggregate(total_qty=Sum("quantity"))["total_qty"]
                    or 0
                )

                available_stock = purchased_stock - sold_stock

                if quantity > available_stock:
                    messages.error(
                        request,
                        f"Not enough stock for '{product.name}'. "
                        f"Available: {available_stock}, Tried: {quantity}."
                    )
                    return redirect("sale_inv_product_update", invoice_id=invoice.id, item_id=item.id)
            else:
                # Skip stock check for services
                available_stock = None

            item.quantity = quantity
            item.unit_price = unit_price
            item.rate = rate
            item.retailPrice = retailPrice
            item.salesTaxWithheldAtSource = salesTaxWithheldAtSource
            item.extraTax = extraTax
            item.furtherTax = furtherTax
            item.fedPayable = fedPayable
            item.discount = discount
            item.saleType = saleType
            item.sroScheduleNo = sroScheduleNo
            item.sroItemSerialNo = sroItemSerialNo
            item.save()

            messages.success(request, f'Item "{item.product.name}" updated successfully.')
            return redirect("sale_invoice", invoice_id=invoice.id)

        except Exception as e:
            messages.error(request, f"Something went wrong: {e}")
            return redirect("sale_invoice", invoice_id=invoice.id, item_id=item.id)

    # GET request → render form with prefilled values
    context = {
        "products": products,
        "invoice": invoice,
        "item":item,
        "transaction_types": transaction_types,
        "rates": rates,
        "sro_schedule": sro_schedule,
        "title": "Update Sale Item",
    }
    return render(request, "update_sale_inv_item.html", context)

@login_required(login_url='sign_in')
def delete_sale_inv_item(request, item_id):
    company = request.user.company
    sale_item = get_object_or_404(SaleItem, id=item_id, invoice__company=company)
    invoice_id = sale_item.invoice.id
    
    sale_item.delete()
    messages.success(request, "Item deleted successfully.")
    return redirect("sale_invoice", invoice_id=invoice_id)

@login_required(login_url='sign_in')
def all_sale_invoices(request):
    company = request.user.company

    invoices = SaleInvoice.objects.prefetch_related('items__product').filter(company=company).order_by('-date', '-id')
    invoice_count = invoices.count()

    query = request.GET.get('search')
    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) |   # search by invoice number
            Q(buyer_name__icontains=query) |    # search by customer name (if you have this field)
            Q(items__product__name__icontains=query)  # search by product name
        ).distinct()

    invoice_data = []

    for invoice in invoices:
        items = invoice.items.all()

        # Each item total
        item_data = []
        for item in items:
            item_data.append({
                "product": item.product.name,
                "code": item.product.code,
                "unit_of_measurement": item.product.unit_of_measurement,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_rate": item.rate,
                "discount": item.discount,
                "total": (item.quantity * item.unit_price) - item.discount,
            })

        invoice_data.append({
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "buyer_name": invoice.buyer.name,
            "buyer_ntn": invoice.buyer.ntn,
            "buyer_address": invoice.buyer.address,
            "province": invoice.buyer.province_name,
            "date": invoice.date,
            "tax_rate": items[0].rate if items else 0,
            "subtotal": invoice.subtotal(),
            "total_sales_tax_withheld": invoice.total_sales_tax_withheld(),
            "total_extra_tax": invoice.total_extra_tax(),
            "total_further_tax": invoice.total_further_tax(),
            "total_fed_payable": invoice.total_fed_payable(),
            "total_discount": invoice.total_discount(),
            "tax_total": invoice.tax_total(),
            "grand_total": invoice.grand_total(),
            "items": item_data,
            "invoice_total": sum(i["total"] for i in item_data),
        })

    context = {
        "invoice_data": invoice_data,
        "invoice_count": invoice_count,
        "title": "All Sale Invoices",
        "query": query or "",
    }

    return render(request, 'sale.html', context)

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

@require_POST
def post_sale_invoice(request, invoice_id):
    try:
        invoice = SaleInvoice.objects.get(id=invoice_id)
        company = invoice.company  

        payload = {
            "invoiceType": invoice.doc_type_description,
            "invoiceDate": str(invoice.date.strftime("%Y-%m-%d")),
            "sellerNTNCNIC": company.ntn,
            "sellerBusinessName": company.name,
            "sellerProvince": company.province_name,
            "sellerAddress": company.address.replace("\r\n", " "),
            "buyerNTNCNIC": invoice.buyer.ntn if invoice.buyer.ntn else "",
            "buyerBusinessName": invoice.buyer.name,
            "buyerProvince": invoice.buyer.province_name,
            "buyerAddress": invoice.buyer.address.replace("\r\n", " "),
            "buyerRegistrationType": invoice.buyer.registration_type,
            "invoiceRefNo": str(invoice.invoice_number),
            "scenarioId": "SN001",
            "items": []
        }

        print("========== DEBUGGING ITEMS ==========")
        for idx, item in enumerate(invoice.items.all(), start=1):
            gst_amount = float(item.gst_amount())
            total_price = float(item.total_price())
            retail_price = float(item.retailPrice or 0)

            print(f"Item #{idx}")
            print(f"  HS Code: {item.product.code}")
            print(f"  Description: {item.product.name}")
            print(f"  Quantity: {item.quantity}")
            print(f"  Unit Price: {item.unit_price}")
            print(f"  Retail Price: {retail_price}")
            print(f"  Discount: {item.discount}")
            print(f"  Rate: {item.rate}%")
            print(f"  Total Price: {total_price}")
            print(f"  GST Amount (calculated): {gst_amount}")
            print("-----------------------------------")

        for item in invoice.items.all():
            payload["items"].append({
                "hsCode": item.product.code,
                "productDescription": item.product.name,
                "rate": f"{item.rate}%",
                "uoM": item.product.unit_of_measurement,
                "quantity": round(float(item.quantity), 4),
                "totalValues": round(float(item.total_price() + item.gst_amount()), 2),
                "valueSalesExcludingST": float(item.total_price() - item.discount),
                "fixedNotifiedValueOrRetailPrice": float(item.retailPrice or 0),
                "salesTaxApplicable": round(float(item.gst_amount()), 2),
                "salesTaxWithheldAtSource": float(item.salesTaxWithheldAtSource or 0),
                "extraTax": "" if item.extraTax == 0 else float(item.extraTax),
                "furtherTax": float(item.furtherTax or 0),
                "sroScheduleNo": item.sro_schedule_desc or "",
                "fedPayable": float(item.fedPayable or 0),
                "discount": float(item.discount or 0),
                "saleType": item.saleTypeDesc,
                "sroItemSerialNo": item.sroItemSerialNo or "",
            })

        print("====================================")
        print("Payload being sent to FBR:")
        print(json.dumps(payload, indent=2))
        print("====================================")

        token = company.fbr_api_key
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        url = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb"
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        fbr_response = response.json()

        print("========== FBR RESPONSE ==========")
        print(fbr_response)
        print("=================================")


        response_json = fbr_response
        validation = response_json.get('validationResponse', {})

        # 🟢 SUCCESS CASE
        if validation.get("status") == "Valid":
            invoice.is_sent = True

            fbr_invoice_number = (
                fbr_response.get("invoiceNumber")
                or validation.get("invoiceNumber")
            )
            if fbr_invoice_number:
                invoice.fbr_invoice_number = fbr_invoice_number

            # ✅ Parse and set date
            fbr_date_str = (
                fbr_response.get("dated")
                or fbr_response.get("dateTime")
                or fbr_response.get("fbrInvoiceDate")
                or fbr_response.get("invoiceDateTime")
            )

            if fbr_date_str:
                try:
                    invoice.fbr_dated = parse_datetime(fbr_date_str)
                except Exception:
                    from datetime import datetime
                    invoice.fbr_dated = datetime.strptime(fbr_date_str, "%Y-%m-%d %H:%M:%S")
            else:
                messages.warning(request, "No FBR date found in response.")
                invoice.fbr_dated = timezone.now()

            # ✅ Save invoice *before* generating QR code
            invoice.save(update_fields=["is_sent", "fbr_invoice_number", "fbr_dated"])

            # ✅ Now generate and attach the QR code
            generate_invoice_qr(invoice)

            messages.success(request, "Invoice successfully validated and posted to FBR.")
            return redirect("invoice_view", invoice_id=invoice.id)

        # 🔴 FAILURE CASE — SHOW EXACT FBR ERROR
        else:
            error_detail = validation.get('error', 'Unknown error from FBR')
            error_code = validation.get('errorCode', '')
            messages.error(request, f"FBR Error {error_code}: {error_detail}")

            invoice_statuses = validation.get("invoiceStatuses", [])
            if invoice_statuses:
                for err in invoice_statuses:
                    messages.error(request, f"{err.get('errorCode')}: {err.get('error')}")

            # Stay on same page
            return redirect("sale_invoice", invoice_id=invoice.id)

    except SaleInvoice.DoesNotExist:
        messages.error(request, "Invoice not found.")
        return redirect("invoice_list")
    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
        return redirect("sale_invoice", invoice_id=invoice_id)

def invoice_pdf(request, invoice_id):
    try:
        invoice = SaleInvoice.objects.get(id=invoice_id)
        items = invoice.items.all()
        company_info = invoice.company

        template = get_template("sale_invoice_fbr.html")
        html_content = template.render({
            "invoice": invoice,
            "items": items,
            "company_info": company_info,
            "title": f"Invoice_{invoice.invoice_number}"
        })

        # Find CSS files
        bootstrap_path = finders.find("bs/css/bootstrap.min.css")
        custom_css_path = finders.find("css/invoice_pdf_css.css")
        print("Custom CSS Path:", custom_css_path)
        # print("Bootstrap CSS Path:", bootstrap_path)

        stylesheets = []
        # if bootstrap_path:
        #     stylesheets.append(CSS(bootstrap_path))
        if custom_css_path:
            stylesheets.append(CSS(custom_css_path))

        # Extra inline CSS for page margins
        stylesheets.append(CSS(string='@page { size: A4; margin: 1cm }'))

        pdf_file = HTML(
            string=html_content,
            base_url=request.build_absolute_uri()
        ).write_pdf(stylesheets=stylesheets)

        response = HttpResponse(pdf_file, content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        return response

    except SaleInvoice.DoesNotExist:
        return HttpResponse("Invoice not found.", status=404)
    
def invoice_view(request, invoice_id):
    invoice = SaleInvoice.objects.get(id=invoice_id)
    items = invoice.items.all()
    company_info = invoice.company

    context = {
        "invoice": invoice,
        "items": items,
        "company_info": company_info,
        "title": f"Invoice_{invoice.invoice_number}"
    }

    return render(request, "sale_invoice_fbr.html", context)

def generate_invoice_qr(invoice):
    verification_url = f"https://aithon-invoice.onrender.com/verify/{invoice.fbr_invoice_number}"

    qr = qrcode.QRCode(version=2, box_size=10, border=4)
    qr.add_data(verification_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    filename = f"invoice_qr_{invoice.fbr_invoice_number}.png"
    invoice.qr_code.save(filename, ContentFile(buffer.getvalue()), save=True)

def verify_invoice(request, fbr_invoice_number):
    try:
        print(f"Verifying FBR invoice number: {fbr_invoice_number}")  # Debug log
        invoice = SaleInvoice.objects.select_related('company', 'buyer').get(fbr_invoice_number=fbr_invoice_number)
        if not invoice:
            return render(request, 'invalid_invoice.html', status=404)
    except SaleInvoice.DoesNotExist:
        return render(request, 'invalid_invoice.html', status=404)
    except Exception as e:
        return render(request, 'invalid_invoice.html', status=500)
    
    return render(request, 'qr_varification.html', {'invoice': invoice,
                                                    'grand_total': invoice.grand_total(),
                                                    'company_info': invoice.company,
                                                         })




