import gevent.monkey
gevent.monkey.patch_all()
import flask, time, optparse, string, re, signal, marshal, traceback, sys
import math as Math
from flask import request, abort
from flask.ext.cache import Cache
import gevent
from gevent.wsgi import WSGIServer
from gevent.queue import Queue

from ZODB import FileStorage, DB
import transaction
from persistent import Persistent
from persistent.list import PersistentList
from BTrees.IOBTree import IOBTree
from BTrees.OOBTree import OOBTree

sys.path.append("/opt/plotticohost")
try:
    import datastore
    datastore.conn_open()
except ImportError:
    datastore = None

VALUE_CACHE_MAXAGE = 90000

app = flask.Flask(__name__)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

subscriptions = {}
tokenHashes = {}
tokenSubscriptions = {}

import errno    
import os

# http://stackoverflow.com/a/600612/2659616
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
        
DBDIR = "/var/lib/plottico/"
DBPATH = DBDIR+'ValueCache.fs'
mkdir_p(DBDIR)
storage = FileStorage.FileStorage(DBPATH)
db = DB(storage)
conn = db.open()
dbroot = conn.root()

if not dbroot.has_key('vc'):
    dbroot['vc'] = OOBTree()
if not dbroot.has_key('vc_ts'):
    dbroot['vc_ts'] = IOBTree()
if not dbroot.has_key('lhosts'):
    dbroot['lhosts'] = OOBTree()
if not dbroot.has_key('khosts'):
    dbroot['khosts'] = OOBTree()

EPOCH = 1461251697 # TODO: manage EPOCH rotation

global value_cache
global expire_cache
global server
value_cache = dbroot["vc"]
expire_cache = dbroot["vc_ts"]
lhosts = dbroot["lhosts"]
khosts = dbroot["khosts"]

image_views = 0
updates_received = 0
updates_pushed = 0

# used only once, then the cache file should be deleted!
def load_cache():
    global value_cache
    j = marshal.load(file("/var/spool/plottico_datacache.dat"))
    for k in j:
        e = ExpiringDeque(k, j[k]["value"])
        if not k in value_cache: value_cache[k] = e

class ExpiringDeque(PersistentList):
    def __init__(self, phash, d=[], maxlen=50):
        super(ExpiringDeque, self).__init__(d)
        self.maxlen = maxlen
        self.phash = phash
        self.ts = self.gen_ts()
        for v in d:
            self.append(v)
        self.update()
    def gen_ts(self):
        return int((time.time()-EPOCH)*10000)
    def append(self, d):
        super(ExpiringDeque, self).append(d)
        if len(self) > self.maxlen:
            self.pop(0)
    def update(self):
        global expire_cache
        if self.ts in expire_cache:
            del expire_cache[self.ts]
        self.ts = self.gen_ts()
        expire_cache[self.ts] = self.phash
        transaction.commit()

def value_cache_clean_one():
    aged_ts = int(((time.time()-EPOCH) - VALUE_CACHE_MAXAGE) * 10000)
    expired = expire_cache.items(0, aged_ts)
    for ts, phash in expired:
        del expire_cache[ts]
        del value_cache[phash]
        if phash in lhosts:
            del lhosts[phash]
        if phash in khosts:
            del khosts[phash]
    transaction.commit()
        

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
    max_val=0.0
    neg_val=0.0
    min_val=1e300
    for d in dlist:
        vals = [parseFloat(x) for x in d[0].split(",")]
        m=max(vals)
        if m > max_val:
            max_val = m
        m = min([x for x in vals if x is not None])
        if m < min_val:
            min_val = m
        if m < neg_val:
            neg_val = m
        data.append(vals)
        msgc = rmsg.sub("", d[0])
        if msgc: msg = msgc
    time_half = (dlist[-1][1] / len(dlist) - dlist[0][1] / len(dlist)) * MAXPOINTS / 2
    avg_upd = (dlist[-1][1] - dlist[0][1]) / len(dlist)
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
    
    # TODO: historic min, historic max?
    y_shift = 0.0
    if min_val > 0 and min_val != max_val and (max_val - min_val) / max_val < 0.3 and len(data) > 20 and not ("%" in msg):
        y_shift = min_val
    else:
        min_val = 0.0
    
    # mid_val = (axis_max(max_val,neg_val) + y_shift) / 2
    max_val = axis_max(max_val-y_shift,neg_val)
    mid_val = (max_val + 2*y_shift) / 2
    mid_idx = 0
    while mid_val >= 1e3 and mid_idx < SUPS_LEN-1:
        mid_val /= 1e3
        mid_idx += 1
    if mid_val > 1: mid_val = round(mid_val, 2);
    if mid_val > 0: mid_val = round(mid_val, 2); # TODO: think here and in SVG, 3-d precision is when v < 0.3 https://github.com/grandrew/plotti.co/issues/11
    if mid_idx > 0: mid_val = round(mid_val, 1);
    valueMid = "%s%s" % (strip_0(mid_val), SUPS[mid_idx])
    
    mid_idx = 0
    while min_val >= 1e3 and mid_idx < SUPS_LEN-1:
        min_val /= 1e3
        mid_idx += 1
    if min_val > 1: min_val = round(min_val, 2);
    if min_val > 0: min_val = round(min_val, 2); # TODO: think here and in SVG, 3-d precision is when v < 0.3 https://github.com/grandrew/plotti.co/issues/11
    if mid_idx > 0: min_val = round(min_val, 1);
    valueMin = "%s%s" % (strip_0(min_val), SUPS[mid_idx])
    
    
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
                y_used = y - y_shift
                yold_used = data[i-1][v] - y_shift
                max_val_used = max_val
                onerow += '<polyline class="src%s" points="%s,%s %s,%s"/>' % (v, oldx,int(yold_used/max_val_used*FIG_HEIGHT),x,int(y_used/max_val_used*FIG_HEIGHT))
                v+=1
            points+=onerow+"</g>"
        oldx = x
        x = oldx + 500 / MAXPOINTS # width / pts
        i+=1
    
    l_y = ""
    if len(data) == 1:
        for v in data[0]:
            if not v is None:
                if int(v) == float(v): 
                    v = int(v)
                if l_y: 
                    l_y = "%s;%s"%(l_y,v)
                else: 
                    l_y = str(v)
        
    if len(data) == 0 or (avg_upd > 0 and time.time() - dlist[-1][1] > avg_upd * 2):
        nodata = "&#xf071;"
        late = "%.1f minutes late" % ((time.time() - dlist[-1][1] - avg_upd)/60)
    else:
        nodata = ""
        late = "No data stream"
    return max_val, valueMid, timestring, time_half, neg_val, msg, points, y_shift, valueMin, l_y, nodata, avg_upd, late # trdn=20

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
    
@cache.cached(timeout=500)
@app.route( '/eventsource.min.js' )
def es():
    return flask.Response( file('eventsource.min.js','r').read(),  mimetype= 'text/javascript')
@cache.cached(timeout=500)
@app.route( '/plottico.png' )
def preview():
    return flask.Response( file('plottico.png','rb').read(),  mimetype= 'image/png')

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
            max_val, valueMid, timeMid, secondsMid, neg_val, msg, points, y_shift, valueMin, l_y, nodata, avg_upd, late = generate_points(value_cache[hashstr])
            value_cache[hashstr].update()
            if neg_val: trdn -= 68
            svg = apply_template(svg, {"MAXPOINTS":MAXPOINTS, "TRDN": trdn, "MSG":msg, "VALUEMID":valueMid, "TIMEMID":timeMid, "DATAPOINTS":points, "INIT_MAX_Y": max_val, "MAX_Y": max_val, "SECONDS_SCALE": secondsMid, "Y_SHIFT": y_shift, "ZERO": valueMin, "L_Y":l_y, "NODATA":nodata, "AVG_UPD": avg_upd, "LATE": late}) # TODO templating engine
        except:
            print "GENERATE_ERROR"
            traceback.print_exc()
            svg = apply_template(svg, {"MAXPOINTS":MAXPOINTS, "TRDN": trdn, "MSG":"", "VALUEMID":"0.5", "TIMEMID":"10s", "DATAPOINTS":"","INIT_MAX_Y": "false", "MAX_Y": 0, "SECONDS_SCALE":0, "Y_SHIFT": 0, "ZERO": 0, "L_Y":"", "NODATA":"&#xf071;", "AVG_UPD": 0, "LATE": "No data stream"}) # TODO templating engine
    else:
        svg = apply_template(svg, {"MAXPOINTS":MAXPOINTS, "TRDN": trdn, "MSG":"", "VALUEMID":"0.5", "TIMEMID":"10s", "DATAPOINTS":"","INIT_MAX_Y": "false", "MAX_Y": 0, "SECONDS_SCALE":0, "Y_SHIFT": 0, "ZERO": 0, "L_Y":"", "NODATA":"&#xf071;", "AVG_UPD": 0, "LATE": "No data stream"}) # TODO templating engine
        
    if width and height: svg = svg.replace('height="210" width="610"', 'height="%s" width="%s"' % (height, width)) # TODO: switch to templating
    image_views += 1
    return flask.Response(svg,  mimetype= 'image/svg+xml', headers={'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache'})

@app.route('/lock/<hashstr>', methods=['GET'])
def lock(hashstr):
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    if hashstr not in lhosts and hashstr not in khosts:
        lhosts[hashstr] = ip
    return feeder(hashstr)

@app.route('/<hashstr>', methods=['GET'])
def feeder(hashstr):
    global updates_received 
    data = request.args.get('d')
    if not data:
        return plot(hashstr)
    key = request.args.get('k', '')
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    if key and hashstr not in khosts and hashstr not in lhosts:
        khosts[hashstr] = key
    elif hashstr in khosts and key != khosts[hashstr]: 
        abort(403)
    elif hashstr in lhosts and ip != lhosts[hashstr]: 
        abort(403)
            
    if len(data) > 1024:
        return "" # TODO: return data error code
    if not hashstr in value_cache:
        value_cache[hashstr] = ExpiringDeque(hashstr)
        value_cache[hashstr].append((data, int(time.time())))
        value_cache[hashstr].update()
    else:
        value_cache[hashstr].append((data, int(time.time())))
        value_cache[hashstr].update()
    if datastore: datastore.addData(hashstr, data)
    if not hashstr in subscriptions and not hashstr in tokenHashes: 
        # print "ERR: no subscribers, can not push", hashstr
        return ""
    
    def notify():
        global updates_pushed 
        updateHash = str(int(time.time()*1000))
        if hashstr in subscriptions: 
            updates_pushed += len(subscriptions[hashstr])
            for sub in subscriptions[hashstr][:]:
                sub.put("%s\t%s\t%s" % (hashstr, updateHash, data))
        if hashstr in tokenHashes:
            lClean = []
            for ptoken in tokenHashes[hashstr]:
                if not ptoken in tokenSubscriptions:
                    lClean.append(ptoken)
                    continue
                # TODO: clean up the tokenHashes by scheduled task
                updates_pushed += len(tokenSubscriptions[ptoken])
                for sub in tokenSubscriptions[ptoken][:]:
                    sub.put("%s\t%s\t%s" % (hashstr, updateHash, data))
            for ptoken in lClean:
                tokenHashes[hashstr].remove(ptoken)
                # print "Deleting ptoken",ptoken 
                if len(tokenHashes[hashstr]) == 0:
                    # print "Deleting tokanhash", hashstr
                    del tokenHashes[hashstr]
            
    gevent.spawn(notify)
    updates_received += 1
    return flask.Response('<svg xmlns="http://www.w3.org/2000/svg"></svg>', mimetype= 'image/svg+xml', headers={'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache'})

@app.route('/<hashstr>/stream', methods=['GET'])
def stream(hashstr):
    # ptoken = request.cookies.get('ptoken', '')
    ptoken = request.values.get("ptoken", "")
    # print "STREAM request: ptoken is ", ptoken, " for hash", hashstr
    
    if ptoken:
        if hashstr in tokenHashes: 
            # TODO: optimize here vvv
            if not ptoken in tokenHashes[hashstr]: tokenHashes[hashstr].append(ptoken)
        else:
            tokenHashes[hashstr] = [ptoken]
        #return "";
        
    def send_proc():
        q = Queue()
        if ptoken:
            if ptoken in tokenSubscriptions:
                tokenSubscriptions[ptoken].append(q)
            else:
                tokenSubscriptions[ptoken] = [q]
        if not hashstr in subscriptions:
            subscriptions[hashstr] = [q]
        else:
            subscriptions[hashstr].append(q)
        try:
            while True:
                yield "data: %s\n\n" % q.get()
        # TODO: this may actually not work, need an explicit cleanup here
        finally:
            # print "Finally! for ptoken", ptoken, "hash:", hashstr 
            if hashstr in subscriptions:
                try:
                    subscriptions[hashstr].remove(q)
                except ValueError:
                    pass
                if len(subscriptions[hashstr]) == 0:
                    # print "Subs zero", ptoken, "hash:", hashstr 
                    try:
                        del subscriptions[hashstr]
                    except KeyError:
                        pass
            if ptoken and ptoken in tokenSubscriptions:
                try:
                    tokenSubscriptions[ptoken].remove(q)
                except ValueError:
                    pass
                if len(tokenSubscriptions[ptoken]) == 0:
                    # print "Tokens zero!", ptoken, "hash:", hashstr 
                    try:
                        del tokenSubscriptions[ptoken]
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
    global server, conn, db
    print('Shutting down ...')
    transaction.commit()
    server.stop(timeout=2)
    transaction.commit()
    conn.close()
    db.close()
    if datastore: datastore.conn_close()

def dump_stats():
    try:
        fs = file("/tmp/plottico_stats","w")
        fs.write("%s\n%s\n%s\n%s\n%s\n" % (image_views, updates_received, updates_pushed, len(subscriptions), len(value_cache)))
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
        
    print "Starting on port", port
    

    app.debug = debug
    if debug: server = WSGIServer((host, port), app)
    else: server = WSGIServer((host, port), app, log=None)
    print "serving"
    server.serve_forever()
