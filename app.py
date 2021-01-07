import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import utils
from dash.dependencies import Input, Output, State
import json
import pandas as pd
from flask_caching import Cache
from flask import request
import dash_leaflet as dl



app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP,
                'https://fonts.googleapis.com/css?family=Open+Sans:300,400,700'],
                url_base_pathname='/mosmix/',
                meta_tags=[{'name': 'viewport', 
                            'content': 'width=device-width, initial-scale=1'}])

server = app.server

cache = Cache(server, config={'CACHE_TYPE': 'filesystem', 
                              'CACHE_DIR': '/tmp'})


controls = dbc.Card(
    [
        dbc.InputGroup(
            [
                dbc.InputGroupAddon("query", addon_type="prepend"),
                dbc.Input(placeholder="type address or get current location on map", id='from_address', 
                          type='text', autoComplete=True),
            ],
            className="mb-2",
        ),
        dbc.Button("Search", id="search-button", className=["mr-2", "mb-2"]),
        dbc.InputGroup(
            [
                dbc.InputGroupAddon("location", addon_type="prepend"),
                dbc.Select(
                    id="locations",
                    options=[],
                    value=[],
                ),
            ],
            className="mb-2",
        ),
        dbc.Button("Generate", id="generate-button", className="mr-2"),
    ],
    body=True, className="mb-2"
)

map_card = dbc.Card(
    [
        html.Div(id='map-div')
    ],
   className="mb-2"
)

fig_card = dbc.Card(
    [
        # dbc.Checklist(
        #     options=[
        #         {"label": "More details", "value": "time_series"},
        #     ],
        #     value=[],
        #     id="switches-input",
        #     switch=True,
        # ),
        dcc.Graph(id='time-plot')
    ],
    className="mb-2"
)


help_card =  dbc.Card (  [
        dbc.CardBody(
            [
                html.H4("Help", className="card-title"),
                # html.P(
                #     ["Enter the start and end point of your journey and press on generate. "
                #     "After a few seconds the graph will show precipitation forecast on your journey for different start times. You can then decide when to leave. "
                #     "For details see ", html.A('here', href='https://github.com/guidocioni/no-more-wet-rides-new')],
                #     className="card-text",
                # ),
            ]
        ),
    ],className="mb-1" )


app.layout = dbc.Container(
    [
        html.H1("Mosmix webapp"),
        # html.H6('A simple webapp to save your bike rides from the crappy german weather'),
        html.Hr(),
        # dbc.Alert("Since the radar only covers Germany and neighbouring countries the app will fail if you enter an address outside of this area", 
        #     color="warning",
        #     dismissable=True,
        #     duration=5000),
        # dbc.Alert("Your ride duration exceeds the radar forecast horizon. Results will only be partial! Click on \"more details\" in the plot to show the used data.",
        #     dismissable=True,
        #     color="warning",
        #     is_open=False,
        #     id='long-ride-alert'),
        dbc.Row(
            [
                dbc.Col([
                        dbc.Row(
                            [
                                dbc.Col(controls),
                            ],
                        ),
                        dbc.Row(
                            [
                                dbc.Col(map_card),
                            ],
                        ),
                        ], sm=12, md=12, lg=4, align='center'),
                dbc.Col(
                    [
                    dbc.Spinner(fig_card),
                    help_card
                    ],
                 sm=12, md=12, lg=7, align='center'),
            ], justify="center",
        ),

    # html.Div(id='intermediate-value', style={'display': 'none'}),
    # html.Div(id='radar-data-2', style={'display': 'none'})
    ],
    fluid=True,
)


# generate map plot at loading AND when the location is updated
@app.callback(
    [Output("map-div", "children")],
    [Input("generate-button", "n_clicks")],
    [State("locations", "value")]
)
def create_coords_and_map(n_clicks, from_address):
    if n_clicks is None:
        return utils.generate_map_plot(None)
    else:
        if from_address is not None:
            mosmix_stations = get_stations()
            if 'value' in from_address:
                sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address['value']]
            else:
                sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address]

            fig = utils.generate_map_plot(sel_station)

            return fig
        else:
            return utils.generate_map_plot(None)


@app.callback(
    Output("time-plot", "figure"),
    [Input("generate-button", "n_clicks")],
    [State("locations", "value")]
)
def func(n_clicks, from_address):
    if n_clicks is None:
        return utils.make_fig_time(None)
    else:
        if from_address is not None:
            mosmix_stations = get_stations()
            if 'value' in from_address:
                sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address['value']]
            else:
                sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address]

            df = get_data(sel_station.WMO_ID.item())
            fig = utils.make_fig_time(df)

            return fig
        else:
            return utils.make_fig_time(None)


@app.callback(
    [Output("locations", "options"),
     Output("locations", "value")],
    [Input("search-button", "n_clicks")],
    [State("from_address", "value")],
    prevent_initial_call=True
)
def get_closest_address(n_clicks, from_address):
    if n_clicks is None:
        return []
    else:
        mosmix_stations = get_stations()
        point = get_place_address(from_address)
        # find 4 closest stations
        df = closest_points(mosmix_stations, point).head()

        options = []
        for _, row in df.head().iterrows():
            options.append(
                {
                    "label": "%s (%2.1f,%2.1f,%3.0f m)" % (row.STATION_NAME.lower(), row.LON, row.LAT, row.STATION_HEIGHT),
                    "value": row.WMO_ID
                }
            )

        return [options, options[0]]


# get location with geolocation button
@app.callback(
    Output("from_address", "value"), 
    [Input("map", "location_lat_lon_acc")],
    prevent_initial_call=True)
def update_location(location):
    if location is not None:
        return get_place_address_reverse(location[1], location[0])
    else:
        raise dash.exceptions.PreventUpdate


#@cache.memoize(1800)
def get_data(station):
    mosmix = utils.DWDMosmixData(
        station_ids=[station],
        mosmix_type=utils.DWDMosmixType.LARGE,
        humanize_parameters=True,
        tidy_data=True
    )

    for data in mosmix.query():
        break

    df = data.data
    # Fill NAN otherwise plotly has problems...don't understand why
    #df = df.fillna(method='ffill').fillna(method='bfill')
    # remove categories
    df.PARAMETER = df.PARAMETER.astype(str)
    # Do some units conversion
    params = ['TEMPERATURE_AIR_200', 'TEMPERATURE_DEW_POINT_200', 'TEMPERATURE_AIR_MAX_200',
              'TEMPERATURE_AIR_MIN_200', 'TEMPERATURE_AIR_005', 'TEMPERATURE_AIR_MIN_005_LAST_12H',
              "TEMPERATURE_AIR_200_LAST_24H"]
    df.loc[df.PARAMETER.isin(params), 'VALUE'] = df.loc[df.PARAMETER.isin(params), 'VALUE'] - 273.15
    return df


@cache.memoize(86400)
def get_stations():
    mosmix_stations = utils.metadata_for_forecasts()
    mosmix_stations['LAT'] = mosmix_stations['LAT'].astype(float)
    mosmix_stations['LON'] = mosmix_stations['LON'].astype(float)
    mosmix_stations['STATION_HEIGHT'] = mosmix_stations['STATION_HEIGHT'].astype(float)

    return mosmix_stations


@cache.memoize(86400)
def closest_point(data, point):
    p = 0.017453292519943295
    a = 0.5 - utils.np.cos((data['LAT']-point["lat"])*p)/2 + \
              utils.np.cos(point["lat"]*p)*utils.np.cos(data['LAT']*p) * \
              (1-utils.np.cos((data['LON']-point["lon"])*p)) / 2

    dist = 12742 * utils.np.arcsin(utils.np.sqrt(a))

    return data.iloc[dist.argmin()]


@cache.memoize(86400)
def closest_points(data, point):
    p = 0.017453292519943295
    a = 0.5 - utils.np.cos((data['LAT']-point["lat"])*p)/2 + \
              utils.np.cos(point["lat"]*p)*utils.np.cos(data['LAT']*p) * \
              (1-utils.np.cos((data['LON']-point["lon"])*p)) / 2

    dist = 12742 * utils.np.arcsin(utils.np.sqrt(a))
    data['dist'] = dist

    return data.sort_values(by='dist')


@cache.memoize(86400)
def get_place_address(place):
    apiURL_places = "https://api.mapbox.com/geocoding/v5/mapbox.places"

    url = "%s/%s.json?&access_token=%s" % (apiURL_places, place, utils.apiKey)

    response = utils.requests.get(url)
    json_data = json.loads(response.text)

    place_name = json_data['features'][0]['place_name']
    lon, lat = json_data['features'][0]['center']

    return {
        'place_name': place_name,
        'lon': lon,
        'lat': lat
    }


@cache.memoize(86400)
def get_place_address_reverse(lon, lat):
    apiURL_places = "https://api.mapbox.com/geocoding/v5/mapbox.places"

    url = "%s/%s,%s.json?&access_token=%s&country=DE&types=address" % (apiURL_places, lon, lat, utils.apiKey)

    response = utils.requests.get(url)
    json_data = json.loads(response.text)

    place_name = json_data['features'][0]['place_name']

    return place_name


if __name__ == "__main__":
    app.run_server()
