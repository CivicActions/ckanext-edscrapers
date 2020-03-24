"""
This app creates a simple sidebar layout using inline style arguments and the
dbc.Nav component.

dcc.Location is used to track the current location. There are two callbacks,
one uses the current location to render the appropriate page content, the other
uses the current location to toggle the "active" properties of the navigation
links.

For more details on building multi-page Dash applications, check out the Dash
documentation: https://dash.plot.ly/urls
"""
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from .pages import air, insights

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div(
    [
        html.Img(src='https://www.datopian.com/img/datopian-logo.png', style={'width': 200, 'float': 'right', 'margin': 20}),
        html.Img(src='https://i.stack.imgur.com/wSpIb.png', style={'width': 200, 'float': 'right', 'margin': 20}),
        html.H5("Scraping Dashboard", className="display-6"),
        html.Hr(),
        html.P(
            "Statistics on data extracted from ED sites", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("Insights", href="/insights", id="page-1-link"),
                dbc.NavLink("Trends", href="/trends", id="page-2-link"),
                dbc.NavLink("AIR comparison", href="/air", id="page-3-link"),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(id="page-content", style=CONTENT_STYLE)

def generate_layout():
    return html.Div([dcc.Location(id="url"), sidebar, content])

app.layout = generate_layout


# this callback uses the current pathname to set the active state of the
# corresponding nav link to true, allowing users to tell see page they are on
@app.callback(
    [Output(f"page-{i}-link", "active") for i in range(1, 4)],
    [Input("url", "pathname")],
)
def toggle_active_links(pathname):
    if pathname == "/":
        # Treat page 1 as the homepage / index
        return True, False, False
    return [pathname == f"/{i}" for i in ['insights', 'trends', 'air']]


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname in ["/insights"]:
        return insights.generate_split_layout()
    elif pathname == "/trends":
        return html.P("This is the content of page 2. Yay!")
    elif pathname in ["/", "/air"]:
        return air.generate_split_layout()
    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


if __name__ == '__main__':
    app.run_server(debug=False, dev_tools_hot_reload=True, host='0.0.0.0')
