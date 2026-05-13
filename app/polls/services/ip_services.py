"""
Module for handling ip related functions.
"""

def get_client_ip(request):
    """
    Docstring for get_client_ip

    :param request: Description
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")