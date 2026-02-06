from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from .models import ServiceRequest, ServiceRequestMedia
from django.core.management import call_command
from datetime import timedelta
import os
import shutil
from django.conf import settings

class ServiceRequestMediaTest(TestCase):
    def setUp(self):
        self.request = ServiceRequest.objects.create(
            mobile_number="1234567890",
            address="Test Address"
        )
        
        # Ensure media directory exists for tests
        self.media_root = settings.MEDIA_ROOT
        if not os.path.exists(self.media_root):
            os.makedirs(self.media_root)

    def tearDown(self):
        # Clean up created files
        media_path = os.path.join(self.media_root, 'service_media')
        if os.path.exists(media_path):
            shutil.rmtree(media_path)

    def test_create_media(self):
        image = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        media = ServiceRequestMedia.objects.create(
            service_request=self.request,
            file=image,
            file_type='image'
        )
        self.assertEqual(media.file_type, 'image')
        self.assertTrue(media.file.name.startswith('service_media/test_image'))

    def test_cleanup_command(self):
        # Create old media (25 hours ago)
        old_image = SimpleUploadedFile("old_image.jpg", b"old_content", content_type="image/jpeg")
        old_media = ServiceRequestMedia.objects.create(
            service_request=self.request,
            file=old_image,
            file_type='image'
        )
        # Hack to set created_at in the past (auto_now_add makes this tricky)
        old_media.created_at = timezone.now() - timedelta(hours=25)
        old_media.save()
        # Direct DB update needed because save() updates auto_now fields if they existed, 
        # but created_at is auto_now_add. Wait, auto_now_add only sets on creation.
        # But we need to force it.
        ServiceRequestMedia.objects.filter(id=old_media.id).update(created_at=timezone.now() - timedelta(hours=25))

        # Create new media (1 hour ago)
        new_image = SimpleUploadedFile("new_image.jpg", b"new_content", content_type="image/jpeg")
        new_media = ServiceRequestMedia.objects.create(
            service_request=self.request,
            file=new_image,
            file_type='image'
        )
        
        # Verify both exist
        self.assertEqual(ServiceRequestMedia.objects.count(), 2)
        
        # Run cleanup command
        call_command('cleanup_service_media')
        
        # Verify old deleted, new remains
        self.assertEqual(ServiceRequestMedia.objects.count(), 1)
        self.assertTrue(ServiceRequestMedia.objects.filter(id=new_media.id).exists())
        self.assertFalse(ServiceRequestMedia.objects.filter(id=old_media.id).exists())
