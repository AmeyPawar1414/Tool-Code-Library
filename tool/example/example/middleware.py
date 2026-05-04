import time
import logging
import traceback
from accounts.models import AuditLog 

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        path = request.path
        
        # Skip static files and admin panel
        if not path.startswith('/static/') and not path.startswith('/admin/'):
            user = request.user if request.user.is_authenticated else None
            status_code = response.status_code
            
            level = 'INFO'
            if status_code >= 500:
                level = 'ERROR'
            elif status_code >= 400:
                level = 'WARNING'
                
            # 1. Create the Database Record (Django Admin)
            AuditLog.objects.create(
                user=user, level=level, ip_address=self.get_client_ip(request),
                path=path, method=request.method, status_code=status_code,
                message=f"Page loaded in {duration:.3f}s"
            )
            
            # 2. Write to VS Code File
            log_msg = f"[{status_code}] {request.method} {path} | User: {user} | IP: {self.get_client_ip(request)}"
            if level == 'ERROR' or level == 'WARNING':
                logger.error(log_msg)
            else:
                logger.info(log_msg)

        return response

    # 🌟 NEW: This catches severe system crashes (500 errors) before the yellow screen
    def process_exception(self, request, exception):
        user = request.user if request.user.is_authenticated else None
        error_msg = f"{str(exception)}\n\n{traceback.format_exc()}"
        
        # 1. Save crash to Django Admin
        AuditLog.objects.create(
            user=user, level='ERROR', ip_address=self.get_client_ip(request),
            path=request.path, method=request.method, status_code=500,
            message=error_msg[:2000] # Truncate to prevent db overflow
        )
        
        # 2. Save crash to VS Code error.log
        logger.error(f"SYSTEM CRASH at {request.path}: {str(exception)}")
        return None 

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip