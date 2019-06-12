from django.views.decorators.http import require_http_methods
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


@require_http_methods(["HEAD", "GET", "POST"])
def article(request, msid):
    try:
        if request.method == "POST":
            data = request.body
            results = logic.add_result(data)
            response = {
                "successful": len(results["successful"]),
                "failed": len(results["failed"]),
            }
            status_code = 200 if not results["failed"] else 400
            return JsonResponse(response, status=status_code)
        else:
            # GET, HEAD
            art_data = logic.protocol_data(msid)
            # returning a list is unsafe??
            return JsonResponse(art_data, status=200, safe=False)
    except models.ArticleProtocol.DoesNotExist:
        return JsonResponse({}, status=404)
    except Exception:
        LOG.exception("unhandled exception calling /article")
        return JsonResponse({}, status=500)
