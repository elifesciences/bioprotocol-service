import re
from . import models
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


def splitfilter(fn, lst):
    a = []
    b = []
    [(a if fn(x) else b).append(x) for x in lst]
    return a, b


def subdict(d, key_list):
    return {k: v for k, v in d.items() if k in key_list}


def create_or_update(
    Model, orig_data, key_list=None, create=True, update=True, commit=True, **overrides
):
    inst = None
    created = updated = False
    data = {}
    data.update(orig_data)
    data.update(overrides)
    key_list = key_list or data.keys()
    try:
        # try and find an entry of Model using the key fields in the given data
        inst = Model.objects.get(**subdict(data, key_list))
        # object exists, otherwise DoesNotExist would have been raised
        if update:
            [setattr(inst, key, val) for key, val in data.items()]
            updated = True
    except Model.DoesNotExist:
        if create:
            inst = Model(**data)
            created = True

    if (updated or created) and commit:
        inst.full_clean()
        inst.save()

    # it is possible to neither create nor update.
    # if create=True and update=False and object already exists, you'll get: (obj, False, False)
    # if the model cannot be found then None is returned: (None, False, False)
    return (inst, created, updated)


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
            has_all_keys(result, expected_keys),
            "result is missing keys: %s"
            % ", ".join(set(expected_keys) - set(result.keys())),
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
        create_or_update(
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
