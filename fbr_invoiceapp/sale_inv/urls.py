from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('sale-invoice-details/', sale_invoice_details, name='sale_invoice_details'),
    path('sale-invoice/<int:invoice_id>', sale_invoice, name='sale_invoice'),
    path('company-info/', company_info, name='company_info'),
    path('all-sale-invoices/', all_sale_invoices, name='all_sale_invoices'),
    path('sale_invoice_view/<int:invoice_id>', sale_invoice_view, name='sale_invoice_view'),
    path('sale-invoice/<int:invoice_id>/item/<int:item_id>/update/', sale_inv_product_update, name="sale_inv_product_update"),
    path('sale_inv_product_update/<int:item_id>/update', sale_inv_product_update, name='sale_inv_product_update'),
    path('delete_sale_inv_item/<int:item_id>/delete', delete_sale_inv_item, name='delete_sale_inv_item'),
    path("sale-invoice/<int:invoice_id>/item/<int:item_id>/update/", sale_inv_product_update, name="sale_inv_product_update"),
    path("send-invoice-to-fbr/<int:invoice_id>/", post_sale_invoice, name="post_sale_invoice"),
    path("get_sro_schedule/", get_sro_schedule, name="get_sro_schedule"),
    path("get-rates/", get_rates, name="get_rates"),
    path("get_hs_uom/", get_hs_uom, name="get_hs_uom"),
    path("get_sro_items/", get_sro_items, name="get_sro_items"),
    # path("check-registration-type/", check_registration_type, name="check_registration_type"),
    path("invoice/pdf/<int:invoice_id>/", invoice_pdf, name="invoice_pdf"),
    path("invoice_view/<int:invoice_id>/", invoice_view, name="invoice_view"),
    path("post-sale-invoice/<int:invoice_id>/", post_sale_invoice, name="post_sale_invoice"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)