from django.http import HttpResponse, JsonResponse
from . import logic, models
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


#


def article(request, msid):
    try:
        art_data = logic.protocol_data(msid)
        return JsonResponse(art_data, status=200)
    except models.ArticleProtocol.DoesNotExist:
        return JsonResponse({}, status=404)
    except Exception:
        LOG.exception("unhandled exception calling /article")
        return JsonResponse({}, status=500)
