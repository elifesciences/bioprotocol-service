from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse as DJsonResponse
from . import logic, models
import logging
import json

LOG = logging.getLogger()


def JsonResponse(*args, **kwargs):
    kwargs["json_dumps_params"] = {"indent": 4}
    return DJsonResponse(*args, **kwargs)


def error(message, status=500, content_type="application/json"):
    return JsonResponse({"error": message}, status=status, content_type=content_type)


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
        if request.method != "POST":  # GET, HEAD

            art_data = logic.protocol_data(msid)
            return JsonResponse(
                art_data, status=200, content_type=settings.ELIFE_CONTENT_TYPE
            )

        else:  # POST

            content_encoding = request.content_type.strip().lower()
            if (
                "application/json" not in content_encoding
                and settings.ELIFE_CONTENT_TYPE not in content_encoding
            ):
                return error("unable to negotiate a content encoding", 406)
            try:
                data = json.loads(request.body)
            except Exception:
                return error("failed to parse given JSON", 400)

            if not data:
                return error("empty request", 400)

            results = logic.add_result({"elifeID": msid, "data": data})
            response = {
                "msid": msid,
                "successful": len(results["successful"]),
                "failed": len(results["failed"]),
            }
            status_code = 200 if not results["failed"] else 400
            return JsonResponse(
                response, status=status_code, content_type=settings.ELIFE_CONTENT_TYPE
            )

    except models.ArticleProtocol.DoesNotExist:
        return error("Not found", 404)
    except Exception:
        LOG.exception("unhandled exception calling /article")
        return error("Server error", 500)
