from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from home.models import CustomUser
from services.models import ServiceRequest, ServiceCategory, ServiceSubCategory

class AdminApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Admin User
        self.admin = CustomUser.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword',
            first_name='Admin',
            role='admin'
        )
        
        # Create Normal User
        self.user = CustomUser.objects.create_user(
            email='user@example.com',
            password='userpassword',
            first_name='Test',
            last_name='User',
            role='user'
        )
        
        # Create Service Category
        self.category = ServiceCategory.objects.create(name="Cleaning")
        self.subcategory = ServiceSubCategory.objects.create(
            category=self.category,
            name="House Cleaning"
        )
        
        # Create Service Requests
        ServiceRequest.objects.create(
            user=self.user,
            request_id="SR-001",
            category=self.category,
            subcategory=self.subcategory,
            mobile_number="1234567890",
            address="Test Address",
            status="Pending"
        )
        ServiceRequest.objects.create(
            user=self.user,
            request_id="SR-002",
            category=self.category,
            subcategory=self.subcategory,
            mobile_number="1234567890",
            address="Test Address",
            status="Completed"
        )

    def test_list_users_pagination(self):
        """Test that the user list is paginated."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('list-users')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check for pagination keys
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
        # We have 2 users (admin + user)
        self.assertEqual(response.data['count'], 2)

    def test_user_details_view(self):
        """Test the detailed user view with analytics."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-user-details', args=[self.user.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertIn('user', data)
        self.assertIn('analytics', data)
        self.assertIn('service_requests', data)
        
        # Check User Data
        self.assertEqual(data['user']['email'], self.user.email)
        
        # Check Analytics
        self.assertEqual(data['analytics']['total_requests'], 2)
        self.assertEqual(data['analytics']['pending_requests'], 1)
        self.assertEqual(data['analytics']['completed_requests'], 1)
        
        # Check Service Requests
        self.assertEqual(len(data['service_requests']), 2)
        self.assertEqual(data['service_requests'][0]['request_id'], "SR-002") # Latest first

    def test_user_details_permission(self):
        """Test that non-admins cannot access the details view."""
        self.client.force_authenticate(user=self.user)
        url = reverse('admin-user-details', args=[self.admin.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
