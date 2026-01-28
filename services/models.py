from django.db import models
from home.models import CustomUser

from django.utils import timezone
import uuid

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.FileField(upload_to='service_icons/', blank=True, null=True)
    image = models.FileField(upload_to='category_images/', blank=True, null=True)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()

    class Meta:
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name

class ServiceSubCategory(models.Model):
    category = models.ForeignKey(ServiceCategory, related_name='subcategories', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    image = models.FileField(upload_to='subcategory_images/', blank=True, null=True)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()

    class Meta:
        verbose_name_plural = "Service Sub Categories"

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class ServiceRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )

    request_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='service_requests', null=True, blank=True)
    # Contact info - mandatory even for registered users as they might book for others
    mobile_number = models.CharField(max_length=15)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, related_name='requests')
    subcategory = models.ForeignKey(ServiceSubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests')
    
    # Flexible field for specific nuances (e.g. food items list, medicine description)
    service_details = models.JSONField(default=dict, blank=True)
    
    # Location
    address = models.TextField()
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        if not self.request_id:
            # Generate unique ID: SR-TIMESTAMP-RANDOM
            import time
            import random
            timestamp = int(time.time())
            rand = random.randint(1000, 9999)
            self.request_id = f"SR-{timestamp}-{rand}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_id} ({self.status})"
