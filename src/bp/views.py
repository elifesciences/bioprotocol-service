from django.http import HttpResponse, JsonResponse
from . import logic


def ping(request):
    return HttpResponse("pong", content_type="text/plain")


def status(request):
    resp = {"last-updated": logic.last_updated(), "row-count": logic.row_count()}
    status = 200
    if not resp["last-updated"] or not resp["row-count"]:
        status = 500
    return JsonResponse(resp, status=status)
