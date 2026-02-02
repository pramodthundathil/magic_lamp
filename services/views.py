from rest_framework import generics, status, permissions, views, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import ServiceCategory, ServiceSubCategory, ServiceRequest
from django.core.mail import EmailMessage
from django.conf import settings
from .serializers import (
    ServiceCategorySerializer, 
    ServiceSubCategorySerializer,
    ServiceRequestCreateSerializer, 
    ServiceRequestListSerializer,
    ServiceRequestAdminSerializer
)
from rest_framework.permissions import IsAuthenticated
import threading
from home.models import AdminEmails

# Attempt to import IsAdmin from home, else define it
try:
    from home.views import IsAdmin
except ImportError:
    class IsAdmin(permissions.BasePermission):
        def has_permission(self, request, view):
            return request.user and request.user.is_authenticated and getattr(request.user, 'role', '') == 'admin'

def send_admin_email_async(service_request):
    """
    Sends email to high-priority admins asynchronously.
    """
    try:
        # Fetch emails with priority 1 (Admin) and 2 (Semi Admin)
        admin_emails = list(AdminEmails.objects.filter(priority__in=[1, 2]).values_list('email', flat=True))
        
        if not admin_emails:
            print("No high-priority admin emails found.")
            return

        mail_subject = f"New Service Request: {service_request.request_id}"
        
        # HTML Message
        html_message = f"""
        <html>
            <body>
                <h2>New Service Request Received!</h2>
                <p><strong>ID:</strong> {service_request.request_id}</p>
                <p><strong>Category:</strong> {service_request.category.name if service_request.category else 'N/A'}</p>
                <p><strong>SubCategory:</strong> {service_request.subcategory.name if service_request.subcategory else 'N/A'}</p>
                <p><strong>Customer:</strong> {service_request.customer_name or 'Guest'}</p>
                <p><strong>Mobile:</strong> {service_request.mobile_number}</p>
                <p><strong>Address:</strong> {service_request.address}</p>
                <br>
                <p>Please login to the admin dashboard for more details.</p>
            </body>
        </html>
        """
        print(admin_emails,"------------")

        email = EmailMessage(mail_subject, html_message, to=admin_emails)
        email.content_subtype = "html"
        email.send(fail_silently=False)
        print(f"Email sent successfully to {admin_emails}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# --- Category Views ---

class ServiceCategoryListView(generics.ListAPIView):
    """
    Returns a list of all active service categories and their subcategories.
    Publicly accessible.
    """
    permission_classes = [permissions.AllowAny]
    # queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer

    def get_queryset(self):
        from django.db.models import Prefetch
        return ServiceCategory.objects.filter(is_active=True).order_by('order', 'name').prefetch_related(
            Prefetch('subcategories', queryset=ServiceSubCategory.objects.filter(is_active=True).order_by('order', 'name'))
        )

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
            service_request = serializer.save()

            # Send Email Asynchronously
            email_thread = threading.Thread(target=send_admin_email_async, args=(service_request,))
            email_thread.start()

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
    filter_backends = [filters.SearchFilter]
    search_fields = ['request_id', 'mobile_number', 'customer_name', 'status']
     # ordering_fields = ['created_at', 'status']
     # ordering = ['-created_at']

    def get_queryset(self):
        # Soft deleted items are automatically excluded by the Manager
        # If admin wants to see deleted items, we might need all_objects, but user implied standard view
        queryset = ServiceRequest.objects.all()
        status_param = self.request.query_params.get('status')
        category_id = self.request.query_params.get('category_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if status_param:
            queryset = queryset.filter(status__iexact=status_param)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        from django.db.models import Case, When, Value, IntegerField
        
        return queryset.annotate(
            status_priority=Case(
                When(status='Pending', then=Value(0)),
                When(status='Assigned', then=Value(1)),
                When(status='In Progress', then=Value(2)),
                When(status='Completed', then=Value(3)),
                When(status='Cancelled', then=Value(4)),
                default=Value(5),
                output_field=IntegerField(),
            )
        ).order_by('status_priority', 'created_at')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        # Stats Aggregation (Respecting Date Filters, ignoring Status filters)
        stats_queryset = ServiceRequest.objects.all()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            stats_queryset = stats_queryset.filter(created_at__date__gte=start_date)
        if end_date:
            stats_queryset = stats_queryset.filter(created_at__date__lte=end_date)
            
        from django.db.models import Count, Q
        stats = stats_queryset.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='Pending')),
            assigned=Count('id', filter=Q(status='Assigned')),
            in_progress=Count('id', filter=Q(status='In Progress')),
            completed=Count('id', filter=Q(status='Completed')),
            cancelled=Count('id', filter=Q(status='Cancelled')),
        )
        
        # Inject stats into the response data (works for paginated responses which are dicts)
        if isinstance(response.data, dict):
            response.data['stats'] = stats
            
        return response

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
