import os
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st
from dateutil import parser
import pdfplumber

st.set_page_config(page_title="Control de Vencimientos", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
COMPROBANTES_DIR = os.path.join(BASE_DIR, "comprobantes")
DB_PATH = os.path.join(BASE_DIR, "servicios.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(COMPROBANTES_DIR, exist_ok=True)

def init_db():
 conn = sqlite3.connect(DB_PATH)
 cur = conn.cursor()
 cur.execute("""
 CREATE TABLE IF NOT EXISTS documentos (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 usuario TEXT,
 servicio TEXT,
 titular TEXT,
 vencimiento TEXT,
 importe TEXT,
 consumo TEXT,
 periodo TEXT,
 referencia TEXT,
 detalle TEXT,
 pdf_path TEXT,
 comprobante_path TEXT,
 estado TEXT,
 fecha_carga TEXT
 )
 """)
 conn.commit()
 conn.close()

def insert_document(data):
 conn = sqlite3.connect(DB_PATH)
 cur = conn.cursor()
 cur.execute("""
 INSERT INTO documentos (
 usuario, servicio, titular, vencimiento, importe, consumo,
 periodo, referencia, detalle, pdf_path, comprobante_path,
 estado, fecha_carga
 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
 """, data)
 conn.commit()
 conn.close()

def get_documents(usuario):
 conn = sqlite3.connect(DB_PATH)
 df = pd.read_sql_query(
 "SELECT * FROM documentos WHERE usuario = ? ORDER BY vencimiento ASC",
 conn,
 params=(usuario,)
 )
 conn.close()
 return df

def update_estado(doc_id, estado, comprobante_path=None):
 conn = sqlite3.connect(DB_PATH)
 cur = conn.cursor()
 if comprobante_path:
 cur.execute("""
 UPDATE documentos
 SET estado = ?, comprobante_path = ?
 WHERE id = ?
 """, (estado, comprobante_path, doc_id))
 else:
 cur.execute("""
 UPDATE documentos
 SET estado = ?
 WHERE id = ?
 """, (estado, doc_id))
 conn.commit()
 conn.close()

USUARIOS = {
 "usuario1": "1234",
 "usuario2": "1234"
}

if "logged_in" not in st.session_state:
 st.session_state.logged_in = False
if "usuario" not in st.session_state:
 st.session_state.usuario = ""

def login():
 st.title("Control de Vencimientos")
 st.subheader("Ingreso")
 usuario = st.text_input("Usuario")
 clave = st.text_input("Contraseña", type="password")
 if st.button("Ingresar"):
 if usuario in USUARIOS and USUARIOS[usuario] == clave:
 st.session_state.logged_in = True
 st.session_state.usuario = usuario
 st.rerun()
 else:
 st.error("Usuario o contraseña incorrectos")

def extraer_texto_pdf(pdf_path):
 texto = ""
 try:
 with pdfplumber.open(pdf_path) as pdf:
 for page in pdf.pages:
 texto += page.extract_text() or ""
 except:
 pass
 return texto

def detectar_servicio(texto):
 t = texto.lower()
 if "edenor" in t or "epec" in t or "edesur" in t or "luz" in t:
 return "Luz"
 if "naturgy" in t or "gas" in t:
 return "Gas"
 if "aysa" in t or "agua" in t:
 return "Agua"
 if "personal" in t or "movistar" in t or "claro" in t or "telecom" in t or "internet" in t:
 return "Internet"
 if "visa" in t or "mastercard" in t or "amex" in t or "tarjeta" in t:
 return "Tarjeta de Crédito"
 if "municip" in t or "abl" in t:
 return "Municipal"
 return "Desconocido"

def intentar_fecha(texto):
 import re
 patrones = [
 r"\b\d{2}/\d{2}/\d{4}\b",
 r"\b\d{2}-\d{2}-\d{4}\b"
 ]
 for p in patrones:
 m = re.search(p, texto)
 if m:
 try:
 return parser.parse(m.group(), dayfirst=True).strftime("%Y-%m-%d")
 except:
 pass
 return ""

def intentar_importe(texto):
 import re
 patrones = [
 r"\$\s?[\d\.\,]+",
 r"importe\s*total[:\s]*\$?\s?[\d\.\,]+",
 r"total a pagar[:\s]*\$?\s?[\d\.\,]+"
 ]
 for p in patrones:
 m = re.search(p, texto.lower())
 if m:
 val = m.group()
 val = val.replace("importe total", "").replace("total a pagar", "").replace("$", "").strip()
 return val
 return ""

init_db()

if not st.session_state.logged_in:
 login()
 st.stop()

st.sidebar.title("Control de Vencimientos")
st.sidebar.write(f"Usuario: **{st.session_state.usuario}**")
if st.sidebar.button("Cerrar sesión"):
 st.session_state.logged_in = False
 st.session_state.usuario = ""
 st.rerun()

st.title("Control de Vencimientos")
st.caption("Dashboard personal de servicios y vencimientos")

df = get_documents(st.session_state.usuario)

col1, col2, col3, col4 = st.columns(4)
if not df.empty:
 hoy = datetime.now().date()
 df["vencimiento_dt"] = pd.to_datetime(df["vencimiento"], errors="coerce")
 df["estado_calc"] = df.apply(
 lambda r: "Abonada" if str(r["estado"]).lower() == "abonada"
 else ("Vence en 5 días" if pd.notnull(r["vencimiento_dt"]) and 0 <= (r["vencimiento_dt"].date() - hoy).days <= 5
 else ("Vencida" if pd.notnull(r["vencimiento_dt"]) and (r["vencimiento_dt"].date() - hoy).days < 0
 else "Normal")),
 axis=1
 )
 col1.metric("Total cargados", len(df))
 col2.metric("Abonadas", int((df["estado"].fillna("").str.lower() == "abonada").sum()))
 col3.metric("Vencidas", int((df["estado_calc"] == "Vencida").sum()))
 col4.metric("Vence en 5 días", int((df["estado_calc"] == "Vence en 5 días").sum()))
else:
 col1.metric("Total cargados", 0)
 col2.metric("Abonadas", 0)
 col3.metric("Vencidas", 0)
 col4.metric("Vence en 5 días", 0)

st.divider()

st.subheader("Subir PDF de servicio")
pdf = st.file_uploader("Seleccioná un PDF", type=["pdf"])

if pdf is not None:
 if st.button("Procesar PDF"):
 path = os.path.join(UPLOAD_DIR, pdf.name)
 with open(path, "wb") as f:
 f.write(pdf.read())

 texto = extraer_texto_pdf(path)
 servicio = detectar_servicio(texto)
 vencimiento = intentar_fecha(texto)
 importe = intentar_importe(texto)

 nueva_data = (
 st.session_state.usuario,
 servicio,
 "",
 vencimiento,
 importe,
 "",
 "",
 "",
 "",
 path,
 "",
 "Pendiente",
 datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 )
 insert_document(nueva_data)
 st.success("PDF procesado y guardado")

st.divider()

st.subheader("Servicios cargados")

if df.empty:
 st.info("Todavía no hay documentos cargados.")
else:
 mostrar = df.copy()
 mostrar["estado_final"] = mostrar["estado"]
 mostrar.loc[mostrar["estado_final"].str.lower() == "abonada", "estado_final"] = "Abonada"
 mostrar.loc[mostrar["estado_calc"] == "Vence en 5 días", "estado_final"] = "Vence en 5 días"
 mostrar.loc[mostrar["estado_calc"] == "Vencida", "estado_final"] = "Vencida"

 st.dataframe(
 mostrar[["id", "servicio", "titular", "vencimiento", "importe", "consumo", "periodo", "referencia", "estado_final"]],
 use_container_width=True
 )

 for _, row in mostrar.iterrows():
 with st.expander(f"{row['servicio']} - Vence: {row['vencimiento']} - Estado: {row['estado_final']}"):
 comprobante = st.file_uploader(
 f"Subir comprobante para ID {row['id']}",
 type=["pdf", "png", "jpg", "jpeg"],
 key=f"comp_{row['id']}"
 )
 if comprobante is not None:
 comp_path = os.path.join(COMPROBANTES_DIR, comprobante.name)
 with open(comp_path, "wb") as f:
 f.write(comprobante.read())
 update_estado(row["id"], "Abonada", comp_path)
 st.success("Comprobante cargado. Estado cambiado a Abonada.")
 st.rerun()
2) Guardalo
Bajá y tocá Commit changes.

3) Después hacé esto mismo para las carpetas
Creá dos archivos vacíos:

uploads/.gitkeep
Add file > Create new file
escribí: uploads/.gitkeep
dejalo vacío
Commit changes
comprobantes/.gitkeep
Add file > Create new file
escribí: comprobantes/.gitkeep
dejalo vacío
Commit changes
4) Cuando termines
Decime exactamente:

“ya subí app.py”

y seguimos con el siguiente paso, que es conectarlo a Streamlit Cloud.




no encuentro donde dice ahora crear new file cambio la pantalla de inicio , esta como te la envie en la ultima foto

Perfecto, eso es normal. Estás en la pantalla principal del repo y ahí no siempre aparece “Create new file” a simple vista.

Hacé esto:
Opción 1: desde el botón verde
Buscá el botón verde que dice:

Code

Si no estás viendo “Add file”, probá esto:

Tocá Code
Mirá si abajo aparece Create new file o Upload files
Opción 2: usar la barra de arriba
En la parte superior del repo suele aparecer algo como:

Code
Issues
Pull requests
Actions
Projects
Wiki
Security
Tenés que estar en Code.

Ahí debería aparecer un botón o menú que dice:

Add file
Upload files
Create new file
Opción 3: si no aparece, te explico el atajo
En GitHub, muchas veces podés crear un archivo así:

Entrá al repo
En la barra de dirección del navegador, al final de la URL escribí:
txt


/new/main
o directamente:

txt


github.com/TU_USUARIO/control-vencimientos/new/main
Eso abre la pantalla para crear un archivo nuevo.

Lo más probable
Si ves solo la pantalla inicial del repo, hacé esto:

asegurate de estar en la pestaña Code
buscá el botón Add file
dentro de ese menú está Create new file
Si querés, te guío paso a paso según lo que veas
Decime cuál de estas opciones ves en pantalla:

Code
Add file
Upload files
Create new file
y te digo exactamente qué tocar.




Captura.PNG
done

Perfecto, ya veo la pantalla.

Ahora hacé esto:
Cerrá el menú de Code porque ese es para clonar, no para crear archivos.

Paso 1
Arriba, al lado del botón verde Code, tenés que tocar:

Add file
Paso 2
Se abre un menú y ahí elegís:

Create new file
Paso 3
Ahí sí creás el archivo.

Empecemos por requirements.txt
En el nombre del archivo escribí:
txt


requirements.txt
Pegá esto adentro:
txt


streamlit
pandas
openpyxl
pdfplumber
PyMuPDF
python-dateutil
Después:
Bajá hasta el final y tocá:

Commit changes
Después seguimos con app.py
Pero primero hacé solo requirements.txt.

Si no ves “Add file”
En tu imagen sí se ve, está justo:

al lado de “Go to file”
antes del botón verde Code
Lo que tenés que hacer ahora
cerrá el panel de Code
tocá Add file
tocá Create new file
creá requirements.txt
pegá el contenido
Commit changes
Cuando lo tengas, decime: “ya subí requirements” y seguimos con el siguiente archivo.




marcamelo en la imagen porque no lo veo

Puedo ayudarte, pero acá no puedo dibujar sobre la imagen directamente.

Te lo marco con texto exacto para que lo ubiques rápido:

Dónde está
En la fila superior del repositorio, buscá esto:

a la izquierda: nombre del repo
en el centro: Code / Issues / Pull requests / Actions
debajo o cerca de ahí: Go to file
a la derecha de “Go to file” aparece el botón que dice:
Add file
Y dentro de ese menú está:

Create new file
Cómo encontrarlo fácil
Mirá la parte de arriba del repo
Buscá el botón verde Code
A su izquierda, o cerca de esa zona, está Add file
Tocá Add file
Elegí Create new file
Si no te aparece Add file
Probá esto:

Escribir la URL manual
En la barra del navegador, al final de la URL del repo poné:

txt


/new/main
Ejemplo:

txt


https://github.com/TU_USUARIO/control-vencimientos/new/main
Eso te lleva directo a crear un archivo nuevo.

Si querés, te voy guiando con lo que ves
Mandame una respuesta corta con una de estas opciones:

veo Code
veo Go to file
veo Add file
no veo nada
Y te digo el clic exacto según tu pantalla.




ya lo encontre ahora decime denuevo que colocar

Perfecto. Ahora hacé esto:

Nombre del archivo
txt


requirements.txt
Pegá este contenido:
txt


streamlit
pandas
openpyxl
pdfplumber
PyMuPDF
python-dateutil
Después
Bajá hasta el final y tocá:

Commit changes

Cuando lo tengas, decime: “ya quedó requirements”

y te paso el siguiente archivo.




ya quedo requeriments

Perfecto. Ahora seguimos con app.py.

Paso 1
Volvé al repo.

Paso 2
Tocá otra vez: Add file → Create new file

Paso 3
En el nombre del archivo escribí:

txt


app.py
Paso 4
Pegá este código completo:

python


import os
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st
from dateutil import parser
import pdfplumber

st.set_page_config(page_title="Control de Vencimientos", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
COMPROBANTES_DIR = os.path.join(BASE_DIR, "comprobantes")
DB_PATH = os.path.join(BASE_DIR, "servicios.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(COMPROBANTES_DIR, exist_ok=True)

def init_db():
 conn = sqlite3.connect(DB_PATH)
 cur = conn.cursor()
 cur.execute("""
 CREATE TABLE IF NOT EXISTS documentos (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 usuario TEXT,
 servicio TEXT,
 titular TEXT,
 vencimiento TEXT,
 importe TEXT,
 consumo TEXT,
 periodo TEXT,
 referencia TEXT,
 detalle TEXT,
 pdf_path TEXT,
 comprobante_path TEXT,
 estado TEXT,
 fecha_carga TEXT
 )
 """)
 conn.commit()
 conn.close()

def insert_document(data):
 conn = sqlite3.connect(DB_PATH)
 cur = conn.cursor()
 cur.execute("""
 INSERT INTO documentos (
 usuario, servicio, titular, vencimiento, importe, consumo,
 periodo, referencia, detalle, pdf_path, comprobante_path,
 estado, fecha_carga
 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
 """, data)
 conn.commit()
 conn.close()

def get_documents(usuario):
 conn = sqlite3.connect(DB_PATH)
 df = pd.read_sql_query(
 "SELECT * FROM documentos WHERE usuario = ? ORDER BY vencimiento ASC",
 conn,
 params=(usuario,)
 )
 conn.close()
 return df

def update_estado(doc_id, estado, comprobante_path=None):
 conn = sqlite3.connect(DB_PATH)
 cur = conn.cursor()
 if comprobante_path:
 cur.execute("""
 UPDATE documentos
 SET estado = ?, comprobante_path = ?
 WHERE id = ?
 """, (estado, comprobante_path, doc_id))
 else:
 cur.execute("""
 UPDATE documentos
 SET estado = ?
 WHERE id = ?
 """, (estado, doc_id))
 conn.commit()
 conn.close()

USUARIOS = {
 "usuario1": "1234",
 "usuario2": "1234"
}

if "logged_in" not in st.session_state:
 st.session_state.logged_in = False
if "usuario" not in st.session_state:
 st.session_state.usuario = ""

def login():
 st.title("Control de Vencimientos")
 st.subheader("Ingreso")
 usuario = st.text_input("Usuario")
 clave = st.text_input("Contraseña", type="password")
 if st.button("Ingresar"):
 if usuario in USUARIOS and USUARIOS[usuario] == clave:
 st.session_state.logged_in = True
 st.session_state.usuario = usuario
 st.rerun()
 else:
 st.error("Usuario o contraseña incorrectos")

def extraer_texto_pdf(pdf_path):
 texto = ""
 try:
 with pdfplumber.open(pdf_path) as pdf:
 for page in pdf.pages:
 texto += page.extract_text() or ""
 except:
 pass
 return texto

def detectar_servicio(texto):
 t = texto.lower()
 if "edenor" in t or "epec" in t or "edesur" in t or "luz" in t:
 return "Luz"
 if "naturgy" in t or "gas" in t:
 return "Gas"
 if "aysa" in t or "agua" in t:
 return "Agua"
 if "personal" in t or "movistar" in t or "claro" in t or "telecom" in t or "internet" in t:
 return "Internet"
 if "visa" in t or "mastercard" in t or "amex" in t or "tarjeta" in t:
 return "Tarjeta de Crédito"
 if "municip" in t or "abl" in t:
 return "Municipal"
 return "Desconocido"

def intentar_fecha(texto):
 import re
 patrones = [
 r"\b\d{2}/\d{2}/\d{4}\b",
 r"\b\d{2}-\d{2}-\d{4}\b"
 ]
 for p in patrones:
 m = re.search(p, texto)
 if m:
 try:
 return parser.parse(m.group(), dayfirst=True).strftime("%Y-%m-%d")
 except:
 pass
 return ""

def intentar_importe(texto):
 import re
 patrones = [
 r"\$\s?[\d\.\,]+",
 r"importe\s*total[:\s]*\$?\s?[\d\.\,]+",
 r"total a pagar[:\s]*\$?\s?[\d\.\,]+"
 ]
 for p in patrones:
 m = re.search(p, texto.lower())
 if m:
 val = m.group()
 val = val.replace("importe total", "").replace("total a pagar", "").replace("$", "").strip()
 return val
 return ""

init_db()

if not st.session_state.logged_in:
 login()
 st.stop()

st.sidebar.title("Control de Vencimientos")
st.sidebar.write(f"Usuario: **{st.session_state.usuario}**")
if st.sidebar.button("Cerrar sesión"):
 st.session_state.logged_in = False
 st.session_state.usuario = ""
 st.rerun()

st.title("Control de Vencimientos")
st.caption("Dashboard personal de servicios y vencimientos")

df = get_documents(st.session_state.usuario)

col1, col2, col3, col4 = st.columns(4)
if not df.empty:
 hoy = datetime.now().date()
 df["vencimiento_dt"] = pd.to_datetime(df["vencimiento"], errors="coerce")
 df["estado_calc"] = df.apply(
 lambda r: "Abonada" if str(r["estado"]).lower() == "abonada"
 else ("Vence en 5 días" if pd.notnull(r["vencimiento_dt"]) and 0 <= (r["vencimiento_dt"].date() - hoy).days <= 5
 else ("Vencida" if pd.notnull(r["vencimiento_dt"]) and (r["vencimiento_dt"].date() - hoy).days < 0
 else "Normal")),
 axis=1
 )
 col1.metric("Total cargados", len(df))
 col2.metric("Abonadas", int((df["estado"].fillna("").str.lower() == "abonada").sum()))
 col3.metric("Vencidas", int((df["estado_calc"] == "Vencida").sum()))
 col4.metric("Vence en 5 días", int((df["estado_calc"] == "Vence en 5 días").sum()))
else:
 col1.metric("Total cargados", 0)
 col2.metric("Abonadas", 0)
 col3.metric("Vencidas", 0)
 col4.metric("Vence en 5 días", 0)

st.divider()

st.subheader("Subir PDF de servicio")
pdf = st.file_uploader("Seleccioná un PDF", type=["pdf"])

if pdf is not None:
 if st.button("Procesar PDF"):
 path = os.path.join(UPLOAD_DIR, pdf.name)
 with open(path, "wb") as f:
 f.write(pdf.read())

 texto = extraer_texto_pdf(path)
 servicio = detectar_servicio(texto)
 vencimiento = intentar_fecha(texto)
 importe = intentar_importe(texto)

 nueva_data = (
 st.session_state.usuario,
 servicio,
 "",
 vencimiento,
 importe,
 "",
 "",
 "",
 "",
 path,
 "",
 "Pendiente",
 datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 )
 insert_document(nueva_data)
 st.success("PDF procesado y guardado")

st.divider()

st.subheader("Servicios cargados")

if df.empty:
 st.info("Todavía no hay documentos cargados.")
else:
 mostrar = df.copy()
 mostrar["estado_final"] = mostrar["estado"]
 mostrar.loc[mostrar["estado_final"].str.lower() == "abonada", "estado_final"] = "Abonada"
 mostrar.loc[mostrar["estado_calc"] == "Vence en 5 días", "estado_final"] = "Vence en 5 días"
 mostrar.loc[mostrar["estado_calc"] == "Vencida", "estado_final"] = "Vencida"

 st.dataframe(
 mostrar[["id", "servicio", "titular", "vencimiento", "importe", "consumo", "periodo", "referencia", "estado_final"]],
 use_container_width=True
 )

 for _, row in mostrar.iterrows():
 with st.expander(f"{row['servicio']} - Vence: {row['vencimiento']} - Estado: {row['estado_final']}"):
 comprobante = st.file_uploader(
 f"Subir comprobante para ID {row['id']}",
 type=["pdf", "png", "jpg", "jpeg"],
 key=f"comp_{row['id']}"
 )
 if comprobante is not None:
 comp_path = os.path.join(COMPROBANTES_DIR, comprobante.name)
 with open(comp_path, "wb") as f:
 f.write(comprobante.read())
 update_estado(row["id"], "Abonada", comp_path)
 st.success("Comprobante cargado. Estado cambiado a Abonada.")
 st.rerun()
