import webapp2
import os
import logging
import urllib
import random
import string

import model
import markdown

from google.appengine.api import mail
from webapp2_extras import routes
from webapp2_extras import jinja2

#method for handling errors
def error(request, response, exception):
    logging.exception(exception)
    params = {
        'error' : exception.code
    }
    jinja = jinja2.get_jinja2()
    response.write(jinja.render_template('error.html', **params))


#base handler
class BaseHandler(webapp2.RequestHandler):

    @webapp2.cached_property
    def jinja2(self):
        # Returns a Jinja2 renderer cached in the app registry.
        return jinja2.get_jinja2(app=self.app)

    def render_response(self, _template, **params):
        # Renders a template and writes the result to the response.
        temp = self.jinja2.render_template(_template, **params)
        self.response.write(temp)

#welcome page handler
class HomeHandler(BaseHandler):
    def get(self):
        params = {
            'page' : 'home'
        }
        self.render_response('home.html',**params)

#handler for blog
class BlogHandler(BaseHandler):
    def get(self):

        #code to search the database for blog posts

        params = {
            'page' : 'blog',
            'tittle' : tittle,
            'date' : date
        }
        self.render_response('blog.html',**params)

#handler for serving article
class ArticleHandler(BaseHandler):
    def get(self, **kwargs):
        article_url = kwargs['article_url']

        #string manipulation to replace url - with  ' ' and compare to tittle

        if tittle:

            # query database for tittle, content & date

            params = {
                'page' : 'article',
                'tittle' : tittle,
                'content' : content,
                'date' : date
            }
            self.render_response('article.html',**params)
        else:
            self.abort(404)

#handler for writing blog
class WriteHandler(BaseHandler):

    # add function to authenticate user


    def get(self, **kwargs):
        auth = kwargs['token']
        verify = model.Auth.query(model.Auth.token == auth).get()
        if verify :
            params = {
                'page' : 'write',
                'message' : 'welcome'
            }

        else:
            verify = model.Auth.query().get()
            if verify :
                    params = {
                    'page' : 'write',
                    'message' :  'Already a request is pending. Check your mail!'
                }
            else :
                gtoken =  ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
                save = model.Auth(token = gtoken)
                save.put()

                # in production
                # mail.send_mail(sender="Vikash Kumar <mailkumarvikash@gmail.com>",
                #   to="Vikash Kumar <mailkumarvikash@gmail.com>",
                #   subject="Link to write blog",
                #   body="""
                #     https://blog.vikashkumar.me/write/%s
                # """, %(gtoken))
                # params = {
                #     'page' : 'token'
                #     'message' : 'check your mail for link to write'
                # }

                # for test
                url = 'http://localhost:8080/blog/write/' + gtoken
                params = {
                    'page' : 'token',
                    'message' : url
                }

        self.render_response('write.html',**params)

        #code for redirecting to generate token

        #first check authentication
    def post(self, **kwargs):
        tittle = self.response.get('tittle')
        content = self.response.get('content')
        save = model.Article(tittle = tittle,
                            content = content)
        save.put()
        token = model.Auth.query().get()
        token.key.delete()
        #code to upload image to cloud storage

        params = {
            'page' : 'author'
        }

        # inform that post has been updated
        self.render_response('write.html',**params)

#handler for about page
class AboutHandler(BaseHandler):
    def get(self):
        params = {
            'page' : 'about'
        }
        self.render_response('about.html',**params)


#handler to redirect to naked domain
class WwwHandler(BaseHandler):
    def get(self):
        self.redirect('http://vikashkumar.me')


#error handler
class ErrorHandler(BaseHandler):
    def get(self,*args):
        params = {
            'error' : error
        }
        self.response.write(error)


app = webapp2.WSGIApplication([
    routes.DomainRoute('blog.vikashkumar.me', [
        webapp2.Route('/<article_url>', handler=ArticleHandler, name='article'),
        webapp2.Route('/write/<token>', handler=WriteHandler, name='write'),
        webapp2.Route('/', handler=BlogHandler, name='blog'),
    ]),
    webapp2.Route('/about', handler=AboutHandler, name='about'),
    webapp2.Route('/blog', handler=BlogHandler, name='blog'),
    webapp2.Route('/blog/<article_url>', handler=ArticleHandler, name='article'),
    webapp2.Route('/blog/write/<token>', handler=WriteHandler, name='write'),
    webapp2.Route('/', handler=HomeHandler, name='home'),
    ],
    debug=True)

#errors
app.error_handlers[404] = error
app.error_handlers[500] = error
