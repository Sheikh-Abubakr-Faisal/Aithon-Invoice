from django.db import models
from django.core.validators import RegexValidator
from company.models import CompanyInfo
from product.models import Product
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from decimal import Decimal
from num2words import num2words
from client.models import Client
                    
class SaleInvoice(models.Model):
    company = models.ForeignKey(CompanyInfo, on_delete=models.CASCADE) 
    buyer = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        limit_choices_to={"client_type__in": ["Buyer", "Both"]},
        related_name="sale_invoices"
    )
    invoice_number = models.CharField(max_length=100)
    date = models.DateField(null=False, blank=False)
    doc_type_id = models.IntegerField(null=False, blank=False)
    doc_type_description = models.CharField(max_length=100, null=False, blank=False)

    fbr_invoice_number = models.CharField(max_length=100, blank=True, null=True, unique=True)
    fbr_dated = models.DateTimeField(blank=True, null=True)
    qr_code = models.ImageField(upload_to='invoice_qr/', blank=True, null=True)  
    is_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ('company', 'invoice_number')

    def __str__(self):
        return f"Sale {self.invoice_number}"
    
    
    def subtotal(self):
        """
        Sum of quantity * unit_price for all items (before discount/taxes)
        """
        return self.items.aggregate(
            subtotal=Sum(ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField()))
        )["subtotal"] or 0

    def total_discount(self):
        """
        Total discount across all items
        """
        return self.items.aggregate(total=Sum("discount"))["total"] or 0

    def total_sales_tax_withheld(self):
        """
        Total Sales Tax Withheld At Source
        """
        return self.items.aggregate(total=Sum("salesTaxWithheldAtSource"))["total"] or 0

    def total_extra_tax(self):
        return self.items.aggregate(total=Sum("extraTax"))["total"] or 0

    def total_further_tax(self):
        return self.items.aggregate(total=Sum("furtherTax"))["total"] or 0

    def total_fed_payable(self):
        return self.items.aggregate(total=Sum("fedPayable"))["total"] or 0
        
    def tax_total(self):
        return sum(item.gst_amount() for item in self.items.all())


    def grand_total(self):
        """
        Final amount after applying everything:
        subtotal - discount + gst - withheld tax + extra + further + fed
        """
        return (
            self.subtotal()
            - self.total_discount()
            + self.tax_total()
            - self.total_sales_tax_withheld()
            + self.total_extra_tax()
            + self.total_further_tax()
            + self.total_fed_payable()
        )
    def amount_in_words(self):
        return num2words(self.grand_total(), to="cardinal", lang="en").capitalize() + " only"

class SaleItem(models.Model):
    invoice = models.ForeignKey(SaleInvoice, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, null=False, blank=False)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=False, blank=False)
    retailPrice = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=5, decimal_places=2, null=False, blank=False)
    rate_id = models.CharField(max_length=50, null=True, blank=True)
    salesTaxWithheldAtSource = models.DecimalField(decimal_places=2, max_digits=12, blank=False, null=False, default=0)
    extraTax = models.DecimalField(decimal_places=2, max_digits=12, blank=True, null=True, default=0)
    furtherTax = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True, default=0) 
    sroScheduleNo = models.CharField(max_length=250, null=True, blank=True)
    sro_schedule_desc = models.CharField(max_length=255, null=True, blank=True)
    fedPayable = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True, default=0)
    discount = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True, default=0)
    saleType = models.IntegerField(null=False, blank=False)
    saleTypeDesc = models.CharField(max_length=255, blank=False, null=False)
    sroItemSerialNo = models.CharField(max_length=50,  null=True, blank=True )

    def total_price(self):
        return self.quantity * self.unit_price
    
    def rate_as_int(self):
        return float(self.rate)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} @ {self.unit_price}"

    def total_price(self):
        return self.quantity * self.unit_price 
    
    def gst_amount(self):
        # GST calculation:
        # - For normal goods → (unit_price × qty - discount) × rate
        # - For 3rd Schedule goods → (MRP × qty) × rate

        gst_rate = Decimal(self.rate_as_int()) / Decimal(100)

        # If it's a 3rd schedule item, calculate on unit_price (treated as MRP)
        if self.saleTypeDesc and "3rd schedule goods" in self.saleTypeDesc.lower():
            retail_price = self.retailPrice or Decimal(0)
            return retail_price * gst_rate
        else:
            # Normal calculation → (total price - discount) * GST rate
            return (self.total_price() - self.discount) * gst_rate