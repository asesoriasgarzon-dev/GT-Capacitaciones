import streamlit as st
import pandas as pd
import os
import io
import pytz
import qrcode
import threading
import random
import plotly.express as px
import time
import zipfile
from urllib.parse import unquote
from io import BytesIO
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from PIL import Image
from streamlit_gsheets import GSheetsConnection
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# =============================================================================
# CONFIGURACIÓN DE PÁGINA
# =============================================================================
st.set_page_config(
    page_title="REGISTRO DE ASISTENCIA DIGITAL - MIP",
    layout="centered",
    page_icon="🏗️"
)

# =============================================================================
# SESSION STATE
# =============================================================================
TOTAL_PAGINAS = 4
st.session_state.setdefault("rol", None)
st.session_state.setdefault("paso", 0)          # 0 = autorización imagen
st.session_state.setdefault("tema_actual", None)
st.session_state.setdefault("modulo", None)
st.session_state.setdefault("esperando_clave", False)
st.session_state.setdefault("resumen_actual", "")
st.session_state.setdefault("tipo_actividad", "CAPACITACIÓN")
st.session_state.setdefault("actividad_seleccionada", None)
st.session_state.setdefault("filtro_admin", {})
st.session_state.setdefault("logs", [])

# =============================================================================
# CSS CORPORATIVO MIP
# =============================================================================
CSS_CORPORATIVO = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700;800&display=swap');

    * {
        font-family: 'Century Gothic', 'CenturyGothic', 'Nunito', 'Apple Gothic', sans-serif !important;
    }

    .stApp { 
        background-color: #F4F7FA !important;
        position: relative !important;
    }

    .stApp::before {
        content: '' !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        background-image: url('https://raw.githubusercontent.com/asesoriasgarzon-dev/GT-Capacitaciones/main/assets/Fondo_MIP.png') !important;
        background-size: cover !important;
        background-position: center center !important;
        background-repeat: no-repeat !important;
        opacity: 0.35 !important;
        z-index: 0 !important;
        pointer-events: none !important;
    }

    .stApp > * {
        position: relative !important;
        z-index: 1 !important;
    }
    
    [data-testid="stSidebar"] { background-color: #0A2A43; }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    
    .stButton > button {
        background: linear-gradient(135deg,#0A2A43,#1E88E5) !important; 
        color: white !important; 
        border: none !important;
        border-radius: 8px !important; 
        font-weight: 900 !important; 
        font-size: 18px !important; 
        padding: 0.6rem 1.5rem !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    .stButton > button:hover { 
        background-color: #42A5F5 !important; 
        color: #0A2A43 !important;
    }

    h1, h2, h3 {
        color: #0A2A43;
        font-weight: 800 !important;
        letter-spacing: 1px;
    }

    .stTextInput > div > div > input {
        border: 2px solid #1E88E5; border-radius: 6px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #42A5F5; box-shadow: 0 0 0 2px rgba(66,165,245,0.3);
    }

    [data-testid="stMetricValue"] {
        color: #1E88E5; font-weight: bold;
    }

    .stTabs [data-baseweb="tab"] {
        color: #0A2A43; font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid #42A5F5 !important; color: #0A2A43 !important;
    }

    footer { visibility: hidden; }

    .stDownloadButton > button {
        background-color: #42A5F5; color: #0A2A43;
        font-weight: bold; border: none; border-radius: 8px;
    }
    .stDownloadButton > button:hover { background-color: #0A2A43; color: white; }

    .hero-logos {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: transparent !important;
        width: 100%;
    }

    .hero-logos img {
        height: 65px !important; 
        width: auto !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        object-fit: contain !important;
    }

    .hero-gerencia {
        background: linear-gradient(135deg,#0A2A43,#1E88E5,#42A5F5) !important;
        border-radius: 26px !important;
        padding: 28px 25px !important;
        margin-bottom: 20px !important;
        border: none !important;
        text-align: center !important;
        box-shadow: 0 18px 40px rgba(0,0,0,.16) !important;
    }
    
    .hero-gerencia h1 {
        color: white !important;
        margin: 10px 0 0 0 !important;
        font-size: 32px !important;
        font-weight: 800 !important;
        letter-spacing: 1px !important;
    }

    .hero-mini {
        font-size: 11px !important;
        color: rgba(255, 255, 255, 0.9) !important;
        margin-top: 15px !important;
        opacity: 0.85 !important;
    }

    [data-testid="metric-container"] {
        border-radius: 14px !important;
        padding: 1rem !important;
        background: white !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05) !important;
    }

</style>
"""
st.markdown(CSS_CORPORATIVO, unsafe_allow_html=True)

st.markdown("""
<style>
.main .block-container {
    max-width: 100% !important;
    width: 100% !important;
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    padding-left: 1.8rem !important;
    padding-right: 1.8rem !important;
}
section.main > div {
    max-width: 100% !important;
}
[data-testid="column"] {
    padding: 0.2rem !important;
}
[data-testid="stDataFrame"] {
    width: 100% !important;
}
.stForm {
    width: 100% !important;
}
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
        padding-top: 0.5rem !important;
    }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    .stButton > button { width: 100% !important; }
    [data-testid="metric-container"] { padding: 0.8rem !important; }
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONEXIÓN A DATOS
# =============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

EMAIL_USER = "ghmip2026@gmail.com"
EMAIL_PASS = "xitlgjvjreekydxc"
ADMIN_PASS = st.secrets.get("admin_password", "mip2026")

CARPETA_CERTIFICADOS = "certificados"
os.makedirs(CARPETA_CERTIFICADOS, exist_ok=True)

# =============================================================================
# EMPRESA FIJA – MIP
# =============================================================================
EMPRESA_ACTIVA = {
    "nombre": "MEZCLAS INTEGRALES PROGRAMADAS S.A.S.",
    "logo1": "Logo_Mip-1.png",
    "logo2": "mip_1.png",
    "color": "#0A2A43"
}

# =============================================================================
# PARÁMETROS URL
# =============================================================================
from urllib.parse import unquote
import base64
import zlib

params = st.query_params

# =============================================================================
# FUNCIÓN PARA DESCOMPRIMIR RESUMEN (si algún día lo usas)
# =============================================================================
def descomprimir_resumen(texto):
    try:
        texto_bytes = base64.urlsafe_b64decode(texto.encode())
        texto_final = zlib.decompress(texto_bytes).decode("utf-8")
        return texto_final
    except:
        return ""

# =========================
# TEMA
# =========================
tema_desde_url = unquote(params.get("tema", ""))
if tema_desde_url:
    st.session_state.tema_actual = tema_desde_url.strip().upper()

if not st.session_state.get("tema_actual"):
    st.session_state.tema_actual = "CAPACITACIÓN GENERAL"

tema_actual = st.session_state.tema_actual

# =========================
# RESUMEN
# =========================
resumen_comprimido = params.get("resumen", "")
if resumen_comprimido:
    st.session_state.resumen_actual = descomprimir_resumen(resumen_comprimido).strip()

if not st.session_state.get("resumen_actual"):
    st.session_state.resumen_actual = ""

resumen_actual = st.session_state.resumen_actual

# =========================
# TIPO
# =========================
tipo_desde_url = unquote(params.get("tipo", ""))
if tipo_desde_url:
    st.session_state.tipo_actividad = tipo_desde_url.strip()

if not st.session_state.get("tipo_actividad"):
    st.session_state.tipo_actividad = "CAPACITACIÓN"

tipo_actividad = st.session_state.tipo_actividad

# =========================
# ROL
# =========================
rol_url = params.get("rol")
if rol_url and st.session_state.rol is None:
    if rol_url.lower() == "empleado":
        st.session_state.rol = "Empleado"
    elif rol_url.lower() == "admin":
        st.session_state.rol = "Admin"

# =============================================================================    
# LOGOS EN CACHÉ (se leen una sola vez)
# =============================================================================
@st.cache_resource(show_spinner=False)
def cargar_logos():
    logos = {}
    for clave, ruta in [("mip", "Logo_Mip-1.png")]:
        if os.path.exists(ruta):
            logos[clave] = Image.open(ruta).copy()
    return logos

LOGOS = cargar_logos()

# =============================================================================
# FUNCIONES DE DATOS
# =============================================================================
@st.cache_data(ttl=60, show_spinner=False)
def obtener_datos():
    """Carga empleados.xlsx (si existe)."""
    ruta = "empleados.xlsx"
    if os.path.exists(ruta):
        try:
            df = pd.read_excel(ruta, engine="openpyxl", dtype={"ID": str})
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"Error al leer empleados.xlsx: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def leer_asistencias():
    """Lectura de asistencias desde Google Sheets."""
    try:
        df = conn.read(worksheet="Hoja")
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Error leyendo asistencias: {e}")
        return pd.DataFrame()

def guardar_en_google_sheets(datos):
    """Guarda una asistencia con reintentos para evitar colisiones."""
    import time
    try:
        if not datos.get("ID") or not datos.get("Nombre"):
            st.error("Datos incompletos")
            return False

        nueva_fila = pd.DataFrame([{
            "Fecha":   datos.get("Fecha"),
            "ID":      str(datos.get("ID")),
            "Nombre":  datos.get("Nombre"),
            "Empresa": datos.get("Empresa"),
            "Cargo":   datos.get("Cargo", "NO REGISTRA"),
            "Tema":    datos.get("Tema"),
            "RutaPDF": datos.get("RutaPDF", ""),
            "LinkPDF": datos.get("LinkPDF", ""),
            "Tipo":    datos.get("Tipo", "CAPACITACIÓN")
        }])

        for intento in range(4):
            try:
                actual = conn.read(worksheet="Hoja", ttl=0)
                if actual is None or actual.empty:
                    df_final = nueva_fila
                else:
                    actual = actual.dropna(how="all")
                    df_final = pd.concat([actual, nueva_fila], ignore_index=True)

                conn.update(worksheet="Hoja", data=df_final)
                leer_asistencias.clear()
                return True

            except Exception:
                time.sleep(random.uniform(1, 4))

        return False

    except Exception as e:
        st.error(f"Error guardando en Google Sheets: {e}")
        return False


# =============================================================================
# FUNCIÓN DE ENVÍO DE CORREO (ASÍNCRONO)
# =============================================================================
def enviar_respaldo_async(datos, pdf_bytes):

    def _proceso_envio():
        try:
            print("📩 Enviando respaldo a RRHH...")

            msg = MIMEMultipart()
            msg['From'] = EMAIL_USER
            msg['To'] = EMAIL_USER
            msg['Subject'] = f"📄 Asistencia registrada: {datos['Nombre']} - {datos['Tema']}"

            cuerpo = f"""
            <html>
            <body style="font-family: Arial;">
                <h2 style="color:#0A2A43;">📋 Respaldo de Asistencia</h2>

                <p><b>Empleado:</b> {datos['Nombre']}</p>
                <p><b>Cédula:</b> {datos['ID']}</p>
                <p><b>Empresa:</b> {datos['Empresa']}</p>
                <p><b>Cargo:</b> {datos.get('Cargo', 'NO REGISTRA')}</p>
                <p><b>Tema:</b> {datos['Tema']}</p>
                <p><b>Fecha:</b> {datos['Fecha']}</p>

                <hr>
                <small>Enviado automáticamente desde MIP</small>
            </body>
            </html>
            """

            msg.attach(MIMEText(cuerpo, 'html'))

            # PDF adjunto
            adjunto = MIMEBase('application', 'octet-stream')
            adjunto.set_payload(pdf_bytes)
            encoders.encode_base64(adjunto)
            adjunto.add_header(
                'Content-Disposition',
                f"attachment; filename=Certificado_{datos['ID']}.pdf"
            )
            msg.attach(adjunto)

            # Envío
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, [EMAIL_USER], msg.as_string())
            server.quit()

            print(f"✅ CORREO ENVIADO para {datos['ID']}")

        except Exception as e:
            import traceback
            print("❌ ERROR EN CORREO:")
            print(traceback.format_exc())

    threading.Thread(target=_proceso_envio, daemon=True).start()

# =============================================================================
# SUBIR PDF A GOOGLE DRIVE
# =============================================================================
def subir_pdf_drive(pdf_buffer, nombre_archivo):
    try:
        SCOPES = ['https://www.googleapis.com/auth/drive']

        creds = service_account.Credentials.from_service_account_info(
            dict(st.secrets["connections"]["gsheets"]),
            scopes=SCOPES
        )

        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': nombre_archivo,
            'parents': [st.secrets["DRIVE_FOLDER_ID"]]
        }

        media = MediaIoBaseUpload(
            pdf_buffer,
            mimetype='application/pdf',
            resumable=True
        )

        archivo = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        print(f"✅ PDF SUBIDO A DRIVE: {nombre_archivo}")
        return archivo

    except Exception as e:
        print(f"❌ ERROR GOOGLE DRIVE: {e}")
        return None

# =============================================================================
# GENERACIÓN DE PDF MIP
# =============================================================================
def generar_pdf(datos, imagen_firma, imagen_foto):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    azul_oscuro = (0.04, 0.16, 0.26)
    azul_medio  = (0.12, 0.53, 0.90)
    azul_claro  = (0.26, 0.65, 0.96)
    gris_fondo  = (0.96, 0.97, 0.98)

    # Fondo
    p.setFillColorRGB(1, 1, 1)
    p.rect(0, 0, width, height, fill=1, stroke=0)

    # Marco
    p.setStrokeColorRGB(*azul_oscuro)
    p.setLineWidth(1.4)
    p.roundRect(20, 20, width - 40, height - 40, 14)

    # Encabezado
    p.setFillColorRGB(*azul_oscuro)
    p.roundRect(20, height - 125, width - 40, 105, 14, fill=1, stroke=0)

    # Línea decorativa
    p.setFillColorRGB(*azul_claro)
    p.rect(20, height - 125, width - 40, 5, fill=1, stroke=0)

    # Logos
    for clave, x in [("mip", 35)]:
        if clave in LOGOS:
            try:
                img_logo = LOGOS[clave].convert("RGBA")
                buf_logo = BytesIO()
                img_logo.save(buf_logo, format="PNG")
                buf_logo.seek(0)

                p.drawImage(
                    ImageReader(buf_logo),
                    x, height - 112,
                    width=110, height=72,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception as ex:
                print(f"[PDF LOGO] {ex}")

    # Título
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width / 2, height - 80, "CERTIFICADO DE ASISTENCIA")

    # Texto central
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, 610, "Se certifica que:")

    p.setFillColorRGB(*azul_oscuro)
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, 575, datos["Nombre"].upper())

    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 12)
    p.drawCentredString(
        width / 2,
        545,
        f"Identificado(a) con documento No. {datos['ID']} asistió a:"
    )

    # Bloque de capacitación
    resumen = datos.get("Resumen", "")
    tipo    = datos.get("Tipo", "CAPACITACIÓN")

    alto_rect = 125 if resumen else 100

    p.setFillColorRGB(*gris_fondo)
    p.roundRect(60, 405, width - 120, alto_rect, 10, fill=1, stroke=0)

    # Tipo
    p.setFillColorRGB(*azul_oscuro)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(80, 405 + alto_rect - 14, f"{tipo}:")

    # Tema
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(80, 405 + alto_rect - 30, datos["Tema"])

    # Resumen
    if resumen:
        p.setFont("Helvetica", 9)
        p.setFillColorRGB(0.3, 0.3, 0.3)

        palabras = resumen.split()
        linea = ""
        y_res = 405 + alto_rect - 48

        for palabra in palabras:
            prueba = linea + " " + palabra if linea else palabra
            if p.stringWidth(prueba, "Helvetica", 9) < (width - 160):
                linea = prueba
            else:
                p.drawString(80, y_res, linea)
                y_res -= 13
                linea = palabra

        if linea:
            p.drawString(80, y_res, linea)

    # Datos
    p.setFont("Helvetica", 11)
    p.drawString(80, 385, f"Empresa: {datos['Empresa']}")
    p.drawString(80, 365, f"Cargo: {datos.get('Cargo', 'NO REGISTRA')}")
    p.drawString(80, 345, f"Fecha Registro: {datos['Fecha']}")

    base_y = 185

    # Foto
    if imagen_foto is not None:
        try:
            img = Image.open(imagen_foto).convert("RGB")
            img.thumbnail((150, 150))
            p.drawImage(ImageReader(img), 75, base_y, width=110, height=110)
            p.setFont("Helvetica", 8)
            p.drawCentredString(130, base_y - 12, "Validación de Registro")
        except Exception as ex:
            print(f"[PDF FOTO] {ex}")

    # Firma
    if imagen_firma is not None:
        try:
            p.drawImage(
                ImageReader(imagen_firma),
                width - 255,
                base_y + 28,
                width=145,
                height=55,
                preserveAspectRatio=True,
            )
        except Exception as ex:
            print(f"[PDF FIRMA] {ex}")

    p.setStrokeColorRGB(*azul_oscuro)
    p.line(width - 275, base_y + 18, width - 95, base_y + 18)

    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(width - 185, base_y + 3, "Firma Autorizada")

    # Pie
    p.setFillColorRGB(*azul_medio)
    p.roundRect(20, 20, width - 40, 25, 0, fill=1, stroke=0)

    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica", 8)
    p.drawCentredString(width / 2, 30, "Documento digital emitido por MEZCLAS INTEGRALES PROGRAMADAS S.A.S.")

    p.showPage()
    p.save()
    buffer.seek(0)

    return buffer

# =============================================================================
# PANTALLA DE LOGIN INICIAL
# =============================================================================
if "rol" not in st.session_state:
    st.session_state.rol = None

# Manejo de rol desde URL
if rol_url and rol_url.lower() == "empleado":
    st.session_state.rol = "Empleado"

# Si no hay rol, mostrar pantalla de acceso
if st.session_state.get("rol") is None:

    st.markdown("""
    <style>
    .hero-gerencia {
        background: linear-gradient(135deg,#0A2A43,#1E88E5,#42A5F5);
        padding: 28px 25px;
        border-radius: 26px;
        text-align:center;
        color:white;
        box-shadow:0 18px 40px rgba(0,0,0,.16);
        margin-bottom:18px;
    }
    .hero-gerencia h1 {
        margin:0;
        font-size:38px;
        font-weight:800;
        letter-spacing:1px;
        color: white !important;
    }
    .titulo-acceso {
        text-align:center;
        color:#0A2A43;
        font-size:36px;
        font-weight:800;
        margin-top:8px;
    }
    .sub-acceso {
        text-align:center;
        color:#6b7280;
        font-size:16px;
        margin-bottom:18px;
    }
    .stButton > button {
        height:70px !important;
        border-radius:18px !important;
        font-size:22px !important;
        font-weight:800 !important;
        border:none !important;
        background:linear-gradient(135deg,#0A2A43,#1E88E5) !important;
        color:white !important;
        box-shadow:0 10px 22px rgba(27,94,32,.20);
    }
    .stButton > button:hover {
        transform:translateY(-2px);
        background: #42A5F5 !important;
        color: #0A2A43 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hero-gerencia">
        <h1>REGISTRO DE ASISTENCIA MIP</h1>
        <div class="hero-mini">Sistema Digital de Control de Asistencia</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h2 class='titulo-acceso'>Selecciona tu tipo de acceso</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Empleado"):
            st.session_state.rol = "Empleado"
            st.rerun()

    with col2:
        if st.button("Administrador"):
            st.session_state.rol = "Admin"
            st.rerun()

    st.stop()

# =============================================================================
# FLUJO DEL EMPLEADO
# =============================================================================
if st.session_state.rol == "Empleado":

    paso = st.session_state.paso

    # ============================
    # PASO 0 — AUTORIZACIÓN
    # ============================
    if paso == 0:
        st.title("Autorización de Uso de Imagen")

        st.write("""
        Para continuar con el registro de asistencia, autoriza el uso de tu imagen
        para validar tu identidad en el certificado digital.
        """)

        if st.button("Autorizo y deseo continuar"):
            st.session_state.paso = 1
            st.rerun()

        st.stop()

    # ============================
    # PASO 1 — INGRESO DE CÉDULA
    # ============================
    if paso == 1:
        st.title("Identificación del Empleado")

        cedula = st.text_input("Ingresa tu número de documento:", max_chars=15)

        if st.button("Continuar"):
            if not cedula.strip():
                st.error("Debes ingresar un número de documento.")
                st.stop()

            df = obtener_datos()

            if df.empty:
                st.error("No se encontró el archivo empleados.xlsx")
                st.stop()

            df["ID"] = df["ID"].astype(str).str.strip()

            fila = df[df["ID"] == cedula.strip()]

            if fila.empty:
                st.error("No se encontró un empleado con ese documento.")
                st.stop()

            empleado = fila.iloc[0].to_dict()

            st.session_state.empleado = empleado
            st.session_state.paso = 2
            st.rerun()

        st.stop()

    # ============================
    # PASO 2 — FOTO
    # ============================
    if paso == 2:
        st.title("Captura de Foto")

        st.write("Toma una fotografía para validar tu identidad.")

        foto = st.camera_input("Tomar Foto")

        if foto:
            st.session_state.foto = foto
            st.session_state.paso = 3
            st.rerun()

        st.stop()

    # ============================
    # PASO 3 — FIRMA
    # ============================
    if paso == 3:
        st.title("Firma Digital")

        st.write("Firma dentro del recuadro para completar tu registro.")

        canvas_result = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=2,
            stroke_color="#0A2A43",
            background_color="#FFFFFF",
            height=200,
            width=500,
            drawing_mode="freedraw",
            key="canvas_firma"
        )

        if st.button("Continuar"):
            if canvas_result.image_data is None:
                st.error("Debes realizar una firma.")
                st.stop()

            firma_buffer = BytesIO()
            Image.fromarray(canvas_result.image_data.astype("uint8")).save(firma_buffer, format="PNG")
            firma_buffer.seek(0)

            st.session_state.firma = firma_buffer
            st.session_state.paso = 4
            st.rerun()

        st.stop()

    # ============================
    # PASO 4 — GENERACIÓN DE CERTIFICADO
    # ============================
    if paso == 4:
        st.title("Generando Certificado...")

        empleado = st.session_state.empleado
        foto = st.session_state.foto
        firma = st.session_state.firma

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        datos = {
            "ID": empleado["ID"],
            "Nombre": empleado["Nombre"],
            "Empresa": empleado.get("Empresa", "NO REGISTRA"),
            "Cargo": empleado.get("Cargo", "NO REGISTRA"),
            "Tema": st.session_state.tema_actual,
            "Resumen": st.session_state.resumen_actual,
            "Fecha": fecha,
            "Tipo": st.session_state.tipo_actividad
        }

        pdf_buffer = generar_pdf(datos, firma, foto)

        nombre_pdf = f"Certificado_{empleado['ID']}.pdf"

        archivo_drive = subir_pdf_drive(pdf_buffer, nombre_pdf)

        if archivo_drive:
            datos["RutaPDF"] = archivo_drive.get("id", "")
            datos["LinkPDF"] = archivo_drive.get("webViewLink", "")

        guardar_en_google_sheets(datos)

        enviar_respaldo_async(datos, pdf_buffer.getvalue())

        st.success("¡Registro completado con éxito!")

        st.download_button(
            "Descargar Certificado",
            data=pdf_buffer,
            file_name=nombre_pdf,
            mime="application/pdf"
        )

        st.write("Puedes cerrar esta ventana.")

        st.stop()

# =============================================================================
# PANEL ADMINISTRATIVO COMPLETO
# =============================================================================
if st.session_state.rol == "Admin":

    with st.sidebar:
        st.markdown("<h2 style='color:white;'>⚙️ Panel Administrativo</h2>", unsafe_allow_html=True)
        opcion_admin = st.radio(
            "Seleccione un módulo:",
            ["Generar Enlace / QR", "Base de Empleados", "Cargar Personal", "Dashboard", "Historial"]
        )
        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.rol = None
            st.rerun()

    # ───────────────────────────────────────────────────────────────
    # MÓDULO: GENERAR ENLACE
    # ───────────────────────────────────────────────────────────────
    if opcion_admin == "Generar Enlace":
        st.markdown("### 🔗 Generar Enlace")

        tema_input = st.text_input("Tema de la capacitación:")
        tipo_act = st.selectbox("Tipo de actividad:", ["CAPACITACIÓN", "INDUCCIÓN", "REENTRENAMIENTO", "CHARLA", "REUNIÓN"])
        resumen_input = st.text_area("Resumen del contenido:")

        if st.button("Generar Enlace🚀", use_container_width=True):
            if tema_input.strip():
                resumen_bytes = resumen_input.strip().encode('utf-8')
                resumen_comp = zlib.compress(resumen_bytes)
                resumen_b64 = base64.urlsafe_b64encode(resumen_comp).decode('utf-8')

                url_base = st.secrets.get("base_url", "https://asistencias-mip.streamlit.app/")
                url_final = f"{url_base}?rol=Empleado&tema={quote(tema_input.strip().upper())}&tipo={quote(tipo_act)}&resumen={resumen_b64}"

                st.success("Enlace generado:")
                st.write("### Enlace generado:")
                st.code(url_final, language="text")                
            else:
                st.error("Debe ingresar un tema.")

    # ───────────────────────────────────────────────────────────────
    # MÓDULO: BASE DE EMPLEADOS
    # ───────────────────────────────────────────────────────────────
    elif opcion_admin == "Base de Empleados":
        st.markdown("### 👥 Base de Empleados")
        df_emp = obtener_datos()

        if not df_emp.empty:
            st.write(f"Total colaboradores: **{len(df_emp)}**")
            st.dataframe(df_emp, use_container_width=True, hide_index=True)
        else:
            st.warning("No existe archivo empleados.xlsx")

    # ───────────────────────────────────────────────────────────────
    # MÓDULO: CARGA MASIVA
    # ───────────────────────────────────────────────────────────────
    elif opcion_admin == "Cargar Personal":
        st.markdown("### 📤 Cargar o Actualizar Base de Empleados")

        archivo = st.file_uploader("Subir archivo Excel (.xlsx):", type=["xlsx"])

        if archivo is not None:
            try:
                df_test = pd.read_excel(archivo, engine="openpyxl")
                if "ID" in df_test.columns and "Nombre" in df_test.columns:
                    with open("empleados.xlsx", "wb") as f:
                        f.write(archivo.getbuffer())
                    obtener_datos.clear()
                    st.success("Base de empleados actualizada correctamente.")
                else:
                    st.error("El archivo debe contener las columnas 'ID' y 'Nombre'.")
            except Exception as e:
                st.error(f"Error procesando archivo: {e}")

    # ───────────────────────────────────────────────────────────────
    # MÓDULO: DASHBOARD
    # ───────────────────────────────────────────────────────────────
    elif opcion_admin == "Dashboard":
        st.markdown("### 📊 Dashboard Analítico")

        df_asist = leer_asistencias()

        if not df_asist.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Registros", len(df_asist))
            c2.metric("Colaboradores Únicos", df_asist["ID"].nunique())
            c3.metric("Temas Dictados", df_asist["Tema"].nunique())

            st.markdown("---")

            df_temas = df_asist["Tema"].value_counts().reset_index()
            df_temas.columns = ["Tema", "Cantidad"]

            fig = px.bar(df_temas, x="Cantidad", y="Tema", orientation="h", color_discrete_sequence=["#0A2A43"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay registros para mostrar.")

    # ───────────────────────────────────────────────────────────────
    # MÓDULO: HISTORIAL
    # ───────────────────────────────────────────────────────────────
    elif opcion_admin == "Historial":
        st.markdown("### 🗄️ Historial de Registros")

        df_asist = leer_asistencias()

        if not df_asist.empty:
            filtro_tema = st.selectbox("Filtrar por tema:", ["TODOS"] + list(df_asist["Tema"].unique()))

            df_filtrado = df_asist.copy()
            if filtro_tema != "TODOS":
                df_filtrado = df_filtrado[df_filtrado["Tema"] == filtro_tema]

            st.write(f"Mostrando **{len(df_filtrado)}** registros:")
            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

            buf_excel = BytesIO()
            with pd.ExcelWriter(buf_excel, engine="openpyxl") as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name="Asistencias")

            st.download_button(
                label="📥 Descargar Excel",
                data=buf_excel.getvalue(),
                file_name=f"Asistencias_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.info("No hay registros disponibles.")
