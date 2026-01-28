import ssl
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend

class UnverifiedSmtpEmailBackend(SmtpEmailBackend):
    """
    Custom EmailBackend that disables SSL certificate verification.
    Use this ONLY for development environments where certificates are missing.
    """
    def _get_ssl_context(self):
        if self.ssl_context is None:
            self.ssl_context = ssl._create_unverified_context()
        return self.ssl_context
