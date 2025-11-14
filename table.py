import psycopg2

# Conexión a la base de datos de Render
conn = psycopg2.connect(
    host="dpg-d4bbgqf5r7bs7392def0-a.oregon-postgres.render.com",
    database="dataset_flags",
    user="dataset_flags_user",
    password="0lqRQBeVEvULYsxSsrfNu5ISPlFE14lc",
    port=5432
)
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute("""
CREATE TABLE IF NOT EXISTS flags (
    id SERIAL PRIMARY KEY,
    poligono VARCHAR(50),
    color VARCHAR(50),
    img BYTEA
)
""")

conn.commit()
cursor.close()
conn.close()
print("Tabla creada en Render sin instalar PostgreSQL localmente")
