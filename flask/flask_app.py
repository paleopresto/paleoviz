# flask imports
from flask import Flask, render_template, request, redirect, url_for
#panel and bokeh imports
import panel as pn
from bokeh.client import pull_session
from bokeh.embed import server_session
# local imports
import viz_lib as vl
#standard imports
import sys
from os import listdir
import json

app = Flask(__name__)

####################################
## Global configuration variables ##
####################################
# filepath to look for a config file at
config_filename = None;
# bokeh server config 
bokeh_port_num = None
bokeh_host = None
bokeh_protocol = None
bokeh_url = None

flask_port_num = None
flask_host = None
flask_protocol = None
flask_url = None

data_dir = None

# locally creates a page
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        selection = request.form['reconstruction']
        return redirect(url_for('viz', filename=selection))
    else:
    	files = listdir(data_dir)
    	return render_template('data_form.html', files=files)

@app.route('/viz/<filename>', methods=['POST', 'GET'])
def viz(filename):

    # get user choice for dataset
    datapath = data_dir + filename
    viz_type = vl.get_viz_type(datapath)

    print(f'  - Viz type requested: {viz_type}')

    if viz_type == 'geo':
        with pull_session(url=bokeh_url, arguments=dict(datapath=datapath)) as session:
            # generate a script to load the customized session
            script = server_session(session_id=session.id, url=bokeh_url)
            #use the script in the rendered page
        return render_template('embed.html', script=script, template='Flask')
    elif viz_type == 'time':
        timeseries_tuple = vl.generate_timeseries_html(datapath, plot_width=500, plot_height=500)
        return render_template('bokeh.html', script=timeseries_tuple[0], div=timeseries_tuple[1], template='Flask')
    else:
        return render_template('error.html')


if __name__ == '__main__':

    if len(sys.argv) > 1:
        print(f'- Using provided config file: {sys.argv[1]}')
        config_filename = sys.argv[1]
    else:
        print('- No config file provided. Using default: server_config.json')
        config_filename = 'server_config.json'
    # configuration
    try:
        with open(config_filename, 'r') as config_file:
            config_dict = json.load(config_file)
    except OSError as ose:
        print('Error occurred while attempting to open config file. Using defaults...')
        # use defaults
        config_dict = {'bokeh_port_num':5005, 'flask_port_num':5000, 'bokeh_host':'localhost', 'flask_host':'localhost'}
        with open('server_config.json', 'w') as config_file:
            json.dump(config_dict, config_file)

    bokeh_port_num = config_dict['bokeh_port_num']
    flask_port_num = config_dict['flask_port_num']

    bokeh_protocol = config_dict['bokeh_protocol']
    flask_protocol = config_dict['flask_protocol']
    
    bokeh_host = config_dict['bokeh_host']
    flask_host = config_dict['flask_host']

    data_dir = config_dict.get("data_dir", "data/")

    bokeh_url = bokeh_protocol + '://' + bokeh_host + ':' + str(bokeh_port_num)
    flask_url = flask_protocol + '://' + flask_host + ':' + str(flask_port_num)


    print(f" - Configuration: ")
    print(f"  - Flask server port: {flask_port_num}\n  - Flask hostname: {flask_host}\n  - Flask protocol: {flask_protocol}")
    print(f"  - Bokeh server port: {bokeh_port_num}\n  - Bokeh hostname: {bokeh_host}\n  - Bokeh protocol: {bokeh_protocol}")
    print(f' - Starting embedded bokeh server on port {bokeh_port_num}...')
    bokeh_server = vl.start_server(threaded=True, allow_websocket_origin=[flask_url], show=False, port=bokeh_port_num)
    bokeh_server.start()
    if bokeh_server.is_alive():
        print(' - Bokeh server created successfully!')
    else:
        print('Bokeh server encountered an error! Exiting...')
        exit()
    print(type(bokeh_server.io_loop))
    # start main app server loop
    app.run(host=flask_host, port=flask_port_num, debug=True, use_reloader=False)
    
    # stop the managed threads
    bokeh_server.stop()
    
    print(' - Visualization server cleanup complete. Exiting...')
