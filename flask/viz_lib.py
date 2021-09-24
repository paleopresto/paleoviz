'''
A small module to support creation of custom bokeh plots and server processes
'''


# basic python imports
import signal
from os.path import isfile
import time

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


def get_viz_type(datapath):
    '''Generates either a time series(as a tuple of string), geospatial visualization, or returns None
    
    Parameters
    ----------
    datapath : str
        The file location of the dataset to check
    Returns
    -------
        A string describing the viz type or None on error.
    '''
    if not isfile(datapath):
        return None

    xr_dataset = xr.open_dataset(datapath)
    # decide what to make by checking key dimensions
    dim_len = len(xr_dataset.dims)
    xr_dataset.close()
    if(dim_len > 3):
        # geospatial visualization
        return 'geo'
    elif (dim_len == 3):
        # time series
        return 'time'
    else:
        # uninterpritable data error
        return None
    

def generate_geospatial(datapath, **kwargs):
    '''Generates and returns a geospatial visualization as a HoloViews DynamicMap
    
    Parameters
    ----------
    datapath : str
        The file location of the dataset to use
    kwargs : dict
        additional arguments to the DynamicMap opts function (customizations)
    Returns
    -------
        A HoloViews DynamicMap containing the visualization
    '''
    xr_dataset = xr.open_dataset(datapath).load()
    
    # fill in monte carlo coordinates
    num_coords = xr_dataset.dims['MCrun']
    mcrun_coords = []
    i = 0
    while i < num_coords:
        mcrun_coords.append(i)
        i += 1
    xr_dataset = xr_dataset.assign_coords({'MCrun': mcrun_coords})
    
    # get dims for visualization
    kdims = list(xr_dataset.dims.keys())
    vdims = list(xr_dataset.data_vars.keys())

    # create gv_dataset wrapper
    gv_dataset = gv.Dataset(xr_dataset, kdims=kdims, vdims=vdims)
    
    # create visualization
    dynamicMap = gv_dataset.to(gv.Image, ['lon', 'lat'], dynamic=True)
    finalViz = dynamicMap.opts(**kwargs) * gv.feature.coastline()
    return finalViz
    

# takes in an xarray dataset and returns a 
def generate_timeseries_html(datapath, **kwargs):
    '''Generates and returns the elements necessary to embed a bokeh plot in html
    
    Parameters
    ----------
    datapath : str
        The file location of the dataset to use 
    kwargs : dict
        additional arguments to generate_timeseries
    Returns
    -------
        A tuple containing an html <script> and a target <div> to display to 
    '''
    
    plot = generate_timeseries(datapath, **kwargs)
    script, div = components(plot)
    return script, div

def generate_timeseries(datapath, **kwargs):
    '''Generates and returns a bokeh timeseries plot given a datapath
    
    Parameters
    ----------
    datapath : str
        The file location of the dataset to use 
    kwargs : dict
        additional arguments to bokeh's figure function
    Returns
    -------
        A bokeh figure containing the desired timeseries plot
    '''

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
    p = figure(title=vdims[0].capitalize() + ' Over Time', **kwargs)
    p.xaxis.axis_label = "Time"
    p.yaxis.axis_label = vdims[0]
    p.line(times, y)
    return p
    
def start_server(threaded=False, io_loop=None, **kwargs):
    '''Either returns a thread to run create_server or runs create_server with given or new io_loop
    
    Parameters
    ----------
    threaded: bool
        whether or not to run the server on a seperate thread of execution
    io_loop: IOLoop | None
        An io loop to use with the server. If None and threaded=True, create a new io loop
    kwargs : dict
        additional arguments to pass to create_server
    Returns
    -------
        A StoppableThread that is running the BokehServer
    '''
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
    '''Creates a new BokehServer object with the required handlers
    
    Parameters
    ----------
    kwargs : dict
        additional arguments to pass to bokeh Server function
    Returns
    -------
        The BokehServer that has been started
    '''
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
        viz_server.stop(False)
        viz_server.io_loop.stop()
        viz_server.io_loop.close()
        
    try:
        signal.signal(signal.SIGINT, signal_exit)
    except ValueError:
        pass
    
    viz_server.start()
    
    viz_server.io_loop.start()
    return viz_server
    
    
def add_viz_model(doc):
    '''Adds a geospatial visualization to a given bokeh Document object
    
    Parameters
    ----------
    doc: Document
        A bokeh document to add a new geospatial visualization model to.
    Returns
    -------
    None
    '''
    args = doc.session_context.request.arguments
    if args.get('datapath') == None:
        viz = "Error occurred!"
        print("Error occurred! Datapath not given!")
    else:
        datapath = str(args.get('datapath')[0].decode('UTF-8'))
        if not isfile(datapath):
            viz = "Error occurred!"
            print(f"Error occurred! File at {datapath} not found!")
        else:
            viz = generate_geospatial(datapath, width=600, height=360, colorbar=True, cmap='plasma')
    # create a panel from the holoviews DynamicMap and attach it to the document.
    panel(viz).server_doc(doc=doc)

