from django.contrib import admin
from .models import *
import requests
from company.models import CompanyInfo
from django import forms
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin

admin.site.site_header = "Aithon Invoice Admin Panel"
admin.site.site_title = "Aithon Invoice Admin"
admin.site.index_title = "Welcome to Aithon Invoice Dashboard"

class CompanyInfoForm(forms.ModelForm):
    class Meta:
        model = CompanyInfo
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fetch provinces from FBR API
        provinces = []
        try:
            token = "2a7dd7c6-7160-3ff7-b360-b786bf7e24ba"
            province_url = "https://gw.fbr.gov.pk/pdi/v1/provinces"
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(province_url, headers=headers, timeout=10)
            if response.status_code == 200:
                provinces = response.json()  # list of dicts with code & desc
        except Exception as e:
            pass  # If API fails, dropdown will be empty

        # Create choices for dropdowns in format "Name - ID"
        choices_code = [(p["stateProvinceCode"], f"{p['stateProvinceCode']} - {p['stateProvinceDesc']}") for p in provinces]
        choices_name = [(p["stateProvinceDesc"], f"{p['stateProvinceCode']} - {p['stateProvinceDesc']}") for p in provinces]


        # Province code dropdown
        self.fields['province_code'] = forms.ChoiceField(
            choices=choices_code,
            required=True,
            label="Province Code"
        )

        # Province name dropdown
        self.fields['province_name'] = forms.ChoiceField(
            choices=choices_name,
            required=True,
            label="Province Name"
        )

class CompanyInfoAdmin(admin.ModelAdmin):
    form = CompanyInfoForm
    list_display = ("name", "province_code", "province_name", "ntn", "phone", "email")

    def save_model(self, request, obj, form, change):
        # province_name is already filled in clean(), just save both
        super().save_model(request, obj, form, change)


admin.site.register(CompanyInfo, CompanyInfoAdmin)

class CompanyInfoInline(admin.StackedInline):
    model = CompanyInfo
    form = CompanyInfoForm
    can_delete = False
    verbose_name_plural = "Company Info"


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    inlines = [CompanyInfoInline]

    list_display = ("email", "get_company_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "company__name")   # allows searching by company name
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active"),
        }),
    )

    def get_company_name(self, obj):
        return obj.company.name if hasattr(obj, "company") else "—"
    get_company_name.short_description = "Company Name"


admin.site.register(CustomUser, CustomUserAdmin)

