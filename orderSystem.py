import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])

DEFAULT_DATASTORE_NAME = 'default_datastore'

# create a default key for the datastore
def datastore_key(data_store_name=DEFAULT_DATASTORE_NAME):
    return ndb.Key('datastore', data_store_name)

# order class holds an order
class Order(ndb.Model):
    beignet_order = ndb.StringProperty(indexed=False)
    content = ndb.StringProperty(indexed=False)
    customer = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    fulfilled = ndb.BooleanProperty()
    url_string = ndb.StringProperty(indexed=False)

# handler for the main page (homepage)
class MainPage(webapp2.RequestHandler):
    def get(self):
	template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render())

# handler for the page used to enter order entries
class OrderEntryPage(webapp2.RequestHandler):
    def get(self):
	template = JINJA_ENVIRONMENT.get_template('orderentry.html')
        self.response.write(template.render())

# handler for the page used by the kitchen to fill orders
class ChefViewPage(webapp2.RequestHandler):
    def get(self):
        data_store_name = self.request.get('data_store_name',
                                          DEFAULT_DATASTORE_NAME)

        order_query = Order.query(
            ancestor=datastore_key(data_store_name)).filter(Order.fulfilled == False).order(-Order.date)
        orders = order_query.fetch(10)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'orders': orders,
            'data_store_name': urllib.quote_plus(data_store_name),
            'url': url,
            'url_linktext': url_linktext,
        }

        template = JINJA_ENVIRONMENT.get_template('chefview.html')
        self.response.write(template.render(template_values))

# used to submit and store orders (go from web form to app engine data store)
class OrderInput(webapp2.RequestHandler):
    def post(self):
        data_store_name = self.request.get('data_store_name',
                                          DEFAULT_DATASTORE_NAME)
        order = Order(parent=datastore_key(data_store_name))

	# fill order with data from form
        order.content = self.request.get('content')
        order.customer = self.request.get('customer_name')
	order.beignet_order = self.request.get('AppleQuantity') + " Beignets"
	order.fulfilled = False
        orderExtras = self.request.get_all('Extras')
        for extra in orderExtras:
            order.beignet_order = order.beignet_order + " +" + extra
        order_key = order.put()
        order.url_string = order_key.urlsafe()
        order.put()
        query_params = {'data_store_name': data_store_name}
        self.redirect('/orderEntry')

class FulfillOrder(webapp2.RequestHandler):
    def post(self):
        key_string = self.request.get('order')
        order_key = ndb.Key(urlsafe=key_string)
        order = order_key.get()
        order.fulfilled = True
        order.put()
        data_store_name = self.request.get('data_store_name',
                                          DEFAULT_DATASTORE_NAME)
        query_params = {'data_store_name': data_store_name}
        self.redirect('/chefView')

class ResetOrders(webapp2.RequestHandler):
    def get(self):
        ndb.delete_multi(Order.query().fetch(999999, keys_only=True))
        self.redirect('/?')

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/orderEntry', OrderEntryPage),
    ('/chefView', ChefViewPage),
    ('/sign', OrderInput),
    ('/fulfilOrder', FulfillOrder),
    ('/resetOrders', ResetOrders),
], debug=True)