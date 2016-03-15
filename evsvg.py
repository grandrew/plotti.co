import flask, time, random
from flask import request
from flask.ext.cache import Cache
# from pubsub import pub
# from threadsafepub import pub as tpub
# from threading import Event, Thread
import gevent
from gevent.wsgi import WSGIServer
from gevent.queue import Queue

app = flask.Flask(__name__)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

subscriptions = {}

@app.route( '/svg' )
def svg():
    return flask.Response( file('main.svg','r').read(),  mimetype= 'image/svg+xml')

# @app.route( '/stream' )
# def stream():
#     def read_process():
#         y1=0.0
#         y2=0.0
#         y3=0.0
#         while True:
#             time.sleep(0.2)
#             y1+=random.uniform(-0.1, 0.1)
#             y2+=random.uniform(-0.1, 0.1)
#             y3+=random.uniform(-0.1, 0.1)
#             if y1 < 0: y1 = 0
#             if y2 < 0: y2 = 0
#             if y3 < 0: y3 = 0
#             yield "data: %sbps,%s,%s\n\n" % (y1,y2,y3)
#     return flask.Response( read_process(), mimetype= 'text/event-stream')

#@cache.cached(timeout=50)
@app.route( '/<hashstr>/plot.svg' )
def plot(hashstr):
    return flask.Response( file('main.svg','r').read(),  mimetype= 'image/svg+xml')

@app.route('/<hashstr>', methods=['GET'])
def feeder(hashstr):
    print "send", hashstr, request.args.get('d')
    if not hashstr in subscriptions: return ""
    data = request.args.get('d')
    def notify():
        for sub in subscriptions[hashstr][:]:
            sub.put(data)
    gevent.spawn(notify)
    return flask.Response('<svg xmlns="http://www.w3.org/2000/svg"></svg>', mimetype= 'image/svg+xml')
    
@app.route('/<hashstr>/stream', methods=['GET'])
def stream(hashstr):
    print "sub to", hashstr
    
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
            print "Unsub", hashstr
            subscriptions[hashstr].remove(q)
            if len(subscriptions[hashstr]) == 0:
                del subscriptions[hashstr]
    return flask.Response( send_proc(), mimetype= 'text/event-stream')



if __name__ == "__main__":
    app.debug = True
    server = WSGIServer(("", 80), app)
    print "serving"
    server.serve_forever()
    #app.run(host="0.0.0.0", port=80, debug=True, threaded=True)
