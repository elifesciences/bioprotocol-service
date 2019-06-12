import re


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


def has_only_keys(d, key_list):
    return all([k in key_list for k in d.keys()])


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
