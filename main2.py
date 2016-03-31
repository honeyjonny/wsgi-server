import re
from cgi import escape
from wsgiref.simple_server import make_server
from urllib.parse import urlparse
from io import StringIO
import http.client


def index(environ, start_response):
    """This function will be mounted on "/" and display a link
    to the hello world page."""
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [b'''Hello World Application
               This is the Hello World application:continue <hello/>''']


def hello(environ, start_response):
    """Like the example above, but it uses the name specified in the
URL."""
    # get the name from the url if it was specified there.
    args = environ['myapp.url_args']
    if args:
        subject = escape(args[0])
    else:
        subject = 'World'
    start_response('200 OK', [('Content-Type', 'text/html')])
    resp = "Hello %s!" % subject
    return [resp.encode("utf-8")]


def not_found(environ, start_response):
    """Called if no URL matches."""
    start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
    return [b'Not Found']



class WebController(object):    
    allowed_methods = ("get", "post")

    def __init__(self):
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
            body = response.body.getvalue()
            print(body)#.encode("utf-8").split("\n")
            response.body.close()
            start_response(response.status, headers)
            return [body.encode("utf-8")]
        return wsgi_resp


class WebResponse(object):
    def __init__(self, request):
        self.request = request
        self.status = None
        self.headers = {"Content-Type": "text/plain"}
        self.body = StringIO()

    def add_header(self, header_dict):
        item = header_dict.popitem()
        self.headers[item[0]] = item[1]
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
            self.query = urlparse.parse_qs(querystr)
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
        match = re.search(regex, self.path)
        if match is not None:
            self.urlargs = match.groupdict()
            return True
        return False

    def get_response(self):
        return WebResponse(self)


class WSGIApplication(object):

    def __init__(self, handlers):
        self.app = None
        self.handlers = handlers

    def __call__(self, environ, start_response):
        request = WebRequest(environ)

        for regex, callback in self.handlers:
            if request.match_url(regex):
                instance = callback()
                response = instance.handle(request)
                return response(environ, start_response)
        return not_found(environ, start_response)


class SimpleApp(WSGIApplication):
    def __init__(self):
        # map urls to functions
        urls = [
            (r'^/$', Index),
            (r'/hello/$', hello),
            (r'/hello/(?P<name>.+)$', hello)
        ]

        super(SimpleApp, self).__init__(urls)


class Index(WebController):
    def get(self, request):
        resp = request.get_response()
        resp.set_status(http.client.OK)
        resp.write("hello world")
        return resp

if __name__ == '__main__':
    app = SimpleApp()
    serv = make_server("", 8080, app)
    try:
        serv.serve_forever()
    except Exception:
        serv.server_close()