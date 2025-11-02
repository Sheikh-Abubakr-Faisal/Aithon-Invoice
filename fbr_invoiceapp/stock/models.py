from django.db import models
from company.models import CompanyInfo
from product.models import Product

class Stock(models.Model):
    company = models.ForeignKey(CompanyInfo, on_delete=models.CASCADE)
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def update_stock(self, quantity_change, unit_price=None):
        # quantity change: +ve when purchased, -ve when sold
        if quantity_change > 0:
            if self.quantity + quantity_change > 0:
                if unit_price is not None:
                    # Update average price
                    total_cost_existing = self.quantity * self.average_price
                    total_cost_new = quantity_change * unit_price
                    new_total_quantity = self.quantity + quantity_change
                    self.average_price = (total_cost_existing + total_cost_new) / new_total_quantity

            self.quantity += quantity_change
        else:
            if abs(quantity_change) > self.quantity:
                raise ValueError(f"Not enough stock. Available: {self.quantity}")
            self.quantity += quantity_change

        self.total_value = self.quantity * self.average_price
        self.save()

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.unit_of_measurement}"

