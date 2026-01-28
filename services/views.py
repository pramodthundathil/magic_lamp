from rest_framework import generics, status, permissions, views, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import ServiceCategory, ServiceSubCategory, ServiceRequest
from .serializers import (
    ServiceCategorySerializer, 
    ServiceSubCategorySerializer,
    ServiceRequestCreateSerializer, 
    ServiceRequestListSerializer,
    ServiceRequestAdminSerializer
)
from rest_framework.permissions import IsAuthenticated
# Attempt to import IsAdmin from home, else define it
try:
    from home.views import IsAdmin
except ImportError:
    class IsAdmin(permissions.BasePermission):
        def has_permission(self, request, view):
            return request.user and request.user.is_authenticated and getattr(request.user, 'role', '') == 'admin'

# --- Category Views ---

class ServiceCategoryListView(generics.ListAPIView):
    """
    Returns a list of all active service categories and their subcategories.
    Publicly accessible.
    """
    permission_classes = [permissions.AllowAny]
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer

class AdminServiceCategoryCreateView(generics.CreateAPIView):
    """
    Admin: Create a new Service Category.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ServiceCategorySerializer
    queryset = ServiceCategory.objects.all()

class AdminServiceCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin: Retrieve, Update, Partial Update, or Delete a Service Category.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ServiceCategorySerializer
    queryset = ServiceCategory.objects.all()
    lookup_field = 'pk'

class AdminServiceSubCategoryCreateView(generics.CreateAPIView):
    """
    Admin: Create a new SubCategory.
    Requires 'category' ID in the body.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ServiceSubCategorySerializer
    queryset = ServiceSubCategory.objects.all()

class AdminServiceSubCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin: Manage a SubCategory (Update/Delete).
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ServiceSubCategorySerializer
    queryset = ServiceSubCategory.objects.all()
    lookup_field = 'pk'

# --- Customer Request Views ---

class CustomerServiceRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Submit a Service Request",
        operation_description="Guests and Users can submit requests. If authenticated, user is linked.",
        request_body=ServiceRequestCreateSerializer,
        responses={201: ServiceRequestCreateSerializer}
    )
    def post(self, request):
        serializer = ServiceRequestCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="List My Requests",
        operation_description="Registered users can see their request history.",
        responses={200: ServiceRequestListSerializer(many=True)}
    )
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided. History is only for registered users."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        requests = ServiceRequest.objects.filter(user=request.user).order_by('-created_at')
        serializer = ServiceRequestListSerializer(requests, many=True)
        return Response(serializer.data)

# --- Admin Request Views ---

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminServiceRequestListView(generics.ListAPIView):
    """
    Admin: List all service requests.
    Supports filtering by status (?status=Pending) or category (?category_id=1).
    Supports Search (?search=SR-12345) and Ordering.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ServiceRequestListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['request_id', 'mobile_number', 'customer_name', 'status']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        # Soft deleted items are automatically excluded by the Manager
        # If admin wants to see deleted items, we might need all_objects, but user implied standard view
        queryset = ServiceRequest.objects.all()
        status_param = self.request.query_params.get('status')
        category_id = self.request.query_params.get('category_id')

        if status_param:
            queryset = queryset.filter(status__iexact=status_param)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        return queryset

class AdminServiceRequestUpdateView(generics.RetrieveUpdateAPIView):
    """
    Admin: Update status or add admin notes to a request.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestAdminSerializer
    lookup_field = 'pk'

class TrackRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Track a Service Request",
        operation_description="Track request by Request ID (e.g. SR-170000-1234).",
        responses={200: ServiceRequestListSerializer}
    )
    def get(self, request, request_id):
        try:
            service_request = ServiceRequest.objects.get(request_id=request_id)
            serializer = ServiceRequestListSerializer(service_request)
            return Response(serializer.data)
        except ServiceRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found."},
                status=status.HTTP_404_NOT_FOUND
            )
