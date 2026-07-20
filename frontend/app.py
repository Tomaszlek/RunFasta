import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import os
import pages.login as page_login
import pages.register as page_register
import pages.coach as page_coach
import pages.runner as page_runner
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)

app.layout = html.Div([
    dcc.Store(id='session-auth', storage_type='session'),
    dcc.Store(id='current-page', data='login'),

    dcc.Store(id='runner-update-trigger', data=0),
    dcc.Store(id='coach-update-trigger', data=0),

    dcc.Download(id="download-pdf"),
    html.Div([
        html.Button(id='nav-to-register', style={'display': 'none'}),
        html.Button(id='nav-to-login', style={'display': 'none'}),
    ]),
    html.Div(id='page-content')
])

# Rejestracja callbacków ze wszystkich modułów stron
page_login.register_callbacks(app)
page_register.register_callbacks(app)
page_coach.register_callbacks(app)
page_runner.register_callbacks(app)


# ==================== ROUTING ====================

@app.callback(
    Output('page-content', 'children'),
    Input('current-page', 'data'),
    State('session-auth', 'data'),
    prevent_initial_call=False
)
def display_page(current_page, auth_data):
    if auth_data:
        if auth_data['role'] == "COACH":
            return page_coach.layout(auth_data['user'])
        elif auth_data['role'] == "RUNNER":
            return page_runner.layout(auth_data['user'])
    if current_page == 'register':
        return page_register.layout
    return page_login.layout


@app.callback(
    Output('current-page', 'data', allow_duplicate=True),
    [Input('nav-to-register', 'n_clicks'),
     Input('nav-to-login', 'n_clicks')],
    prevent_initial_call=True
)
def switch_page(to_reg, to_login):
    ctx = callback_context
    triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
    if 'nav-to-register' in triggered:
        return 'register'
    if 'nav-to-login' in triggered:
        return 'login'
    return dash.no_update


@app.callback(
    Output('current-page', 'data', allow_duplicate=True),
    Input('session-auth', 'data'),
    prevent_initial_call='initial_duplicate'
)
def on_auth_change(auth_data):
    return 'dashboard' if auth_data else 'login'


@app.callback(
    [Output('session-auth', 'data', allow_duplicate=True), Output('current-page', 'data', allow_duplicate=True)],
    Input('logout-btn', 'n_clicks'),
    prevent_initial_call=True
)
def logout(n):
    if not n:
        return dash.no_update, dash.no_update
    return None, 'login'


if __name__ == '__main__':
    obecna_sciezka = os.path.dirname(os.path.abspath(__file__))

    if os.path.exists(os.path.join(obecna_sciezka, "cert.pem")):
        cert_path = os.path.join(obecna_sciezka, "cert.pem")
        key_path = os.path.join(obecna_sciezka, "key.pem")
    else:
        _root = os.path.dirname(obecna_sciezka)
        cert_path = os.path.join(_root, "cert.pem")
        key_path = os.path.join(_root, "key.pem")

    app.run(
        debug=True,
        host='0.0.0.0',
        port=8050,
        ssl_context=(cert_path, key_path)
    )