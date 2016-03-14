import flask, time, random

app = flask.Flask(__name__)

@app.route( '/svg' )
def svg():
    return flask.Response( file('main.svg','r').read(),  mimetype= 'image/svg+xml')

@app.route( '/stream' )
def stream():
    def read_process():
        y=0.0
        while True:
            time.sleep(0.2)
            y+=random.uniform(-0.1, 0.1)
            if y < -1: y = -1
            yield "data: %s\n\n" % y 
    return flask.Response( read_process(), mimetype= 'text/event-stream')

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, threaded=True)
