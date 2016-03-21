import flask, time, optparse, collections, string, re, signal, marshal, traceback
import math as Math
from flask import request, abort
from flask.ext.cache import Cache
import gevent
from gevent.wsgi import WSGIServer
from gevent.queue import Queue

VALUE_CACHE_MAXAGE = 4000

app = flask.Flask(__name__)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

subscriptions = {}
lhosts = {}
global value_cache
global server
value_cache = collections.OrderedDict()

image_views = 0
updates_received = 0
updates_pushed = 0

def dump_cache():
    d={}
    for k in value_cache:
        d[k]={}
        d[k]["value"] = list(value_cache[k])
        d[k]["ts"] = value_cache[k].ts
    marshal.dump(d, file("/var/spool/plottico_datacache.dat",'w'))

def load_cache():
    global value_cache
    j = marshal.load(file("/var/spool/plottico_datacache.dat"))
    for k in j:
        e = ExpiringDeque(j[k]["value"])
        e.ts = j[k]["ts"]
        value_cache[k] = e


class ExpiringDeque(collections.deque):
    def __init__(self, d=[]):
        super(ExpiringDeque, self).__init__(d, maxlen=50)
        self.ts = time.time()
    def is_expired(self):
        if time.time() - self.ts > VALUE_CACHE_MAXAGE:
            return True
        return False
    def update(self):
        self.ts = time.time()
# TODO: updater method to re-add to top while updatuing
def value_cache_clean_one():
    if len(value_cache) == 0: return
    d = value_cache.popitem(False)
    if not d[1].is_expired():
        value_cache[d[0]]=d[1]

allc=string.maketrans('','')
nodigs=allc.translate(allc, string.digits+".")
translate_table = dict((ord(char), None) for char in nodigs)
def parseFloat(txt):
    try:
        return float(txt)
    except ValueError:
        try:
            #return float(txt.translate(allc, nodigs))
            return float(txt.translate(translate_table))
        except ValueError:
            return None
rmsg = re.compile("[\\d.,]+")
SUPS=["","k","M","G","T","e"]
SUPS_LEN = len(SUPS)
MAXPOINTS = 50
FIG_HEIGHT = 150 # TODO: use in template generator
def axis_max(val,neg):
    max_y = max(val, -neg)
    dig=max_y;
    max_y = (Math.floor(dig/Math.pow(10,Math.floor(Math.log10(dig))))+1)*Math.pow(10,Math.floor(Math.log10(dig))); 
    if neg: max_y*=2
    return max_y

def strip_0(d):
    s = str(d)
    return (s.rstrip('0').rstrip('.') if '.' in s else s)

def round_to_1(x):
    x = int(x)
    if x == 0: return "0"
    return strip_0(str(round(x, -int(Math.floor(Math.log10(abs(x)))))))
    

def generate_points(dlist):
    msg=""
    data=[]
    max_val=0
    neg_val=0
    for d in dlist:
        vals = [parseFloat(x) for x in d[0].split(",")]
        m=max(vals)
        if m > max_val:
            max_val = m
        m = min([x for x in vals if x is not None])
        if m < neg_val:
            neg_val = m
        data.append(vals)
        msgc = rmsg.sub("", d[0])
        if msgc: msg = msgc
    time_half = (dlist[-1][1] / len(dist) - dlist[0][1] / len(dist)) * MAXPOINTS / 2
    hrs = int(time_half / 3600);
    mins = int((time_half % 3600) / 60);
    secs = int(time_half % 60);
    timestring = "";
    if hrs:
        timestring = str(hrs)+"h";
        timestring += round_to_1(mins)+"m";
    elif mins:
        timestring += round_to_1(mins)+"m";
        if 4>mins and secs > 10:
            timestring += round_to_1(secs)+"s";
    else:
        timestring = round_to_1(secs)+"s";
    
    max_val = axis_max(max_val,neg_val)
    mid_val = max_val / 2
    
    mid_idx = 0
    while mid_val >= 1e3 and mid_idx < SUPS_LEN-1:
        mid_val /= 1e3
        mid_idx += 1
    if mid_val > 1: mid_val = round(mid_val, 2);
    if mid_val > 0: mid_val = round(mid_val, 2); # TODO: think here and in SVG, 3-d precision is when v < 0.3 https://github.com/grandrew/plotti.co/issues/11
    valueMid = "%s%s" % (strip_0(mid_val), SUPS[mid_idx])
    
    points = ""
    oldx = 0
    x = 0
    i = 0
    for vals in data:
        onerow="<g>"
        v = 0
        if i != 0:
            for y in vals:
                if y is None or v >= len(data[i-1]) or data[i-1][v] is None: 
                    v+=1
                    continue
                onerow += '<polyline class="src%s" points="%s,%s %s,%s"/>' % (v, oldx,int(data[i-1][v]/max_val*FIG_HEIGHT),x,int(y/max_val*FIG_HEIGHT))
                v+=1
            points+=onerow+"</g>"
        oldx = x
        x = oldx + 500 / MAXPOINTS # width / pts
        i+=1
    return max_val, valueMid, timestring, time_half, neg_val, msg, points # trdn=20

def apply_template(s, keys):
    for k in keys:
        s=s.replace("$%s"%k, str(keys[k]))
    return s

@cache.cached(timeout=500)
@app.route( '/css/main.css' )
def main_css():
    return flask.Response( file('plotti.co/_site/css/main.css','r').read(),  mimetype= 'text/css')

@cache.cached(timeout=500)
@app.route( '/' )
def index():
    return flask.Response( file('plotti.co/_site/index.html','r').read(),  mimetype= 'text/html')

#@cache.cached(timeout=500)
@app.route( '/<hashstr>/plot.svg' )
def plot(hashstr):
    return plotwh(hashstr,0,0)

#@cache.cached(timeout=500)
@app.route( '/<hashstr>/<width>x<height>.svg' )
def plotwh(hashstr,width,height):
    global image_views 
    value_cache_clean_one()
    svg = file('main.svg','r').read()
    trdn = 20
    if hashstr in value_cache:
        try:
            max_val, valueMid, timeMid, secondsMid, neg_val, msg, points = generate_points(value_cache[hashstr])
            value_cache[hashstr].update()
            if neg_val: trdn -= 68
            svg = apply_template(svg, {"MAXPOINTS":MAXPOINTS, "TRDN": trdn, "MSG":msg, "VALUEMID":valueMid, "TIMEMID":timeMid, "DATAPOINTS":points, "INIT_MAX_Y": max_val, "MAX_Y": max_val, "SECONDS_SCALE": secondsMid}) # TODO templating engine
        except:
            print "GENERATE_ERROR"
            traceback.print_exc()
            svg = apply_template(svg, {"MAXPOINTS":MAXPOINTS, "TRDN": trdn, "MSG":"", "VALUEMID":"0.5", "TIMEMID":"10s", "DATAPOINTS":"","INIT_MAX_Y": "false", "MAX_Y": 0, "SECONDS_SCALE":0}) # TODO templating engine
    else:
        svg = apply_template(svg, {"MAXPOINTS":MAXPOINTS, "TRDN": trdn, "MSG":"", "VALUEMID":"0.5", "TIMEMID":"10s", "DATAPOINTS":"","INIT_MAX_Y": "false", "MAX_Y": 0, "SECONDS_SCALE":0}) # TODO templating engine
        
    if width and height: svg = svg.replace('height="210" width="610"', 'height="%s" width="%s"' % (height, width)) # TODO: switch to templating
    image_views += 1
    return flask.Response(svg,  mimetype= 'image/svg+xml')

@app.route('/lock/<hashstr>', methods=['GET'])
def lock(hashstr):
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    if not hashstr in lhosts:
        lhosts[hashstr] = ip
    return feeder(hashstr)

@app.route('/<hashstr>', methods=['GET'])
def feeder(hashstr):
    global updates_received 
    data = request.args.get('d')
    if not data:
        return plot(hashstr)
    if len(data) > 1024:
        return "" # TODO: return data error code
    if not hashstr in value_cache:
        value_cache[hashstr] = ExpiringDeque()
        value_cache[hashstr].append((data, time.time()));
    else:
        value_cache[hashstr].append((data,int(time.time())))
        value_cache[hashstr].update()
    if not hashstr in subscriptions: return ""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    try:
        if hashstr in lhosts and ip != lhosts[hashstr]: 
            abort(403)
            return ""
    except KeyError:
        return ""
    def notify():
        global updates_pushed 
        updates_pushed += len(subscriptions[hashstr])
        for sub in subscriptions[hashstr][:]:
            sub.put(data)
    gevent.spawn(notify)
    updates_received += 1
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

def shutdown():
    global server
    print('Shutting down ...')
    server.stop(timeout=2)
    print('Saving state ...')
    t1=time.time()
    dump_cache()
    print "Cache dump took", time.time()-t1, "seconds"
    #dill.dump(value_cache, file("/var/spool/plottico_datacache.dat",'w'))
    #exit(signal.SIGTERM)

def dump_stats():
    try:
        fs = file("/tmp/plottico_stats","w")
        fs.write("%s\n%s\n%s\n" % (image_views, updates_received, updates_pushed))
        fs.flush()
        fs.close()
    except IOError:
        print "Could not dump stats!"

gevent.signal(signal.SIGTERM, shutdown)
gevent.signal(signal.SIGUSR1, dump_stats)

if __name__ == "__main__":
    global server
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
    
    try:
        t1=time.time()
        load_cache()
        print "Cache load took", time.time()-t1, "seconds"
    except IOError:
        print "Not loading value cache..."
        pass
        
    print "Starting on port", port
    

    app.debug = debug
    if debug: server = WSGIServer((host, port), app)
    else: server = WSGIServer((host, port), app, log=None)
    print "serving"
    server.serve_forever()
