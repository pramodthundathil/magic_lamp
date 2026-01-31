

from rest_framework.test import APIClient
from home.models import CustomUser, AdminEmails
from rest_framework import status


def test_admin_emails_permissions():
    # Setup
    client = APIClient()
    
    # Create users
    superuser_email = "super@test.com"
    staff_email = "staff@test.com"
    
    if not CustomUser.objects.filter(email=superuser_email).exists():
        superuser = CustomUser.objects.create_superuser(email=superuser_email, password="password")
    else:
        superuser = CustomUser.objects.get(email=superuser_email)
        
    if not CustomUser.objects.filter(email=staff_email).exists():
        staff = CustomUser.objects.create_user(email=staff_email, password="password", is_staff=True, role='admin')
    else:
        staff = CustomUser.objects.get(email=staff_email)

    # Create an AdminEmail object
    admin_email_obj, created = AdminEmails.objects.get_or_create(email="test@admin.com", defaults={"priority": 1})
    detail_url = f"/admin-emails/{admin_email_obj.id}/"
    list_url = "/admin-emails/"

    print("--- Testing Staff User (Should Fail Update/Delete) ---")
    client.force_authenticate(user=staff)
    
    # Try GET (Should Succeed)
    response = client.get(list_url)
    print(f"GET (List): {response.status_code} (Expected 200)")
    
    # Try PATCH (Should Fail)
    response = client.patch(detail_url, {"priority": 2})
    print(f"PATCH: {response.status_code} (Expected 403)")
    
    # Try DELETE (Should Fail)
    response = client.delete(detail_url)
    print(f"DELETE: {response.status_code} (Expected 403)")

    print("\n--- Testing Superuser (Should Succeed Update/Delete) ---")
    client.force_authenticate(user=superuser)

    # Try PATCH (Should Succeed)
    response = client.patch(detail_url, {"priority": 2})
    print(f"PATCH: {response.status_code} (Expected 200)")
    
    # Try DELETE (Should Succeed)
    response = client.delete(detail_url)
    print(f"DELETE: {response.status_code} (Expected 204)")

test_admin_emails_permissions()
