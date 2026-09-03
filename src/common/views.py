"""Root-level views that aren't tied to a feature app."""
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def root_hello(request):
    """
    GET /  → NestJS AppController.getHello() returns the plain string
    "Hello World!" (text, not JSON). Public, no auth.
    """
    return HttpResponse("Hello World!")
