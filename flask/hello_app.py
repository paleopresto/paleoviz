# flask imports
from flask import Flask, render_template, request, redirect, url_for
#panel and bokeh imports
from bokeh.client import pull_session
from bokeh.embed import server_session
# local imports
import viz_lib as vl


app = Flask(__name__)

# locally creates a page
@app.route('/', methods=['POST', 'GET'])
def index():
    with pull_session(url='localhost:5005') as session:
        # generate a script to load the customized session
        script = server_session(session_id=session.id, url='localhost:5005')
        #use the script in the rendered page
    return render_template('embed.html', script=script, template='Flask')
    


if __name__ == '__main__':
    hello_panel_server = vl.start_hello_server()

    # start main app server loop
    app.run(port=5000, debug=True, use_reloader=False)

    # stop the managed threads
    embed_server.stop()
    print(' - Visualization server cleanup complete. Exiting...')