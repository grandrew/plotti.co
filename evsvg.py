import flask, time, random

app = flask.Flask(__name__)

@app.route( '/svg' )
def svg():
    return flask.Response( file('main.svg','r').read(),  mimetype= 'image/svg+xml')

@app.route( '/stream' )
def stream():
    def read_process():
        y1=0.0
        y2=0.0
        y3=0.0
        while True:
            time.sleep(0.2)
            y1+=random.uniform(-0.1, 0.1)
            y2+=random.uniform(-0.1, 0.1)
            y3+=random.uniform(-0.1, 0.1)
            if y1 < 0: y1 = 0
            if y2 < 0: y2 = 0
            if y3 < 0: y3 = 0
            yield "data: %s,%s,%s\n\n" % (y1,y2,y3)
    return flask.Response( read_process(), mimetype= 'text/event-stream')

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, threaded=True)
