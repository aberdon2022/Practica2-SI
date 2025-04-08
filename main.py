from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request, send_file
import sqlite3
import pandas as pd
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

def get_df():
    con = sqlite3.connect('bdPractica2.db')
    sql = """SELECT t.id AS ticket_id, t.fecha_apertura AS fecha_a, t.fecha_cierre AS fecha_c, 
           t.es_mantenimiento, 
           t.satisfaccion_cliente, t.tipo_incidencia_id, t.es_critico, c.nombre as cliente, c.telefono, c.provincia,
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
    df['dia'] = df['fecha_a'].dt.day_name()

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
        if cve.get("containers") and cve.get("cveMetadata"):
            filtered.append(cve)

    top10 = filtered[:10]
    aux = []

    for vuln in top10:
        cve_id = vuln.get("cveMetadata").get("cveId")

        cna = vuln.get("containers").get("cna")
        descriptions = cna.get("descriptions")

        if descriptions:
            details = []
            for desc in descriptions:
                if "value" in desc:
                    details.append(desc["value"])
            details = ", ".join(details)

        published = vuln.get("cveMetadata").get("datePublished")
        updated = vuln.get("cveMetadata").get("dateUpdated")

        if published:
            published_datetime = datetime.fromisoformat(published)
            Madrid = ZoneInfo("Europe/Madrid")
            published = published_datetime.astimezone(Madrid).strftime("%d-%m-%Y %H:%M:%S")
        if updated:
            updated_datetime = datetime.fromisoformat(updated)
            Madrid = ZoneInfo("Europe/Madrid")
            updated = updated_datetime.astimezone(Madrid).strftime("%d-%m-%Y %H:%M:%S")

        refs = cna.get("references")

        if refs:
            urls = []
            for ref in refs:
                if "url" in ref:
                    urls.append(ref["url"])
            refs = ", ".join(urls)

        aux.append({
            "CVE ID": cve_id,
            "Details": details,
            "Published Date": published,
            "Date Updated": updated,
            "References": refs
        })

    dfCVE = pd.DataFrame(aux)
    return dfCVE.to_html()

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
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/ej1', methods=['GET', 'POST'])
def ej1():
    opcion_empleados = request.args.get('opcion_empleados', '0')  # Por defecto, top_clientes

    if opcion_empleados == '1':
        opcion = 'empleados'
    else:
        opcion = 'clientes'

    res = res_ej1(opcion)

    if request.method == 'POST' and 'ej4PDF' in request.form:
        ej4PDF(res)
        return send_file("informe.pdf", as_attachment=True)

    return render_template('ej1.html', res=res)

@app.route('/ej3')
def ej3():
    res = res_ej3()
    return render_template('ej3.html', res=res)

@app.route('/ej4API')
def ej4API():
    stories = res_ej4API()  # Llamamos a la función
    return render_template('ej4API.html', stories=stories)

if __name__ == '__main__':
    app.run(port=8080)