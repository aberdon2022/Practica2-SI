import json
import sqlite3

with open('data_clasified.json', 'r') as f:
    data = json.load(f)

conn = sqlite3.connect('bdPractica2.db')
cursor = conn.cursor()

for tipo in data['tipos_incidentes']:
    cursor.execute("INSERT INTO tipo_incidencia (id, nombre) VALUES (?, ?)",
                   (tipo['id_inci'], tipo['nombre']))

for cliente in data['clientes']:
    cursor.execute("INSERT INTO clientes (id, nombre, telefono, provincia) VALUES (?, ?, ?, ?)",
                   (cliente['id_cli'], cliente['nombre'], cliente['telefono'], cliente['provincia']))

for ticket in data['tickets_emitidos']:
    cursor.execute("INSERT INTO tickets (cliente_id, fecha_apertura, fecha_cierre, es_mantenimiento, satisfaccion_cliente, tipo_incidencia_id, es_critico) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (ticket['cliente'], ticket['fecha_apertura'], ticket['fecha_cierre'], ticket['es_mantenimiento'], ticket['satisfaccion_cliente'], ticket['tipo_incidencia'], ticket['es_critico']))
    ticket_id = cursor.lastrowid
    for contacto in ticket['contactos_con_empleados']:
        cursor.execute("INSERT INTO contacto_empleados_ticket (ticket_id, empleado_id, fecha, tiempo) VALUES (?, ?, ?, ?)",
                       (ticket_id, contacto['id_emp'], contacto['fecha'], contacto['tiempo']))

for empleado in data['empleados']:
    cursor.execute("INSERT INTO empleados (id, nombre, nivel, fecha_contrato) VALUES (?, ?, ?, ?)",
                   (empleado['id_emp'], empleado['nombre'], empleado['nivel'], empleado['fecha_contrato']))

conn.commit()
conn.close()