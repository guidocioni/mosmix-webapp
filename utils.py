import os
import numpy as np
import plotly.graph_objs as go
import dash_leaflet as dl
from PIL import Image

apiURL = "https://api.mapbox.com/directions/v5/mapbox"
apiKey = os.environ['MAPBOX_KEY']

# mapURL = 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png'
mapURL = 'https://api.mapbox.com/styles/v1/mapbox/dark-v10/tiles/{z}/{x}/{y}{r}?access_token=' + apiKey
attribution = '© <a href="https://www.mapbox.com/feedback/">Mapbox</a> © <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'

folder_glyph = 'yrno_png/'
WMO_GLYPH_LOOKUP_PNG = {
    '0': '01',
    '1': '02',
    '2': '02',
    '3': '04',
    '45': '15',
    '51': '40',
    '55': '41',
    '57': '43',
    '63': '09',
    '66': '12',
    '71': '49',
    '75': '45',
    '80': '06',
    '82': '11',
    '86': '34',
    '96': '32',
    '48': '15',
    '53': '05',
    '56': '07',
    '61': '05',
    '65': '10',
    '67': '43',
    '73': '49',
    '77': '48',
    '81': '11',
    '85': '33',
    '95': '22'
}


def get_weather_icons(ww, time):
    """
    Get the path to a png given the weather representation 
    """
    weather = []
    for w in ww.values:
        if str(int(w)) in WMO_GLYPH_LOOKUP_PNG:
            weather.append(WMO_GLYPH_LOOKUP_PNG[str(int(w))])
        else:
            weather.append('empty')
    weather_icons = []
    for date, weath in zip(time, weather):
        if date.hour >= 6 and date.hour <= 18:
            add_string = 'd'
        elif date.hour >= 0 and date.hour < 6:
            add_string = 'n'
        elif date.hour > 18 and date.hour < 24:
            add_string = 'n'

        pngfile = folder_glyph+'%s.png' % (weath+add_string)
        if os.path.isfile(pngfile):
            weather_icons.append({'time': date, 'icon': pngfile})
        else:
            pngfile = folder_glyph+'%s.png' % weath
            weather_icons.append({'time': date, 'icon': pngfile})

    return(weather_icons)


def wind_components(speed, wdir):
    '''Get wind components from speed and direction.'''

    wdir = np.deg2rad(wdir)

    u = speed * np.sin(wdir)
    v = speed * np.cos(wdir)

    return u, v


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
        lon_zoom = np.interp(width, lon_zoom_range, range(20, 0, -1))
        lat_zoom = np.interp(height, lon_zoom_range, range(20, 0, -1))
        zoom = round(min(lon_zoom, lat_zoom), 2)
    else:
        raise NotImplementedError(
            'projection is not implemented'
        )

    return zoom, center


def make_fig_time(df):
    if df is not None:
        xaxis = df.loc[df.parameter.isin(['temperature_air_200']), 'date']

        plot_traces = []

        if ('sunshine_duration' in df.parameter.unique()):
            trace_sun = go.Scatter(name='Sun. dur.',
                                   x=xaxis,
                                   y=df.loc[df.parameter.isin(
                                       ['sunshine_duration']), 'value'],
                                   mode='lines',
                                   showlegend=True,
                                   line=dict(
                                       color='rgba(246, 207, 113, 0.1)', width=0),
                                   yaxis='y3',
                                   fill='tozeroy')

            plot_traces.append(trace_sun)

        if ('temperature_air_200' in df.parameter.unique()):
            trace_temp = go.Scatter(name='Temp',
                                    x=xaxis,
                                    y=df.loc[df.parameter.isin(
                                        ['temperature_air_200']), 'value'],
                                    mode="lines",
                                    showlegend=True,
                                    line=dict(color='rgb(179, 179, 179)', width=3))

            plot_traces.append(trace_temp)

        if ('temperature_dew_point_200' in df.parameter.unique()):
            trace_dewp = go.Scatter(name='Dewp',
                                    x=xaxis,
                                    y=df.loc[df.parameter.isin(
                                        ['temperature_dew_point_200']), 'value'],
                                    mode="lines",
                                    showlegend=True,
                                    line=dict(color='rgba(179, 179, 179, 0.5)', width=3))

            plot_traces.append(trace_dewp)

        if ('error_absolute_temperature_air_200' in df.parameter.unique()):
            tperr = df.loc[df.parameter.isin(['temperature_air_200']), 'value'].values + \
                df.loc[df.parameter.isin(
                    ['error_absolute_temperature_air_200']), 'value'].values
            tmerr = df.loc[df.parameter.isin(['temperature_air_200']), 'value'].values - \
                df.loc[df.parameter.isin(
                    ['error_absolute_temperature_air_200']), 'value'].values

            trace_temp_err = go.Scatter(name='uncertainty',
                                        x=xaxis,
                                        y=tperr,
                                        mode="lines",
                                        showlegend=False,
                                        line=dict(color='rgb(179, 179, 179)', width=0))

            trace_temp_err2 = go.Scatter(name='uncertainty',
                                         x=xaxis,
                                         y=tmerr,
                                         mode="lines",
                                         showlegend=False,
                                         line=dict(
                                             color='rgb(179, 179, 179)', width=0),
                                         fill='tonexty')

            plot_traces.append(trace_temp_err)
            plot_traces.append(trace_temp_err2)

        if ('temperature_air_min_200' in df.parameter.unique()):
            min_temp = df.loc[df.parameter.isin(
                ['temperature_air_min_200'])].dropna()
            max_temp = df.loc[df.parameter.isin(
                ['temperature_air_max_200'])].dropna()

            trace_temp_min = go.Scatter(name='min',
                                        x=min_temp['date'],
                                        y=min_temp['value'],
                                        mode="markers",
                                        showlegend=False,
                                        line=dict(color='rgb(102, 197, 204)'))

            plot_traces.append(trace_temp_min)

            trace_temp_max = go.Scatter(name='max',
                                        x=max_temp['date'],
                                        y=max_temp['value'],
                                        mode="markers",
                                        showlegend=False,
                                        line=dict(color='rgb(248, 156, 116)'))

            plot_traces.append(trace_temp_max)

        if ('precipitation_consist_last_1h' in df.parameter.unique()):
            trace_prec = go.Bar(name='Rain',
                                x=xaxis,
                                y=df.loc[df.parameter.isin(
                                    ['precipitation_consist_last_1h']), 'value'],
                                showlegend=True,
                                marker_color='rgb(102, 197, 204)',
                                yaxis="y2")

            plot_traces.append(trace_prec)

        if ('precipitation_snow_equiv_last_1h' in df.parameter.unique()):
            trace_snow = go.Bar(name='Snow',
                                x=xaxis,
                                y=df.loc[df.parameter.isin(
                                    ['precipitation_snow_equiv_last_1h']), 'value'],
                                showlegend=True,
                                marker_color='rgb(254, 136, 177)',
                                yaxis="y2")

            plot_traces.append(trace_snow)

        fig = go.Figure(data=plot_traces)

        if ('weather_significant' in df.parameter.unique()):
            weather = df.loc[df.parameter.isin(['weather_significant'])].dropna(
            ).set_index('date').resample('8H').nearest().reset_index()
            icons = get_weather_icons(weather.value, weather.date)

            for icon in icons:
                fig.add_layout_image(dict(
                    source=Image.open(icon['icon']),
                    xref='x',
                    x=icon['time'],
                    yref='paper',
                    y=0.92,
                    sizex=2*24*10*60*1000, sizey=1.0,
                    xanchor="right", yanchor="bottom"
                ))

        fig.update_layout(
            legend_orientation="h",
            xaxis=dict(title='', range=[xaxis.min(),
                       xaxis.max()], showgrid=True),
            yaxis=dict(title='Temp (°C)', showgrid=False, zeroline=True),
            yaxis3=dict(title='', showgrid=False, overlaying="y",
                        range=[3600, 0], showticklabels=False),
            yaxis2=dict(title='P [mm/h]', overlaying="y", side="right", range=[0,
                                                                               df.loc[df.parameter.isin(['precipitation_consist_last_1h']), 'value'].max() * 3.], showgrid=False),
            height=390,
            margin={"r": 0.1, "t": 0.1, "l": 0.1, "b": 0.1},
            template='plotly_white',
            barmode='overlay'
        )
    else:
        fig = make_empty_figure()

    return fig


def make_fig_wind(df):
    if df is not None:
        xaxis = df.loc[df.parameter.isin(['wind_speed']), 'date']

        plot_traces = []

        trace_wind = go.Scatter(name='Wind speed',
                                x=xaxis,
                                y=df.loc[df.parameter.isin(
                                    ['wind_speed']), 'value'],
                                mode="lines",
                                showlegend=True,
                                line=dict(color='rgb(179, 179, 179)', width=3))

        plot_traces.append(trace_wind)

        # u, v = wind_components(df.loc[df.parameter =='wind_speed', 'value'].values,
        #         df.loc[df.parameter =='WIND_DIRECTION', 'value'].values)

        # norm = np.sqrt(u**2 + v**2)
        # u, v = u / norm, v / norm

        # # we need to use the polar plot for the direction

        trace_mslp = go.Scatter(name='Pressure',
                                x=xaxis,
                                y=df.loc[df.parameter.isin(
                                    ['pressure_air_surface_reduced']), 'value'],
                                mode="lines",
                                showlegend=True,
                                line=dict(color='rgb(220, 176, 242)', width=3),
                                yaxis="y2")

        plot_traces.append(trace_mslp)

        if 'error_absolute_wind_speed' in df.parameter.unique():
            tperr = df.loc[df.parameter.isin(['wind_speed']), 'value'].values + \
                df.loc[df.parameter.isin(
                    ['error_absolute_wind_speed']), 'value'].values
            tmerr = df.loc[df.parameter.isin(['wind_speed']), 'value'].values - \
                df.loc[df.parameter.isin(
                    ['error_absolute_wind_speed']), 'value'].values

            trace_wind_err = go.Scatter(name='uncertainty',
                                        x=xaxis,
                                        y=tperr,
                                        mode="lines",
                                        showlegend=False,
                                        line=dict(color='rgb(179, 179, 179)', width=0))

            trace_wind_err2 = go.Scatter(name='uncertainty',
                                         x=xaxis,
                                         y=tmerr,
                                         mode="lines",
                                         showlegend=False,
                                         line=dict(
                                             color='rgb(179, 179, 179)', width=0),
                                         fill='tonexty')

            plot_traces.append(trace_wind_err)
            plot_traces.append(trace_wind_err2)

        max_wind = df.loc[df.parameter.isin(
            ['wind_gust_max_last_3h'])].dropna()

        trace_wind_max = go.Scatter(name='Gusts',
                                    x=max_wind['date'],
                                    y=max_wind['value'],
                                    mode="markers",
                                    showlegend=True,
                                    line=dict(color='rgb(248, 156, 116)'))

        plot_traces.append(trace_wind_max)

        fig = go.Figure(data=plot_traces)

        fig.add_trace(trace_mslp)

        fig.update_layout(
            legend_orientation="h",
            xaxis=dict(title='', range=[xaxis.min(), xaxis.max()]),
            yaxis=dict(title='Speed (km/h)', rangemode='tozero'),
            yaxis2=dict(title='Pressure (hPa)', overlaying="y", side="right"),
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


def make_fig_prec(df):
    if df is not None:
        xaxis = df.loc[df.parameter.isin(
            ['probability_precipitation_liquid_last_1h'])].dropna()['date']

        plot_traces = []

        if ('probability_precipitation_liquid_last_1h' in df.parameter.unique()):
            trace_prec = go.Bar(name='Rain',
                                x=xaxis,
                                y=df.loc[df.parameter.isin(
                                    ['probability_precipitation_liquid_last_1h']), 'value'].dropna(),
                                showlegend=True,
                                marker_color='rgb(102, 197, 204)')

            plot_traces.append(trace_prec)

        if ('probability_precipitation_solid_last_1h' in df.parameter.unique()):
            trace_snow = go.Bar(name='Snow',
                                x=xaxis,
                                y=df.loc[df.parameter.isin(
                                    ['probability_precipitation_solid_last_1h']), 'value'].dropna(),
                                showlegend=True,
                                marker_color='rgb(254, 136, 177)')

            plot_traces.append(trace_snow)

        if ('probability_precipitation_freezing_last_1h' in df.parameter.unique()):
            trace_ice = go.Bar(name='Frzr',
                               x=xaxis,
                               y=df.loc[df.parameter.isin(
                                   ['probability_precipitation_freezing_last_1h']), 'value'].dropna(),
                               showlegend=True,
                               marker_color='rgb(180, 151, 231)')

            plot_traces.append(trace_ice)

        fig = go.Figure(data=plot_traces)

        fig.update_layout(
            legend_orientation="h",
            xaxis=dict(title='', range=[xaxis.min(),
                       xaxis.max()], showgrid=True),
            yaxis=dict(title='Prob [%]', rangemode='tozero'),
            height=310,
            margin={"r": 0.1, "t": 0.1, "l": 0.1, "b": 0.1},
            template='plotly_white',
            barmode='stack'
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
        dl.TileLayer(url=mapURL, attribution=attribution,
                     tileSize=512, zoomOffset=-1),
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
        dl.LocateControl(options={'locateOptions': {
                         'enableHighAccuracy': True}}),
    ],
        center=[lat_center, lon_center], zoom=zoom,
        style={'width': '100%', 'height': '45vh',
               'margin': "auto", "display": "block"},
        id='map')]

    return fig


def generate_map_plot(data):
    if data is not None:
        start_point = data['STATION_NAME'].item()
        point = [data['LAT'].item(), data['LON'].item()]

        fig = [dl.Map([
            dl.TileLayer(url=mapURL, attribution=attribution,
                         tileSize=512, zoomOffset=-1),
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
            dl.LocateControl(options={'locateOptions': {
                             'enableHighAccuracy': True}}),
            dl.Marker(position=point, children=dl.Tooltip(start_point)),
        ],
            center=point,
            zoom=4,
            style={'width': '100%', 'height': '35vh',
                   'margin': "auto", "display": "block"},
            id='map')]
    else:  # make an empty map
        fig = make_empty_map()

    return fig
