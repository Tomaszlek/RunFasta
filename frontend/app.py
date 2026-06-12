import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import requests
import pandas as pd
from datetime import date

import pages.login as page_login
import pages.register as page_register

API = "https://127.0.0.1:8000"

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)

# Wszystkie ID używane w callbackach nawigacyjnych muszą być ZAWSZE w DOM.
# nav-to-register i nav-to-login są tu jako ukryte — widoczne przyciski na stronach
# auth proxy'ują kliknięcia do nich.
app.layout = html.Div([
    dcc.Store(id='session-auth', storage_type='session'),
    dcc.Store(id='current-page', data='login'),
    dcc.Download(id="download-pdf"),
    dcc.Interval(id='auto-refresh', interval=3000, n_intervals=0),
    html.Div([
        html.Button(id='nav-to-register', style={'display': 'none'}),
        html.Button(id='nav-to-login',    style={'display': 'none'}),
    ]),
    html.Div(id='page-content')
])

# Rejestrujemy callbacki ze stron auth
page_login.register_callbacks(app)
page_register.register_callbacks(app)


# ==================== ROUTING ====================

@app.callback(
    Output('page-content', 'children'),
    Input('current-page', 'data'),
    State('session-auth', 'data'),
    prevent_initial_call=False
)
def display_page(current_page, auth_data):
    if auth_data:
        return dashboard_layout(auth_data['user'], auth_data['role'])
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


def dashboard_layout(username, role):
    if role == "COACH":
        hidden = html.Div([
            # Elementy biegacza — ukryte dla trenera
            dcc.Input(id='r-dist',               style={'display': 'none'}),
            dcc.Input(id='r-time',               style={'display': 'none'}),
            dcc.Input(id='r-note',               style={'display': 'none'}),
            dcc.Button(id='r-save-btn',          style={'display': 'none'}),
            html.Div(id='runner-total-dist',     style={'display': 'none'}),
            html.Div(id='runner-count',          style={'display': 'none'}),
            html.Div(id='runner-history-table',  style={'display': 'none'}),
            html.Div(id='runner-plans-table',    style={'display': 'none'}),
            html.Div(id='runner-today-workouts', style={'display': 'none'}),
            dcc.Button(id='btn-pdf',             style={'display': 'none'}),
            # Elementy stron auth — ukryte w dashboardzie
            dcc.Input(id='login-user',           style={'display': 'none'}),
            dcc.Input(id='login-pass',           style={'display': 'none'}),
            dcc.Button(id='login-btn',           style={'display': 'none'}),
            html.Div(id='login-alert',           style={'display': 'none'}),
            dcc.Input(id='register-user',        style={'display': 'none'}),
            dcc.Input(id='register-pass',        style={'display': 'none'}),
            dcc.Dropdown(id='register-role',     style={'display': 'none'}),
            dcc.Button(id='register-btn',        style={'display': 'none'}),
            html.Div(id='register-alert',        style={'display': 'none'}),
            dcc.Button(id='nav-to-register-visible', style={'display': 'none'}),
            dcc.Button(id='nav-to-login-visible',    style={'display': 'none'}),
        ])
        return dbc.Container([
            hidden,
            dbc.NavbarSimple(brand=f"Panel Trenera: {username}", color="dark", dark=True,
                              className="mb-4",
                              children=[dbc.Button("Wyloguj", id='logout-btn', color="secondary", size="sm")]),
            dbc.Row([
                # ---- LEWA KOLUMNA ----
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Twoi Biegacze"),
                        dbc.CardBody([
                            dcc.Dropdown(id='add-runner-select', placeholder="Wybierz biegacza", className="mb-2"),
                            dbc.Button("Dodaj", id='add-runner-btn', color="primary"),
                            html.Div(id='add-runner-msg', className="mb-3 small"),
                            html.Div(id='runners-list'),
                        ])
                    ])
                ], width=4),

                # ---- PRAWA KOLUMNA ----
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Zadaj trening biegaczowi"),
                        dbc.CardBody([
                            dcc.Dropdown(id='select-runner', placeholder="Wybierz biegacza", className="mb-3"),
                            dbc.Input(id='p-dist', type='number', placeholder="Dystans (km)", className="mb-2"),
                            dbc.Input(id='p-time', type='number', placeholder="Czas (min)", className="mb-2"),
                            dcc.DatePickerSingle(
                                id='p-date', date=date.today(),
                                display_format='YYYY-MM-DD', className="mb-2"
                            ),
                            dbc.Textarea(id='p-note', placeholder="Zalecenia trenera", className="mb-2"),
                            dbc.Button("Wyślij Plan", id='plan-btn', color="success", className="w-100"),
                            html.Div(id='plan-msg', className="mt-2 small"),
                        ])
                    ], className="mb-3"),

                    dbc.Card([
                        dbc.CardHeader("Usuń wpis treningowy (podaj ID)"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col(dbc.Input(id='delete-id', type='number', placeholder="ID"), width=8),
                                dbc.Col(dbc.Button("Usuń", id='delete-btn', color="danger", className="w-100"), width=4),
                            ]),
                            html.Div(id='delete-msg', className="mt-2 text-danger small")
                        ])
                    ], className="mb-3"),

                    dbc.Card([
                        dbc.CardHeader("Raporty PDF"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col(dbc.Button("Plan wybranego biegacza", id='btn-pdf-plan-single',
                                                   color="info", className="w-100"), width=6),
                                dbc.Col(dbc.Button("Plany wszystkich biegaczy", id='btn-pdf-plan-all',
                                                   color="secondary", className="w-100"), width=6),
                            ]),
                            html.Div(id='pdf-msg', className="mt-2 small text-danger"),
                        ])
                    ], className="mb-3"),

                    dbc.Card([
                        dbc.CardHeader("Treningi dzisiaj"),
                        dbc.CardBody([
                            dcc.Interval(id='coach-refresh-today', interval=3000, n_intervals=0),
                            html.Div(id='coach-today-workouts', children="Ładowanie...")
                        ])
                    ]),
                ], width=8),
            ]),
        ], fluid=True)

    # ---- LAYOUT BIEGACZA ----
    hidden = html.Div([
        # Elementy trenera — ukryte dla biegacza
        dcc.Dropdown(id='select-runner',         style={'display': 'none'}),
        dcc.Input(id='p-dist',                   style={'display': 'none'}),
        dcc.Input(id='p-time',                   style={'display': 'none'}),
        dcc.Input(id='p-note',                   style={'display': 'none'}),
        dcc.Button(id='plan-btn',                style={'display': 'none'}),
        html.Div(id='plan-msg',                  style={'display': 'none'}),
        html.Div(id='runners-list',              style={'display': 'none'}),
        dcc.Input(id='add-runner-input',         style={'display': 'none'}),
        dcc.Button(id='add-runner-btn',          style={'display': 'none'}),
        html.Div(id='add-runner-msg',            style={'display': 'none'}),
        dcc.Button(id='btn-pdf-plan-single',     style={'display': 'none'}),
        dcc.Button(id='btn-pdf-plan-all',        style={'display': 'none'}),
        html.Div(id='pdf-msg',                   style={'display': 'none'}),
        dcc.Interval(id='coach-refresh-today', interval=999999, n_intervals=0),
        html.Div(id='coach-today-workouts',      style={'display': 'none'}),
        dcc.Input(id='p-date',                   style={'display': 'none'}),
        # Elementy stron auth — ukryte w dashboardzie
        dcc.Input(id='login-user',               style={'display': 'none'}),
        dcc.Input(id='login-pass',               style={'display': 'none'}),
        dcc.Button(id='login-btn',               style={'display': 'none'}),
        html.Div(id='login-alert',               style={'display': 'none'}),
        dcc.Input(id='register-user',            style={'display': 'none'}),
        dcc.Input(id='register-pass',            style={'display': 'none'}),
        dcc.Dropdown(id='register-role',         style={'display': 'none'}),
        dcc.Button(id='register-btn',            style={'display': 'none'}),
        html.Div(id='register-alert',            style={'display': 'none'}),
        dcc.Button(id='nav-to-register-visible', style={'display': 'none'}),
        dcc.Button(id='nav-to-login-visible',    style={'display': 'none'}),
    ])
    return dbc.Container([
        hidden,
        dbc.NavbarSimple(brand=f"Panel Biegacza: {username}", color="success", dark=True,
                          className="mb-4",
                          children=[dbc.Button("Wyloguj", id='logout-btn', color="secondary", size="sm")]),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Łączny dystans"),   html.H2(id='runner-total-dist')])), width=6),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Liczba treningów"), html.H2(id='runner-count')])),      width=6),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Zaraportuj bieg"),
                    dbc.CardBody([
                        dbc.Input(id='r-dist', type='number', placeholder="Dystans (km)", className="mb-2"),
                        dbc.Input(id='r-time', type='number', placeholder="Czas (min)",   className="mb-2"),
                        dbc.Textarea(id='r-note', placeholder="Jak się biegło?",          className="mb-2"),
                        dbc.Button("Zapisz Trening", id='r-save-btn', color="success", className="w-100"),
                    ])
                ]),
                dbc.Card([
                    dbc.CardHeader("Pobierz raport PDF"),
                    dbc.CardBody(
                        dbc.Button("Moje treningi (PDF)", id='btn-pdf', color="info", className="w-100")
                    )
                ], className="mt-3"),
            ], width=4),
            dbc.Col([
                dbc.Tabs([
                    dbc.Tab(label="Dzisiaj", children=[
                        html.Div(id='runner-today-workouts', className="mt-3")
                    ]),
                    dbc.Tab(label="Moja Historia", children=[
                        html.Div(id='runner-history-table', className="mt-3")
                    ]),
                    dbc.Tab(label="Zadania od Trenera", children=[
                        html.Div(id='runner-plans-table', className="mt-3")
                    ]),
                ]),
                dbc.Card([
                    dbc.CardHeader("Usuń wpis (podaj ID z tabeli)"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col(dbc.Input(id='delete-id', type='number', placeholder="ID"), width=8),
                            dbc.Col(dbc.Button("Usuń", id='delete-btn', color="danger", className="w-100"), width=4),
                        ]),
                        html.Div(id='delete-msg', className="mt-2 text-danger small")
                    ])
                ], className="mt-3"),
            ], width=8),
        ]),
    ], fluid=True)


# ==================== CALLBACKI TRENERA ====================

def _fetch_runners(auth):
    res = requests.get(f"{API}/runners", auth=(auth['user'], auth['pass']), verify=False)
    return res.json() if res.status_code == 200 else []


def _fetch_unassigned_runners(auth):
    res = requests.get(f"{API}/runners/unassigned", auth=(auth['user'], auth['pass']), verify=False)
    return res.json() if res.status_code == 200 else []


@app.callback(
    [Output('runners-list', 'children'),
     Output('select-runner', 'options'),
     Output('add-runner-select', 'options'),
     Output('add-runner-msg', 'children')],
    [Input('session-auth', 'data'),
     Input('add-runner-btn', 'n_clicks'),
     Input({'type': 'remove-runner-btn', 'index': dash.ALL}, 'n_clicks')],
    State('add-runner-select', 'value'),
    prevent_initial_call=False
)
def manage_runners(auth, add_clicks, remove_clicks, add_runner_id):
    if not auth or auth['role'] != "COACH":
        return [], [], [], ""

    msg = ""
    ctx = callback_context
    triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else ""

    if 'add-runner-btn' in triggered and add_runner_id:
        res = requests.post(f"{API}/runners/add",
                            json={"runner_id": add_runner_id},
                            auth=(auth['user'], auth['pass']), verify=False)
        msg = (dbc.Alert(f"Dodano biegacza", color="success", duration=3000)
               if res.status_code == 200
               else dbc.Alert(res.json().get('detail', 'Błąd'), color="danger", duration=4000))

    if 'remove-runner-btn' in triggered and any(n for n in remove_clicks if n):
        import json
        runner_id = json.loads(triggered.replace('.n_clicks', ''))['index']
        res = requests.delete(f"{API}/runners/{runner_id}",
                              auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code != 200:
            msg = dbc.Alert("Błąd usuwania biegacza", color="danger", duration=3000)

    runners = _fetch_runners(auth)
    unassigned = _fetch_unassigned_runners(auth)
    list_items = [
        dbc.ListGroupItem([
            html.Span(f"{r['username']}  (ID: {r['id']})", className="me-auto"),
            dbc.Button("✕", id={'type': 'remove-runner-btn', 'index': r['id']},
                       color="danger", size="sm", className="ms-2")
        ], className="d-flex align-items-center justify-content-between")
        for r in runners
    ]
    options = [{'label': r['username'], 'value': r['id']} for r in runners]
    add_options = [{'label': r['username'], 'value': r['id']} for r in unassigned]
    return dbc.ListGroup(list_items, flush=True), options, add_options, msg


@app.callback(
    [Output('plan-btn', 'children'), Output('plan-msg', 'children')],
    Input('plan-btn', 'n_clicks'),
    [State('select-runner', 'value'), State('p-dist', 'value'),
     State('p-time', 'value'), State('p-note', 'value'),
     State('p-date', 'date'), State('session-auth', 'data')],
    prevent_initial_call=True
)
def assign_workout(n, r_id, dist, time, note, plan_date, auth):
    if not r_id or not dist:
        return "Wyślij Plan", dbc.Alert("Wybierz biegacza i podaj dystans!", color="warning")
    payload = {"runner_id": r_id, "distance": dist, "time_minutes": time,
               "note": note, "workout_date": plan_date}
    res = requests.post(f"{API}/workouts/plan", json=payload,
                        auth=(auth['user'], auth['pass']), verify=False)
    if res.status_code == 200:
        return "Wyślij Plan", dbc.Alert("Plan wysłany!", color="success", duration=2000)
    return "Wyślij Plan", dbc.Alert("Błąd wysyłania planu", color="danger")


@app.callback(
    [Output("download-pdf", "data"), Output('pdf-msg', 'children')],
    [Input('btn-pdf-plan-single', 'n_clicks'),
     Input('btn-pdf-plan-all', 'n_clicks')],
    [State('session-auth', 'data'), State('select-runner', 'value')],
    prevent_initial_call=True
)
def download_coach_pdf(n_single, n_all, auth, selected_runner_id):
    if not auth:
        return dash.no_update, ""
    triggered = callback_context.triggered[0]['prop_id']

    if 'btn-pdf-plan-single' in triggered:
        if not selected_runner_id:
            return dash.no_update, dbc.Alert("Wybierz najpierw biegacza z listy!", color="warning")
        url, fname = f"{API}/report/pdf/plan/{selected_runner_id}", f"plan_biegacza_{selected_runner_id}.pdf"
    else:
        url, fname = f"{API}/report/pdf/plan/all", "plany_wszystkich.pdf"

    try:
        res = requests.get(url, auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            return dcc.send_bytes(res.content, fname), ""
        return dash.no_update, dbc.Alert(res.json().get('detail', f'Błąd {res.status_code}'), color="danger")
    except Exception as e:
        return dash.no_update, dbc.Alert(f"Błąd połączenia: {e}", color="danger")


@app.callback(
    Output('coach-today-workouts', 'children'),
    [Input('session-auth', 'data'), Input('coach-refresh-today', 'n_intervals')],
    prevent_initial_call=False
)
def update_coach_today(auth, _):
    if not auth or auth['role'] != "COACH":
        return ""
    try:
        runners = requests.get(f"{API}/runners", auth=(auth['user'], auth['pass']),
                               verify=False, timeout=3).json()
        if not runners:
            return html.P("Nie masz jeszcze biegaczy w grupie", className="text-muted")

        sections = []
        for r in runners:
            res = requests.get(f"{API}/workouts/runner/{r['id']}/today",
                               auth=(auth['user'], auth['pass']), verify=False, timeout=3)
            workouts = res.json() if res.status_code == 200 else []
            if not workouts:
                sections.append(html.Div([
                    html.H6(f"👤 {r['username']}", className="mb-1 text-muted"),
                    html.Small("Brak treningów na dzisiaj", className="text-secondary")
                ], className="mb-3 p-2 border-start border-secondary"))
            else:
                rows = [dbc.ListGroupItem([
                    html.Span(f"📍 {w['distance']} km, {w['time_minutes']} min", className="fw-bold"),
                    dbc.Badge("✓ Ukończono", color="success", className="ms-2") if w.get('completed') else "",
                    html.Br(),
                    html.Small(w.get('note') or "Brak notatek", className="text-secondary")
                ], className="p-2") for w in workouts]
                sections.append(html.Div([
                    html.H6(f"👤 {r['username']}", className="mb-2"),
                    dbc.ListGroup(rows, flush=True)
                ], className="mb-3 p-2 border-start border-primary border-3"))
        return html.Div(sections)
    except Exception as e:
        return f"Błąd: {e}"


# ==================== CALLBACKI BIEGACZA ====================

@app.callback(
    [Output('runner-total-dist', 'children'),
     Output('runner-count', 'children'),
     Output('runner-history-table', 'children'),
     Output('runner-plans-table', 'children')],
    [Input('session-auth', 'data'),
     Input('r-save-btn', 'n_clicks'),
     Input('auto-refresh', 'n_intervals')],
    prevent_initial_call=False
)
def update_runner_data(auth, n, _):
    if not auth or auth['role'] != "RUNNER":
        return dash.no_update

    try:
        stats = requests.get(f"{API}/stats", auth=(auth['user'], auth['pass']),
                             verify=False, timeout=3).json()
        raw = requests.get(f"{API}/workouts", auth=(auth['user'], auth['pass']),
                           verify=False, timeout=3).json()

        if not raw:
            return f"{stats.get('total_distance', 0)} km", str(stats.get('count', 0)), \
                   "Brak historii", "Brak zadań od trenera"

        df = pd.DataFrame(raw)
        df['is_planned'] = df['is_planned'].fillna(False).astype(bool)

        hist_df  = df[~df['is_planned']]
        plans_df = df[df['is_planned']]

        hist_table = (dbc.Table.from_dataframe(
            hist_df[['id', 'distance', 'time_minutes', 'note']], striped=True, hover=True)
            if not hist_df.empty else "Nie biegasz? Czas zacząć!")

        plan_table = (dbc.Table.from_dataframe(
            plans_df[['id', 'distance', 'time_minutes', 'note']], striped=True, color="info")
            if not plans_df.empty else "Trener jeszcze nic nie zaplanował.")

        return (f"{stats.get('total_distance', 0)} km", str(stats.get('count', 0)),
                hist_table, plan_table)
    except Exception as e:
        return "!", "!", "Brak połączenia z API", str(e)


@app.callback(
    Output('runner-today-workouts', 'children'),
    [Input('session-auth', 'data'), Input('auto-refresh', 'n_intervals')],
    prevent_initial_call=False
)
def update_runner_today(auth, _):
    if not auth or auth['role'] != "RUNNER":
        return ""
    try:
        res = requests.get(f"{API}/workouts/today", auth=(auth['user'], auth['pass']),
                           verify=False, timeout=3)
        workouts = res.json() if res.status_code == 200 else []
        if not workouts:
            return html.P("Dziś brak planów treningowych 🎉", className="text-muted mt-2")
        return dbc.ListGroup([
            dbc.ListGroupItem([
                html.Span(f"📍 {w['distance']} km, {w['time_minutes']} min", className="fw-bold"),
                html.Br(),
                html.Small(w.get('note') or "Brak notatek"),
                html.Br(),
                dbc.Button("✓ Ukończono",
                           id={'type': 'complete-workout-btn', 'index': w['id']},
                           color="success", size="sm", className="mt-2")
            ], className="p-3")
            for w in workouts
        ])
    except Exception:
        return "Brak połączenia"


@app.callback(
    Output('runner-today-workouts', 'children', allow_duplicate=True),
    Input({'type': 'complete-workout-btn', 'index': dash.ALL}, 'n_clicks'),
    State('session-auth', 'data'),
    prevent_initial_call=True
)
def complete_workout(n_clicks, auth):
    if not auth or not any(n for n in n_clicks if n):
        return dash.no_update
    import json
    triggered = callback_context.triggered[0]['prop_id']
    workout_id = json.loads(triggered.replace('.n_clicks', ''))['index']
    requests.patch(f"{API}/workouts/{workout_id}/complete",
                   auth=(auth['user'], auth['pass']), verify=False)
    res = requests.get(f"{API}/workouts/today", auth=(auth['user'], auth['pass']),
                       verify=False, timeout=3)
    workouts = res.json() if res.status_code == 200 else []
    if not workouts:
        return html.P("Wszystkie dzisiejsze treningi ukończone! 🎉", className="text-success mt-2")
    return dbc.ListGroup([
        dbc.ListGroupItem([
            html.Span(f"📍 {w['distance']} km, {w['time_minutes']} min", className="fw-bold"),
            html.Br(),
            html.Small(w.get('note') or "Brak notatek"),
            html.Br(),
            dbc.Button("✓ Ukończono",
                       id={'type': 'complete-workout-btn', 'index': w['id']},
                       color="success", size="sm", className="mt-2")
        ], className="p-3")
        for w in workouts
    ])


@app.callback(
    Output('r-save-btn', 'children'),
    Input('r-save-btn', 'n_clicks'),
    [State('r-dist', 'value'), State('r-time', 'value'),
     State('r-note', 'value'), State('session-auth', 'data')],
    prevent_initial_call=True
)
def save_runner_workout(n, dist, time, note, auth):
    if not dist or not time:
        return "Zapisz Trening"
    requests.post(f"{API}/workouts",
                  json={"distance": dist, "time_minutes": time, "note": note},
                  auth=(auth['user'], auth['pass']), verify=False)
    return "Zapisano!"


@app.callback(
    Output('delete-msg', 'children'),
    Input('delete-btn', 'n_clicks'),
    [State('delete-id', 'value'), State('session-auth', 'data')],
    prevent_initial_call=True
)
def delete_action(n, w_id, auth):
    if not w_id:
        return "Podaj ID!"
    res = requests.delete(f"{API}/workouts/{w_id}", auth=(auth['user'], auth['pass']), verify=False)
    if res.status_code == 200:
        return dbc.Alert(f"Usunięto wpis {w_id}.", color="success", duration=3000)
    if res.status_code == 403:
        return dbc.Alert("Brak uprawnień!", color="danger")
    return dbc.Alert(f"Błąd: {res.status_code}", color="danger")


@app.callback(
    Output("download-pdf", "data", allow_duplicate=True),
    Input("btn-pdf", "n_clicks"),
    State('session-auth', 'data'),
    prevent_initial_call=True
)
def download_runner_pdf(n, auth):
    if not auth:
        return dash.no_update
    try:
        me = requests.get(f"{API}/me", auth=(auth['user'], auth['pass']), verify=False).json()
        res = requests.get(f"{API}/report/pdf/runner/{me['id']}",
                           auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            return dcc.send_bytes(res.content, f"raport_{auth['user']}.pdf")
        return dash.no_update
    except Exception:
        return dash.no_update


if __name__ == '__main__':
    app.run(debug=True, port=8050)