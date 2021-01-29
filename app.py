import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import utils
from dash.dependencies import Input, Output, State
import json
from flask_caching import Cache
from flask import request
from dash.exceptions import PreventUpdate
import pandas as pd

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP,
                'https://fonts.googleapis.com/css?family=Open+Sans:300,400,700'],
                url_base_pathname='/mosmix/',
                meta_tags=[{'name': 'viewport', 
                            'content': 'width=device-width, initial-scale=1'}])

server = app.server

cache = Cache(server, config={'CACHE_TYPE': 'filesystem', 
                              'CACHE_DIR': '/tmp'})

# CSS styles to show/hide an element with transition
initial_hidden_style = {'position': 'absolute', 'opacity': 0}
final_shown_style = {'position': 'static',
                     'opacity': 1,
                     'transition': 'opacity 0.5s linear'}

controls = dbc.Card(
    [
        dbc.InputGroup(
            [
                dbc.Input(placeholder="Where are you?",
                    id='from_address', 
                          type='text', autoComplete=True),
            ],
            className="mb-2",
        ),
        dbc.Row(
            [
                dbc.Button("Search", id="search-button",
                    className=["mb-2"],)
            ],justify='center'
            ),
        html.Div('Here are the 5 closest locations',
                id='closest_locations_description'),
        dbc.InputGroup(
            [
                dbc.Select(
                    id="locations",
                    options=[],
                    value=[],
                ),
            ],
            className="mb-2",
        ),
        dbc.InputGroup(
            [
                # dbc.InputGroupAddon("Data type", addon_type="prepend"),
                dbc.RadioItems(
                    options=[
                        {"label": "Large", "value": 'L'},
                        {"label": "Small", "value": 'S'},
                    ],
                    value='L',
                    id="data-type",
                    inline=True,
                    className="ml-2",
                    style=initial_hidden_style
                ),
            ],
            className="mb-2",
        ),
        dbc.Row(
            [
            dbc.Button("Generate", id="generate-button",
                    className="mr-2", style=initial_hidden_style)
            ], justify='center'
            ),
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
        dcc.Graph(id='temp-plot')
    ],
    className="mb-2",
    style=initial_hidden_style,
    id='temp-fig-card'
)

fig_wind_card = dbc.Card(
    [
        dcc.Graph(id='wind-plot')
    ],
    className="mb-2",
    style=initial_hidden_style,
    id='wind-fig-card'
)

fig_prec_card = dbc.Card(
    [
        dcc.Graph(id='prec-plot')
    ],
    className="mb-2",
    style=initial_hidden_style,
    id='prec-fig-card'
)


help_card =  dbc.Card (  [
        dbc.CardBody(
            [
                html.H4("Help", className="card-title"),
            ]
        ),
    ],className="mb-1" )


app.layout = dbc.Container(
    [
        html.H1("Mosmix webapp"),
        html.Div(id='garbage-output-0', style={'display':'none'}),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col([
                        controls,
                        map_card,
                        dbc.Checklist(
                                    options=[
                                        {"label": "Temperature details", "value": "time_series"},
                                    ],
                                    value=["time_series"],
                                    id="switches-input-temp",
                                    switch=True,
                                ),
                        dbc.Spinner(fig_card),
                        dbc.Checklist(
                                    options=[
                                        {"label": "Wind details", "value": "time_series"},
                                    ],
                                    value=[],
                                    id="switches-input-wind",
                                    switch=True,
                                ),
                        dbc.Spinner(fig_wind_card),
                        dbc.Checklist(
                            options=[
                                {"label": "Precipitation details", "value": "time_series"},
                            ],
                            value=[],
                            id="switches-input-prec",
                            switch=True,
                        ),
                        dbc.Spinner(fig_prec_card),
                    ], sm=11, md=10, lg=8, xl=7, align='center')
            ], justify='center'
            )
    ],
    fluid=True,
    id='container',
)


@app.callback(
    [Output("closest_locations_description", "style"),
     Output("generate-button", "style"),
     Output("data-type", "style")],
    [Input("search-button", "n_clicks")],
    prevent_initial_call=True
)
def show_plots(n_clicks):
    if n_clicks is None:
        return [initial_hidden_style, initial_hidden_style, initial_hidden_style]
    else:
        return [final_shown_style, final_shown_style, final_shown_style]


# show plots when generate button has been pressed
@app.callback(
    [Output("temp-fig-card", "style"),
     Output("wind-fig-card", "style"),
     Output("prec-fig-card", "style")],
    [Input("generate-button", "n_clicks")],
    prevent_initial_call=True
)
def show_plots(n_clicks):
    if n_clicks is None:
        return [initial_hidden_style,
                initial_hidden_style,
                initial_hidden_style]
    else:
        return [final_shown_style,
                final_shown_style,
                final_shown_style]

# show plots when generate button has been pressed
@app.callback(
    [Output("switches-input-temp", "style"),
     Output("switches-input-prec", "style"),
     Output("switches-input-wind", "style")],
    [Input("generate-button", "n_clicks")],
)
def show_switches(n_clicks):
    if n_clicks is None:
        return [initial_hidden_style,
                initial_hidden_style,
                initial_hidden_style]
    else:
        return [final_shown_style,
                final_shown_style,
                final_shown_style]


# Callback for the toggles
@app.callback(
    [Output("wind-plot", "style")],
    [Input("switches-input-wind", "value")],
)
def show_plots(switch):
    if switch == ['time_series']:
        return [final_shown_style]
    else:
        return [initial_hidden_style]
#
@app.callback(
    [Output("prec-plot", "style")],
    [Input("switches-input-prec", "value")],
)
def show_plots(switch):
    if switch == ['time_series']:
        return [final_shown_style]
    else:
        return [initial_hidden_style]
#
@app.callback(
    [Output("temp-plot", "style")],
    [Input("switches-input-temp", "value")],
)
def show_plots(switch):
    if switch == ['time_series']:
        return [final_shown_style]
    else:
        return [initial_hidden_style]


# Scroll to first plot when the style of the plots has been modified,
# which happens after the generate button has been pressed
app.clientside_callback(
    """
    function scrollToBottom(clicks, elementid) {
    var counter = 30;
    var checkExist = setInterval(function() {
          counter--
          if (document.getElementById(elementid) != null || counter === 0) {
            clearInterval(checkExist);
            document.getElementById(elementid).scrollIntoView({behavior: "smooth",
                                                            block: "start",
                                                            inline: "nearest"})
          }
        }, 100);
    }
    """,
    Output('garbage-output-0', 'children'),
    [Input("generate-button", "n_clicks")],
    [State('temp-fig-card', 'id')],
    prevent_initial_call=True
)

# generate map plot at loading AND when the location is updated
@app.callback(
    [Output("map-div", "children")],
    [Input("generate-button", "n_clicks")],
    [State("locations", "value")],
    prevent_initial_call=True
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


# generate the data and the plots when generate is pressed 
# (we call get_stations and get_data in every function
# but the parent functions are cached!)
@app.callback(
    Output("temp-plot", "figure"),
    [Input("generate-button", "n_clicks")],
    [State("locations", "value"), State("data-type", "value")],
    prevent_initial_call=True
)
def func(n_clicks, from_address, data_type):
    ctx = dash.callback_context
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'generate-button':
        if n_clicks is None:
            return utils.make_fig_time(None)
        else:
            if from_address is not None:
                mosmix_stations = get_stations()
                if 'value' in from_address:
                    sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address['value']]
                else:
                    sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address]

                df = get_data(sel_station.WMO_ID.item(), data_type[0])
                fig = utils.make_fig_time(df)

                return fig
            else:
                return utils.make_fig_time(None)


@app.callback(
    Output("wind-plot", "figure"),
    [Input("generate-button", "n_clicks")],
    [State("locations", "value"), State("data-type", "value")],
    prevent_initial_call=True
)
def func2(n_clicks, from_address, data_type):
    if n_clicks is None:
        return utils.make_fig_wind(None)
    else:
        if from_address is not None:
            mosmix_stations = get_stations()
            if 'value' in from_address:
                sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address['value']]
            else:
                sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address]

            df = get_data(sel_station.WMO_ID.item(), data_type[0])
            fig = utils.make_fig_wind(df)

            return fig
        else:
            return utils.make_fig_wind(None)


@app.callback(
    Output("prec-plot", "figure"),
    [Input("generate-button", "n_clicks")],
    [State("locations", "value"), State("data-type", "value")],
    prevent_initial_call=True
)
def func3(n_clicks, from_address, data_type):
    if n_clicks is None:
        return utils.make_fig_prec(None)
    else:
        if from_address is not None:
            mosmix_stations = get_stations()
            if 'value' in from_address:
                sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address['value']]
            else:
                sel_station = mosmix_stations[mosmix_stations.WMO_ID == from_address]

            df = get_data(sel_station.WMO_ID.item(), data_type[0])
            fig = utils.make_fig_prec(df)

            return fig
        else:
            return utils.make_fig_prec(None)


@app.callback(
    [Output("locations", "options"),
     Output("locations", "value"),
     Output("locations", "style")],
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

        return [options, options[0], final_shown_style]


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


@cache.memoize(3600)
def get_data(station, data_type):
    if data_type == 'L':
        mosmix_type = utils.DWDMosmixType.LARGE
    elif data_type == 'S':
        mosmix_type = utils.DWDMosmixType.SMALL

    mosmix = utils.DWDMosmixData(
        station_ids=[station],
        mosmix_type=mosmix_type,
        humanize_parameters=True,
        tidy_data=True
    )

    for data in mosmix.query():
        break

    df = data.data
    # remove categories
    df.PARAMETER = df.PARAMETER.astype(str)
    # Do some units conversion
    params = ['TEMPERATURE_AIR_200', 'TEMPERATURE_DEW_POINT_200', 'TEMPERATURE_AIR_MAX_200',
              'TEMPERATURE_AIR_MIN_200', 'TEMPERATURE_AIR_005', 'TEMPERATURE_AIR_MIN_005_LAST_12H',
              "TEMPERATURE_AIR_200_LAST_24H"]
    df.loc[df.PARAMETER.isin(params), 'VALUE'] = df.loc[df.PARAMETER.isin(params), 'VALUE'] - 273.15
    # 
    params = ['WIND_SPEED', 'WIND_GUST_MAX_LAST_1H', 'WIND_GUST_MAX_LAST_3H',
              'WIND_GUST_MAX_LAST_12H']
    df.loc[df.PARAMETER.isin(params), 'VALUE'] = df.loc[df.PARAMETER.isin(params), 'VALUE'] * 3.6
    #
    df.loc[df.PARAMETER == 'PRESSURE_AIR_SURFACE_REDUCED', 'VALUE'] = \
                df.loc[df.PARAMETER == 'PRESSURE_AIR_SURFACE_REDUCED', 'VALUE'] / 100.

    return df


@cache.memoize(86400)
def get_stations():
    # mosmix_stations = utils.metadata_for_forecasts()
    # mosmix_stations['LAT'] = mosmix_stations['LAT'].astype(float)
    # mosmix_stations['LON'] = mosmix_stations['LON'].astype(float)
    # mosmix_stations['STATION_HEIGHT'] = mosmix_stations['STATION_HEIGHT'].astype(float)

    # mosmix_stations.to_pickle('stations_list.pkl')
    mosmix_stations = pd.read_pickle('stations_list.pkl')

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
