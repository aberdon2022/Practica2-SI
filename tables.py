import sqlite3

con = sqlite3.connect('bdPractica2.db')
cur = con.cursor()

cur.execute("CREATE TABLE tipo_incidencia (id INTEGER PRIMARY KEY, nombre TEXT)")

cur.execute("CREATE TABLE clientes (id INTEGER PRIMARY KEY, nombre TEXT, telefono TEXT, provincia TEXT)")

cur.execute("CREATE TABLE tickets (id INTEGER PRIMARY KEY,"
            "cliente_id INTEGER,"
            "fecha_apertura TEXT,"
            "fecha_cierre TEXT,"
            "es_mantenimiento INTEGER,"
            "satisfaccion_cliente INTEGER,"
            "tipo_incidencia_id INTEGER,"
            "es_critico INTEGER,"
            "FOREIGN KEY (tipo_incidencia_id) REFERENCES tipo_incidencia(id),"
            "FOREIGN KEY (cliente_id) REFERENCES clientes(id))")

cur.execute("CREATE TABLE empleados (id INTEGER PRIMARY KEY, nombre TEXT, nivel INTEGER, fecha_contrato TEXT)")

cur.execute("CREATE TABLE contacto_empleados_ticket (id INTEGER PRIMARY KEY, "
            "ticket_id INTEGER,"
            "empleado_id INTEGER,"
            "fecha TEXT,"
            "tiempo REAL,"
            "FOREIGN KEY (ticket_id) REFERENCES tickets(id),"
            "FOREIGN KEY (empleado_id) REFERENCES empleados(id))")

con.commit()
con.close()