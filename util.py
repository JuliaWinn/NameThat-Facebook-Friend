import cPickle as cp
# import json
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

# def pickle_file(obj, path, protocol = -1, json_copy = False):
#     with open(path, 'wb') as f:
#         cp.dump(obj, f, protocol)
#     if json_copy:
#         with open('%s.json' % path, 'w') as f:
#             simplejson.dump(obj, f)
# 
# def unpickle_file(path):
#     with open(path, 'rb') as f:
#         return cp.load(f)

# http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
# http://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
# http://stackoverflow.com/questions/2130016/splitting-a-list-of-arbitrary-size-into-only-roughly-n-equal-parts
def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]
