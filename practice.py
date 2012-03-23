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
from google.appengine.runtime import DeadlineExceededError

from django.utils import simplejson
from example import User, BaseHandler
from face_api import FaceAPI
from google.appengine.ext import db, blobstore
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import taskqueue
from google.appengine.api import images
from google.appengine.api import urlfetch

class PracticeTest(BaseHandler):
	def get(self, num):
		user = self.current_user
		
		if int(num) == 0:
			template_values = {
					'img_url' : '/images/crop0.jpg',
					'friend_list': '"Bill Clinton", "Barack Obama", "George W. Bush"',
					'num': int(num),
					'message' : "<h3>Let's begin with a public figure.<br />Submit your guess or click 'I have no idea' to proceed.</h3>"
				}
		
			path = os.path.join(os.path.dirname(__file__), 'practice.html')
			self.response.out.write(template.render(path, template_values))
			
		if int(num) == 1:
			
			#check if game is ready
			options = db.GqlQuery("SELECT * FROM Options WHERE user_id = :1", str(user.id))
			logging.debug("%d", options.count())
			# if options.count() > 0:
			# 	logging.debug("%s", str(options.count()))
			# 	#if ready:
			# 	self.redirect('/test/0')
			# else:
			template_values = {
					'img_url' : '/images/crop1.jpg',
					'friend_list': '"Bill Clinton", "Barack Obama", "George W. Bush"',
					'num': int(num),
					'message' : "<h3>Let's try another one.</h3>"
				}
		
			path = os.path.join(os.path.dirname(__file__), 'practice.html')
			self.response.out.write(template.render(path, template_values))
		if int(num) == 2:
			# logging.debug("%d", len(user.options_list))
			# if len(user.options_list) > 0:
			# 	logging.debug("%s", str(user.options_list))
			# 	#if ready:
			# 	self.redirect('/test/0')
			# else:
			template_values = {
					'img_url' : '/images/crop2.jpg',
					'friend_list': '"Bill Clinton", "Barack Obama", "George W. Bush"',
					'num': int(num),
					'message' : "<h3>Last one before we begin the game!</h3>"
				}
	
			path = os.path.join(os.path.dirname(__file__), 'practice.html')
			self.response.out.write(template.render(path, template_values))
		# else:
		# 	self.redirect("/test/0")
					
class PracticeDisplay(webapp.RequestHandler):
	def post(self, num):
		name = self.request.get('name')
		noidea = self.request.get('noidea')
		
		number = int(num)
		next = number + 1

		if int(num) == 0:
			answer = "Barack Obama"
			picture = '/images/full0.jpg'
			dims = "width='350px'"
			progress = 33
			next_url = 'http://80b497f232b946047a29b6e7cd4f06.appspot.com/practice_test/1'
		if int(num) == 1:
			answer = "George W. Bush"
			picture = '/images/full1.jpg'
			dims = "width='350px'"
			progress = 66
			next_url = 'http://80b497f232b946047a29b6e7cd4f06.appspot.com/practice_test/2'
		if int(num) == 2:
			answer = "Bill Clinton"
			picture = '/images/full2.jpg'
			dims = "width='350px'"
			progress = 100
			next_url = 'http://80b497f232b946047a29b6e7cd4f06.appspot.com/test/0'


		if name:
			if str(name) == answer:
				template_values = {
					'picture' : picture,
					'next_url' : next_url,
					'name' : answer,
					'progress': progress,
					'dims': dims,
					'wh' : 'w',
					'message' : "<h3>Good job! Click NEXT to continue.</h3>"
				}
			else:
				template_values = {
					'picture' : picture,
					'next_url' : next_url,
					'name' : answer,
					'progress': progress,
					'wrong': '<h3 id="strike" class="name_answer">' + str(name) + '</h3>',
					'dims': dims,
					'wh' : 'w',
					'message' : "<h3>Not quite the right choice, but that's how you submit your answer.</h3>"
				}
			path = os.path.join(os.path.dirname(__file__), 'practice2.html')
			self.response.out.write(template.render(path, template_values))
		
		if noidea:
			template_values = {
				'picture' : picture,
				'next_url' : next_url,
				'name' : answer,
				'progress': progress,
				'dims': dims,
				'wh' : 'w',
				'message' : "<h3>Never seen this guy? <br />Try clicking the input box to see some suggested options.</h3>"
			}

			path = os.path.join(os.path.dirname(__file__), 'practice2.html')
			self.response.out.write(template.render(path, template_values))
		

def main():
	util.run_wsgi_app(webapp.WSGIApplication([("/practice_test/([0-9]+)", PracticeTest),
											  ("/practice_display/([0-9]+)", PracticeDisplay)
											  ], debug=True))


if __name__ == "__main__":
	main()