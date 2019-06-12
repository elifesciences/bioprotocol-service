from . import models, utils
from .utils import rename_key, ensure, first, merge, splitfilter
import logging

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
