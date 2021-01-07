import pandas as pd
from datetime import timedelta
import re
import requests
import os
import numpy as np
import json
import plotly.graph_objs as go
import plotly.express as px
import dash_leaflet as dl
import dash_html_components as html
from wetterdienst.dwd.forecasts.stations import metadata_for_forecasts
from wetterdienst.dwd.forecasts import DWDMosmixData, DWDMosmixType


apiURL = "https://api.mapbox.com/directions/v5/mapbox"
apiKey = os.environ['MAPBOX_KEY']

# mapURL = 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png'
mapURL = 'https://api.mapbox.com/styles/v1/mapbox/dark-v10/tiles/{z}/{x}/{y}{r}?access_token=' + apiKey
attribution = '© <a href="https://www.mapbox.com/feedback/">Mapbox</a> © <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'


def convert_timezone(dt_from, from_tz='utc', to_tz='Europe/Berlin'):
    """
    Convert between two timezones. dt_from needs to be a Timestamp 
    object, don't know if it works otherwise.
    """
    dt_to = dt_from.tz_localize(from_tz).tz_convert(to_tz)
    # remove again the timezone information
    return dt_to.tz_localize(None)


def strfdelta(tdelta, fmt):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def zoom_center(lons: tuple = None, lats: tuple = None, lonlats: tuple = None,
        format: str = 'lonlat', projection: str = 'mercator',
        width_to_height: float = 2.0) -> (float, dict):
    """Finds optimal zoom and centering for a plotly mapbox.
    Must be passed (lons & lats) or lonlats.
    Temporary solution awaiting official implementation, see:
    https://github.com/plotly/plotly.js/issues/3434
    
    Parameters
    --------
    lons: tuple, optional, longitude component of each location
    lats: tuple, optional, latitude component of each location
    lonlats: tuple, optional, gps locations
    format: str, specifying the order of longitud and latitude dimensions,
        expected values: 'lonlat' or 'latlon', only used if passed lonlats
    projection: str, only accepting 'mercator' at the moment,
        raises `NotImplementedError` if other is passed
    width_to_height: float, expected ratio of final graph's with to height,
        used to select the constrained axis.
    
    Returns
    --------
    zoom: float, from 1 to 20
    center: dict, gps position with 'lon' and 'lat' keys

    >>> print(zoom_center((-109.031387, -103.385460),
    ...     (25.587101, 31.784620)))
    (5.75, {'lon': -106.208423, 'lat': 28.685861})
    
    See https://stackoverflow.com/questions/63787612/plotly-automatic-zooming-for-mapbox-maps
    """
    if lons is None and lats is None:
        if isinstance(lonlats, tuple):
            lons, lats = zip(*lonlats)
        else:
            raise ValueError(
                'Must pass lons & lats or lonlats'
            )

    maxlon, minlon = max(lons), min(lons)
    maxlat, minlat = max(lats), min(lats)
    center = {
        'lon': round((maxlon + minlon) / 2, 6),
        'lat': round((maxlat + minlat) / 2, 6)
    }

    # longitudinal range by zoom level (20 to 1)
    # in degrees, if centered at equator
    lon_zoom_range = np.array([
        0.0007, 0.0014, 0.003, 0.006, 0.012, 0.024, 0.048, 0.096,
        0.192, 0.3712, 0.768, 1.536, 3.072, 6.144, 11.8784, 23.7568,
        47.5136, 98.304, 190.0544, 360.0
    ])

    if projection == 'mercator':
        margin = 1.2
        height = (maxlat - minlat) * margin * width_to_height
        width = (maxlon - minlon) * margin
        lon_zoom = np.interp(width , lon_zoom_range, range(20, 0, -1))
        lat_zoom = np.interp(height, lon_zoom_range, range(20, 0, -1))
        zoom = round(min(lon_zoom, lat_zoom), 2)
    else:
        raise NotImplementedError(
            'projection is not implemented'
        )

    return zoom, center


def make_fig_time(df):
    if df is not None:
        xaxis = df.loc[df.PARAMETER.isin(['TEMPERATURE_AIR_200']), 'DATE']

        trace_temp = go.Scatter(name='2m Temp',
                         x=xaxis,
                         y=df.loc[df.PARAMETER.isin(['TEMPERATURE_AIR_200']), 'VALUE'],
                         mode="lines",
                         showlegend=True,
                         line=dict(color='rgb(179, 179, 179)', width=3))

        tperr = df.loc[df.PARAMETER.isin(['TEMPERATURE_AIR_200']), 'VALUE'].values+ \
                df.loc[df.PARAMETER.isin(['ERROR_ABSOLUTE_TEMPERATURE_AIR_200']), 'VALUE'].values
        tmerr = df.loc[df.PARAMETER.isin(['TEMPERATURE_AIR_200']), 'VALUE'].values- \
                df.loc[df.PARAMETER.isin(['ERROR_ABSOLUTE_TEMPERATURE_AIR_200']), 'VALUE'].values

        trace_temp_err = go.Scatter(
                         x=xaxis,
                         y=tperr,
                         mode="lines",
                         showlegend=False,
                         line=dict(color='rgb(179, 179, 179)', width=0))

        trace_temp_err2 = go.Scatter(
                         x=xaxis,
                         y=tmerr,
                         mode="lines",
                         showlegend=False,
                         line=dict(color='rgb(179, 179, 179)', width=0),
                         fill='tonexty')

        min_temp = df.loc[df.PARAMETER.isin(['TEMPERATURE_AIR_MIN_200'])].dropna()
        max_temp = df.loc[df.PARAMETER.isin(['TEMPERATURE_AIR_MAX_200'])].dropna()

        trace_temp_min= go.Scatter(name='min',
                         x=min_temp['DATE'],
                         y=min_temp['VALUE'],
                         mode="markers",
                         showlegend=False,
                         line=dict(color='rgb(102, 197, 204)'))

        trace_temp_max= go.Scatter(name='max',
                         x=max_temp['DATE'],
                         y=max_temp['VALUE'],
                         mode="markers",
                         showlegend=False,
                         line=dict(color='rgb(248, 156, 116)'))


        # trace_log_p1sigma = go.Scatter(
        #   x=df['date'],
        #   showlegend=False,
        #   y=df[variable + '_prediction_upper'],
        #   mode="lines",
        # line=dict(color=color, width=0))

        # trace_log_m1sigma = go.Scatter(
        #   x=df['date'],
        #   showlegend=False,
        #   y=df[variable + '_prediction_lower'],
        #   mode="lines",
        #   line=dict(color=color, width=0),
        #   fill='tonexty')

        plot_traces = [trace_temp, trace_temp_err, trace_temp_err2, trace_temp_min, trace_temp_max]

        fig = go.Figure(data=plot_traces)

        fig.update_layout(
            legend_orientation="h",
            xaxis=dict(title='', rangemode = 'tozero'),
            yaxis=dict(title=''),
            # legend=dict(
            #       title=dict(text='leave at '),
            #       font=dict(size=10)),
            height=390,
            margin={"r": 0.1, "t": 0.1, "l": 0.1, "b": 0.1},
            template='plotly_white',
        )
    else:
        fig = make_empty_figure()

    return fig


def make_empty_figure(text="No data (yet 😃)"):
    '''Initialize an empty figure with style and a centered text'''
    fig = go.Figure()

    fig.add_annotation(x=2.5, y=1.5,
                       text=text,
                       showarrow=False,
                       font=dict(size=30))

    fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
    )

    fig.update_layout(
        height=390,
        margin={"r": 0.1, "t": 0.1, "l": 0.1, "b": 0.1},
        template='plotly_white',
    )

    return fig


def make_empty_map(lat_center=51.326863, lon_center=10.354922, zoom=5):
    fig = [dl.Map([
                dl.TileLayer(url=mapURL, attribution=attribution, tileSize=512, zoomOffset=-1),
                dl.LayerGroup(id="layer"),
                dl.WMSTileLayer(url="https://maps.dwd.de/geoserver/ows?",
                                                layers="dwd:SAT_WELT_KOMPOSIT", 
                                                format="image/png", 
                                                transparent=True, opacity=0.7,
                                                version='1.3.0',
                                                detectRetina=True),
                dl.WMSTileLayer(url="https://maps.dwd.de/geoserver/ows?",
                                                layers="dwd:SAT_EU_RGB", 
                                                format="image/png", 
                                                transparent=True, opacity=0.7,
                                                version='1.3.0',
                                                detectRetina=True),
                dl.LocateControl(options={'locateOptions': {'enableHighAccuracy': True}}),
                    ],
               center=[lat_center, lon_center], zoom=zoom,
               style={'width': '100%', 'height': '45vh', 'margin': "auto", "display": "block"},
               id='map')]

    return fig


def generate_map_plot(data):
    if data is not None:
        start_point = data['STATION_NAME'].item()
        point = [data['LAT'].item(), data['LON'].item()]

        fig = [dl.Map([
                dl.TileLayer(url=mapURL, attribution=attribution, tileSize=512, zoomOffset=-1),
                dl.LayerGroup(id="layer"),
                dl.WMSTileLayer(url="https://maps.dwd.de/geoserver/ows?",
                                                layers="dwd:SAT_WELT_KOMPOSIT", 
                                                format="image/png", 
                                                transparent=True, opacity=0.7,
                                                version='1.3.0',
                                                detectRetina=True),
                dl.WMSTileLayer(url="https://maps.dwd.de/geoserver/ows?",
                                                layers="dwd:SAT_EU_RGB", 
                                                format="image/png", 
                                                transparent=True, opacity=0.7,
                                                version='1.3.0',
                                                detectRetina=True),
                dl.LocateControl(options={'locateOptions': {'enableHighAccuracy': True}}),
                dl.Marker(position=point, children=dl.Tooltip(start_point)),
                    ],
               center=point,
               zoom=4,
               style={'width': '100%', 'height': '45vh', 'margin': "auto", "display": "block"},
               id='map')]
    else:# make an empty map
        fig = make_empty_map()

    return fig