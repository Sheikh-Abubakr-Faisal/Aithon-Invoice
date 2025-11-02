from django.db import models
from django.core.validators import RegexValidator
from company.models import CompanyInfo
from product.models import Product
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from decimal import Decimal
from client.models import Client
from num2words import num2words

class PurchaseInvoice(models.Model):
    company = models.ForeignKey(CompanyInfo, on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=100)
    date = models.DateField(null=False, blank=False)

    supplier = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        limit_choices_to={"client_type__in": ["Supplier", "Both"]},
        related_name="purchase_invoices"
    )
    
    class Meta:
        unique_together = ('company', 'invoice_number')

    def __str__(self):
        return f"Purchase {self.invoice_number}"
    
    
    def subtotal(self):
        return self.items.aggregate(
            subtotal=Sum(ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField()))
            )["subtotal"] or 0

    def total_withholding_tax(self):
        return self.items.aggregate(total=Sum("withholdingTax"))["total"] or 0

    def total_extra_tax(self):
        return self.items.aggregate(total=Sum("extraTax"))["total"] or 0

    def total_further_tax(self):
        return self.items.aggregate(total=Sum("furtherTax"))["total"] or 0

    def total_fed_paid(self):
        return self.items.aggregate(total=Sum("fedPaid"))["total"] or 0

    def total_discount(self):
        return self.items.aggregate(total=Sum("discount"))["total"] or 0

    def tax_total(self):
        first_item = self.items.first()
        if not first_item:
            return 0
        gst_rate = Decimal(first_item.rate_as_int()) / Decimal(100)
        return (self.subtotal() - self.total_discount()) * gst_rate

    def grand_total(self):
        return (
            self.subtotal()
            - self.total_discount()
            + self.tax_total()
            - self.total_withholding_tax()
            + self.total_extra_tax()
            + self.total_further_tax()
            + self.total_fed_paid()
        )
    
    def amount_in_words(self):
        return num2words(self.grand_total(), to="cardinal", lang="en").capitalize() + " only"
    
class PurchaseItem(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    rate = models.CharField(
        max_length=10, null=False,
        validators= [
            RegexValidator(
                regex=r'^\d+$',
                message="Rate must be a whole number (digits only).",
            )
        ]
        ,blank=False, default=18)
    withholdingTax = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    extraTax = models.DecimalField(decimal_places=2, max_digits=12, blank=True, null=True, default=0)
    furtherTax = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True, default=0) 
    fedPaid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)

    def total_price(self):
        return self.quantity * self.unit_price
    
    def rate_as_int(self):
        return int(self.rate)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} @ {self.unit_price}"

