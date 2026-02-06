from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from .models import ServiceRequest, ServiceCategory, ServiceSubCategory
from django.utils import timezone
import datetime

User = get_user_model()

class AdminDashboardAnalyticsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='password123',
            is_staff=True,
            role='admin'
        )
        self.url = reverse('admin-dashboard-analytics')

        # Create Aggregation Data
        self.cat1 = ServiceCategory.objects.create(name="Plumbing")
        self.subcat1 = ServiceSubCategory.objects.create(name="Tap Repair", category=self.cat1)
        
        ServiceRequest.objects.create(
            request_id="SR-001", mobile_number="123", address="Test",
            category=self.cat1, subcategory=self.subcat1, status='Pending'
        )
        ServiceRequest.objects.create(
            request_id="SR-002", mobile_number="123", address="Test",
            category=self.cat1, subcategory=self.subcat1, status='Completed'
        )

    def test_dashboard_analytics_default(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url)
        print("\n--- Response (Default) ---")
        # print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        
        # Verify default date range is 30 days
        start = data['date_range']['start']
        end = data['date_range']['end']
        start_date = datetime.datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date()
        
        self.assertAlmostEqual((end_date - start_date).days, 30, delta=1)
        
        self.assertIn('service_requests_summary', data)
        self.assertIn('service_requests_trend', data)

    def test_dashboard_analytics_date_range(self):
        self.client.force_authenticate(user=self.admin_user)
        today = timezone.now().date()
        start = (today - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        end = today.strftime('%Y-%m-%d')
        
        response = self.client.get(f"{self.url}?start_date={start}&end_date={end}")
        print("\n--- Response (Date Range) ---")
        # print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['date_range']['start'], start)
