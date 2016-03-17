import flask, time, random, optparse
from flask import request
from flask.ext.cache import Cache
import gevent
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = flask.Flask(__name__)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

limiter = Limiter(
    app,
    key_func=get_remote_address,
    #global_limits=["200 per day", "50 per hour"])
)

subscriptions = {}
lhosts = {}

@cache.cached(timeout=500)
@app.route( '/css/main.css' )
def main_css():
    return flask.Response( file('plotti.co/_site/css/main.css','r').read(),  mimetype= 'text/css')

@cache.cached(timeout=500)
@app.route( '/' )
def index():
    return flask.Response( file('plotti.co/_site/index.html','r').read(),  mimetype= 'text/html')

@cache.cached(timeout=500)
@app.route( '/<hashstr>/plot.svg' )
def plot(hashstr):
    return flask.Response( file('main.svg','r').read(),  mimetype= 'image/svg+xml')

@cache.cached(timeout=500)
@app.route( '/<hashstr>/<width>x<height>.svg' )
def plotwh(hashstr,width,height):
    return flask.Response( file('main.svg','r').read().replace('height="210" width="610"', 'height="%s" width="%s"' % (height, width)),  mimetype= 'image/svg+xml')

@limiter.limit("10 per second")
@app.route('/lock/<hashstr>', methods=['GET'])
def lock(hashstr):
    if request.headers.getlist("X-Forwarded-For"):
       ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
       ip = request.remote_addr
    if not hashstr in lhosts:
        lhosts[hashstr] = ip
    if not hashstr in subscriptions: return ""
    return feeder(hashstr)

@limiter.limit("50 per second")
@app.route('/<hashstr>', methods=['GET'])
def feeder(hashstr):
    data = request.args.get('d')
    if not data:
        return plot(hashstr)
    if not hashstr in subscriptions: return ""
    if request.headers.getlist("X-Forwarded-For"):
       ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
       ip = request.remote_addr
    try:
        if hashstr in lhosts and ip != lhosts[hashstr]: return ""
    except KeyError:
        return ""
    def notify():
        for sub in subscriptions[hashstr][:]:
            sub.put(data)
    gevent.spawn(notify)
    return flask.Response('<svg xmlns="http://www.w3.org/2000/svg"></svg>', mimetype= 'image/svg+xml')



    
@app.route('/<hashstr>/stream', methods=['GET'])
def stream(hashstr):
    def send_proc():
        q = Queue()
        if not hashstr in subscriptions:
            # TODO: race here?
            subscriptions[hashstr] = [q]
        else:
            subscriptions[hashstr].append(q)
        try:
            while True:
                yield "data: %s\n\n" % q.get()
        finally:
            subscriptions[hashstr].remove(q)
            if len(subscriptions[hashstr]) == 0:
                try: # race?
                    del subscriptions[hashstr]
                except KeyError:
                    pass
    return flask.Response( send_proc(), mimetype= 'text/event-stream')

def parseOptions():
    '''
    parse program parameters
    '''
    usage = 'usage: %prog [options]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--port', dest='port', metavar='PORT',
                      help='listen server port')
    parser.add_option('--debug', dest='debug', action="store_true",
                      metavar='DEBUG', help='Debugging state')
    parser.add_option('--host', dest='host', metavar='HOST',
                      help='host server address')
    options, args = parser.parse_args()
    return options, args, parser

if __name__ == "__main__":
    opt, args, parser = parseOptions()
    debug = False
    port=80
    host=""
    if opt.debug is True:
        debug = True
    if opt.port:
        port=int(opt.port)
    if opt.host:
        host=opt.host
    print "Starting on port", port

    app.debug = debug
    if debug: server = WSGIServer((host, port), app)
    else: server = WSGIServer((host, port), app, log=None)
    print "serving"
    server.serve_forever()
