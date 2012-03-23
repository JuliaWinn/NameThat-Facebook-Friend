# sample code from Zak Stone
# 7.26.11

import cgi
import datetime
import urllib
import wsgiref.handlers
import json
import math

from example import Friend, Original, FBTags
from face_api import FaceAPI
from google.appengine.ext import db, blobstore
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import taskqueue
from google.appengine.api import images
from google.appengine.api import urlfetch

sample_orig_path = '273.jpg'
sample_crop_path = 'tmp_crop.jpg'

def crop_image(orig_path, crop_path, b = 25):
    im = Image.open(orig_path)
    w, h = im.size
    cropped = im.crop((b,b,w-b,h-b))
    cropped.save(crop_path, quality=90)

if __name__ == '__main__':
    crop_image(sample_orig_path, sample_crop_path)
