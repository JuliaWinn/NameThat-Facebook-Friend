#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A barebones AppEngine application that uses Facebook for login."""

FACEBOOK_APP_ID = ""
FACEBOOK_APP_SECRET = ""

import facebook
import os.path
import wsgiref.handlers
import pprint
import urllib2
import urllib
import cgi
import datetime
import math
import logging

from django.utils import simplejson
from example import Friend, Original, FBTags, FaceTags, User, BaseHandler
from example import Pics, Facebook, Options, Photo
from face_api import FaceAPI
from google.appengine.ext import db, blobstore
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import taskqueue
from google.appengine.api import images
from google.appengine.api import urlfetch

class Delete(BaseHandler):	#delete
	def get(self):
		user = self.current_user
		query1 = db.GqlQuery("SELECT * FROM Friend")
		for i in query1:
			i.delete()
		query2 = db.GqlQuery("SELECT * FROM Original")
		for i in query2:
			i.delete()
		query3 = db.GqlQuery("SELECT * from FBTags")
		for i in query3:
			i.delete()
		query4 = db.GqlQuery("SELECT * FROM FaceTags")
		for i in query4:
			i.delete()
		query5 = db.GqlQuery("SELECT * FROM Data")
		for i in query5:
			i.delete() 
		query6 = db.GqlQuery("SELECT * FROM Options")
		for i in query6:
			i.delete()
		query6b = db.GqlQuery("SELECT * FROM Photo")
		for i in query6b:
			i.delete()
		query7a = db.GqlQuery("SELECT * FROM Connection")
		for i in query7a:
			i.delete()
		query7 = db.GqlQuery("SELECT * FROM User")
		for i in query7:
			i.options_list = []
			i.put()

class Facedotcom(webapp.RequestHandler):	#facedotcom, one for each photo
	def post(self):
		key_string = self.request.get('key_pass')	#key is from "original" entity
		user = self.request.get('user')
		url = self.request.get('url')
		fixed_key = db.Key(key_string)
		# logging.debug("%s", fixed_key)
		tag_query = db.GqlQuery("SELECT * FROM FBTags WHERE ancestor is :1", fixed_key)
		# logging.debug('the url of photo was %s', str(url))
		target = tag_query[0]
		target_x = target.x
		target_y = target.y
		face = FaceAPI()
		r, raw_resp = face.detect_faces(url)
		info = simplejson.loads(raw_resp)
		photos = info["photos"]
		photo = photos[0]
		tags = photo["tags"]
		target.delete()
		target.put()
		for j, k in enumerate(tags):
			tag = k
			center = tag['center']
			x_var = center['x']
			y_var = center['y']		
			x = math.fabs(target_x - x_var)
			y = math.fabs(target_y - y_var)
			sum = math.sqrt((x*x) + (y*y))
			width = float(k['width'])
			recognizable = str(tag['recognizable'])
			#optimize sum later
			if sum < 5 and width > 14 and recognizable == 'True':
				tag_x = float(center['x'])
				tag_y = float(center['y'])
				tag_height = float(k['height'])
				tag_width = float(k['width'])
				
			#if this happened we can mark something and skip the checking process that follows?
			
				original_query = db.GqlQuery("SELECT * FROM Original WHERE url = :1", str(url))
				original = original_query[0]
				uid = original.uid
				f = 0.63
				logging.debug('tag_y = %s', str(tag_y))
				left_x = (tag_x - f*(tag_width))/100
				top_y = (tag_y - f*(tag_height))/100
				right_x = (tag_x + f*(tag_width))/100
				bottom_y = (tag_y + f*(tag_height))/100
				logging.debug("top_y = %s", str(top_y))
				# img = original.blob
				photo = Photo()
				photo.original = db.Blob(urlfetch.fetch(url).content)
				photo.width = float(original.width)
				photo.height = float(original.height)
				photo.uid = uid
				photo.original_url = url
				photo.time = int(str(datetime.datetime.now())[-6:])
				photo.put()
				
				# create temporary storage for blob then delete it?
				img = photo.original
				
				cropped = images.crop(img, math.fabs(left_x), math.fabs(top_y), right_x, bottom_y)
			
			#delete facebook once used up
				# original.delete()

				photo.photo = db.Blob(cropped)
				photo.put()
				friend_query = db.GqlQuery("SELECT * FROM Friend WHERE uid = :1 and user_parent = :2", uid, user)
				
				friend = friend_query[0]
				friend.ready = True
				friend.put()
				option = Options()
				option.friend_id = uid
				option.user_id = user
				option.put()
				

		
def main():
	util.run_wsgi_app(webapp.WSGIApplication([('/delete', Delete),
											  ('/facedotcom', Facedotcom)
											  ], debug=True))


if __name__ == "__main__":
	main()
