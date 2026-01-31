from django.contrib import admin
from .models import ServiceCategory, ServiceSubCategory, ServiceRequest
from home.models import AdminEmails

# Register your models here.
admin.site.register(ServiceCategory)
admin.site.register(ServiceSubCategory)
admin.site.register(ServiceRequest)
admin.site.register(AdminEmails)
