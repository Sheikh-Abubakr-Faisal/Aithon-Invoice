from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError, transaction
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.template.loader import render_to_string
import weasyprint
from num2words import num2words
from .models import PurchaseInvoice, PurchaseItem
from product.models import Product
from stock.models import Stock
from client.models import Client
from weasyprint import HTML, CSS
from django.template.loader import get_template
from django.contrib.staticfiles import finders
from django.db import transaction
from django.views.decorators.http import require_POST

@login_required(login_url='sign_in')
def purchase_invoice_details(request, invoice_id=None):
    # Creating Purchase Invoice
    if request.method == 'POST':
        invoice_number = request.POST.get('invoice_number')
        date = request.POST.get('date')
        supplier_id = request.POST.get('supplier')

        try:
            supplier = get_object_or_404(Client, id=supplier_id, company=request.user.company)

            invoice = PurchaseInvoice.objects.create(
                company=request.user.company,
                invoice_number=invoice_number,
                date=date,
                supplier=supplier,
            )

            messages.success(request, f'Purchase Invoice "{invoice_number}" created successfully. You can now add items to this invoice.')
            return redirect('purchase_invoice', invoice_id=invoice.id)
        except Client.DoesNotExist:
            messages.error(request, "Selected supplier does not exist.")
        except IntegrityError:
            messages.success(request, f"Invoice '{invoice_number}' already exists!")
        except Exception as e:
            messages.error(request, f"Something went wrong: {e}")
        return redirect('purchase_invoice_details')
    
    clients = Client.objects.filter(company=request.user.company, client_type__in=["Supplier", "Both"])

    return render(request, 'purchase_invoice_details.html', {'title':'Purchase Invoice Details', 'clients': clients})

@login_required(login_url='sign_in')
def purchase_invoice(request, invoice_id):
    company = request.user.company
    products = Product.objects.filter(company=company)
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id, company=company)
    item = PurchaseItem.objects.filter(invoice=invoice)

    # Adding items to Purchase Invoice
    if request.method == 'POST':
        
        action = request.POST.get("action")
        item_id = request.POST.get('item')
        item_quantity = request.POST.get('item_quantity')
        item_unit_price = request.POST.get('item_unit_price')
        rate = request.POST.get('rate')
        withholdingTax = request.POST.get('withholdingTax', 0)
        extraTax = request.POST.get('extraTax', 0)
        furtherTax = request.POST.get('furtherTax', 0)
        fedPaid = request.POST.get('fedPaid', 0)
        discount = request.POST.get('discount', 0)
        

        if not item_id or not item_quantity or not item_unit_price:
            messages.error(request, "All fields are required.")
            return redirect("purchase_invoice", invoice_id=invoice.id)

        try:
            product = Product.objects.get(id=item_id, company=company)
            # Skip stock checks if this invoice is for telecommunication services
            if product.product_type == "service":
                product = None  # Services don't have a product in stock
            else:
                product = Product.objects.get(id=item_id, company=company)

            if action == "add_item":

                existing_item = PurchaseItem.objects.filter(invoice=invoice)

                if existing_item.exists():
                    existing_rate = existing_item.first().rate

                    if int(existing_rate) != int(rate):
                        messages.error(request, f"All items in invoice must have the same GST Rate ({existing_rate}%).")
                        return redirect("purchase_invoice", invoice_id=invoice.id)
                
                PurchaseItem.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=item_quantity,
                    unit_price=item_unit_price,
                    rate=rate,
                    withholdingTax=withholdingTax,
                    extraTax=extraTax,
                    furtherTax=furtherTax,
                    fedPaid=fedPaid,
                    discount=discount,
                )
                messages.success(request, f'Item "{product.name}" added successfully.')
        except IntegrityError:
            messages.error(request, f"Item '{product.name}' already exists!")
        except Exception as e:
            messages.error(request, f"Something went wrong: {e}")
        return redirect('purchase_invoice', invoice_id=invoice.id)

    client = getattr(invoice, "client", None)

    context = {
        'products': products,
        'item': item,
        'invoice': invoice,
        'client' : client,
        'title': 'Add Purchased Items',
    } 
    return render(request, 'purchase_invoice.html', context)

@login_required(login_url='sign_in')
def update_purchase_inv_item(request, item_id):
    company = request.user.company
    purchase_item = get_object_or_404(PurchaseItem, id=item_id)
    invoice = purchase_item.invoice

    # Updating Purchase Invoice Item
    if request.method == "POST":
        product_id = request.POST.get("item")
        item_quantity = request.POST.get("item_quantity")
        item_unit_price = request.POST.get("item_unit_price")
        rate = request.POST.get("rate")
        withholdingTax = request.POST.get("withholdingTax")
        extraTax = request.POST.get("extraTax")
        furtherTax = request.POST.get("furtherTax")
        fedPaid = request.POST.get("fedPaid")
        discount = request.POST.get("discount")

        if product_id:
            try:
                product = Product.objects.get(id=product_id, company=company)
                purchase_item.product = product
            except Product.DoesNotExist:
                messages.error(request, "Invalid product selected.")
                return redirect("update_purchase_inv_item", item_id=item_id)

        purchase_item.quantity = item_quantity
        purchase_item.unit_price = item_unit_price
        purchase_item.rate = rate
        purchase_item.withholdingTax = withholdingTax
        purchase_item.extraTax = extraTax
        purchase_item.furtherTax = furtherTax
        purchase_item.fedPaid = fedPaid
        purchase_item.discount = discount
        purchase_item.save()

        messages.success(request, f'Item "{purchase_item.product.name}" updated successfully.')
        return redirect("purchase_invoice", invoice_id=invoice.id)
    
    products = Product.objects.filter(company=company)

    return render(request, 'update_purchase_inv_item.html', {"item": purchase_item, "invoice": invoice, "products": products })

@login_required(login_url='sign_in')
def delete_purchase_inv_item(request, item_id):
    company = request.user.company
    purchase_item = get_object_or_404(PurchaseItem, id=item_id, invoice__company=company)
    invoice_id = purchase_item.invoice.id
    
    purchase_item.delete() # Deleting purchase invoice item
    messages.success(request, "Item deleted successfully.")
    return redirect("purchase_invoice", invoice_id=invoice_id)

@login_required(login_url='sign_in')
def purchase_invoice_view(request, invoice_id):
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id)

    # Get related company info (assuming FK)
    company_info = invoice.company

    # Get all items related to this invoice
    items = PurchaseItem.objects.filter(invoice=invoice)

    context = {
        'invoice': invoice,
        'company_info': company_info,
        'items': items,
    }
    return render(request, 'purchase_invoice_pdf.html', context)

@login_required(login_url='sign_in')
def purchase_invoice_pdf(request, invoice_id):
    try:
        # Get the specific purchase invoice and its related data
        invoice = PurchaseInvoice.objects.get(id=invoice_id)
        items = invoice.items.all()
        company_info = invoice.company

        # Load HTML template
        template = get_template("purchase_invoice_pdf.html")
        html_content = template.render({
            "invoice": invoice,
            "items": items,
            "company_info": company_info,
            "title": f"Purchase_Invoice_{invoice.invoice_number}",
        })

        # Locate static CSS files
        bootstrap_path = finders.find("bs/css/bootstrap.min.css")
        custom_css_path = finders.find("css/invoice_pdf_css.css")

        stylesheets = []
        if bootstrap_path:
            stylesheets.append(CSS(bootstrap_path))
        if custom_css_path:
            stylesheets.append(CSS(custom_css_path))

        # Optional: add inline page setup
        stylesheets.append(CSS(string='@page { size: A4; margin: 1cm }'))

        # Generate PDF from HTML
        pdf_file = HTML(
            string=html_content,
            base_url=request.build_absolute_uri()
        ).write_pdf(stylesheets=stylesheets)

        # Create response with downloadable filename
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response['Content-Disposition'] = (
            f'attachment; filename="purchase_invoice_{invoice.invoice_number}.pdf"'
        )
        return response

    except PurchaseInvoice.DoesNotExist:
        return HttpResponse("Purchase invoice not found.", status=404)

@login_required(login_url='sign_in')
def product_invoices(request):
    company = request.user.company

    # Get all invoices with items (prefetch for efficiency)
    invoices = (
        PurchaseInvoice.objects
        .filter(company=company)
        .select_related("supplier")
        .prefetch_related("items__product")
    )

    invoice_count = invoices.count()

    # --- Search functionality ---
    query = request.GET.get("search")
    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) |
            Q(supplier_name__icontains=query) |
            Q(purchaseitem__product__name__icontains=query)
        ).distinct()

    # --- Build structured data for template ---
    invoice_data = []
    for invoice in invoices:
        items = invoice.items.all()

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
                "total": (item.quantity * item.unit_price) - (item.discount or 0 )
            })

        supplier = invoice.supplier
        invoice_data.append({
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "supplier_name": supplier.name,
            "supplier_ntn": supplier.ntn,
            "supplier_address": supplier.address,
            "province": supplier.province_name,
            "date": invoice.date,
            "subtotal": invoice.subtotal(),
            "total_withholding_tax": invoice.total_withholding_tax(),
            "total_extra_tax": invoice.total_extra_tax(),
            "total_further_tax": invoice.total_further_tax(),
            "total_fed_paid": invoice.total_fed_paid(),
            "total_discount": invoice.total_discount(),
            "tax_total": invoice.tax_total(),
            "grand_total": invoice.grand_total(),
            "items": item_data,
            "invoice_total": sum(i["total"] for i in item_data),
        })

    context = {
        "invoice_data": invoice_data,
        "invoice_count": invoice_count,
        "title": "All Purchase Invoices",
        "query": query or "",
    }
    return render(request, "product.html", context)

def delete_purchase_invoice(request, invoice_id):
    company = request.user.company
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id, company=company)
    items = PurchaseItem.objects.filter(invoice=invoice)

    try:
        with transaction.atomic():
            for item in items:
                stock = Stock.objects.filter(product=item.product).first()
                if not stock:
                    messages.error(request, f"No stock found for {item.product}.")
                    return redirect('product_invoices')

                if stock.quantity < item.quantity:
                    messages.error(
                        request,
                        f"Cannot delete invoice. Only {stock.quantity} {item.product.name} left, "
                        f"but this invoice would remove {item.quantity}."
                    )
                    return redirect('product_invoices')

            # Deduct quantities and delete invoice
            for item in items:
                stock = Stock.objects.get(product=item.product)
                stock.quantity -= item.quantity
                stock.save()

            invoice.delete()
            messages.success(request, "Invoice and its items have been deleted successfully.")
            return redirect('product_invoices')

    except Exception as e:
        messages.error(request, f"Error deleting invoice: {str(e)}")
        return redirect('product_invoices')
