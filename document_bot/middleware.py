from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest
from .analytics import emit, time_block, _safe

class RequestTimingMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        request._t0, request._finish = time_block()
        return None

    def process_response(self, request: HttpRequest, response):
        finish = getattr(request, "_finish", None)
        if finish:
            props = finish({
                "path": request.path,
                "method": request.method,
                "status": getattr(response, "status_code", 0),
                "session": _safe(getattr(request, "session", {}).get("session_key") if hasattr(request,"session") else None)
            })
            emit("http_request", props)
        return response
