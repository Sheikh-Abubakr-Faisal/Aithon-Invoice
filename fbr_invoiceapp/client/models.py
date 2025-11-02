from django.db import models
from django.core.validators import RegexValidator
from django.forms import ValidationError
from company.models import CompanyInfo

class Client(models.Model):
    company = models.ForeignKey(CompanyInfo, on_delete=models.CASCADE)
    CLIENT_TYPE_CHOICES = [
        ("Buyer", "Buyer"),
        ("Supplier", "Supplier"),
        ("Both", "Both"),
    ]

    name = models.CharField(max_length=200)
    ntn = models.CharField(
        max_length=100, blank=True, null=True,
        validators=[
            RegexValidator(
                regex=r'^\d{7}$|^\d{13}$',
                message='NTN/CNIC must be 7 or 13 digits.'
            )
        ]
    )
    address = models.TextField()
    registration_type = models.CharField(max_length=50)
    province_code = models.IntegerField(null=False, blank=False)  
    province_name = models.CharField(max_length=100, null=False, blank=False)
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES, default="Buyer")

    def __str__(self):
        return f"{self.name} ({self.client_type})"

    def clean(self):
        """
        Custom validation for buyer_ntn depending on buyer_registration_type
        """
        if self.registration_type == "Registered" and not self.ntn:
            raise ValidationError({"ntn": "NTN is required for registered clients."})