from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash
import requests

API = "https://192.168.43.66:8000"

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Rejestracja", className="text-center mb-4"),
            dbc.Input(id='register-user', placeholder='Nazwa użytkownika', className="mb-2"),
            dbc.Input(id='register-pass', type='password', placeholder='Hasło', className="mb-2"),
            dcc.Dropdown(
                id='register-role',
                options=[
                    {'label': 'Trener', 'value': 'COACH'},
                    {'label': 'Biegacz', 'value': 'RUNNER'}
                ],
                placeholder="Wybierz rolę",
                className="mb-3"
            ),
            dbc.Button("Zarejestruj się", id='register-btn', color="success", className="w-100 mb-2"),
            dbc.Button("Masz już konto? Zaloguj się",
                       id='nav-to-login-visible', color="link", className="w-100 text-muted"),
            html.Div(id='register-alert', className="mt-2")
        ], width=4)
    ], justify="center", style={"marginTop": "15%"})
])


def register_callbacks(app):
    @app.callback(
        [Output('session-auth', 'data', allow_duplicate=True),
         Output('register-alert', 'children')],
        Input('register-btn', 'n_clicks'),
        [State('register-user', 'value'),
         State('register-pass', 'value'),
         State('register-role', 'value')],
        prevent_initial_call=True
    )
    def register(n, username, password, role):
        if not username or not password or not role:
            return dash.no_update, dbc.Alert("Wypełnij wszystkie pola!", color="warning")
        try:
            res = requests.post(f"{API}/register",
                                json={"username": username, "password": password, "role": role},
                                verify=False)
            if res.status_code == 200:
                auth_res = requests.get(f"{API}/me", auth=(username, password), verify=False)
                if auth_res.status_code == 200:
                    return {'user': username, 'pass': password,
                            'role': auth_res.json()['role']}, ""
            detail = res.json().get('detail', 'Błąd rejestracji')
            return dash.no_update, dbc.Alert(detail, color="danger")
        except Exception as e:
            return dash.no_update, dbc.Alert(f"Błąd: {str(e)}", color="danger")
#trigger logowania
    @app.callback(
        Output('nav-to-login', 'n_clicks'),
        Input('nav-to-login-visible', 'n_clicks'),
        prevent_initial_call=True
    )
    def proxy_to_login(n):
        if n:
            return n
        return dash.no_update