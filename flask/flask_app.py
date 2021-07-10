# flask imports
from flask import Flask, render_template, request
#panel and bokeh imports
import panel as pn
from bokeh.client import pull_session
from bokeh.embed import server_session
# local imports
import viz_lib as vl
#standard imports
from os import listdir

app = Flask(__name__)

# locally creates a page
@app.route('/', methods=['POST', 'GET'])
def index():
    files = listdir('../../data/')
    return render_template('data_form.html', files=files)

@app.route('/viz', methods=['POST', 'GET'])
def viz():

    # get user choice for dataset 
    selection = request.form['reconstruction']
    datapath = '../../data/' + selection
    
    viz_type = vl.get_viz_type(datapath)
    
    if viz_type == 'geo':
        print(datapath)
        with pull_session(url='http://localhost:' + str(5005), arguments=dict(datapath=datapath)) as session:
            # generate a script to load the customized session
            script = server_session(session_id=session.id, url='http://localhost:' + str(5005))
            #use the script in the rendered page
        return render_template('embed.html', script=script, template='Flask')
    elif viz_type == 'time':
        timeseries_tuple = vl.generate_timeseries(datapath)
        return render_template('bokeh.html', script=timeseries_tuple[0], div=timeseries_tuple[1], template='Flask')
    else:
        return render_template('error.html')


if __name__ == '__main__':
    
    print('Starting embedded server...')
    bokeh_server = vl.start_server(threaded=True, allow_websocket_origin=["localhost:5000"], show=False,port=5005)
    
    
    # start main app server loop
    app.run(host='localhost', port=5000, debug=True, use_reloader=False)
    
    # stop the managed threads
    bokeh_server.stop()
    print('Visualization server cleanup complete. Exiting...')
    
