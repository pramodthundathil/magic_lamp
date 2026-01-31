from contextlib import nullcontext
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='email address')
    first_name = models.CharField(max_length=30, null=True, blank=True, verbose_name='first name')
    last_name = models.CharField(max_length=30, null=True, blank=True, verbose_name='last name')

    profile_picture = models.FileField(upload_to="profile_pic", null=True, blank=True)
    profile_picture_url = models.CharField(max_length=200, null=True, blank=True)
    google_id = models.CharField(max_length=100, null=True, blank=True)
    is_google_authenticated = models.BooleanField(default=False)


    is_verified = models.BooleanField(default=False)
    
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")],
        verbose_name='phone number'
    )
    date_of_birth = models.DateField(auto_now_add=False, null=True, blank=True)
    pin_code = models.BigIntegerField(default=1, null=True, blank=True)
    age = models.CharField(max_length=20, null=True, blank=True)
    district = models.CharField(max_length=20, null=True, blank=True)
    state = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(blank=True, null=True, verbose_name='address')
    is_active = models.BooleanField(default=True, verbose_name='active')
    is_staff = models.BooleanField(default=False, verbose_name='staff status')
    role = models.CharField(max_length=20, 
                            choices=(
                                ("admin","admin"),
                                ("user","user"),
                                ("semi-admin","semi-admin"),
                            
                            ),
                            default='user'
                            )
    
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='date joined')
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["first_name","date_of_birth","district","state", "phone_number"]

    

   
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

        
    def __str__(self):
        return str(self.email)


class DeliveryAddress(models.Model):

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="delivery_address", null = True, blank = True)
    delivery_person_name = models.CharField(max_length=255)
    latitude = models.CharField(max_length=20)
    longitude = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    district = models.CharField(max_length=20)
    state = models.CharField(max_length=20)
    country = models.CharField(max_length=20)
    zip_code = models.CharField(max_length=10)
    address = models.TextField(verbose_name='address')
    is_primary = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_primary:
            DeliveryAddress.objects.filter(user=self.user, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{(self.user.first_name)} - Delivery Address {self.delivery_person_name}"
    


class AdminEmails(models.Model):
    email = models.EmailField(unique=True)
    priority = models.IntegerField(default=1, choices=(
        (1, "Admin"),
        (2, "Semi Admin"),
        (3, "staff"),
        (4, "user"),
        (5, "All"),
    ))
    
    def __str__(self):
        return self.email