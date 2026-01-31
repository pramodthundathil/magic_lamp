
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsSuperUserForUpdateDeletePatch(BasePermission):
    """
    Allows access to update, partial_update, and destroy only for superusers.
    Other methods (GET, POST etc.) are allowed for authenticated users (handled by IsAuthenticated or similar).
    """

    def has_permission(self, request, view):
        # Allow all if the method is safe (GET, HEAD, OPTIONS) or POST (create)
        # Note: We rely on additional permissions like IsAuthenticated or IsAdminUser on the view
        # to ensure that anonymous users can't just POST/GET if that's not desired.
        # This permission ONLY guards the modification methods.
        
        if request.method in SAFE_METHODS or request.method == 'POST':
            return True
        
        # For PUT, PATCH, DELETE, user must be a superuser
        return request.user and request.user.is_superuser
