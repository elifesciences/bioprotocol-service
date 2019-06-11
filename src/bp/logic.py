import re
from . import models
import logging

LOG = logging.getLogger()


class ValidationError(Exception):
    pass


class ProcessingError(Exception):
    pass


def first(x):
    return x[0]


def titlecase_to_crocodile_case(titlecase_string):
    bits = re.findall("[A-Z][^A-Z]*", titlecase_string)
    return "_".join(bits).lower()


def rename_key(d, o, n):
    cpy = {}
    cpy.update(d)
    cpy[n] = cpy[o]
    del cpy[o]
    return cpy


def merge(a, b):
    a.update(b)
    return a


def has_all_keys(d, key_list):
    return all([k in d for k in key_list])


def ensure(x, msg):
    if not x:
        raise AssertionError(msg)


#


def protocol_data(msid):
    # {
    #    "type": "section",
    #    "title": "title",
    #    "content": [...],
    #    "bioprotocol": {...}
    # }

    protocol_data = models.ArticleProtocol.objects.filter(msid=msid)
    if not protocol_data:
        # nothing found for given msid, raise a DNE
        raise models.ArticleProtocol.DoesNotExist()

    return {}


#


def pre_process(result):
    "takes BP output and converts it to something our system can eat"
    try:
        result = rename_key(result, "URI", "Uri")
        result = rename_key(result, "msid", "Msid")
        result = {titlecase_to_crocodile_case(k): v for k, v in result.items()}
        return result
    except Exception as e:
        pe = ProcessingError(str(e))
        # pe.data = result # disabled for now until we need it
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
            has_all_keys(result, expected_keys),
            "result is missing keys: %s"
            % ", ".join(set(expected_keys) - set(result.keys())),
        )

        # todo: we can do better than just key checking

        return result
    except Exception as e:
        ve = ValidationError(str(e))
        # ve.data = result # disabled for now until we need it
        raise ve


def _add_result(result):
    "handles individual results in the `data` list"
    try:
        result = pre_process(result)
        result = validate(result)
        ap = models.ArticleProtocol(**result)
        ap.save()
        return ap
    except ProcessingError as pe:
        LOG.error("failed to transform raw BP data", extra={"data": pe.data})

    except ValidationError as ve:
        LOG.error("failed to validate transformed BP data", extra={"data": ve.data})

    except:
        LOG.exception("unhandled exception attempting to add row to database")
        raise


def add_result(result):
    msid = result["elifeID"]
    result_list = result["data"]
    return [_add_result(merge(result, {"msid": msid})) for result in result_list]


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
