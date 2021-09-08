# basic python imports
import signal
from os.path import isfile

# panel imports
from panel.pane.holoviews import HoloViews
from panel.io.server import StoppableThread
from panel.pane.base import panel

# holoviews and geoviews imports
import holoviews as hv
import geoviews as gv

# data structure and math imports
import numpy as np
import xarray as xr

# bokeh/tornado imports
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.server.server import Server
from bokeh.application.handlers.function import FunctionHandler
from bokeh.application.application import Application
from tornado.ioloop import IOLoop

from asyncio import set_event_loop, new_event_loop

#set holoviews backend to bokeh
hv.extension('bokeh')


def generate_visualization(datapath, **kwargs):
    if not isfile(datapath):
        return None

    xr_dataset = xr.open_dataset(datapath).load()
    # decide what to make by checking key dimensions
    if(len(xr_dataset.dims) > 2):
        # geospatial visualization
        geo_viz = generate_geospatial(xr_dataset)
        #print(type(pn.panel(geo_viz)))
        server_thread = pn.serve(geo_viz, **kwargs)
        print(f'Server started on port {kwargs["port"]} with dataset at {datapath}.')
        return server_thread
    elif (len(xr_dataset.dims) == 2):
        # time series
        return generate_timeseries(xr_dataset)
    else:
        # uninterpritable data error
        return None
        
        
def get_viz_type(datapath):
    if not isfile(datapath):
        return None

    xr_dataset = xr.open_dataset(datapath).load()
    # decide what to make by checking key dimensions
    dim_len = len(xr_dataset.dims)
    xr_dataset.close()
    if(dim_len > 2):
        # geospatial visualization
        return 'geo'
    elif (dim_len == 2):
        # time series
        return 'time'
    else:
        # uninterpritable data error
        return None
    

def generate_geospatial(xr_dataset):
    # fill in monte carlo coordinates
    num_coords = xr_dataset.dims['MCrun']
    mcrun_coords = []
    i = 0
    while i < num_coords:
        mcrun_coords.append(i)
        i += 1
    xr_dataset = xr_dataset.assign_coords({'MCrun': mcrun_coords})
    
    # get dims for gv
    kdims = list(xr_dataset.dims.keys())
    vdims = list(xr_dataset.data_vars.keys())

    # create gv_dataset wrapper
    gv_dataset = gv.Dataset(xr_dataset, kdims=kdims, vdims=vdims)
    
    # create visualization
    return gv_dataset.to(gv.Image, ['lon', 'lat'], dynamic=True).opts(width=600, height=360, colorbar=True, cmap='plasma') * gv.feature.coastline()
    

# takes in an xarray dataset and returns a 
def generate_timeseries(xr_dataset):
    if type(xr_dataset) is str:
        xr_dataset = xr.open_dataset(datapath).load()
    
    # Programatically assign members
    num_members = xr_dataset.dims['members']
    members = []
    i = 0
    while i < num_members:
        members.append(i)
        i += 1

    xr_dataset = xr_dataset.assign_coords({'members': members})

    kdims = list(xr_dataset.dims.keys())
    vdims = list(xr_dataset.data_vars.keys())

    # Get x and y coordinates
    x = np.array(xr_dataset['time'])
    y = np.array(xr_dataset[vdims[0]])
    
    # Make y coordinates 1D
    y = np.squeeze(y)
    y = y.flatten()
    
    # Convert times to correct year
    times = []
    
    for x in np.array(xr_dataset['time']):
        times.append(x.year)
    
    # Plot code
    p = figure(title=vdims[0].capitalize() + ' Over Time', plot_width=500, plot_height=500)
    p.xaxis.axis_label = "Time"
    p.yaxis.axis_label = vdims[0]
    p.line(times, y)
    script, div = components(p)
    return script, div
    
    
def start_server(threaded=False, io_loop=None, **kwargs):
    if threaded:
        if io_loop == None:
            loop = IOLoop()
        else:
            loop = io_loop
        server = StoppableThread(target=create_server, io_loop=loop, kwargs=kwargs)
    else:
        server = create_server(**kwargs)
    return server
    
    
    
def create_server(**kwargs):
    # create a handler for application. Should only need the one
    viz_handlers = FunctionHandler(add_viz_model)
    
    # create an application
    viz_app = Application(viz_handlers)
    
    # create server
    set_event_loop(new_event_loop())
    viz_server = Server(viz_app, **kwargs)
    
    def signal_exit():
        viz_server.io_loop.add_callback_from_signal(do_stop)
    
    def do_stop():
        viz_server.io_loop.stop()
        
    try:
        signal.signal(signal.SIGINT, signal_exit)
    except ValueError:
        pass
    
    viz_server.start()
    
    viz_server.io_loop.start()
    return viz_server
    
    
def add_viz_model(doc):
    args = doc.session_context.request.arguments
    if args.get('datapath') == None:
        viz = "Error occurred!"
        print("Error occurred!")
    else:
        datapath = str(args.get('datapath')[0].decode('UTF-8'))
        if not isfile(datapath):
            viz = "Error occurred!"
            print("Error occurred!")
        else:
            xr_dataset = xr.open_dataset(datapath).load()
            viz = generate_geospatial(xr_dataset)
    # create a panel from the holoviews DynamicMap and attach it to the document.
    panel(viz).server_doc(doc=doc)
