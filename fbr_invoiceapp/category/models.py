from django.db import models
from company.models import CompanyInfo

class Category(models.Model):
    company = models.ForeignKey(CompanyInfo, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('company', 'name') 

    def __str__(self):
        return self.name
