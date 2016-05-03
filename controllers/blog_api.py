import random
import re
import string
import json
from datetime import datetime

import webapp2
from google.appengine.api import mail
from webapp2_extras import jinja2
from webapp2_extras import routes
from webapp2_extras import sessions
from google.appengine.datastore.datastore_query import Cursor

from vendors import markdown
from models import model
from config import config
from controllers import server


class JsonRestHandler(webapp2.RequestHandler):
    """
    Base RequestHandler type which provides convenience methods for writing
    JSON HTTP responses.
    """
    JSON_MIMETYPE = "application/json"

    def send_error(self, code, message):
        """
        Convenience method to format an HTTP error response in a standard
        format.
        """
        self.response.set_status(code, message)
        self.response.out.write(message)
        return

    def send_success(self, obj=None):
        """
        Convenience method to format a PhotoHunt JSON HTTP response in a
        standard format.
        """
        self.response.headers["Content-Type"] = "application/json"
        if obj is not None:
            if isinstance(obj, basestring):
                self.response.out.write(obj)
            else:
                self.response.out.write(json.dumps(obj,
                                        cls=model.JsonifiableEncoder))
        else:
            self.response.out.write('[]')


class BlogHandler(server.BaseHandler):
    """Base handler for blog"""

    def __init__(self, request, response):
        # Set self.request, self.response and self.app.
        self.initialize(request, response)

    def handle_dispatch():
        """custom dispatch handler"""
        # TODO: format return to JSON here
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @staticmethod
    def url_shortner(full_url):
        """Method for sortning full URL and saving and returning short URL"""
        short_url = ''.join(random.choice(string.ascii_letters +
                                          string.digits) for _ in range(10))
        save = model.ShortUrl(full_url=full_url,
                              short_url=short_url)
        save.put()
        return short_url


class ArticleHandler(BlogHandler, JsonRestHandler):
    """Article handler - Provides an api for working with articles"""

    def all_articles(self):
        """
        GET request to get all articles - Exposed as `GET /api/articles`
        """
        try:
            cursor = Cursor(urlsafe=self.request.get('cursor'))
            reverse = bool(self.request.get('reverse'))
            limit = self.request.get('limit', default_value=5)
            with_deleted = bool(self.request.get('with_deleted'))
            deleted = bool(self.request.get('deleted'))
            tags = self.request.get_all('tags')
            query = model.Article.query(model.Article.soft_deleted == deleted)
            if tags:
                query = model.Article \
                    .query(model.Article.soft_deleted == deleted,
                           model.Article.tags.IN(tags))
            if with_deleted:
                query = model.Article.query()
                if tags:
                    query = model.Article.query(model.Article.tags.IN(tags))
            final_query = query.order(-model.Article.created_on)
            if reverse:
                final_query = query.order(model.Article.created_on)
            articles, next_cursor, more = final_query.fetch_page(
                                                limit, start_cursor=cursor)
            if articles:
                articles.append(next_cursor.urlsafe())
                articles.append(more)
            self.send_success(articles)
        except Exception as e:
            self.send_error(500, e)

    def get(self, **kwargs):
        """
        GET request to get article by id - Exposed as `GET /api/article/<id>`
        """
        try:
            # TODO get user from session and verify
            id = kwargs['id']
            article = model.Article.get_by_id(long(id))
            if article:
                self.send_success(article)
            else:
                raise TypeError
        except TypeError as te:
            self.send_error(404, 'Resource not found')
        except Exception as e:
            self.send_error(500, e)

    def post(self):
        """POST method for articles - Exposed as `POST /api/article`"""
        try:
            article = model.Article()
            article.from_json(self.request.body)
            article.url = re.sub(
                        r'[/|!|"|:|;|.|%|^|&|*|(|)|@|,|{|}|+|=|_|?|<|>]',
                        'p', article.tittle).replace(' ', '-').lower()
            article.short_url = BlogHandler.url_shortner(article.url)
            article.put()
            self.send_success(article)
        except Exception as e:
                self.send_error(404, e)

    def put(self, **kwargs):
        """
        PUT method for article - Exposed as `PATCH /api/article/<id>/`
        """
        try:
            id = kwargs['id']
            article = model.Article.get_by_id(long(id))
            if article:
                article.from_json(self.request.body)
                article.modified_on = datetime.now()
                article.put()
                self.send_success(article)
            else:
                raise IndexError
        except ValueError as ve:
            self.send_error(404, 'invalid literal')
        except IndexError as e:
            self.send_error(504, 'wrong index')
        except Exception as e:
            self.send_error(500, e)

    def delete(self, **kwargs):
        """
        DELETE method for articles - Exposed as `DELETE /api/article/<id>`
        """
        try:
            id = kwargs['id']
            article = model.Article.get_by_id(long(id))
            if article:
                article.soft_deleted = True
                article.put()
                self.send_success({'message': 'sucess'})
            else:
                raise IndexError
        except IndexError as ie:
            self.send_error(404, 'wrong index')
        except Exception as e:
            self.send_error(500, e)


class SubscriberHandler(BlogHandler, JsonRestHandler):
    """
    Handler for subscribers - Exposes GET, POST, PATCH,
    DELETE for `/api/subscriber`
    """

    def get(self):
        """G
        ET method for subscribers - Exposed as `GET /api/subscribers`
        """
        try:
            article = model.Subscriber.query().fetch()
            self.send_success(article)
        except Exception as e:
            self.send_error(500, e)

    def post(self):
        """
        POST method for subscribers - Exposed as `POST /api/subscriber`
        """
        try:
            subscriber = model.Subscriber()
            subscriber.from_json(self.request.body)
            subscriber.put()
            self.send_success(subscriber)
        except Exception as e:
            self.send_error(500, e)

    def delete(self, **kwargs):
        """
        DELETE method for subscribers -
        Exposed as `DELETE /api/subscriber/<id>`
        """
        try:
            id = kwargs['id']
            subscriber = model.Subscriber.get_by_id(long(id))
            if subscriber:
                subscriber.soft_deleted = True
                self.send_success({'message': 'sucess'})
            else:
                raise IndexError
        except IndexError as ie:
            self.send_error(404, 'wrong index')
        except Exception as e:
            self.send_error(500, e)


class TagHandler(BlogHandler, JsonRestHandler):
    """
    Blog tag handler -
    Exposes api for GET, POST, DELETE
    """
    def get(self):
        """
        GET method for all tags - Exposed as `GET /api/tag`
        """
        try:
            tags = model.Tag.query().fetch()
            self.send_success(tags)
        except Exception as e:
            self.send_error(500, e)

    def post(self):
        """
        POST method for all tags - Exposed as `POST /api/tag`
        """
        try:
            tag = model.Tag()
            tag.from_json(self.request.body)
            tag.put()
            self.send_success(tag)
        except Exception as e:
            self.send_error(500, e)

    def delete(self, **kwargs):
        """
        DELETE method for all tags - Exposed as `DELETE /api/tag/<id>`
        """
        try:
            id = kwargs['id']
            tag = model.Tag.get_by_id(long(id))
            if tag:
                tag.soft_deleted = True
                tag.put()
                self.send_success({'message': 'sucess'})
            else:
                raise IndexError
        except IndexError as ie:
            self.send_error(404, 'wrong index')
        except Exception as e:
            self.send_error(500, e)


class UrlShortnerHandler(BlogHandler, JsonRestHandler):
    """
    URL shortner API handler -
    Exposes GET and POST API
    """

    def get(self):
        """
        GET method for url shortner -
        Exposed as `GET /api/short?short_url=<shortUrl>`
        """
        try:
            query_url = self.request.get('short_url')
            url = model.ShortUrl \
                .query(model.ShortUrl.short_url == query_url).get()
            print query_url
            self.send_success(url)
        except Exception as e:
            self.send_error(500, e)

    def post(self):
        """
        POST method for url shortner -
        Exposed as `POST /api/short>`
        """
        try:
            short_url = model.ShortUrl()
            short_url.from_json(self.request.body)
            short_url.short_url = BlogHandler.url_shortner(short_url.full_url)
            short_url.put()
            self.send_success(short_url)
        except Exception as e:
            self.send_error(500, e)

    def delete(self, **kwargs):
        """
        DELETE method for url shortner -
        Exposed as `DELETE /api/short/<id>`
        """
        try:
            id = kwargs['id']
            short_url = model.ShortUrl.get_by_id(long(id))
            if short_url:
                short_url.soft_deleted = True
                short_url.put()
                self.send_success({'message': 'sucess'})
            else:
                raise IndexError
        except IndexError as ie:
            self.send_error(404, 'wrong index')
        except Exception as e:
            self.send_error(500, e)
