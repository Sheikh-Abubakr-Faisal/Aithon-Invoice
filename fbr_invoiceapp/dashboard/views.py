from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from sale_inv.models import SaleInvoice, SaleItem
from purchase_inv.models import PurchaseInvoice, PurchaseItem
from product.models import Product

@login_required(login_url='sign_in')
def dashboard(request):
    company = request.user.company

    # Total sales = sum of all SaleItems (qty * unit_price)
    total_sales = (
        SaleItem.objects
        .filter(invoice__company=company)
        .aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity') * F('unit_price'),
                    output_field=DecimalField()
                )
            )
        )['total'] or 0
    )

    # Total purchases = sum of all PurchaseItems (qty * unit_price)
    total_purchases = (
        PurchaseItem.objects
        .filter(invoice__company=company)
        .aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity') * F('unit_price'),
                    output_field=DecimalField()
                )
            )
        )['total'] or 0
    )

    total_sales_inv = SaleInvoice.objects.filter(company=company).count()
    total_purchases_inv = PurchaseInvoice.objects.filter(company=company).count()
    total_invoices = total_sales_inv + total_purchases_inv
    total_products = Product.objects.filter(company=company).count()

    # ---- Recent data ----
    recent_sales = SaleInvoice.objects.filter(company=company).order_by('-date')[:5]
    recent_purchases = PurchaseInvoice.objects.filter(company=company).order_by('-date')[:5]

    context = {
        'total_sales': total_sales,
        'total_purchases': total_purchases,
        'total_sales_inv': total_sales_inv,
        'total_purchases_inv': total_purchases_inv,
        'total_invoices': total_invoices,
        'total_products': total_products,
        'recent_sales': recent_sales,
        'recent_purchases': recent_purchases,
    }
    return render(request, 'dashboard.html', context)
