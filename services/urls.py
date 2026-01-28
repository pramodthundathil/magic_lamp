from django.urls import path
from .views import (
    ServiceCategoryListView, 
    AdminServiceCategoryCreateView,
    AdminServiceCategoryDetailView,
    AdminServiceSubCategoryCreateView,
    AdminServiceSubCategoryDetailView,
    CustomerServiceRequestView,
    TrackRequestView,
    AdminServiceRequestListView,
    AdminServiceRequestUpdateView
)

urlpatterns = [
    # Public / Customer
    path('categories/', ServiceCategoryListView.as_view(), name='category-list'),
    path('request/', CustomerServiceRequestView.as_view(), name='customer-request'),
    path('track/<str:request_id>/', TrackRequestView.as_view(), name='track-request'),
    
    # Admin
    path('admin/categories/create/', AdminServiceCategoryCreateView.as_view(), name='admin-category-create'),
    path('admin/categories/<int:pk>/', AdminServiceCategoryDetailView.as_view(), name='admin-category-detail'),
    path('admin/subcategories/create/', AdminServiceSubCategoryCreateView.as_view(), name='admin-subcategory-create'),
    path('admin/subcategories/<int:pk>/', AdminServiceSubCategoryDetailView.as_view(), name='admin-subcategory-detail'),
    path('admin/requests/', AdminServiceRequestListView.as_view(), name='admin-request-list'),
    path('admin/requests/<int:pk>/', AdminServiceRequestUpdateView.as_view(), name='admin-request-update'),
]
