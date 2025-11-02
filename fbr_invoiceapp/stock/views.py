from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Stock

@login_required(login_url='sign_in')
def stock(request):
    company = request.user.company
    qs = Stock.objects.filter(
        company=company,
        product__product_type='good'
        ).select_related("product", "product__category")

    # apply search filter
    if request.GET.get('search'):
        search = request.GET.get('search')
        qs = qs.filter(
            Q(product__name__icontains=search) |
            Q(product__code__icontains=search)
        )

    stock = []
    LOW_STOCK_THRESHOLD = 10

    for item in qs:
        status = "In Stock"
        if item.quantity == 0:
            status = "Out of Stock"
        elif item.quantity <= LOW_STOCK_THRESHOLD:
            status = "Low Stock"

        stock.append({
            "code": item.product.code,
            "name": item.product.name,
            "category": item.product.category.name if item.product.category else None,
            "uom": item.product.unit_of_measurement,
            "quantity": item.quantity,
            "average_price": item.average_price,
            "total_value": item.total_value,
            "status": status,
        })

    # totals
    total_products = len(stock)
    total_money_spent = sum(item["total_value"] or 0 for item in stock)
    total_quantity_all = sum(item["quantity"] or 0 for item in stock)

    total_in_stock = sum(1 for item in stock if item["status"] == "In Stock")
    total_low_stock = sum(1 for item in stock if item["status"] == "Low Stock")
    total_out_stock = sum(1 for item in stock if item["status"] == "Out of Stock")

    return render(request, 'stock.html', {
        'stock': stock,
        'total_products': total_products,
        'total_money_spent': total_money_spent,
        'total_quantity_all': total_quantity_all,
        'total_in_stock': total_in_stock,
        'total_low_stock': total_low_stock,
        'total_out_stock': total_out_stock,
        'title': 'Stock',
    })