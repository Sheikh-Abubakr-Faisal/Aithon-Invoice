from django.db import models
from company.models import CompanyInfo
from category.models import Category

class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
    ('good', 'Good'),
    ('service', 'Service'),
    ]

    company = models.ForeignKey(CompanyInfo, on_delete=models.CASCADE)
    code = models.CharField(max_length=100, null=False, blank=False) 
    name = models.CharField(max_length=255, null=False, blank=False) 
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    product_type = models.CharField(
    max_length=10,
    choices=PRODUCT_TYPE_CHOICES,
    default='good'
    )
    unit_of_measurement = models.CharField(max_length=50, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ('company', 'code')

    def __str__(self):
        return f"{self.code} - {self.name}"

    def is_service(self):
        return self.product_type == 'service'