import os.path
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
import sqlite3
import pandas as pd
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import sqlalchemy as sa
from flask_login import current_user, login_user, logout_user, login_required

from extensions import db, login
from forms import LoginForm, RegisterForm
from models import User

import numpy as np
import matplotlib.pyplot as plt
from sklearn import linear_model
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import export_graphviz
from sklearn import tree
from sklearn.model_selection import train_test_split
import json
import graphviz

app = Flask(__name__)
dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(dir, 'bdPractica2.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24).hex()
login.init_app(app)
db.init_app(app)

with app.app_context():
    inspector = sa.inspect(db.engine)
    if not inspector.has_table("Usuarios"):
        db.create_all()
        print("Tabla Usuarios creada en bdPractica2.db")
    else:
        print("La tabla Usuarios ya existe en bdPractica2.db")

def get_df():
    con = sqlite3.connect('bdPractica2.db')
    sql = """SELECT t.id AS ticket_id, t.fecha_apertura AS fecha_a, t.fecha_cierre AS fecha_c, 
           t.es_mantenimiento, 
           t.satisfaccion_cliente, t.tipo_incidencia_id, t.es_critico, 
           c.id AS cliente_id, c.nombre as cliente, c.telefono, c.provincia,
           ti.nombre as tipo_incidencia, cet.fecha AS fecha_atencion_ticket, cet.tiempo, 
           e.nombre as empleado, e.nivel AS nivel_empleado, e.fecha_contrato AS fecha_contrato_empleado
           FROM tickets t
           JOIN clientes c ON t.cliente_id = c.id
           JOIN tipo_incidencia ti ON t.tipo_incidencia_id = ti.id
           JOIN contacto_empleados_ticket cet ON t.id = cet.ticket_id
           JOIN empleados e ON cet.empleado_id = e.id
           """
    df = pd.read_sql_query(sql, con)
    con.close()

    df['fecha_a'] = pd.to_datetime(df['fecha_a'])
    df['fecha_c'] = pd.to_datetime(df['fecha_c'])

    return df

def res_ej1(opcion = 'clientes'):
    df = get_df()
    print(df.to_string())
    top_clientes = df.groupby('cliente').size().sort_values(ascending=False).head(5)
    top_clientes_html = top_clientes.to_frame().to_html()

    # Dias en resolverse
    df['tiempo_resolucion'] = (df['fecha_c'] - df['fecha_a']).dt.total_seconds() / 86400

    top_incidencias = df.groupby('tipo_incidencia')['tiempo_resolucion'].mean().sort_values(ascending=False).head(5)
    top_incidencias_html = top_incidencias.to_frame().to_html()

    top_empleados = None
    top_empleados_html = None
    if opcion == 'empleados':
        top_empleados = df.groupby('empleado')['tiempo_resolucion'].mean().sort_values(ascending=False).head(5)
        top_empleados_html = top_empleados.to_frame().to_html()

    #dataFrames a texto plano para el PDF
    top_clientes_text = top_clientes.to_string(index=True)
    top_incidencias_text = top_incidencias.to_string(index=True)
    top_empleados_text = top_empleados.to_string(index=True) if top_empleados is not None else None

    results = {
        "top_clientes_html": top_clientes_html,
        "top_incidencias_html": top_incidencias_html,
        "top_empleados_html": top_empleados_html,
        "top_clientes_text": top_clientes_text,
        "top_incidencias_text": top_incidencias_text,
        "top_empleados_text": top_empleados_text
    }

    return results

def res_ej3():
    api = "https://cve.circl.lu/api/last"
    response = requests.get(api)
    data = response.json()

    filtered = []
    for cve in data:
        if cve.get("details"):
            filtered.append(cve)

    top10 = filtered[:10]
    aux = []

    for vuln in top10:
        cve_id = vuln.get("aliases")[0]

        details = vuln.get("details")

        published = vuln.get("published")
        modified = vuln.get("modified")
        if published:
            published_datetime = datetime.fromisoformat(published)
            madrid = ZoneInfo("Europe/Madrid")
            published = published_datetime.astimezone(madrid).strftime("%d-%m-%Y %H:%M:%S")
        if modified:
            modified_datetime = datetime.fromisoformat(modified)
            madrid = ZoneInfo("Europe/Madrid")
            modified = modified_datetime.astimezone(madrid).strftime("%d-%m-%Y %H:%M:%S")

        refs = vuln.get("references")
        if refs:
            urls = [ref.get("url") for ref in refs if ref.get("url")]
            refs = ", ".join(urls)

        aux.append({
            "CVE ID": cve_id,
            "Details": details,
            "Published Date": published,
            "Modified Date": modified,
            "References": refs
        })

    return pd.DataFrame(aux).to_html()

def res_ej4API():
    top_stories_url = 'https://hacker-news.firebaseio.com/v0/topstories.json'
    response = requests.get(top_stories_url)
    story_ids = response.json()

    if not story_ids:
        return None

    #primeros 10 IDs
    top_story_ids = story_ids[:10]

    #pedimos los datos de esas noticias
    stories = []

    for story_id in top_story_ids:
        story_url = f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json'
        story_response = requests.get(story_url)
        story_data = story_response.json()

        if story_data:  # nos aseguramos de que haya datos
            stories.append(story_data)

    return stories


def ej4PDF(res, filename="informe.pdf"):

    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter  # Tamaño de página A4
    y_position = height - 40  # Comienza cerca de la parte superior de la página

    # Título del documento
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_position, "Informe de Incidencias")
    y_position -= 30

    # Top Clientes
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y_position, "Top Clientes con más Incidencias")
    y_position -= 20

    # Escribir los datos de top_clientes_text (convertirlo en líneas)
    c.setFont("Helvetica", 10)
    top_clientes_lines = res["top_clientes_text"].split("\n")
    for line in top_clientes_lines:
        c.drawString(40, y_position, line)
        y_position -= 12  # Decrementar para la siguiente línea
        if y_position < 40:  # Si llegamos al final de la página
            c.showPage()  # Crear una nueva página
            c.setFont("Helvetica", 10)
            y_position = height - 40  # Reiniciar la posición

    y_position -= 20

    # Top Tipos de Incidencias
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y_position, "Top Tipos de Incidencias con Mayor Tiempo de Resolución")
    y_position -= 20

    # Escribir los datos de top_incidencias_text (convertirlo en líneas)
    c.setFont("Helvetica", 10)
    top_incidencias_lines = res["top_incidencias_text"].split("\n")
    for line in top_incidencias_lines:
        c.drawString(40, y_position, line)
        y_position -= 12  # Decrementar para la siguiente línea
        if y_position < 40:  # Si llegamos al final de la página
            c.showPage()  # Crear una nueva página
            c.setFont("Helvetica", 10)
            y_position = height - 40  # Reiniciar la posición

    y_position -= 20

    # Top Empleados (si existe)
    if res["top_empleados_html"]:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y_position, "Top Empleados con Mayor Tiempo de Resolución de Incidencias")
        y_position -= 20

        # Escribir los datos de top_empleados_text (convertirlo en líneas)
        c.setFont("Helvetica", 10)
        top_empleados_lines = res["top_empleados_text"].split("\n")
        for line in top_empleados_lines:
            c.drawString(40, y_position, line)
            y_position -= 12  # Decrementar para la siguiente línea
            if y_position < 40:  # Si llegamos al final de la página
                c.showPage()  # Crear una nueva página
                c.setFont("Helvetica", 10)
                y_position = height - 40  # Reiniciar la posición

    # Guardar el PDF
    c.save()

    print(f"PDF generado: {filename}")

def procesar_datos():
    with open("data_clasified.json", "r") as f:
        data = json.load(f)

    tickets = data.get("tickets_emitidos", [])

    processed = []
    for ticket in tickets:
        processed.append({
            "cliente_id": ticket.get("cliente"),
            "fecha_apertura": pd.to_datetime(ticket.get("fecha_apertura")).timestamp(),
            "fecha_cierre": pd.to_datetime(ticket.get("fecha_cierre")).timestamp(),
            "es_mantenimiento": int(ticket.get("es_mantenimiento")),
            "tipo_incidencia": ticket.get("tipo_incidencia"),
            "es_critico": int(ticket.get("es_critico"))
        })

    df = pd.DataFrame(processed)

    x = df[['cliente_id', 'fecha_apertura', 'fecha_cierre', 'es_mantenimiento', 'tipo_incidencia']]
    y = df['es_critico']

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2)

    return x_train, x_test, y_train, y_test, x

def modelo_arbol(entrada_nueva):
    x_train, x_test, y_train, y_test, x = procesar_datos()

    clf = tree.DecisionTreeClassifier()
    clf.fit(x_train, y_train)

    pred = clf.predict(entrada_nueva)[0]
    es_critico = bool(pred)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    nombre_archivo = f"arbol_{timestamp}"
    ruta_imagen = f"{nombre_archivo}.png"

    dot_data = tree.export_graphviz(
        clf,
        out_file=None,
        feature_names=x.columns,
        class_names=["No Crítico", "Crítico"],
        filled=True,
        rounded=True,
        special_characters=True
    )
    graph = graphviz.Source(dot_data)
    graph.render(filename=nombre_archivo, directory="static", format="png", cleanup=True)

    return es_critico, ruta_imagen


def modelo_random_forest(entrada_nueva):
    x_train, x_test, y_train, y_test, x = procesar_datos()

    clf = RandomForestClassifier(max_depth=3, random_state=0, n_estimators=5)
    clf.fit(x_train, y_train)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    imagenes = []

    for i, estimator in enumerate(clf.estimators_):
        nombre_archivo = f"rf_tree_{i}_{timestamp}"
        ruta_imagen = f"{nombre_archivo}.png"

        dot_data = export_graphviz(
            estimator,
            out_file=None,
            feature_names=x.columns,
            class_names=["No Crítico", "Crítico"],
            rounded=True,
            proportion=False,
            precision=2,
            filled=True
        )

        graph = graphviz.Source(dot_data)
        graph.render(filename=nombre_archivo, directory="static", format="png", cleanup=True)
        imagenes.append(ruta_imagen)

    pred = clf.predict(entrada_nueva)[0]
    es_critico = bool(pred)

    return es_critico, imagenes


def modelo_lineal(entrada_nueva):
    x_train, x_test, y_train, y_test, x = procesar_datos()

    modelo = linear_model.LinearRegression()
    modelo.fit(x_train, y_train)

    y_pred = modelo.predict(x_test)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    ruta_imagen = f"roc_curve_{timestamp}.png"
    ruta_completa = f"static/{ruta_imagen}"

    plt.figure(figsize=(8, 6))
    plt.scatter(range(len(y_test)), y_test, color="black", label="Datos Reales", alpha=0.6)
    plt.scatter(range(len(y_pred)), y_pred, color="blue", label="Predicciones", alpha=0.6, linewidth=3)
    plt.yticks([0, 1])
    plt.legend()
    plt.savefig(ruta_completa)
    plt.close()

    pred = modelo.predict(entrada_nueva)[0]
    es_critico = pred >= 0.5

    return bool(es_critico), ruta_imagen


def res_ej5(form):
    cliente_id = int(form.get('cliente'))
    fecha_apertura = form.get('fecha_apertura')
    fecha_cierre = form.get('fecha_cierre')
    es_mantenimiento = int(form.get('es_mantenimiento'))
    tipo_incidencia = int(form.get('tipo_incidencia'))

    fecha_apertura = pd.to_datetime(fecha_apertura).timestamp()
    fecha_cierre = pd.to_datetime(fecha_cierre).timestamp()

    datos = np.array([[cliente_id, fecha_apertura, fecha_cierre, es_mantenimiento, tipo_incidencia]])

    modelo = form.get('modelo')
    if modelo == "lineal":
        return modelo_lineal(datos)
    elif modelo == "arbol":
        return modelo_arbol(datos)
    elif modelo == "bosque":
        return modelo_random_forest(datos)
    else:
        return False, ""

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/profile')
@login_required
def profile():
    if current_user.is_authenticated:
        return render_template('profile.html', username=current_user.username)
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data)
        )
        if user is None or not user.check_password(form.password.data):
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('profile'))
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        logout_user()
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, password=form.password.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Usuario registrado correctamente')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('home'))

@app.route('/ej1', methods=['GET', 'POST'])
@login_required
def ej1():
    opcion_empleados = request.args.get('opcion_empleados', '0')  # Por defecto, top_clientes

    if opcion_empleados == '1':
        session['opcion'] = 'empleados'
    else:
        session.setdefault('opcion', 'clientes')

    res = res_ej1(session['opcion'])

    if request.method == 'POST' and 'ej4PDF' in request.form:
        ej4PDF(res)
        return send_file("informe.pdf", as_attachment=True)

    return render_template('ej1.html', res=res)

@app.route('/ej3')
@login_required
def ej3():
    res = res_ej3()
    return render_template('ej3.html', res=res)

@app.route('/ej4API')
@login_required
def ej4API():
    stories = res_ej4API()  # Llamamos a la función
    return render_template('ej4API.html', stories=stories)

@app.route('/ej5', methods=['GET', 'POST'])
@login_required
def ej5():
    df = get_df()

    clientes_list = df[['cliente_id', 'cliente']].drop_duplicates().values.tolist()
    tipos_list = df[['tipo_incidencia_id', 'tipo_incidencia']].drop_duplicates().values.tolist()

    if request.method == 'POST':
        resultado, grafica_path = res_ej5(request.form)
        return render_template('ej5.html', resultado=resultado, grafica=grafica_path, clientes=clientes_list, tipos=tipos_list)
    else:
        return render_template('ej5.html', clientes=clientes_list, tipos=tipos_list)


if __name__ == '__main__':
    app.run(port=8080)