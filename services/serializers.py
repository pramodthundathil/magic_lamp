from rest_framework import serializers
from .models import ServiceCategory, ServiceSubCategory, ServiceRequest
from home.serializers import CustomUserSerializer

class ServiceSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceSubCategory
        fields = ['id', 'category', 'name', 'image', 'service_charge', 'is_active']

class ServiceCategorySerializer(serializers.ModelSerializer):
    subcategories = ServiceSubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'icon', 'image', 'service_charge', 'is_active', 'subcategories']

class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'mobile_number', 'customer_name', 'category', 'subcategory', 
            'service_details', 'address', 'latitude', 'longitude'
        ]

    def validate(self, attrs):
        # Ensure subcategory belongs to category
        category = attrs.get('category')
        subcategory = attrs.get('subcategory')

        if subcategory and subcategory.category != category:
            raise serializers.ValidationError({"subcategory": "This subcategory does not belong to the selected category."})
        
        return attrs

    def create(self, validated_data):
        # Automatically assign user if authenticated
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)

class ServiceRequestListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    category_icon = serializers.ImageField(source='category.icon', read_only=True)
    user = CustomUserSerializer(read_only=True) # Optional: showing full user details to Admin

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'request_id', 'user', 'mobile_number', 'customer_name', 
            'category', 'category_name', 'category_icon',
            'subcategory', 'subcategory_name',
            'service_details', 'address', 'latitude', 'longitude',
            'status', 'created_at', 'updated_at'
        ]

class ServiceRequestAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = ['status', 'admin_notes']
