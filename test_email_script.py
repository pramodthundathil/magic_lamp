import os
import django
from django.core.mail import EmailMessage
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magic_lamp.settings')
django.setup()

def send_test_email():
    print("Attempting to send email...")
    print(f"HOST: {settings.EMAIL_HOST}")
    print(f"PORT: {settings.EMAIL_PORT}")
    print(f"USER: {settings.EMAIL_HOST_USER}")
    # Don't print the password validation
    
    try:
        email = EmailMessage(
            'Test Email',
            'This is a test email.',
            to=['gopinath.pramod@gmail.com']
        )
        email.send(fail_silently=False)
        print("Email sent successfully!")
    except Exception as e:
        print(f"FAILED to send email: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    send_test_email()
