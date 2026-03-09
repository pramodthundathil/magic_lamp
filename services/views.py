from rest_framework import generics, status, permissions, views, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi
from .models import ServiceCategory, ServiceSubCategory, ServiceRequest, ServiceRequestMedia
from django.core.mail import EmailMessage
from django.conf import settings
from .serializers import (
    ServiceCategorySerializer, 
    ServiceSubCategorySerializer,
    ServiceRequestCreateSerializer, 
    ServiceRequestListSerializer,
    ServiceRequestAdminSerializer,
    ServiceRequestUpdateSerializer
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
    pagination_class = None

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

from rest_framework.parsers import MultiPartParser, FormParser

class CustomerServiceRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Submit a Service Request",
        operation_description="Guests and Users can submit requests. If authenticated, user is linked.",
        manual_parameters=[
            openapi.Parameter(
                name="images",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE),
                description="Upload images (multiple supported)"
            ),
            openapi.Parameter(
                name="audio",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE),
                description="Upload audio files (multiple supported)"
            ),
            openapi.Parameter(
                name="mobile_number",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=True,
                description="Mobile Number"
            ),
            openapi.Parameter(
                name="customer_name",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Customer Name"
            ),
            openapi.Parameter(
                name="category",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Category ID"
            ),
            openapi.Parameter(
                name="subcategory",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                description="SubCategory ID"
            ),
            openapi.Parameter(
                name="address",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=True,
                description="Address"
            ),
             openapi.Parameter(
                name="service_details",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="JSON String of service details"
            ),
            openapi.Parameter(
                name="latitude",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Latitude"
            ),
            openapi.Parameter(
                name="longitude",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Longitude"
            ),
        ],
        request_body=no_body,
        responses={201: ServiceRequestListSerializer},
        consumes=['multipart/form-data']
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

class CustomerServiceRequestUpdateView(generics.UpdateAPIView):
    """
    Authenticated Users can edit their own service requests if the status is 'Pending'.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceRequestUpdateSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ServiceRequest.objects.none()
        return ServiceRequest.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="Update My Service Request (Full)",
        operation_description="Users can edit their own requests if status is 'Pending'.",
        manual_parameters=[
            openapi.Parameter(
                name="images", in_=openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE), description="Upload images"
            ),
            openapi.Parameter(
                name="audio", in_=openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE), description="Upload audio"
            ),
            openapi.Parameter(name="mobile_number", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="email", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="customer_name", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="service_details", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="address", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="latitude", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="longitude", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
        ],
        request_body=no_body,
        responses={200: ServiceRequestListSerializer},
        consumes=['multipart/form-data']
    )
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Edit My Service Request (Partial)",
        operation_description="Users can edit their own requests if status is 'Pending'.",
        manual_parameters=[
            openapi.Parameter(
                name="images", in_=openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE), description="Upload images"
            ),
            openapi.Parameter(
                name="audio", in_=openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE), description="Upload audio"
            ),
            openapi.Parameter(name="mobile_number", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="email", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="customer_name", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="service_details", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="address", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="latitude", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter(name="longitude", in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
        ],
        request_body=no_body,
        responses={200: ServiceRequestListSerializer},
        consumes=['multipart/form-data']
    )
    def patch(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        if instance.status != 'Pending':
            return Response(
                {"detail": "Only requests with 'Pending' status can be edited."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

class CustomerServiceRequestMediaDeleteView(generics.DestroyAPIView):
    """
    Authenticated Users can delete media from their own service requests if the status is 'Pending'.
    """
    permission_classes = [IsAuthenticated]
    queryset = ServiceRequestMedia.objects.all()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ServiceRequestMedia.objects.none()
        return ServiceRequestMedia.objects.filter(service_request__user=self.request.user)

    def perform_destroy(self, instance):
        if instance.service_request.status != 'Pending':
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Media can only be deleted for requests with 'Pending' status.")
        instance.delete()

class CustomerServiceRequestCancelView(views.APIView):
    """
    Authenticated Users can cancel their own service requests if the status is 'Pending'.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Cancel My Service Request",
        operation_description="Users can cancel their own requests if status is 'Pending'.",
        responses={200: "Success Message", 400: "Error Message", 404: "Not Found"}
    )
    def post(self, request, pk):
        try:
            service_request = ServiceRequest.objects.get(pk=pk, user=request.user)
        except ServiceRequest.DoesNotExist:
            return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

        if service_request.status != 'Pending':
            return Response(
                {"detail": "Only requests with 'Pending' status can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        service_request.status = 'Cancelled'
        service_request.save()
        return Response({"detail": "Request cancelled successfully."}, status=status.HTTP_200_OK)

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

class AdminDashboardAnalyticsView(views.APIView):
    """
    Admin: Get dashboard analytics (Service Counts, User Growth, User Roles).
    Supports ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD.
    Defaults to current month if no dates are provided.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_summary="Admin Dashboard Analytics",
        operation_description="Returns analytics for Service Requests, User Growth, and User Roles.",
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY, description="YYYY-MM-DD", type=openapi.TYPE_STRING),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="YYYY-MM-DD", type=openapi.TYPE_STRING),
        ],
        responses={200: "JSON Data"}
    )
    def get(self, request):
        from django.utils import timezone
        from .models import ServiceRequest
        from home.models import CustomUser
        from django.db.models import Count, Q
        from django.db.models.functions import TruncDate
        import datetime
        from collections import defaultdict

        # 1. Date Range Handling
        today = timezone.now().date()
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if start_date_str and end_date_str:
            try:
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                 return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Default to past 30 days
            start_date = today - datetime.timedelta(days=30)
            end_date = today

        # Base Querysets
        requests_query = ServiceRequest.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        # 2. Service Request Analytics (Overall Summary)
        request_summary = requests_query.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='Pending')),
            assigned=Count('id', filter=Q(status='Assigned')),
            in_progress=Count('id', filter=Q(status='In Progress')),
            completed=Count('id', filter=Q(status='Completed')),
            cancelled=Count('id', filter=Q(status='Cancelled')),
        )

        # 3. 3D Analytics: Service Requests by Date & Status
        # We want: [{date: '2023-01-01', status: 'Pending', count: 5}, ...]
        sr_by_date = requests_query.annotate(
            date=TruncDate('created_at')
        ).values('date', 'status').annotate(
            count=Count('id')
        ).order_by('date')

        # Transform to: { '2023-01-01': {'Pending': 5, 'Completed': 2} } for easier frontend consumption or keep flat
        # Let's keep it flat structured but maybe grouped by date for charts
        # Preferred Chart Structure: labels: [Dates], datasets: [{label: 'Pending', data: [...]}, ...]
        # We will return the raw "by_date" list, frontend can pivot it.
        sr_by_date_data = [
            {
                "date": item['date'].strftime("%Y-%m-%d"),
                "status": item['status'],
                "count": item['count']
            }
            for item in sr_by_date
        ]

        # 4. Category Analytics
        # Summary (Pie Chart)
        cat_summary = requests_query.values('category__name').annotate(count=Count('id')).order_by('-count')
        cat_summary_data = [{"category": item['category__name'] or "Uncategorized", "count": item['count']} for item in cat_summary]

        # By Date (Line Chart)
        cat_by_date = requests_query.annotate(
            date=TruncDate('created_at')
        ).values('date', 'category__name').annotate(
            count=Count('id')
        ).order_by('date')

        cat_by_date_data = [
            {
                "date": item['date'].strftime("%Y-%m-%d"),
                "category": item['category__name'] or "Uncategorized",
                "count": item['count']
            }
            for item in cat_by_date
        ]

        # 5. SubCategory Analytics
        # Summary
        subcat_summary = requests_query.values('subcategory__name').annotate(count=Count('id')).order_by('-count')
        subcat_summary_data = [{"subcategory": item['subcategory__name'] or "None", "count": item['count']} for item in subcat_summary]

        # By Date
        subcat_by_date = requests_query.annotate(
            date=TruncDate('created_at')
        ).values('date', 'subcategory__name').annotate(
            count=Count('id')
        ).order_by('date')

        subcat_by_date_data = [
            {
                "date": item['date'].strftime("%Y-%m-%d"),
                "subcategory": item['subcategory__name'] or "None",
                "count": item['count']
            }
            for item in subcat_by_date
        ]

        # 6. User Growth Analytics (unchanged logic)
        user_growth_query = CustomUser.objects.filter(
            date_joined__date__gte=start_date,
            date_joined__date__lte=end_date
        ).annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        user_growth_data = [
            {"date": item['date'].strftime("%Y-%m-%d"), "count": item['count']}
            for item in user_growth_query
        ]

        # 7. User Roles (Snapshot)
        user_roles_query = CustomUser.objects.values('role').annotate(count=Count('id')).order_by('role')
        user_roles_data = [{"role": item['role'], "count": item['count']} for item in user_roles_query]

        # Construct Response
        data = {
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            },
            "service_requests_summary": request_summary,
            "service_requests_trend": sr_by_date_data,
            "category_analytics": {
                "summary": cat_summary_data,
                "trend": cat_by_date_data
            },
            "subcategory_analytics": {
                "summary": subcat_summary_data,
                "trend": subcat_by_date_data
            },
            "user_growth": user_growth_data,
            "user_roles_distribution": user_roles_data
        }

        return Response(data, status=status.HTTP_200_OK)
