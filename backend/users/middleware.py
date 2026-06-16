class ForceHttpsForProxyMiddleware:
    """
    Middleware that forces request.is_secure() to return True
    when the request comes through a trusted proxy that sets
    X-Forwarded-Proto, but the header may be missing.

    This is a safety net – the real fix should be in the proxy config.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.is_secure():
            proto = request.META.get('HTTP_X_FORWARDED_PROTO', '')
            ssl = request.META.get('HTTP_X_FORWARDED_SSL', '')
            if proto == 'https' or ssl == 'on':
                request.META['wsgi.url_scheme'] = 'https'
                request.META['HTTPS'] = 'on'
        return self.get_response(request)
