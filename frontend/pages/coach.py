import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import requests
from datetime import date

API = "https://192.168.43.66:8000"


# pomocnicze funkcje do sciagania biegaczy do listy mozliwych przypisan
def _fetch_runners(auth):
    try:
        res = requests.get(f"{API}/runners", auth=(auth['user'], auth['pass']), verify=False, timeout=3)
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []


def _fetch_unassigned_runners(auth):
    try:
        res = requests.get(f"{API}/runners/unassigned", auth=(auth['user'], auth['pass']), verify=False, timeout=3)
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []


# layout

def _get_group_panel_layout():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Zarządzanie grupą"),
                dbc.CardBody([
                    dcc.Dropdown(id='add-runner-select', placeholder="Wybierz biegacza do dodania", className="mb-2"),
                    dbc.Button("Dodaj do Grupy", id='add-runner-btn', color="success", className="w-100 mb-3"),
                    html.Div(id='add-runner-msg'),
                    html.Div(id='runners-list'),
                ])
            ])
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Statystyki biegacza dla wybranego zakresu dat"),
                dbc.CardBody([
                    dcc.Dropdown(id='stats-runner-select', placeholder="Wybierz biegacza", className="mb-3"),
                    dcc.DatePickerRange(
                        id='stats-date-range',
                        start_date=None,
                        end_date=date.today(),
                        display_format='YYYY-MM-DD',
                        className="mb-3 d-block"
                    ),
                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Dystans łączny", className="small text-muted py-1"),
                            dbc.CardBody(html.H4(id='stats-total-dist', children="0.0 km"),
                                         className="py-2 text-center")
                        ]), width=6),
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Suma treningów", className="small text-muted py-1"),
                            dbc.CardBody(html.H4(id='stats-total-count', children="0"), className="py-2 text-center")
                        ]), width=6),
                    ], className="mb-3"),
                ])
            ], className="mb-3"),
            dbc.Card([
                dbc.CardHeader("Dzisiejsze plany twoich podopiecznych"),
                dbc.CardBody(html.Div(id='coach-today-workouts'))
            ])
        ], width=8)
    ])


def _get_assign_panel_layout():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Zadaj nowy trening podopiecznemu"),
                dbc.CardBody([
                    dcc.Dropdown(id='select-runner', placeholder="Wybierz biegacza", className="mb-3"),
                    dbc.Row([
                        dbc.Col(dbc.Input(id='p-dist', type='number', placeholder="Dystans (km)", className="mb-2"),
                                width=6),
                        dbc.Col(
                            dbc.Input(id='p-time', type='number', placeholder="Planowany Czas (min)", className="mb-2"),
                            width=6),
                    ]),
                    dcc.DatePickerSingle(id='p-date', date=date.today(), display_format='YYYY-MM-DD',
                                         className="mb-2 d-block"),

                    dbc.Label("Docelowe tempo i prędkość (uzupełniają się automatycznie):"),
                    dbc.Row([
                        dbc.Col(dbc.Input(id='p-pace-minkm', type='number', step=0.01, placeholder="Tempo (min/km)",
                                          className="mb-2"), width=6),
                        dbc.Col(dbc.Input(id='p-speed-kmh', type='number', step=0.01, placeholder="Prędkość (km/h)",
                                          className="mb-2"), width=6),
                    ], className="mb-3"),

                    dbc.Checklist(
                        options=[{"label": "Trening interwałowy", "value": 1}],
                        value=[], id="p-interval-toggle", switch=True, className="mb-3"
                    ),
                    html.Div(id="interval-form-container", style={"display": "none"}, children=[
                        dbc.Row([
                            dbc.Col(dbc.Input(id='p-int-repeats', type='number', placeholder="Liczba powtórzeń (np. 5)",
                                              className="mb-2"), width=6),
                            dbc.Col(dbc.Input(id='p-int-dist', type='number', placeholder="Dystans powtórzenia (m)",
                                              className="mb-2"), width=6),
                        ]),
                        dbc.Input(id='p-int-recovery', type='text', placeholder="Opis przerwy (np. 2 min marsz)",
                                  className="mb-3"),
                    ]),

                    dbc.Textarea(id='p-note', placeholder="Dodatkowe zalecenia trenera", className="mb-3"),
                    dbc.Button("Akceptuj i wyślij trening podopiecznemu", id='plan-btn', color="success", className="w-100"),
                    html.Div(id='plan-msg', className="mt-2 small"),
                ])
            ])
        ], width=6, className="mx-auto")
    ])


def _get_chat_panel_layout():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Uzyskaj raporty treningów w PDFie"),
                dbc.CardBody([
                    dcc.Dropdown(id='pdf-runner-select', placeholder="Wybierz biegacza", className="mb-3"),
                    dbc.Button("Pobierz Plan Wybranego", id='btn-pdf-plan-single', color="info",
                               className="w-100 mb-2"),
                    dbc.Button("Pobierz Plany Wszystkich", id='btn-pdf-plan-all', color="secondary", className="w-100"),
                    html.Div(id='pdf-msg', className="mt-2 text-danger small")
                ])
            ])
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Czat z Biegaczem"),
                dbc.CardBody([
                    dcc.Dropdown(id='chat-runner-select', placeholder="Wybierz biegacza, by pisać", className="mb-3"),
                    html.Div(
                        id='chat-box',
                        style={"height": "300px", "overflowY": "scroll", "border": "1px solid #ddd", "padding": "10px",
                               "backgroundColor": "#fdfdfd"},
                        className="mb-3 rounded"
                    ),
                    dbc.Row([
                        dbc.Col(dbc.Input(id='chat-input-text', placeholder="Napisz wiadomość"), width=9),
                        dbc.Col(dbc.Button("Wyślij", id='chat-send-btn', color="primary", className="w-100"), width=3)
                    ])
                ])
            ])
        ], width=8)
    ])


def layout(username):
    return dbc.Container([
        dcc.Store(id='coach-active-panel', data='group'),
        dcc.Interval(id='chat-refresh', interval=5000, n_intervals=0),

        dbc.NavbarSimple(
            brand=f"Panel Trenera: {username}",
            color="dark",
            dark=True,
            className="mb-4",
            children=[dbc.Button("Wyloguj", id='logout-btn', color="secondary", size="sm")]
        ),

        dbc.Row([
            dbc.Col(
                dbc.ButtonGroup([
                    dbc.Button("Panel grupy podopiecznych i statystyki", id='btn-panel-group', color="primary", outline=True,
                               className="px-4"),
                    dbc.Button("Zadawanie treningów podopiecznym", id='btn-panel-assign', color="primary", outline=True,
                               className="px-4"),
                    dbc.Button("Czat z podopiecznymi i raportowanie treningów do PDF", id='btn-panel-chat', color="primary", outline=True,
                               className="px-4"),
                ], className="w-100"),
                width=12, className="mb-4 text-center"
            )
        ]),

        html.Div(id='coach-panel-group-container', children=_get_group_panel_layout(), style={"display": "block"}),
        html.Div(id='coach-panel-assign-container', children=_get_assign_panel_layout(), style={"display": "none"}),
        html.Div(id='coach-panel-chat-container', children=_get_chat_panel_layout(), style={"display": "none"}),
    ], fluid=True)

def register_callbacks(app):
    # przełączanie aktywnego panelu
    @app.callback(
        Output('coach-active-panel', 'data'),
        [Input('btn-panel-group', 'n_clicks'),
         Input('btn-panel-assign', 'n_clicks'),
         Input('btn-panel-chat', 'n_clicks')],
        prevent_initial_call=True
    )
    def switch_sub_panel(group, assign, chat):
        ctx = callback_context
        if not ctx.triggered:
            return 'group'
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'btn-panel-assign':
            return 'assign'
        if button_id == 'btn-panel-chat':
            return 'chat'
        return 'group'

    # przerzucanie styli css dla panelow
    @app.callback(
        [Output('coach-panel-group-container', 'style'),
         Output('coach-panel-assign-container', 'style'),
         Output('coach-panel-chat-container', 'style')],
        Input('coach-active-panel', 'data')
    )
    def toggle_containers(active_panel):
        group_s = {"display": "block"} if active_panel == 'group' else {"display": "none"}
        assign_s = {"display": "block"} if active_panel == 'assign' else {"display": "none"}
        chat_s = {"display": "block"} if active_panel == 'chat' else {"display": "none"}
        return group_s, assign_s, chat_s

    # pokazywanie/ukrywanie sekcji interwałów
    @app.callback(
        Output('interval-form-container', 'style'),
        Input('p-interval-toggle', 'value'),
        prevent_initial_call=False
    )
    def toggle_interval_fields(val):
        if val and 1 in val:
            return {"display": "block"}
        return {"display": "none"}

    # synchro tempo -> predkosc, zeby na froncie uzupełniało od razu
    @app.callback(
        [Output('p-pace-minkm', 'value'),
         Output('p-speed-kmh', 'value'),
         Output('plan-msg', 'children', allow_duplicate=True)],
        [Input('p-dist', 'value'),
         Input('p-time', 'value'),
         Input('p-pace-minkm', 'value'),
         Input('p-speed-kmh', 'value')],
        prevent_initial_call=True
    )
    def sync_pace_speed_coach(dist, time, pace, speed):
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # Wyliczanie z dystansu i czasu
        if trigger_id in ['p-dist', 'p-time']:
            if dist and time and dist > 0 and time > 0:
                calc_pace = round(time / dist, 2)
                calc_speed = round((dist / time) * 60, 2)
                if calc_speed < 3 or calc_speed > 20:
                    return calc_pace, calc_speed, dbc.Alert(
                        "Ostrzeżenie: Podana prędkość wykracza poza dopuszczalny zakres (3-20 km/h)!",
                        color="warning")
                return calc_pace, calc_speed, ""
            return dash.no_update, dash.no_update, dash.no_update

        # tempa (min/km) -> Prędkość (km/h)
        if trigger_id == 'p-pace-minkm':
            if pace and pace > 0:
                calc_speed = round(60 / pace, 2)
                if calc_speed < 3 or calc_speed > 20:
                    return pace, calc_speed, dbc.Alert(
                        "Błąd: Prędkość musi wynosić od 3 km/h (20 min/km) do 20 km/h (3 min/km)!", color="danger")
                return pace, calc_speed, ""
            return None, None, ""

        # prędkości (km/h) -> Tempo (min/km)
        if trigger_id == 'p-speed-kmh':
            if speed and speed > 0:
                calc_pace = round(60 / speed, 2)
                if speed < 3 or speed > 20:
                    return calc_pace, speed, dbc.Alert(
                        "Błąd: Prędkość musi wynosić od 3 km/h (20 min/km) do 20 km/h (3 min/km)!", color="danger")
                return calc_pace, speed, ""
            return None, None, ""

        return dash.no_update, dash.no_update, dash.no_update

    # pobranie listy
    @app.callback(
        [Output('runners-list', 'children'),
         Output('select-runner', 'options'),
         Output('add-runner-select', 'options'),
         Output('stats-runner-select', 'options'),
         Output('chat-runner-select', 'options'),
         Output('pdf-runner-select', 'options')],
        [Input('session-auth', 'data'),
         Input('coach-update-trigger', 'data')],
        prevent_initial_call=False
    )
    def load_runners_list(auth, _):
        if not auth or auth['role'] != "COACH":
            return [], [], [], [], [], []

        runners = _fetch_runners(auth)
        unassigned = _fetch_unassigned_runners(auth)

        list_items = [
            dbc.ListGroupItem([
                html.Span(f"{r['username']} (ID: {r['id']})", className="me-auto"),
                dbc.Button("x", id={'type': 'remove-runner-btn', 'index': r['id']}, color="danger", size="sm",
                           className="ms-2")
            ], className="d-flex align-items-center justify-content-between") for r in runners
        ] if runners else [html.Small("Brak biegaczy w grupie.", className="text-muted")]

        options = [{'label': r['username'], 'value': r['id']} for r in runners]
        add_options = [{'label': r['username'], 'value': r['id']} for r in unassigned]

        return dbc.ListGroup(list_items, flush=True), options, add_options, options, options, options

    # dodawanie biegacza do grup
    @app.callback(
        [Output('add-runner-msg', 'children'),
         Output('coach-update-trigger', 'data', allow_duplicate=True)],
        Input('add-runner-btn', 'n_clicks'),
        [State('add-runner-select', 'value'),
         State('session-auth', 'data'),
         State('coach-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def add_runner_action(n, add_runner_id, auth, current_trigger):
        if not auth or not add_runner_id:
            return dash.no_update, dash.no_update

        res = requests.post(f"{API}/runners/add", json={"runner_id": add_runner_id}, auth=(auth['user'], auth['pass']),
                            verify=False)
        if res.status_code == 200:
            msg = dbc.Alert("Dodano biegacza do grupy", color="success", duration=3000)
            return msg, (current_trigger or 0) + 1
        else:
            msg = dbc.Alert(res.json().get('detail', 'Błąd'), color="danger", duration=4000)
            return msg, dash.no_update

    # biegacz jest usuwant
    @app.callback(
        Output('coach-update-trigger', 'data', allow_duplicate=True),
        Input({'type': 'remove-runner-btn', 'index': dash.ALL}, 'n_clicks'),
        [State('session-auth', 'data'), State('coach-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def remove_runner_action(n_clicks, auth, current_trigger):
        if not auth or not any(n for n in n_clicks if n):
            return dash.no_update

        ctx = callback_context
        triggered = ctx.triggered[0]['prop_id']
        import json
        runner_id = json.loads(triggered.replace('.n_clicks', ''))['index']

        res = requests.delete(f"{API}/runners/{runner_id}", auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            return (current_trigger or 0) + 1
        return dash.no_update

    #Statystyki z zakresu dat
    @app.callback(
        [Output('stats-total-dist', 'children'),
         Output('stats-total-count', 'children')],
        [Input('stats-runner-select', 'value'),
         Input('stats-date-range', 'start_date'),
         Input('stats-date-range', 'end_date')],
        State('session-auth', 'data'),
        prevent_initial_call=True
    )
    def update_runner_stats(runner_id, start_date, end_date, auth):
        if not auth or not runner_id:
            return "0.0 km", "0"
        url = f"{API}/stats/runner/{runner_id}"
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        try:
            res = requests.get(url, params=params, auth=(auth['user'], auth['pass']), verify=False)
            if res.status_code == 200:
                data = res.json()
                return f"{data.get('total_distance', 0)} km", str(data.get('count', 0))
        except Exception:
            pass
        return "0.0 km", "0"

    #dzisiejsze plany biegaczy w grupie
    @app.callback(
        Output('coach-today-workouts', 'children'),
        [Input('session-auth', 'data'), Input('coach-update-trigger', 'data')],
        prevent_initial_call=False
    )
    def update_coach_today(auth, _):
        if not auth or auth['role'] != "COACH":
            return ""
        try:
            runners = _fetch_runners(auth)
            if not runners:
                return html.Small("Przypisz biegaczy, by widzieć ich treningi.", className="text-muted")

            sections = []
            for r in runners:
                res = requests.get(f"{API}/workouts/runner/{r['id']}/today", auth=(auth['user'], auth['pass']),
                                   verify=False, timeout=3)
                workouts = res.json() if res.status_code == 200 else []
                if not workouts:
                    sections.append(html.Div([
                        html.H6(f"{r['username']}", className="mb-1 text-muted small"),
                        html.Small("Brak planów na dziś", className="text-secondary")
                    ], className="mb-2 p-2 border-start border-secondary"))
                else:
                    rows = []
                    for w in workouts:
                        pace_inf = f" (Tempo: {w['target_pace']})" if w.get('target_pace') else ""
                        int_inf = f"Interwały {w['interval_repeats']}x{w['interval_distance_meters']}m | " if w.get(
                            'is_interval') else ""
                        rows.append(dbc.ListGroupItem([
                            html.Span(f"{w['distance']} km, {w['time_minutes']} min{pace_inf}",
                                      className="fw-bold small"),
                            dbc.Badge("Ukończono", color="success", className="ms-2") if w.get('completed') else "",
                            html.Br(),
                            html.Small(f"{int_inf}{w.get('note') or 'Brak notatek'}", className="text-secondary small")
                        ], className="p-1"))
                    sections.append(html.Div([
                        html.H6(f"{r['username']}", className="mb-1 small"),
                        dbc.ListGroup(rows, flush=True)
                    ], className="mb-2 p-2 border-start border-primary border-2"))
            return html.Div(sections)
        except Exception as e:
            return f"Błąd połączenia: {e}"

    # zadawanie planu z walidacjsd prędkości krańcowych
    @app.callback(
        [Output('plan-btn', 'children'), Output('plan-msg', 'children'),
         Output('coach-update-trigger', 'data', allow_duplicate=True)],
        Input('plan-btn', 'n_clicks'),
        [State('select-runner', 'value'), State('p-dist', 'value'),
         State('p-time', 'value'), State('p-note', 'value'),
         State('p-date', 'date'), State('p-pace-minkm', 'value'), State('p-speed-kmh', 'value'),
         State('p-interval-toggle', 'value'), State('p-int-repeats', 'value'),
         State('p-int-dist', 'value'), State('p-int-recovery', 'value'),
         State('session-auth', 'data'), State('coach-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def assign_workout(n, r_id, dist, time, note, plan_date, pace_minkm, speed_kmh,
                       int_toggle, int_repeats, int_dist, int_recovery, auth, current_trigger):
        if not r_id or not dist:
            return "Akceptuj i wyślij trening podopiecznemu", dbc.Alert("Wybierz biegacza i podaj dystans!",
                                                    color="warning"), dash.no_update

        if speed_kmh and (speed_kmh < 3 or speed_kmh > 20):
            return "Akceptuj i wyślij trening podopiecznemu", dbc.Alert("Błąd zapisu: Dozwolona prędkość to wyłącznie zakres 3 - 20 km/h!",
                                                    color="danger"), dash.no_update

        pace_str = f"{pace_minkm} min/km ({speed_kmh} km/h)" if pace_minkm else None
        is_interval = bool(int_toggle and 1 in int_toggle)

        payload = {
            "runner_id": r_id, "distance": dist, "time_minutes": time, "note": note,
            "workout_date": plan_date, "target_pace": pace_str, "is_interval": is_interval,
            "interval_repeats": int_repeats if is_interval else None,
            "interval_distance_meters": int_dist if is_interval else None,
            "interval_recovery": int_recovery if is_interval else None
        }

        res = requests.post(f"{API}/workouts/plan", json=payload, auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            return "Akceptuj i wyślij trening podopiecznemu", dbc.Alert("Plan został pomyślnie wysłany!", color="success", duration=2500), (
                                                                                                                                   current_trigger or 0) + 1
        return "Akceptuj i wyślij trening podopiecznemu", dbc.Alert("Błąd wysyłania planu", color="danger"), dash.no_update

    # PDF
    @app.callback(
        [Output("download-pdf", "data", allow_duplicate=True), Output('pdf-msg', 'children')],
        [Input('btn-pdf-plan-single', 'n_clicks'),
         Input('btn-pdf-plan-all', 'n_clicks')],
        [State('session-auth', 'data'), State('pdf-runner-select', 'value')],
        prevent_initial_call=True
    )
    def download_coach_pdf(n_single, n_all, auth, selected_runner_id):
        if not auth:
            return dash.no_update, ""
        triggered = callback_context.triggered[0]['prop_id']

        if 'btn-pdf-plan-single' in triggered:
            if not selected_runner_id:
                return dash.no_update, dbc.Alert("Wybierz najpierw biegacza!", color="warning")
            url, fname = f"{API}/report/pdf/plan/{selected_runner_id}", f"plan_biegacza_{selected_runner_id}.pdf"
        else:
            url, fname = f"{API}/report/pdf/plan/all", "plany_wszystkich.pdf"

        try:
            res = requests.get(url, auth=(auth['user'], auth['pass']), verify=False)
            if res.status_code == 200:
                return dcc.send_bytes(res.content, fname), ""
            return dash.no_update, dbc.Alert("Brak planów do wygenerowania PDF", color="danger")
        except Exception as e:
            return dash.no_update, dbc.Alert(f"Błąd połączenia: {e}", color="danger")

    # Pobieranie czatu
    @app.callback(
        Output('chat-box', 'children'),
        [Input('chat-runner-select', 'value'),
         Input('chat-refresh', 'n_intervals'),
         Input('coach-update-trigger', 'data')],
        State('session-auth', 'data'),
        prevent_initial_call=False
    )
    def load_chat(runner_id, n, _, auth):
        if not auth or not runner_id:
            return html.Small("Wybierz biegacza z listy, aby wyświetlić historię rozmów.", className="text-muted")

        try:
            res = requests.get(f"{API}/messages/thread/{runner_id}", auth=(auth['user'], auth['pass']), verify=False)
            if res.status_code == 200:
                msgs = res.json()
                if not msgs:
                    return html.Small("Brak wiadomości. Napisz coś do swojego biegacza!", className="text-secondary")

                chat_elements = []
                for m in msgs:
                    is_me = (m['sender_id'] != runner_id)
                    align = "text-end" if is_me else "text-start"
                    color = "#e2f0d9" if is_me else "#f2f2f2"

                    chat_elements.append(html.Div([
                        html.Div(m['text'], style={
                            "padding": "6px 12px", "borderRadius": "12px",
                            "backgroundColor": color, "display": "inline-block",
                            "maxWidth": "70%", "textAlign": "left"
                        }),
                        html.Div(html.Small(m['created_at'].replace('T', ' ')[:16], className="text-muted",
                                            style={"fontSize": "10px"}), className="mt-1")
                    ], className=f"mb-2 {align} d-flex flex-column align-items-{'end' if is_me else 'start'}"))
                return chat_elements
        except Exception:
            return "Błąd pobierania wiadomości czatu."

    # wiadomości na czacie
    @app.callback(
        [Output('chat-input-text', 'value'),
         Output('coach-update-trigger', 'data', allow_duplicate=True)],
        Input('chat-send-btn', 'n_clicks'),
        [State('chat-input-text', 'value'),
         State('chat-runner-select', 'value'),
         State('session-auth', 'data'),
         State('coach-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def send_chat_msg(n, text, runner_id, auth, current_trigger):
        if not auth or not runner_id or not text or not text.strip():
            return dash.no_update, dash.no_update

        try:
            requests.post(f"{API}/messages", json={"receiver_id": runner_id, "text": text},
                          auth=(auth['user'], auth['pass']), verify=False)
            return "", (current_trigger or 0) + 1
        except Exception:
            return text, dash.no_update

    # usuwanie treningu
    @app.callback(
        [Output('coach-delete-msg', 'children'),
         Output('coach-update-trigger', 'data', allow_duplicate=True)],
        Input('coach-delete-btn', 'n_clicks'),
        [State('coach-delete-id', 'value'), State('session-auth', 'data'),
         State('coach-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def coach_delete_action(n, w_id, auth, coach_trig):
        if not w_id:
            return "Podaj ID!", dash.no_update
        res = requests.delete(f"{API}/workouts/{w_id}", auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            return dbc.Alert(f"Usunięto wpis o ID {w_id}.", color="success", duration=3000), (coach_trig or 0) + 1
        if res.status_code == 403:
            return dbc.Alert("Brak uprawnień do usunięcia tego treningu!", color="danger"), dash.no_update
        return dbc.Alert(f"Błąd: {res.status_code}", color="danger"), dash.no_update