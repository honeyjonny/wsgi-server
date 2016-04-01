import re
from cgi import escape
from wsgiref.simple_server import make_server
from urllib.parse import urlparse, parse_qs
from io import StringIO
import http.client


class WebController(object):    
    allowed_methods = ("get", "post")

    def __init__(self, settings):
        if settings:
            [setattr(self, name, value) for name, value in settings.items()]
        pass

    def handle(self, request):
        if request.method.lower() in self.allowed_methods:
            handler = getattr(self, request.method.lower())
            response = handler(request, **request.urlargs)
            return self.finish(response)
        ##write else block

    def finish(self, response):
        def wsgi_resp(environ, start_response):
            headers = list(response.headers.items())
            body = response.body.getvalue().encode("utf-8")
            response.body.close()
            start_response(response.status, headers)
            return [body]
        return wsgi_resp


class WebResponse(object):
    def __init__(self, request):
        self.request = request
        self.status = None
        self.headers = {"Content-Type": "text/plain"}
        self.body = StringIO()

    def add_header(self, header_dict):
        key, val = header_dict.popitem()
        self.headers[key] = val
        return

    def set_status(self, status_const):        
        self.status = "%d %s" % (status_const.value, status_const.name)
        return

    def write(self, content):
        self.body.write(content)
        return


class WebRequest(object):
    def __init__(self, environ):

        self.method = environ.get("REQUEST_METHOD")
        self.path = environ.get("PATH_INFO")
        self.urlargs = dict() #environ.get("myapp.url_args")
        self.headers = dict()

        if environ.get("QUERY_STRING"):
            querystr =  environ["QUERY_STRING"]
            self.query = parse_qs(querystr)
        else:
            self.query = ""            

        if environ.get("CONTENT_TYPE"):
            self.headers["Content-Type"] = environ["CONTENT_TYPE"]


        if environ.get("CONTENT_LENGTH"):
            self.headers["Content-Length"] = environ["CONTENT_LENGTH"]

            length = int(self.headers["Content-Length"])
            stdinp = environ.get("wsgi.input")
            self.body = stdinp.read(length)
        else:
            self.body = ""

    def __str__(self): 
        return """%s %s %s %s""" % (self.method, self.path, self.headers, self.body)
    
    def match_url(self, regex):
        match = regex.match(self.path)
        if match is not None:
            self.urlargs = match.groupdict()
            return True
        return False

    def get_response(self):
        return WebResponse(self)


class WSGIApplication(object):

    def __init__(self, handlers, settings=None):
        self.settings = settings
        self.handlers = [ (re.compile(pattern), callback) for pattern, callback in handlers]

    def __call__(self, environ, start_response):
        request = WebRequest(environ)

        for regex, callback in self.handlers:
            if request.match_url(regex):
                instance = callback(self.settings)
                response = instance.handle(request)
                return response(environ, start_response)
        return self.not_found(environ, start_response)

    def not_found(self, environ, start_response):
        """Called if no URL matches."""
        start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
        return [b'Not Found']


class SimpleApp(WSGIApplication):
    def __init__(self):
        # map urls to WebControllers
        urls = [
            (r'^/$', Index),
            (r'/hello/$', Hello),
            (r'/hello/(?P<name>.+)$', Hello)
        ]

        settings = dict(
                db = dict()
            )

        super(SimpleApp, self).__init__(urls, settings)


class Index(WebController):
    def get(self, request):
        resp = request.get_response()
        resp.set_status(http.client.OK)
        print(self.db)
        resp.write("hello world")
        return resp

class Hello(WebController):
    def get(self, request, name="World"):
        response = request.get_response()
        response.set_status(http.client.OK)
        body = "Hello %s" % name
        response.write(body)
        return response

if __name__ == '__main__':
    app = SimpleApp()
    serv = make_server("", 8080, app)
    serv.serve_forever()
