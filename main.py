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

# from load import BaseHandler, HomeHandler, Pics, Pictures, Facebook
# from load import *
import facebook
import os.path
import time
import logging
from google.appengine.runtime import DeadlineExceededError

from face_api import FaceAPI
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import taskqueue

ROUNDS = 10

class User(db.Model):
	id = db.StringProperty(required=True)
	created = db.DateTimeProperty(auto_now_add=True)
	updated = db.DateTimeProperty(auto_now=True)
	name = db.StringProperty(required=True)
	profile_url = db.StringProperty(required=True)
	access_token = db.StringProperty(required=True)
	friend_list = db.StringListProperty()
	friend_count = db.IntegerProperty()
	options_list = db.StringListProperty(default=[])

class Options(db.Model):		#parent is user
	friend_id = db.StringProperty()
	user_id = db.StringProperty()

class Connection(db.Model):
	user = db.StringProperty()
	friend = db.StringProperty()
	score = db.IntegerProperty()

class Friend(db.Model):	#parent is NO LONGER USER User
	uid = db.StringProperty()
	name = db.StringProperty()
	ready = db.BooleanProperty(default=False)
	user_parent = db.StringProperty()	#the parent user's id
	closeness = db.FloatProperty()

class Photo(db.Model):	#parent is friend, maybe 3 or so per friend
	photo = db.BlobProperty(default=None)
	original = db.BlobProperty(default=None)
	original_url = db.StringProperty()
	width = db.FloatProperty()
	height = db.FloatProperty()
	uid = db.StringProperty()

class Original(db.Model):	#parent is Friend
	url = db.StringProperty()
	height = db.IntegerProperty()
	width = db.IntegerProperty()
	created_time = db.StringProperty()	
	blob = db.BlobProperty(default=None)
	uid = db.StringProperty()
	default = db.BooleanProperty(default=False)
	rejected = db.BooleanProperty(default=False)

class FBTags(db.Model):		#parent is original
	x = db.FloatProperty()
	y = db.FloatProperty()
	uid = db.StringProperty()

class FaceTags(db.Model):
	x = db.FloatProperty()
	y = db.FloatProperty()
	height = db.FloatProperty()
	width = db.FloatProperty()
	sum = db.FloatProperty()
	recognizable = db.StringProperty()
	choice = db.BooleanProperty(default=False)
	url = db.StringProperty()

class Data(db.Model):			#parent = user
	guess = db.StringProperty()
	answer = db.StringProperty()
	round = db.IntegerProperty()
	correct = db.StringProperty()
	
class BaseHandler(webapp.RequestHandler):

	@property
	def current_user(self):
		if not hasattr(self, "_current_user"):
			self._current_user = None
			cookie = facebook.get_user_from_cookie(
				self.request.cookies, FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)
			if cookie:
			# Store a local instance of the user data so we don't need
			# a round-trip to Facebook on every request
				user = User.get_by_key_name(cookie["uid"])
				if not user:
					graph = facebook.GraphAPI(cookie["access_token"])
					profile = graph.get_object("me")
					user = User(key_name=str(profile["id"]),
								id=str(profile["id"]),
								name=profile["name"],
								profile_url=profile["link"],
								access_token=cookie["access_token"])
					user.put()
					#check if process initialized already?
					#initialize picture sorting!
					user_id = str(profile["id"])
					token = str(cookie["access_token"])
					taskqueue.add(queue_name="pictures", url='/pictures', params={'user_id': user_id, 'token': token})
				elif user.access_token != cookie["access_token"]:
					user.access_token = cookie["access_token"]
					user.put()
				self._current_user = user
		return self._current_user


class HomeHandler(BaseHandler):
	def get(self):
		path = os.path.join(os.path.dirname(__file__), "example.html")
		args = dict(current_user=self.current_user,
					facebook_app_id=FACEBOOK_APP_ID)
		self.response.out.write(template.render(path, args))
		
class Pics(BaseHandler):
	def get(self):
		user = self.current_user
		try:
			oauth_access_token = user.access_token
			try:
				graph = facebook.GraphAPI(oauth_access_token)
				friends = graph.get_connections(user.id, "friends")
				friend_list_obj = friends['data']
				key = user.key()
				friend_list = []
				for j in range(0,50):
					i = friend_list_obj[j]
					name = i['name']
					uid = i['id']
					taskqueue.add(queue_name="facebook", url='/facebook', params={'id': uid, 'token': oauth_access_token,'key': key, 'name': name, 'user': user.id})
				for i in friend_list_obj:
					friend_list.append(i['name'])
				user.friend_count = int(len(friend_list))
				logging.debug('i just tried to put something in the ffriend count joyyyy')
				user.friend_list = friend_list
				user.put()
				self.response.out.write('<h2>loading...</h2><br />')
				self.response.out.write('<p>Click <a href="test/0">HERE</a> in a minute or so.</p>')
			except DeadlineExceededError:
				self.response.out.write('<h2>Sorry, we failed to establish a connection with Facebook.</h2><br />')
				self.response.out.write('<h3>Click <a href="/home" >HERE</a> to try again.</h3>')
		except AttributeError:
			self.redirect('/home')

class Pictures(webapp.RequestHandler):	#alternative autoload mode
	def post(self):
		user_id = self.request.get('user_id')
		token = self.request.get('token')
		user_query = db.GqlQuery("SELECT * FROM User WHERE id = :1", str(user_id))
		user = user_query[0]
		token = user.access_token
		
		graph = facebook.GraphAPI(token)
		friends = graph.get_connections(user_id, "friends")
		friend_list_obj = friends['data']
		key = user.key()
		logging.debug("user key is %s", str(key))
		friend_list = []
		#how many friends we are selecting from
		for j in range(0,100):
			i = friend_list_obj[j]
			name = i['name']
			logging.debug("friend added is %s", name)
			uid = i['id']
			taskqueue.add(queue_name="facebook", url='/facebook', params={'id': uid, 'token': token, 'key': key, 'name': name, 'user': user_id})
		for i in friend_list_obj:
			friend_list.append(i['name'])
		user.friend_count = int(len(friend_list))
		user.friend_list = friend_list
		user.put()

class Facebook(webapp.RequestHandler):	#facebook
	def post(self):
		uid = self.request.get("id")
		token = self.request.get("token")
		key = self.request.get("key")
		name = self.request.get("name")
		user = self.request.get('user')
		
		graph = facebook.GraphAPI(token)
		picture_query = graph.get_connections(uid, "photos")
		photos = picture_query["data"]
		if photos:
			reconstitutedKey = db.Key(key)
			friend = Friend()
			friend.name = name
			friend.uid = uid
			friend.user_parent = str(user)
			friend.put()
			
			for j in range(0,12):
				try:
					chosen = photos[j]
					url = chosen['source']
					original = Original(parent=friend)
					original.url = url
					original.height = int(chosen["height"])
					original.width = int(chosen["width"])
					original.created_time = (chosen['created_time'])[:10]
					# original.blob = db.Blob(urlfetch.fetch(url).content)
					original.uid = str(uid)
					original.put()
					key_pass = original.key()
					tag_obj = chosen["tags"]
					tags = tag_obj["data"]
					for i in tags:
						if str(i['id']) == str(uid):
							tag = FBTags(parent=original)
							tag.uid = i['id']
							tag.x = float(i['x'])
							tag.y = float(i['y'])
							tag.put()
							taskqueue.add(queue_name="facedotcom", url='/facedotcom', params={'user': user, 'key_pass': key_pass, 'url': url})
				except IndexError:
					pass
					#break?
			# look for co-occurances in photos
			#also look through the users uploaded photos?
			#get created time to also calculate rank
			dates = []
			connection_count = 0
			current_date = time.gmtime()
			#go through all of this friend's photos
			for photo in photos:
				tag_obj = photo["tags"]
				tags = tag_obj["data"]
				for tag in tags:
					if str(tag['id']) == str(user):
						connection_count += 1
						logging.debug("added to connection count with %s", str(tag['name']))
						date = str(tag['created_time'])[:7]
						logging.debug("%s", date)
						dates.append(date)
			#go through all the dates of co-existing photos
			score = 0
			for date in dates:
				yr_obj = int(str(date)[:4])	#2009
				cur_yr = current_date.tm_year	#2011
				yr_difference = (cur_yr - yr_obj)*12
				mon_obj = int(str(date)[5:7])
				cur_mth = current_date.tm_mon
				mth_difference = cur_mth - mon_obj
				total_time = mth_difference + yr_difference
				logging.debug("total time is %s months", str(total_time))
				logging.debug('total time = %s', str(total_time))
				points = 3*(2**(-(float(total_time))/24))
				score += float(points)
				logging.debug('score is %s', str(score))

			# now it will be updating this person's friend profile
			friend.closeness = float(score)
			friend.put()
					

class Record(BaseHandler):
	def post(self, num):
		name = self.request.get('name')
		noidea = self.request.get('noidea')
		friend_id = self.request.get('friend')
		user = self.current_user
		friends = user.friend_list
		next = int(num) + 1
		
		current = '/test/' + str(num)
		logging.debug('the id is %s', friend_id)
		query = db.GqlQuery("SELECT * FROM Friend WHERE uid = :1", friend_id)
		query_name = query[0]
		#check that the input is valid
		if name:
			logging.debug('name!!')
			if query[0].name == str(name):
				correct = 'True'
				next_url = '/display/' + str(num) + '/' + str(friend_id) + '?answer='
			else:
				correct = 'False'
				next_url = '/display/' + str(num) + '/' + str(friend_id) + '?answer=' + str(name)
			data = Data(parent=user)
			data.guess = str(name)
			data.round = int(num)
			data.answer = query[0].name
			data.correct = correct
			data.put()
			self.redirect(next_url)
		if noidea:
			next_url = '/display/' + str(num) + '/' + str(friend_id) + '?answer='
			logging.debug('no idea!!!')
			data = Data(parent=user)
			data.guess = 'None'
			data.round = int(num)
			data.answer = query[0].name
			data.correct = 'False'
			data.put()
			self.redirect(next_url)
		else:
			self.response.out.write('<h2>There was an error, please go back and try again.</h2>')

class Display(BaseHandler):
	def get(self, num1, num2):
		tally = self.request.get('answer')
		user = self.current_user
		number = int(num1)
		next = number + 1
		
		friends = db.GqlQuery("SELECT * FROM Friend WHERE uid = :1 ", str(num2))
		friend = friends[0]

		photos = db.GqlQuery("SELECT * FROM Photo WHERE uid = :1", str(num2))
		if photos.count() > 0:
			width = photos[0].width
			height = photos[0].height
			if width > height:
				new_width = 350
				new_height = height*(new_width/width)
				dims = "width='350px'"
				wh = 'w'
			elif height > width:
				new_height = 350
				new_width = width*(new_height/height)
				dims = "height='350px'"
				wh = 'h'
			else: 	#if width and height are equal, and a catch all for the rest?
				new_width = 280
				new_height = height*(new_width/width)
				dims = "width='280px'"
				wh = 'w'
			
		# picture = '/image2?uid=' + str(friend.uid)
		picture = photos[0].original_url
		next = number + 1
		next_url = '/test/' + str(next)
		progress = (float(number)/float(10))*100
		
		if tally == '':
			template_values = {
				'picture' : picture,
				'number' : str(next),
				'name' : friend.name,
				'progress': progress,
				'dims': dims,
				'wh': wh,
			}
			
		else:
			wrong = '<h3 id="strike" class="name_answer">' + str(tally) + '</h3>'
			template_values = {
				'picture' : picture,
				'number' : str(next),
				'name' : friend.name,
				'progress': progress,
				'dims': dims,
				'wrong': wrong,
				'wh': wh,
			}
		
		path = os.path.join(os.path.dirname(__file__), 'display.html')
		self.response.out.write(template.render(path, template_values))

class Test(BaseHandler):
	def get(self, num):
		number = int(num)
		
		if number == ROUNDS:
			self.response.out.write('<h2>You are done! Congrats.</h2>')
			self.redirect('/end.html')
		else:
			user = self.current_user

			if user.options_list:
				option_list = user.options_list
			else:
				option_list = []
			logging.debug('user id is %s', user.id)
			# options = db.GqlQuery("SELECT * FROM Options")
			options = Options.all()
			options.filter('user_id =', user.id)
			if options:
				for i in options:
					logging.debug('in options and i is %s', i.friend_id)
					if i.friend_id in option_list:
						pass
					else:
						option_list.append(i.friend_id)
					i.delete()
				user.options_list = option_list
				user.put()
			try:
				friendthisround = user.options_list[number]
				friend = db.GqlQuery("SELECT * FROM Friend WHERE uid = :1 AND status = 'complete'", friendthisround)
				next = number + 1
				record_url = '/record/' + str(num)
				mystery = '/image?uid=' + str(friendthisround)
				friend_list = user.friend_list
				string = ""
				for i in friend_list:
					string += '"' + i + '", '
				progress = (number*100)/ROUNDS
			
				template_values = {
						'mystery' : mystery,
						'friend_list': string,
						'number': number,
						'friend_id': friendthisround,
						'progress': progress,
					}
	
				path = os.path.join(os.path.dirname(__file__), 'test.html')
				self.response.out.write(template.render(path, template_values))
			except IndexError:
				if number == 0:
					self.response.out.write('<h2>The game is not quite ready to begin</h2>')
					self.response.out.write('<h3>Wait a little while longer, then click <a href="/test/0">HERE</a> to begin.</h3>')
				else:
					self.response.out.write('<h2>You are done! </h2>')
		
class GetImage(webapp.RequestHandler):
	def get(self):
		uid = self.request.get('uid')
		photos = db.GqlQuery("SELECT * FROM Photo WHERE uid = :1", uid)
		if photos.count() > 0:
			for i, j in enumerate(photos):
				j.order = i
				j.put()
			self.response.headers['Content-Type'] = 'image/jpeg'
			self.response.out.write(photos[0].photo)
		else:
			pass


class GetImage2(webapp.RequestHandler):
	def get(self):
		uid = self.request.get('uid')
		# photos = db.GqlQuery("SELECT * FROM Photo WHERE uid = :1 ORDER BY order", uid)
		photos = db.GqlQuery("SELECT * FROM Photo WHERE uid = :1", uid)
		if photos.count() > 0:
			self.response.headers['Content-Type'] = 'image/jpeg'
			self.response.out.write(photos[0].original)
		else:
			pass


class Correct(webapp.RequestHandler):
	def get(self, num):
		uid = self.request.get('uid')
		photos = db.GqlQuery("SELECT * FROM Photo WHERE uid = :1", uid)
		count = photos.count()
		if count > 0:
			j = photos[0]
			j.delete()
			logging.debug('deleted bad photo')
		if count == 1:
			#remove from options lists
			users = db.GqlQuery("SELECT * FROM User")
			for user in users:
				if user.options_list:
					options = user.options_list
					if str(uid) in options:
						options.remove(str(uid))
						logging.debug("removed from users options list")
		next_url = '/test/' + str(num)
		self.redirect(next_url)
		


def main():
	util.run_wsgi_app(webapp.WSGIApplication([('/test/([0-9]+)', Test),
									  		  ('/image', GetImage),
											  ('/image2', GetImage2),
											  ('/display/([0-9]+)/([0-9]+)', Display),
											  ('/record/([0-9]+)', Record),
											  ('/correct/([0-9]+)', Correct),
											  ("/home", HomeHandler),
											  ('/pics', Pics),
											  ('/facebook', Facebook),
											  ('/pictures', Pictures)
											  ], debug=True))


if __name__ == "__main__":
	main()
