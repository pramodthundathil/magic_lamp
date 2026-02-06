from rest_framework.test import APITestCase
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from .models import ServiceRequest, ServiceRequestMedia
import os
import shutil
from django.conf import settings

class ServiceRequestMediaAPITest(APITestCase):
    def setUp(self):
        self.url = reverse('customer-request')
        
        # Ensure media directory exists for tests
        self.media_root = settings.MEDIA_ROOT
        if not os.path.exists(self.media_root):
            os.makedirs(self.media_root)

    def tearDown(self):
        # Clean up created files
        media_path = os.path.join(self.media_root, 'service_media')
        if os.path.exists(media_path):
            shutil.rmtree(media_path)

    def test_create_service_request_with_media(self):
        image_content = b"fake_image_content"
        image = SimpleUploadedFile("test_image.jpg", image_content, content_type="image/jpeg")
        
        audio_content = b"fake_audio_content"
        audio = SimpleUploadedFile("test_audio.mp3", audio_content, content_type="audio/mpeg")
        
        data = {
            'mobile_number': '1234567890',
            'address': 'Test API Address',
            'images': [image],
            'audio': [audio]
        }
        
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check DB
        service_request = ServiceRequest.objects.get(id=response.data['id'])
        self.assertEqual(service_request.media_files.count(), 2)
        self.assertTrue(service_request.media_files.filter(file_type='image').exists())
        self.assertTrue(service_request.media_files.filter(file_type='audio').exists())

    def test_list_service_request_with_media(self):
        # Create request with media first
        image = SimpleUploadedFile("test_image.jpg", b"content", content_type="image/jpeg")
        data = {
            'mobile_number': '9876543210',
            'address': 'Test List Address',
            'images': [image]
        }
        self.client.post(self.url, data, format='multipart')
        
        # Get list (authentication needed for list view in existing code? 
        # Checking view... CustomerServiceRequestView.get requires auth)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(email='test@example.com', password='password')
        self.client.force_authenticate(user=user)
        
        # We need to link the request to the user to see it in list
        created_request = ServiceRequest.objects.latest('created_at')
        created_request.user = user
        created_request.save()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # response.data is a list
        self.assertTrue(len(response.data) > 0)
        self.assertIn('media_files', response.data[0])
        self.assertEqual(len(response.data[0]['media_files']), 1)

    def test_admin_retrieve_request_with_media(self):
        # Create request with media
        image = SimpleUploadedFile("admin_test.jpg", b"content", content_type="image/jpeg")
        service_request = ServiceRequest.objects.create(
            mobile_number="5555555555",
            address="Admin Test Address"
        )
        ServiceRequestMedia.objects.create(service_request=service_request, file=image, file_type='image')
        
        # Create Admin User
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user = User.objects.create_superuser(email='admin@test.com', password='password', role='admin')
        self.client.force_authenticate(user=admin_user)
        
        # URL for admin update view
        url = reverse('admin-request-update', kwargs={'pk': service_request.pk})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('media_files', response.data)
        self.assertEqual(len(response.data['media_files']), 1)
        # Check other fields exist
        self.assertIn('mobile_number', response.data)
        self.assertEqual(response.data['mobile_number'], "5555555555")
