from django.db import models
from django.core.validators import RegexValidator
from base.models import CustomUser

class CompanyInfo(models.Model):     
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="company")
    name = models.CharField(max_length=255, blank=False, null=False)
    province_code = models.CharField(null=False, blank=False, max_length=100)
    province_name = models.CharField(max_length=100, null=False, blank=False)
    address = models.TextField(null=False, blank=False)
    ntn = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^\d{7}$|^\d{13}$',
                message='NTN/CNIC must be either 7 or 13 digits'
            )
        ]
        ,blank=False, null=False)
    strn = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    fbr_api_key = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name
