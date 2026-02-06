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
    order = models.IntegerField(default=0)
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
    order = models.IntegerField(default=0)
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
            now = timezone.localtime(timezone.now())
            # Format: SR-YYMMDDHHMM-XXXXX
            # Example: SR-2602051330-00001
            
            date_str = now.strftime('%y%m%d')
            time_str = now.strftime('%H%M')
            
            # Count requests created today to determine sequence
            # We filter by ID prefix SR-YYMMDD to get the daily count
            prefix_date = f"SR-{date_str}"
            
            # Use all_objects to include soft-deleted records in the sequence count
            daily_count = ServiceRequest.all_objects.filter(request_id__startswith=prefix_date).count()
            sequence = daily_count + 1
            
            self.request_id = f"{prefix_date}{time_str}-{sequence:05d}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_id} ({self.status})"

class ServiceRequestMedia(models.Model):
    MEDIA_TYPES = (
        ('image', 'Image'),
        ('audio', 'Audio'),
    )
    
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to='service_media/')
    file_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Media for {self.service_request.request_id} ({self.file_type})"
