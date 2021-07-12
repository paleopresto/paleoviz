# flask imports
from flask import Flask, render_template, request, redirect, url_for
#panel and bokeh imports
import panel as pn
from bokeh.client import pull_session
from bokeh.embed import server_session
# local imports
import viz_lib as vl
#standard imports
from os import listdir
import json


app = Flask(__name__)

try:
    with open('server_config.json', 'r') as config_file:
        config_dict = json.load(config_file)
except OSError as e:
    # use defaults
    config_dict = {'embed_port_num':5005, 'flask_port_num':5000, 'embed_host':'localhost', 'flask_host':'localhost'}
    with open('server_config.json', 'w') as config_file:
        json.dump(config_dict, config_file)

embed_port_num = config_dict['embed_port_num']
flask_port_num = config_dict['flask_port_num']

embed_host = config_dict['embed_host']
flask_host = config_dict['flask_host']

embed_url = 'http://' + embed_host + ':' + str(embed_port_num)
flask_url = 'http://' + flask_host + ':' + str(flask_port_num)


# locally creates a page
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        selection = request.form['reconstruction']
        return redirect(url_for('viz', filename=selection))
    else:
    	files = listdir('data/')
    	return render_template('data_form.html', files=files)

@app.route('/viz/<filename>', methods=['POST', 'GET'])
def viz(filename):

    # get user choice for dataset
    datapath = 'data/' + filename
    viz_type = vl.get_viz_type(datapath)

    if viz_type == 'geo':
        print(datapath)
        with pull_session(url=embed_url, arguments=dict(datapath=datapath)) as session:
            # generate a script to load the customized session
            script = server_session(session_id=session.id, url=embed_url)
            #use the script in the rendered page
        return render_template('embed.html', script=script, template='Flask')
    elif viz_type == 'time':
        timeseries_tuple = vl.generate_timeseries(datapath)
        return render_template('bokeh.html', script=timeseries_tuple[0], div=timeseries_tuple[1], template='Flask')
    else:
        return render_template('error.html')


if __name__ == '__main__':
    
    
    print(f" - Configuration: ")
    print(f"  - Flask server port: {flask_port_num}\n  - Flask hostname: {flask_host}")
    print(f"  - Embedded server port: {embed_port_num}\n  - Embedded hostname: {embed_host}")

    
    print(f' - Starting embedded server on port {embed_port_num}...')
    embed_server = vl.start_server(threaded=True, allow_websocket_origin=[flask_url], show=False,port=embed_port_num)
    
    
    # start main app server loop
    app.run(host=flask_host, port=flask_port_num, debug=True, use_reloader=False)
    
    # stop the managed threads
    bokeh_server.stop()
    print('Visualization server cleanup complete. Exiting...')
