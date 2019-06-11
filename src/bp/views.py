from django.http import HttpResponse, JsonResponse
from . import logic
import logging

LOG = logging.getLogger()


def ping(request):
    return HttpResponse("pong", content_type="text/plain")


def status(request):
    try:
        resp = {"last-updated": logic.last_updated(), "row-count": logic.row_count()}
        return JsonResponse(resp, status=200)
    except Exception:
        LOG.exception("unhandled exception calling /status")
        return JsonResponse({}, status=500)
