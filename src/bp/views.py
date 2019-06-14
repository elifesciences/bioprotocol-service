from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse
from . import logic, models
import logging
import json

LOG = logging.getLogger()

def error(message, status=500):
    return JsonResponse({"error": message}, status=status)


@require_http_methods(["HEAD", "GET"])
def ping(request):
    return HttpResponse("pong", content_type="text/plain")

@require_http_methods(["HEAD", "GET"])
def status(request):
    try:
        resp = {"last-updated": logic.last_updated(), "row-count": logic.row_count()}
        return JsonResponse(resp, status=200)
    except Exception:
        LOG.exception("unhandled exception calling /status")
        return error("unexpected error")


@require_http_methods(["HEAD", "GET", "POST"])
def article(request, msid):
    try:
        if request.method == "POST":
            if "application/json" not in request.content_type.lower():
                return error(
                    "failed to find supported content-type (application/json)", 400
                )
            try:
                # TODO: check body length
                # TODO: check body encoding
                data = json.loads(request.body)
            except Exception:
                return error("failed to parse given JSON", 400)

            if not data:
                return error("empty data", 400)

            results = logic.add_result({"elifeID": msid, "data": data})
            response = {
                "msid": msid,
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
        return error("Not found", status=404)
    except Exception:
        LOG.exception("unhandled exception calling /article")
        return error("Server error")
