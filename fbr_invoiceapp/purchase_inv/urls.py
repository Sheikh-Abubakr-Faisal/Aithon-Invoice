from django.urls import path
from .views import *

urlpatterns = [
    path('purchase-invoice/', purchase_invoice, name='purchase_invoice'),
    path('all-purchase-invoices/', product_invoices, name='product_invoices'),
    path('purchase-invoice-details/', purchase_invoice_details, name='purchase_invoice_details'),
    path('purchase-invoice/<int:invoice_id>/', purchase_invoice, name='purchase_invoice'),
    path('purchase-invoice-view/<int:invoice_id>/', purchase_invoice_view, name='purchase_invoice_view'),
    path('delete-purchase-invoice/<int:invoice_id>/', delete_purchase_invoice, name='delete_purchase_invoice'),
    path('purchase-invoice-pdf/<int:invoice_id>/pdf', purchase_invoice_pdf, name='purchase_invoice_pdf'),
    path('update_purchase_inv_item/<int:item_id>/update', update_purchase_inv_item, name='update_purchase_inv_item'),
    path('delete_purchase_inv_item/<int:item_id>/delete', delete_purchase_inv_item, name='delete_purchase_inv_item'),
]   
