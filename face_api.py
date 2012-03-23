import urllib2
import httplib
from urllib import urlencode
from openanything import fetch
# import json
from django.utils import simplejson
import cStringIO
from util import pp, pp_str, TemporaryError
import time
import traceback

class FaceAPI:
    
    # NOTE: SET THESE!
    api_key = ''
    api_secret = ''
    namespace = ''
    raise Exception("Please set the api_key, api_secret, and namespace at the top of face_api.py and comment out this exception")

    def __init__(self, namespace = None, api_key = None, api_secret = None):
        self.namespace = namespace
        
        self.log_path = 'log.txt'
        self.log_separator = '-----------<-<-<->->->-----------'

        if api_key and api_secret:
            self.api_key = api_key
            self.api_secret = api_secret

        if namespace:
           self.namespace = namespace
 
        self.rest_url = 'http://api.face.com/'
        self.rest_host = 'api.face.com'
        self.format = 'json'

    def detect_faces(self, url):
        return self.get_request('faces/detect', 
                                {'urls':[url]}, 
                                raw_resp = True)

    # NOTE: They save the uploaded image with the filename set to the 
    # MD5 hash of the file, which causes problems when images are used
    # multiple times in different splits
    def detect_faces_post(self, pid, data):
        return self.post_request('faces/detect', pid, data, {'nd':1})

    def under_limit(self):
        r = self.get_request('account/limits')
        # pp(r)
        return ((int(r['usage']['remaining']) > 0) and (int(r['usage']['namespace_remaining']) > 0))
            
    def existing_users(self):
        r = self.get_request('account/users', {'namespaces':[self.namespace]})
        status = r['status']
        if status != 'success':
            pp(r)

            raise TemporaryError("Failed to retrieve user list; status %s" % status)
        raw_user_list = r['users'][self.namespace]
        uids = [user.split('@')[0] for user in raw_user_list]
        return uids

    def save_tag(self, tid, uid):
        full_uid = '%s@%s' % (uid, self.namespace)
        return self.get_request('tags/save', {'tids':[tid], 'uid':full_uid}, raw_resp = True)

    def get_tags(self, uid):
        full_uid = '%s@%s' % (uid, self.namespace)
        return self.get_request('tags/get', {'uids':[full_uid]}, raw_resp = True)

    def train_uid(self, uid):
        full_uid = '%s@%s' % (uid, self.namespace)
        return self.get_request('faces/train', {'uids':[full_uid]}, raw_resp = True)

    def recognize_face(self, url, uids):
        return self.get_request('faces/recognize',
                                {'urls':[url],
                                 'uids':uids,
                                 'namespace':self.namespace},
                                raw_resp = True)

    def recognize_face_post(self, uids, pid, data):
        return self.post_request('faces/recognize',
                                 pid,
                                 data,
                                {'uids':uids,
                                 'namespace':self.namespace},
                                raw_resp = True)

    # urlencode seems to cause problems, so I'm using this for now
    def fake_encode(self, params):
        pairs = []
        for k,v in params:
            pairs.append('%s=%s' % (k,v))
        return '&'.join(pairs)

    def get_request_url(self, method, params = None):
        
        all_params = [('api_key', self.api_key),
                      ('api_secret', self.api_secret)]

        if params:
            for k, v in params.items():
                if v == None:
                    continue
                if type(v) == list:
                    v = ','.join(v)
                all_params.append((k,v))

        components = [self.rest_url,
                      method,
                      '.',
                      self.format,
                      '?',
                      self.fake_encode(all_params)]

        request_url = ''.join(components)
        return request_url

    def get_request(self, method, params = None, raw_resp = False, max_attempts = 10, log = False, debug = False):

        all_params = [('api_key', self.api_key),
                      ('api_secret', self.api_secret)]

        if params:
            for k, v in params.items():
                if v == None:
                    continue
                if type(v) == list:
                    v = ','.join(v)
                all_params.append((k,v))

        components = [self.rest_url,
                      method,
                      '.',
                      self.format,
                      '?',
                      self.fake_encode(all_params)]

        request_url = ''.join(components)

        if debug:
            print "request_url: %s" % request_url
        

        start_time = time.time()
        result = fetch(request_url)
        end_time = time.time()

        if result['status'] == 200:
            if debug:
                print "Success"
            resp_data = result['data']
        
            # if log:
            #     with open(self.log_path, 'a') as f:
            #         f.write('%s: %s\n\n%s: <json>\n%s\n</json>\n%s\n\n' % (start_time, request_url, end_time, resp_data, self.log_separator))
            #         
            r = simplejson.loads(resp_data)
            status = r['status']
            if status != 'success':
                pp(r)
                # if log:
                #       with open(self.log_path, 'a') as f:
                #           f.write('Remote Error: %s\n\n' % pp_str(r))
                raise TemporaryError("Response received with status %s" % status)
            if raw_resp:
                return r, resp_data
            else: 
                return r
        else:
            # if log:
            #     with open(self.log_path, 'a') as f:
            #         f.write('%s: %s\n\nError: Status %s\n%s\n' % (time.time(), request_url, result['status'], self.log_separator))
            #         
            raise TemporaryError("Received HTTP status %s" % result['status'])


    def prepare_post_request(self, method, params = None):
        from httputil import HTTPHeaders
        all_params = [('api_key', self.api_key),
                      ('api_secret', self.api_secret)]

        if params:
            for k, v in params.items():
                if v == None:
                    continue
                if type(v) == list:
                    v = ','.join(v)
                all_params.append((k,v))

        boundary = 'nonRelevantString'
        
        message = []
        message_tail = []

        for k,v in all_params:
            message.append('--' + boundary)
            message.append('Content-Disposition: form-data; name="%s"' % k)
            message.append('')
            message.append(str(v))
        message.append('--' + boundary + '--')
        message.append('')
        body = '\r\n'.join(message)

        headers = HTTPHeaders({'Content-Type':'multipart/form-data; boundary=%s' % boundary,
                               'Content_Length':str(len(body))})

        # headers = 'Content-Type: multipart/form-data; boundary=%s\r\nContent-Length: %s\r\n' % (boundary, str(len(body)))
        return headers, body


    def post_request(self, method, filename, data, params = None, raw_resp = True):
        print "Don't use the POST method unless it is really necessary"
        # raise Exception("Don't use the POST method unless it is really necessary")
        all_params = [('api_key', self.api_key),
                      ('api_secret', self.api_secret)]

        if params:
            for k, v in params.items():
                if v == None:
                    continue
                if type(v) == list:
                    v = ','.join(v)
                all_params.append((k,v))

        boundary = 'nonRelevantString'
        
        message = []
        message_tail = []

        for k,v in all_params:
            message.append('--' + boundary)
            message.append('Content-Disposition: form-data; name="%s"' % k)
            message.append('')
            message.append(str(v))
        message.append('--' + boundary)
        message.append('Content-Disposition: form-data; filename="%s"' % filename)
        message.append('Content-Type: image/jpeg')
        message.append('')
        message_head = '\r\n'.join(message)

        message_tail.append('--' + boundary + '--')
        message_tail.append('')
        message_tail = '\r\n'.join(message_tail)

        # Without this workaround, Python seemed to try to apply an ASCII 
        # encoding to the binary data for some reason
        bin_str = cStringIO.StringIO()
        bin_str.write(message_head)
        bin_str.write('\r\n')
        bin_str.write(data)
        bin_str.write('\r\n')
        bin_str.write(message_tail)
        final_message = bin_str.getvalue()
        
        h = httplib.HTTPConnection(self.rest_host)
        # h.set_debuglevel(2)
        h.putrequest('POST', '/%s.simplejson' % method)
        h.putheader('Content-Type', 'multipart/form-data; boundary=%s' % boundary)
        h.putheader('Content-Length', str(len(final_message)))
        h.endheaders()
        h.send(final_message)
        resp = h.getresponse()
        resp_data = resp.read()
        resp.close()
        if raw_resp:
            return simplejson.loads(resp_data), resp_data
        else: 
            return simplejson.loads(resp_data)
                
if __name__ == '__main__':
	face = FaceAPI()
	
	print "*** GET EXAMPLE WITH REMOTE URL ***" 
	# url = 'https://fbcdn-sphotos-a.akamaihd.net/hphotos-ak-ash4/262277_10100112951476288_15720816_45641485_538387_n.jpg'
	# r, raw_resp = face.detect_faces(url)
	# # info = json.dumps(r, sort_keys = True, indent = 4)
	# info = json.loads(raw_resp)
	# photos = info["photos"]
	# for i in photos:
	# 	height = i["height"]
	# 	width = i["width"]
	# 	tags = i["tags"]
	# 	for j in tags:
	# 		print j["center"]["x"]
	# 		print j["center"]["y"]
			