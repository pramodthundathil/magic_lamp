from rest_framework import serializers
from .models import CustomUser,DeliveryAddress

class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",'email', 'first_name', 'last_name', 'phone_number','profile_picture',"profile_picture_url",
            'date_of_birth', 'pin_code', 'age', 'district',
            'state', 'address', 'role', 'password',"is_active"
        ]

    def create(self, validated_data):
        # Use `set_password` to hash the password
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user
    


# serializers.py
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'phone_number', 'profile_picture',
            'date_of_birth', 'pin_code', 'age', 'district',
            'state', 'address',
        ]
        
    def update(self, instance, validated_data):
        # Handle profile picture upload
        profile_picture = validated_data.get('profile_picture')
        if profile_picture:
            instance.profile_picture = profile_picture
            
            
            
        # Update other fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
        instance.pin_code = validated_data.get('pin_code', instance.pin_code)
        instance.age = validated_data.get('age', instance.age)
        instance.district = validated_data.get('district', instance.district)
        instance.state = validated_data.get('state', instance.state)
        instance.address = validated_data.get('address', instance.address)
        
        instance.save()
        return instance


from .models import DeliveryAddress

class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = "__all__"  # Includes all fields
        read_only_fields = ["user"]  # User should be automatically assigned in views

    def create(self, validated_data):
        # Ensure only one primary address per user
        if validated_data.get("is_primary", False):
            DeliveryAddress.objects.filter(user=self.context["request"].user, is_primary=True).update(is_primary=False)
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Ensure only one primary address per user
        if validated_data.get("is_primary", False):
            DeliveryAddress.objects.filter(user=instance.user, is_primary=True).exclude(id=instance.id).update(is_primary=False)
        
        return super().update(instance, validated_data)


