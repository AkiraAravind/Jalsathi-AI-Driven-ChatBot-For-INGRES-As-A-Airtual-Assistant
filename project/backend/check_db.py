import psycopg2
conn = psycopg2.connect('postgresql://postgres:postgres@127.0.0.1:54322/postgres')
cursor = conn.cursor()
cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='users'")
for row in cursor.fetchall():
    print(row)
