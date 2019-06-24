from django.conf import settings
from . import models, utils
from .utils import rename_key, ensure, first, merge, splitfilter
import logging
import requests, requests.exceptions
import backoff
from collections import OrderedDict

LOG = logging.getLogger()


class BPError(RuntimeError):
    data = None
    original = None


class ValidationError(BPError):
    pass


class ProcessingError(BPError):
    pass


def format_error(bperr):
    # "ValidationError: 'KeyError' thrown with message 'URI' on data: {...}"
    clsname = lambda e: e.__class__.__name__
    return "%s: %r thrown with message %r on data: %s" % (
        clsname(bperr),
        clsname(bperr.original),
        str(bperr),
        bperr.data,
    )


#
# public response data handling
#

PROTOCOL_DATA_KEYS = [
    "protocol_sequencing_number",
    "protocol_title",
    "is_protocol",
    "protocol_status",
    "uri",
]

# TODO: response representation hasn't been decided upon, this is just temporary
def serialise_protocol_data(apobj):
    "converts internal representation of protocol data into the one served to the public"
    return {k: getattr(apobj, k) for k in PROTOCOL_DATA_KEYS}


# TODO: response representation hasn't been decided upon, this is just temporary
def protocol_data(msid):
    """returns a list of protocol data given an msid
    raises ArticleProtocol.DoesNotExist if no data for given msid found"""
    protocol_data = models.ArticleProtocol.objects.filter(msid=msid)
    if not protocol_data:
        raise models.ArticleProtocol.DoesNotExist()
    return [serialise_protocol_data(apobj) for apobj in protocol_data]


def last_updated():
    """returns an iso8601 formatted date of the most recently updated row in db. 
    returns None if no data in database."""
    try:
        ap = first(
            models.ArticleProtocol.objects.all().order_by("-datetime_record_updated")
        )
        dt = ap.datetime_record_updated.isoformat()
        return dt
    except IndexError:
        # no data in database
        return None


def row_count():
    "returns the total number of rows in database"
    return models.ArticleProtocol.objects.count()


#
# bio-protocol data handling
#


def pre_process(result):
    "takes BP output and converts it to something our system can eat"
    try:
        result = rename_key(result, "URI", "Uri")
        result = rename_key(result, "msid", "Msid")
        result = {utils.titlecase_to_crocodile_case(k): v for k, v in result.items()}
        return result
    except Exception as e:
        pe = ProcessingError(str(e))
        pe.data = result
        pe.original = e
        raise pe


def validate(result):
    "takes processed data and ensures it looks valid"
    try:
        expected_keys = [
            "protocol_sequencing_number",
            "protocol_title",
            "is_protocol",
            "protocol_status",
            "uri",
            "msid",
        ]
        ensure(
            utils.has_all_keys(result, expected_keys),
            "result is missing keys: %s"
            % ", ".join(set(expected_keys) - set(result.keys())),
        )

        ensure(
            utils.has_only_keys(result, expected_keys),
            "result has unexpected extra data: %s"
            % ", ".join(set(result.keys()) - set(expected_keys)),
        )

        # todo: we can do better than just key checking

        return result
    except Exception as e:
        ve = ValidationError(str(e))
        ve.data = result
        ve.original = e
        raise ve


def upsert(result):
    return first(
        utils.create_or_update(
            models.ArticleProtocol, result, ["msid", "protocol_sequencing_number"]
        )
    )


def _add_result_item(result):
    "handles individual results in the `data` list"
    try:
        result = pre_process(result)
        result = validate(result)
        return upsert(result)
    except (ProcessingError, ValidationError) as pe:
        LOG.error(format_error(pe))
        return pe

    except:
        LOG.exception("unhandled exception attempting to add row to database")
        raise


def add_result(result):
    msid = result["elifeID"]
    result_list = result["data"]
    result_list = [
        _add_result_item(merge(result, {"msid": msid})) for result in result_list
    ]
    failed, successful = splitfilter(lambda x: isinstance(x, BPError), result_list)
    return {"msid": msid, "successful": successful, "failed": failed}


#


def visit(data, pred, fn, coll=None):
    "visits every value in the given data and applies `fn` when `pred` is true "
    if pred(data):
        if coll is not None:
            data = fn(data, coll)
        else:
            data = fn(data)
        # why don't we return here after matching?
        # the match may contain matches within child elements (lists, dicts)
        # we want to visit them, too
    if isinstance(data, OrderedDict):
        results = OrderedDict()
        for key, val in data.items():
            results[key] = visit(val, pred, fn, coll)
        return results
    elif isinstance(data, dict):
        return OrderedDict(
            [(key, visit(val, pred, fn, coll)) for key, val in data.items()]
        )
    elif isinstance(data, list):
        return [visit(row, pred, fn, coll) for row in data]
    # unsupported type/no further matches
    return data


def extract_protocols(article_json):
    ensure(isinstance(article_json, dict), "given data must be a dictionary")
    if not article_json:
        return None

    # first, find the 'materials and methods' section
    def pred1(data):
        return (
            isinstance(data, dict)
            and data.get("title")
            and data["title"].lower() == "materials and methods"
        )

    def identity(data, coll):
        coll.append(data["content"])
        return data

    mandms = []
    visit(article_json, pred1, identity, mandms)

    # next, extract the id and title of each sub-section
    def pred2(data):
        return isinstance(data, dict) and data.get("type") == "section"

    def extractor(data, coll):
        coll.append(utils.subdict(data, ["id", "title"]))
        return data

    targets = []
    visit(mandms, pred2, extractor, targets)

    # finally, ensure each of the targets is exactly as expected
    def scrub_targets(target):
        ensure(
            len(target) == 2 and "id" in target and "title" in target,
            "expecting two keys 'id' and 'title' but only found: %s"
            % list(target.keys()),
        )
        return utils.rename_keys(
            target, [("id", "ProtocolSequencingNumber"), ("title", "ProtocolTitle")]
        )

    return list(map(scrub_targets, targets))


@backoff.on_exception(
    backoff.expo,
    (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ),
    max_tries=5,
    max_time=60,
)
def _get(url, **kwargs):
    headers = {"user-agent": settings.USER_AGENT}
    resp = requests.get(url, headers=headers, auth=kwargs.get("auth"))
    resp.raise_for_status()
    return resp


def get(url, **kwargs):
    try:
        return _get(url, **kwargs)
    except (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ) as e:
        custom_msg = kwargs.get("on_error_message")
        default_msg = "request failed with status code %r: %s" % (
            e.response.status_code,
            url,
        )
        LOG.error(custom_msg or default_msg)
        return e.response
    except Exception as e:
        custom_msg = kwargs.get("on_exception_message")
        default_msg = "unhandled exception requesting: %s" % str(e)
        LOG.exception(custom_msg or default_msg)


@backoff.on_exception(
    backoff.expo,
    (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ),
    max_tries=5,
    max_time=60,
)
def _deliver_protocol_data(msid, protocol_data):
    "POSTs protocol data to BioProtocol."
    padded_msid = "elife" + utils.pad_msid(msid)
    url = "https://dev.bio-protocol.org/api/" + padded_msid + "?action=sendArticle"
    auth = (settings.BP_AUTH["user"], settings.BP_AUTH["password"])
    headers = {"user-agent": settings.USER_AGENT}
    resp = requests.post(url, json=protocol_data, headers=headers, auth=auth)
    resp.raise_for_status()
    return resp


def deliver_protocol_data(msid, protocol_data):
    """POSTs protocol data to BioProtocol.
    exponential backoff will attempt to deliver data N times. the first successful or final unsuccessful response is returned"""
    try:
        return _deliver_protocol_data(msid, protocol_data)
    except (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ) as e:
        LOG.error("failed to deliver article to BioProtocol: %s" % msid)
        return e.response
    except Exception as e:
        LOG.exception(
            "unhandled exception attempting to deliver article '%s' to BioProtocol: %s"
            % (msid, str(e))
        )
        pass


#


def download_elife_article(msid):
    "downloads the latest article data for given msid"
    url = settings.ELIFE_GATEWAY + "/articles/" + str(msid)
    auth = (settings.BP_AUTH["user"], settings.BP_AUTH["password"])
    resp = get(url, auth=auth)
    if resp:
        return resp.json()


def download_parse_deliver_data(msid):
    article_json = download_elife_article(msid)
    protocol_data = extract_protocols(article_json)
    return deliver_protocol_data(msid, protocol_data)


#


def fetch_protocol_data(msid):
    "fetches article data (if any) from BioProtocol and inserts it into the database."
    padded_msid = "elife" + utils.pad_msid(msid)
    url = "https://dev.bio-protocol.org/api/" + padded_msid
    auth = (settings.BP_AUTH["user"], settings.BP_AUTH["password"])
    resp = get(url, auth=auth)
    if resp:
        return resp.json()


def reload_article_data(msid):
    bp_data = fetch_protocol_data(msid)

    # coerce output from their API to what they POST to us
    bp_data = utils.rename_keys(
        bp_data, [("elifeid", "elifeID"), ("Protocols", "data")]
    )

    bp_data and add_result(bp_data)
