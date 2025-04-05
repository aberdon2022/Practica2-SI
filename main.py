from flask import Flask, render_template, abort
import sqlite3
import pandas as pd
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

def res_ej1():
    df = get_df()
    print(df.to_string())
    top_clientes = df.groupby('cliente').size().sort_values(ascending=False).head(5)
    top_clientes = top_clientes.to_frame().to_html()

    # Dias en resolverse
    df['tiempo_resolucion'] = (df['fecha_c'] - df['fecha_a']).dt.total_seconds() / 86400

    top_incidencias = df.groupby('tipo_incidencia')['tiempo_resolucion'].mean().sort_values(ascending=False).head(5)
    top_incidencias = top_incidencias.to_frame().to_html()

    results = {
        "top_clientes": top_clientes,
        "top_incidencias": top_incidencias
    }

    return results

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/ej1')
def ej1():
    res = res_ej1()
    return render_template('ej1.html', res=res)

if __name__ == '__main__':
    app.run(port=8080)