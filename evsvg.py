import flask, time, random, optparse, collections, string, re
from flask import request
from flask.ext.cache import Cache
import gevent
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

VALUE_CACHE_MAXAGE = 600

app = flask.Flask(__name__)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

limiter = Limiter(
    app,
    key_func=get_remote_address,
)

subscriptions = {}
lhosts = {}
value_cache = collections.OrderedDict()

class ExpiringDeque(collections.deque):
    def __init__(self, data):
        super(ExpiringDeque, self).__init__(maxlen=50)
        self.append(data)
        self.ts = time.time()
    def is_expired(self):
        if time.time() - self.ts > VALUE_CACHE_MAXAGE:
            return True
        return False
    def update(self):
        self.ts = time.time()

def value_cache_clean_one():
    d = value_cache.popitem(False)
    if not d[1].is_expired():
        value_cache[d[0]]=d[1]

allc=string.maketrans('','')
nodigs=allc.translate(allc, string.digits+".")
def parseFloat(txt):
    try:
        return float(txt)
    except ValueError:
        try:
            return float(txt.translate(allc, nodigs))
        except ValueError:
            return None
rmsg = re.compile("[\\d.,]+")
SUPS=["","k","M","G","T","e"]
SUPS_LEN = len(SUPS)
def generate_points(dlist):
    msg=""
    data=[]
    max_val=0
    neg_val=False
    for d in dlist:
        vals = [parseFloat(x) for x in d[0].split(",")]
        m=max(vals)
        if m > max_val:
            max_val = m
        if min(vals) < 0:
            neg_val = True
        data.append(vals)
        msg = rmsg.sub("", d[0])
    timeMid = (dlist[0][1] - dlist[-1][1]) / 2
    max_val = axis_max(max_val)
    mid_val = max_val / 2
    
    mid_idx = 0
    while mid_val >= 1e3 and mid_idx < SUPS_LEN-1:
        mid_val /= 1e3
        mid_idx += 1
    if(mid_val > 1) mid_val = round(mid_val, 2);
    if(mid_val > 0) mid_val = round(mid_val, 2); # TODO: think here and in SVG, 3-d precision is when v < 0.3 https://github.com/grandrew/plotti.co/issues/11
    valueMid = "%s%s" % (mid_val, SUPS[mid_idx])
    
    points = ""
    oldx = 0
    for vals in data:
        onerow="<g>"
        r = 0
        oldy = 0 # TODO fix 0-problem https://github.com/grandrew/plotti.co/issues/10
        x = oldx + 500 / 50 # width / pts
        for y in vals:
            if r == 0:
                oldy = y
            else:
                onerow += '<polyline class="src%s" points="%s,%s %s,%s"/>' % (r, oldx,oldy,x,y)
            oldy = y
            r+=1
        points+=onerow
        oldx = x
    
    return max_val, valueMid, timeMid, neg_val, points+"</g>" # trdn=20
        
    
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
    return plotwh(hashstr,0,0)

@cache.cached(timeout=500)
@app.route( '/<hashstr>/<width>x<height>.svg' )
def plotwh(hashstr,width,height):
    value_cache_clean_one()
    svg = file('main.svg','r').read()
    if hashstr in value_cache:
        
    if width and height: svg = svg.replace('height="210" width="610"', 'height="%s" width="%s"' % (height, width))
    return flask.Response(svg,  mimetype= 'image/svg+xml')

@limiter.limit("50 per second")
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
    if len(data) > 1024:
        return ""
    if not data:
        return plot(hashstr)
    if not hashstr in value_cache:
        value_cache[hashstr] = ExpiringDeque(data);
    else:
        value_cache[hashstr].append((data,int(time.time())))
        value_cache[hashstr].update()
        
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
