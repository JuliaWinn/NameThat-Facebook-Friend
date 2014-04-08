import cPickle as cp
from django.utils import simplejson


def pp(obj):
    print pp_str(obj)


def pp_str(obj):
    return simplejson.dumps(obj, sort_keys = True, indent = 4)


class TemporaryError(Exception):
    pass


def pickle(obj):
    return cp.dumps(obj, -1)


def unpickle(str):
    return cp.loads(str)


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]
