import flask, time, random
from flask import request
from flask.ext.cache import Cache
import gevent
from gevent.wsgi import WSGIServer
from gevent.queue import Queue

app = flask.Flask(__name__)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

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

@app.route('/lock/<hashstr>', methods=['GET'])
def lock(hashstr):
    if not hashstr in lhosts:
        lhosts[hashstr] = request.remote_addr
    if not hashstr in subscriptions: return ""
    return feeder(hashstr)

@app.route('/<hashstr>', methods=['GET'])
def feeder(hashstr):
    if not hashstr in subscriptions: return ""
    if hashstr in lhosts and request.remote_addr != lhosts[hashstr]: return ""
    data = request.args.get('d')
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
            subscriptions[hashstr] = [q]
        else:
            subscriptions[hashstr].append(q)
        try:
            while True:
                yield "data: %s\n\n" % q.get()
        finally:
            subscriptions[hashstr].remove(q)
            if len(subscriptions[hashstr]) == 0:
                del subscriptions[hashstr]
    return flask.Response( send_proc(), mimetype= 'text/event-stream')

if __name__ == "__main__":
    #app.debug = True
    server = WSGIServer(("", 80), app)
    print "serving"
    server.serve_forever()
