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
from urllib.parse import unquote, quote
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
import base64
import zlib

# =============================================================================
# CONFIGURACIÓN DE PÁGINA MIP
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

# =============================================================================
# CSS CORPORATIVO MIP
# =============================================================================
CSS_CORPORATIVO = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700;800&display=swap');

    * {
        font-family: 'Century Gothic', 'CenturyGothic', 'Nunito', 'Apple Gothic', sans-serif !important;
    }

    /* ==========================================================
       FONDO PRINCIPAL
       ========================================================== */
    .stApp {

        background-color: #F7FAFC !important;
    
        background-image:
            url("https://raw.githubusercontent.com/asesoriasgarzon-dev/GT-Capacitaciones/main/campo_mip.png") !important;
    
        background-repeat: no-repeat !important;
    
        background-position: center center !important;
    
        background-size: 1000px !important;
    
        background-attachment: fixed !important;
    }
    /* Mantener contenido encima del fondo */
    .stApp > * {
        position: relative !important;
        z-index: 1 !important;
    }

    /* ==========================================================
       SIDEBAR
       ========================================================== */
    [data-testid="stSidebar"] {
        background-color: #0A2A43 !important;
    }

    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }

    /* ==========================================================
       BOTONES
       ========================================================== */
    .stButton > button {
        background: linear-gradient(
            135deg,
            #0A2A43,
            #1565C0,
            #1E88E5
        ) !important;

        color: white !important;
        border: none !important;
        border-radius: 10px !important;

        font-weight: 900 !important;
        font-size: 18px !important;

        padding: 0.70rem 1.50rem !important;

        letter-spacing: 1px !important;
        text-transform: uppercase !important;

        box-shadow:
            0 8px 18px rgba(30,136,229,.25) !important;

        transition: all .25s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        background: linear-gradient(
            135deg,
            #1E88E5,
            #42A5F5
        ) !important;

        color: white !important;
    }

    /* ==========================================================
       TITULOS
       ========================================================== */
    h1, h2, h3 {
        color: #0A2A43 !important;
        font-weight: 800 !important;
        letter-spacing: 1px !important;
    }

    /* ==========================================================
       INPUTS
       ========================================================== */
    .stTextInput > div > div > input {
        border: 2px solid #1E88E5 !important;
        border-radius: 8px !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #42A5F5 !important;
        box-shadow: 0 0 0 3px rgba(66,165,245,0.25) !important;
    }

    /* ==========================================================
       MÉTRICAS
       ========================================================== */
    [data-testid="stMetricValue"] {
        color: #1565C0 !important;
        font-weight: bold !important;
    }

    [data-testid="metric-container"] {
        border-radius: 14px !important;
        padding: 1rem !important;

        background: rgba(255,255,255,0.95) !important;

        backdrop-filter: blur(6px);

        box-shadow:
            0 2px 12px rgba(0,0,0,0.08) !important;
    }

    /* ==========================================================
       TABS
       ========================================================== */
    .stTabs [data-baseweb="tab"] {
        color: #0A2A43 !important;
        font-weight: bold !important;
    }

    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid #42A5F5 !important;
        color: #1565C0 !important;
    }

    /* ==========================================================
       DOWNLOAD BUTTON
       ========================================================== */
    .stDownloadButton > button {
        background: linear-gradient(
            135deg,
            #42A5F5,
            #1E88E5
        ) !important;

        color: white !important;
        font-weight: bold !important;

        border: none !important;
        border-radius: 8px !important;
    }

    .stDownloadButton > button:hover {
        background: #0A2A43 !important;
        color: white !important;
    }

    /* ==========================================================
       HERO LOGOS
       ========================================================== */
    .hero-logos {
        display: flex;
        justify-content: space-between;
        align-items: center;
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

    /* ==========================================================
       BANNER PRINCIPAL
       ========================================================== */
    .hero-gerencia {
        background: linear-gradient(
            135deg,
            #0A2A43,
            #1565C0,
            #42A5F5
        ) !important;

        border-radius: 26px !important;

        padding: 28px 25px !important;

        margin-bottom: 20px !important;

        text-align: center !important;

        box-shadow:
            0 18px 40px rgba(0,0,0,.16) !important;
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
        color: rgba(255,255,255,0.90) !important;
        margin-top: 15px !important;
    }

    .sub-acceso {
        font-weight: 800 !important;
        font-size: 15px !important;
        color: #0A2A43 !important;
    }

    .footer-premium {
        font-weight: 800 !important;
        font-size: 13px !important;
        color: #0A2A43 !important;
    }

    footer {
        visibility: hidden;
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

    background: rgba(255,255,255,0.78) !important;

    backdrop-filter: blur(2px) !important;

    border-radius: 18px !important;
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

    h1 {
        font-size: 1.6rem !important;
    }

    h2 {
        font-size: 1.3rem !important;
    }

    .stButton > button {
        width: 100% !important;
    }

    [data-testid="metric-container"] {
        padding: 0.8rem !important;
    }
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

# =============================================================================
# CARPETAS DEL SISTEMA
# =============================================================================
CARPETA_CERTIFICADOS = "certificados"
os.makedirs(CARPETA_CERTIFICADOS, exist_ok=True)

# =============================================================================
# PARÁMETROS URL
# =============================================================================
params = st.query_params

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
# LOGOS EN CACHÉ
# =============================================================================
@st.cache_resource(show_spinner=False)
def cargar_logos():
    logos = {}
    for clave, ruta in [("mip", "Logo_Mip_blanco.png")]:
        if os.path.exists(ruta):
            logos[clave] = Image.open(ruta).copy()
    return logos

LOGOS = cargar_logos()

# =============================================================================
# FUNCIONES DE DATOS
# =============================================================================
@st.cache_data(ttl=60, show_spinner=False)
def obtener_datos():
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
    try:
        df = conn.read(worksheet="Hoja")
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Error leyendo asistencias: {e}")
        return pd.DataFrame()

def guardar_en_google_sheets(datos):
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
            "Resumen": datos.get("Resumen", ""),
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

    p.setFillColorRGB(1, 1, 1)
    p.rect(0, 0, width, height, fill=1, stroke=0)

    p.setStrokeColorRGB(*azul_oscuro)
    p.setLineWidth(1.4)
    p.roundRect(20, 20, width - 40, height - 40, 14)

    p.setFillColorRGB(*azul_oscuro)
    p.roundRect(20, height - 125, width - 40, 105, 14, fill=1, stroke=0)

    p.setFillColorRGB(*azul_claro)
    p.rect(20, height - 125, width - 40, 5, fill=1, stroke=0)

    if "mip" in LOGOS:
        try:
            img_logo = LOGOS["mip"].convert("RGBA")
            buf_logo = BytesIO()
            img_logo.save(buf_logo, format="PNG")
            buf_logo.seek(0)

            p.drawImage(
                ImageReader(buf_logo),
                35, height - 112,
                width=110, height=72,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception as ex:
            print(f"[PDF LOGO] {ex}")

    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width / 2, height - 80, "CERTIFICADO DE ASISTENCIA")

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

    resumen = datos.get("Resumen", "")
    tipo    = datos.get("Tipo", "CAPACITACIÓN")

    alto_rect = 125 if resumen else 100

    p.setFillColorRGB(*gris_fondo)
    p.roundRect(60, 405, width - 120, alto_rect, 10, fill=1, stroke=0)

    p.setFillColorRGB(*azul_oscuro)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(80, 405 + alto_rect - 14, f"{tipo}:")

    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(80, 405 + alto_rect - 30, datos["Tema"])

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

    p.setFont("Helvetica", 11)
    p.drawString(80, 385, f"Empresa: {datos['Empresa']}")
    p.drawString(80, 365, f"Cargo: {datos.get('Cargo', 'NO REGISTRA')}")
    p.drawString(80, 345, f"Fecha Registro: {datos['Fecha']}")

    base_y = 185

    if imagen_foto is not None:
        try:
            img = Image.open(imagen_foto).convert("RGB")
            img.thumbnail((150, 150))
            p.drawImage(ImageReader(img), 75, base_y, width=110, height=110)
            p.setFont("Helvetica", 8)
            p.drawCentredString(130, base_y - 12, "Validación de Registro")
        except Exception as ex:
            print(f"[PDF FOTO] {ex}")

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
# ENVÍO CORREO ASYNC
# =============================================================================
def enviar_respaldo_async(datos, pdf_bytes):

    def _proceso_envio():
        try:
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

            adjunto = MIMEBase('application', 'octet-stream')
            adjunto.set_payload(pdf_bytes)
            encoders.encode_base64(adjunto)
            adjunto.add_header(
                'Content-Disposition',
                f"attachment; filename=Certificado_{datos['ID']}.pdf"
            )
            msg.attach(adjunto)

            server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, [EMAIL_USER], msg.as_string())
            server.quit()

        except Exception as e:
            print(f"❌ ERROR CORREO: {e}")

    threading.Thread(target=_proceso_envio, daemon=True).start()

# =============================================================================
# PANTALLA DE LOGIN INICIAL
# =============================================================================
if "rol" not in st.session_state:
    st.session_state.rol = None

if 'rol_url' in locals() and rol_url and rol_url.lower() == "empleado":
    st.session_state.rol = "Empleado"

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
    .hero-logos {
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:10px;
    }
    .hero-logo-img {
        background: transparent !important;
        height: 65px !important;
        width: auto !important;
        object-fit: contain;
    }
    .hero-gerencia h1 {
        margin:0;
        font-size:38px;
        font-weight:800;
        letter-spacing:1px;
        color: white !important;
    }
    .hero-mini {
        margin-top: 15px !important;
        font-size: 11px !important;
        opacity: .85;
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
    .footer-premium {
        text-align:center;
        color:#7b7b7b;
        margin-top:18px;
        font-size:15px;
    }
    </style>
    """, unsafe_allow_html=True)

    def logo_to_base64(img_pil):
        buf = BytesIO()
        img_pil.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    logo_mip_html = f'<img src="data:image/png;base64,{logo_to_base64(LOGOS["mip"])}" class="hero-logo-img">' if "mip" in LOGOS else "<div></div>"

    paso = st.session_state.get("paso", 0)
    texto_pagina = f" | Página: {paso} de {TOTAL_PAGINAS}" if paso > 0 else ""

    st.markdown(f"""
    <div class="hero-gerencia">
        <div class="hero-logos">
            {logo_mip_html}
        </div>
        <h1>REGISTRO ASISTENCIA DIGITAL MIP</h1>
        <div class="hero-mini">
            Sistema de control de asistencia • Versión 2026{texto_pagina}
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="titulo-acceso">Acceso Corporativo</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-acceso">Seleccione el perfil para ingresar</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)

        with c1:
            if st.button("INGRESO COLABORADOR", use_container_width=True):
                st.session_state.rol = "Empleado"
                st.session_state.paso = 0
                st.rerun()

        with c2:
            if st.button("INGRESO     ADMINISTRADOR", use_container_width=True):
                st.session_state.esperando_clave = True
                st.rerun()

        if st.session_state.get("esperando_clave"):
            st.markdown("---")
            with st.form("login_admin", clear_on_submit=False):
                clave = st.text_input(
                    "🔑 Ingrese Clave de Administrador:",
                    type="password",
                    placeholder="Contraseña corporativa"
                )
                col_bt1, col_bt2 = st.columns(2)
                with col_bt1:
                    entrar = st.form_submit_button("Entrar")
                with col_bt2:
                    cancelar = st.form_submit_button("Cancelar")

                if entrar:
                    if clave == ADMIN_PASS:
                        st.session_state.rol = "Admin"
                        st.session_state.esperando_clave = False
                        st.rerun()
                    else:
                        st.error("Clave incorrecta ❌")

                if cancelar:
                    st.session_state.esperando_clave = False
                    st.rerun()

        st.markdown(
            '''<div class="footer-premium"> Plataforma Corporativa de Formación y Control de Asistencia<br>© 2026 Mezclas Integrales Programadas S.A.S.</div>''',
            unsafe_allow_html=True
        )

    st.stop()

# =============================================================================
# BARRA SUPERIOR (botón volver + logos + título)
# =============================================================================
if st.session_state.rol == "Admin":

    col_volver, col_vacia = st.columns([1, 4])

    with col_volver:
        if st.button("INICIO", use_container_width=True):

            for key in list(st.session_state.keys()):
                del st.session_state[key]

            st.rerun()

    def logo_b64(img_pil):
        buf = BytesIO()
        img_pil.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    logo_mip = (
        f'<img src="data:image/png;base64,{logo_b64(LOGOS["mip"])}" class="hero-logo-img">'
        if "mip" in LOGOS else ""
    )

    paso = st.session_state.get("paso", 0)
    texto_pagina = f" | Página: {paso} de {TOTAL_PAGINAS}" if paso > 0 else ""

    st.markdown(f"""
        <div class="hero-gerencia">
            <div class="hero-logos">
                {logo_mip}
            </div>
            <h1>REGISTRO ASISTENCIA DIGITAL MIP</h1>
            <div class="hero-mini">
                Sistema de control de asistencia • Versión 2026{texto_pagina}
            </div>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# MENÚ SEGÚN ROL
# =============================================================================
if st.session_state.rol == "Empleado":
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display:none;}
        #MainMenu {visibility:hidden;}
        header {visibility:hidden;}
    </style>
    """, unsafe_allow_html=True)
    menu = "Registro Asistencia"

else:
    with st.sidebar:
        if "mip" in LOGOS:
            st.image(LOGOS["mip"], width=180)
        st.markdown("## Panel Administrativo")
        st.markdown("Gestión Humana / MIP")
        st.markdown("---")
        menu = st.radio("Seleccione módulo", [
            "Configurar Tema",
            "Registro Asistencia",
            "Lista Empleados",
            "Cargar Base de Personal",
            "Dashboard",
            "Historial",
            "Reportes",
            "Gestor Certificados",
        ])
        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            del st.session_state["rol"]
            st.rerun()

# =============================================================================
# PANEL ADMIN
# =============================================================================
if st.session_state.rol == "Admin":

    if menu == "Configurar Tema":
        st.markdown("## ⚙️ Configuración de la Capacitación")
        with st.container(border=True):
            st.markdown("### 1. Definir Tema")
            tipo_actividad = st.selectbox(
                "Tipo de actividad:",
                ["CAPACITACIÓN", "INDUCCIÓN", "REINDUCCIÓN", "ACTIVIDAD", "TALLER","SEMINARIO", "OTRO"]
            )
            nuevo_tema = st.text_input(
                "Nombre de la Actividad:",
                placeholder="Ej: CAPACITACIÓN SEGURIDAD INDUSTRIAL 2026"
            )
            nuevo_resumen = st.text_area(
                "Resumen de contenido (opcional):",
                placeholder="Ej: Temas tratados: EPP, riesgos eléctricos, evacuación...",
                max_chars=500,
                height=100
            )
            if st.button("💾 Guardar y Activar Tema"):
                if nuevo_tema:
                    st.session_state.tema_actual    = nuevo_tema.upper()
                    st.session_state.resumen_actual = nuevo_resumen.strip()
                    st.session_state.tipo_actividad = tipo_actividad
                    st.success(f"✅ Tema actualizado: **{nuevo_tema.upper()}**")
                else:
                    st.error("⚠️ Por favor escribe un nombre antes de guardar.")

        def comprimir_resumen(texto):
            texto_comprimido = zlib.compress(texto.encode("utf-8"))
            return base64.urlsafe_b64encode(texto_comprimido).decode()

        if "tema_actual" in st.session_state:
            st.markdown("---")
            st.markdown("### 🔗 Enlace de Acceso")

            base_url = "https://asistencias-mip.streamlit.app/"

            tema_url = quote(st.session_state.tema_actual)
            resumen_url = comprimir_resumen(st.session_state.get("resumen_actual", ""))
            tipo_url = quote(st.session_state.get("tipo_actividad", "CAPACITACIÓN"))

            url_final = (
                f"{base_url}"
                f"?tema={tema_url}"
                f"&resumen={resumen_url}"
                f"&tipo={tipo_url}"
                f"&rol=Empleado"
            )

            st.info(f"Copia este enlace y envíalo por WhatsApp:\n\n{url_final}")

    if menu == "Lista Empleados":
        st.markdown("## 👥 Base de Empleados")
        df_emp = obtener_datos()
        if df_emp is not None and not df_emp.empty:
            st.success(f"Total empleados cargados: {len(df_emp)}")
            buscar = st.text_input("🔎 Buscar empleado")
            if buscar:
                filtro = df_emp.astype(str).apply(
                    lambda x: x.str.contains(buscar, case=False, na=False)
                ).any(axis=1)
                df_emp = df_emp[filtro]
            st.dataframe(df_emp, use_container_width=True)
            excel = BytesIO()
            with pd.ExcelWriter(excel, engine="openpyxl") as writer:
                df_emp.to_excel(writer, index=False, sheet_name="Empleados")
            st.download_button("📥 Descargar Excel", excel.getvalue(), "empleados.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("No existe archivo empleados.xlsx")

    elif menu == "Cargar Base de Personal":
        st.markdown("## 📤 Actualizar Base de Personal")
        archivo = st.file_uploader("Subir archivo Excel actualizado", type=["xlsx"])
        if archivo is not None:
            with open("empleados.xlsx", "wb") as f:
                f.write(archivo.getbuffer())
            obtener_datos.clear()
            st.success("✅ Archivo actualizado correctamente.")

    elif menu == "Dashboard":
        st.markdown("## 📊 Dashboard Ejecutivo")

        if st.button("🔄 Actualizar datos"):
            leer_asistencias.clear()
            st.rerun()

        try:
            df = leer_asistencias()

            if df.empty:
                st.warning("No hay registros.")
                st.stop()

            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce", dayfirst=True)
            df = df.dropna(subset=["Fecha"])

            with st.expander("🎯 Filtros", expanded=False):
                colf1, colf2, colf3 = st.columns(3)

                with colf1:
                    empresa_sel = st.multiselect(
                        "🏢 Empresa",
                        options=sorted(df["Empresa"].dropna().unique()),
                        default=sorted(df["Empresa"].dropna().unique())
                    )

                with colf2:
                    tema_sel = st.multiselect(
                        "📚 Tema",
                        options=sorted(df["Tema"].dropna().unique()),
                        default=sorted(df["Tema"].dropna().unique())
                    )

                with colf3:
                    fecha_sel = st.date_input(
                        "📅 Rango de fechas",
                        value=(df["Fecha"].min().date(), df["Fecha"].max().date())
                    )

            df_filtrado = df[
                (df["Empresa"].isin(empresa_sel)) &
                (df["Tema"].isin(tema_sel))
            ].copy()

            if isinstance(fecha_sel, tuple) and len(fecha_sel) == 2:
                inicio, fin = fecha_sel
                df_filtrado = df_filtrado[
                    (df_filtrado["Fecha"].dt.date >= inicio) &
                    (df_filtrado["Fecha"].dt.date <= fin)
                ]

            if df_filtrado.empty:
                st.warning("⚠️ No hay datos con los filtros seleccionados.")
                st.stop()

            total = len(df_filtrado)
            personas = df_filtrado["ID"].nunique()
            temas = df_filtrado["Tema"].nunique()
            empresas = df_filtrado["Empresa"].nunique()

            st.markdown("""
            <style>
            .card {
                background: white;
                padding: 18px;
                border-radius: 16px;
                box-shadow: 0 6px 16px rgba(0,0,0,0.08);
                border-left: 6px solid #1E88E5;
                text-align: center;
            }
            .card h3 { margin:0; font-size:14px; color:#6B7280; }
            .card h1 { margin:5px 0; font-size:30px; color:#0A2A43; }
            </style>
            """, unsafe_allow_html=True)

            k1, k2, k3, k4 = st.columns(4)

            with k1:
                st.markdown(f'<div class="card"><h3>📋 Registros</h3><h1>{total}</h1></div>', unsafe_allow_html=True)
            with k2:
                st.markdown(f'<div class="card"><h3>👥 Personas</h3><h1>{personas}</h1></div>', unsafe_allow_html=True)
            with k3:
                st.markdown(f'<div class="card"><h3>📚 Capacitaciones</h3><h1>{temas}</h1></div>', unsafe_allow_html=True)
            with k4:
                st.markdown(f'<div class="card"><h3>🏢 Empresas</h3><h1>{empresas}</h1></div>', unsafe_allow_html=True)

            st.markdown("---")

            df_fecha = df_filtrado.copy()
            df_fecha["Fecha"] = df_fecha["Fecha"].dt.date
            df_fecha = df_fecha.groupby("Fecha").size().reset_index(name="Registros")

            fig_line = px.line(df_fecha, x="Fecha", y="Registros", markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

            st.markdown("---")

            st.subheader("📋 Resumen por Empresa")

            resumen = df_filtrado.groupby("Empresa").agg(
                Registros=("ID", "count"),
                Personas=("ID", "nunique")
            ).reset_index()

            st.dataframe(resumen, use_container_width=True)

        except Exception as e:
            st.error(f"Error crítico en el Dashboard: {e}")

    elif menu == "Historial":
        st.markdown("## 📄 Historial de Asistencias")

        try:
            df = leer_asistencias()

            ced = st.text_input("Buscar por cédula")

            if ced:
                df = df[df["ID"].astype(str) == ced]

            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.warning(f"Error historial: {e}")

    elif menu == "Reportes":
        st.markdown("## 📁 Reportes")

        try:
            df = leer_asistencias()

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Descargar CSV", csv, "reporte.csv", "text/csv")

            excel = BytesIO()
            with pd.ExcelWriter(excel, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Reporte")

            st.download_button(
                "📥 Descargar Excel",
                excel.getvalue(),
                "reporte.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.warning(f"Error reportes: {e}")

    elif menu == "Gestor Certificados":

        import re

        st.markdown("## 📂 Gestor de Certificados")

        if not os.path.exists(CARPETA_CERTIFICADOS):
            st.warning("No existe carpeta de certificados.")
            st.stop()

        archivos_pdf = sorted([
            f for f in os.listdir(CARPETA_CERTIFICADOS)
            if f.lower().endswith(".pdf")
        ])

        if not archivos_pdf:
            st.info("No hay certificados guardados.")
            st.stop()

        temas_detectados = []

        for archivo in archivos_pdf:
            try:
                nombre_limpio = archivo.replace(".pdf", "")
                partes = nombre_limpio.split("_")
                if len(partes) >= 4:
                    tema = "_".join(partes[:-3])
                else:
                    tema = "SIN CLASIFICAR"
                temas_detectados.append(tema)
            except:
                temas_detectados.append("SIN CLASIFICAR")

        df_pdf = pd.DataFrame({
            "Archivo": archivos_pdf,
            "Tema": temas_detectados
        })

        colk1, colk2 = st.columns(2)

        with colk1:
            st.success(f"📄 Certificados encontrados: {len(df_pdf)}")

        with colk2:
            st.info(f"📚 Capacitaciones detectadas: {df_pdf['Tema'].nunique()}")

        st.markdown("### 🎯 Filtros")

        colf1, colf2 = st.columns(2)

        with colf1:
            tema_seleccionado = st.selectbox(
                "📚 Filtrar por capacitación",
                ["TODOS"] + sorted(df_pdf["Tema"].unique().tolist())
            )

        with colf2:
            buscar = st.text_input("🔎 Buscar por nombre o cédula")

        df_filtrado = df_pdf.copy()

        if tema_seleccionado != "TODOS":
            df_filtrado = df_filtrado[df_filtrado["Tema"] == tema_seleccionado]

        if buscar:
            df_filtrado = df_filtrado[
                df_filtrado["Archivo"].str.contains(buscar, case=False, na=False)
            ]

        if df_filtrado.empty:
            st.warning("No existen certificados con ese filtro.")
            st.stop()

        st.markdown("### 📋 Certificados Encontrados")

        st.dataframe(
            df_filtrado,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")

        st.markdown("## 📥 Descargar Individual")

        archivo_sel = st.selectbox(
            "Seleccione certificado",
            df_filtrado["Archivo"].tolist()
        )

        ruta_sel = os.path.join(
            CARPETA_CERTIFICADOS,
            archivo_sel
        )

        with open(ruta_sel, "rb") as f:
            st.download_button(
                "📄 Descargar PDF",
                data=f.read(),
                file_name=archivo_sel,
                mime="application/pdf",
                use_container_width=True
            )

        st.markdown("---")

        st.markdown("## 🗜️ Descarga Masiva")

        cantidad_zip = len(df_filtrado)

        st.info(f"Se incluirán {cantidad_zip} certificados en el ZIP.")

        nombre_zip = (
            f"{tema_seleccionado}_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
            if tema_seleccionado != "TODOS"
            else f"Certificados_Completos_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
        )

        if st.button("📦 Generar ZIP", use_container_width=True):

            with st.spinner("Generando ZIP..."):

                zip_buffer = BytesIO()

                with zipfile.ZipFile(
                    zip_buffer,
                    "w",
                    zipfile.ZIP_DEFLATED
                ) as zipf:

                    for archivo in df_filtrado["Archivo"]:

                        ruta = os.path.join(
                            CARPETA_CERTIFICADOS,
                            archivo
                        )

                        if os.path.exists(ruta):

                            zipf.write(
                                ruta,
                                arcname=archivo
                            )

                zip_buffer.seek(0)

                st.success("✅ ZIP generado correctamente.")

                st.download_button(
                    "⬇️ Descargar ZIP",
                    data=zip_buffer,
                    file_name=nombre_zip,
                    mime="application/zip",
                    use_container_width=True
                )

        st.markdown("---")

        st.markdown("### 📊 Resumen")

        resumen = (
            df_filtrado
            .groupby("Tema")
            .size()
            .reset_index(name="Cantidad PDFs")
        )

        st.dataframe(
            resumen,
            use_container_width=True,
            hide_index=True
        )

# =============================================================================
# FLUJO EMPLEADO
# =============================================================================
if menu == "Registro Asistencia":

    if st.session_state.get("modulo") != "registro_asistencia":
        st.session_state.modulo    = "registro_asistencia"
        st.session_state.paso      = 0
        st.session_state.persona   = None
        st.session_state.cedula    = None
        st.session_state.foto_data = None
        st.session_state.pdf_doc   = None

    if st.session_state.paso == 0:

        st.markdown("""
        <div style='background-color:#E3F2FD; border-left:5px solid #1E88E5;
                    padding:12px 16px; border-radius:6px; margin-bottom:1.2rem;'>
            📋 <strong>Antes de continuar, por favor lee y acepta la siguiente autorización.</strong>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='
            border: 2px solid #0A2A43;
            border-radius: 12px;
            padding: 28px 32px;
            background-color: #ffffff;
            max-width: 680px;
            margin: 0 auto 20px auto;
            font-family: Arial, sans-serif;
        '>
            <h3 style='text-align:center; color:#0A2A43; font-size:17px; font-weight:800; margin-bottom:16px;'>
                AUTORIZACIÓN DE USO DE DATOS PERSONALES, DERECHOS DE IMAGEN Y FIRMA DIGITAL
            </h3>
            <p style='font-size:14px; color:#222; line-height:1.7; text-align:justify;'>
                Autorizo a <strong>MEZCLAS INTEGRALES PROGRAMADAS S.A.S.</strong>, en calidad de responsable del
                tratamiento de datos personales, para que recopile, almacene y utilice la
                siguiente información: <strong>fotografía</strong> para validación de identidad,
                <strong>firma manuscrita digitalizada</strong> como constancia de asistencia, y
                <strong>datos de identificación</strong> (nombre, cédula, cargo, empresa).
            </p>
            <p style='font-size:14px; color:#222; line-height:1.7; text-align:justify; margin-top:12px;'>
                La finalidad del tratamiento es <strong>exclusivamente</strong> el registro y
                certificación de asistencia a capacitaciones y actividades corporativas, conforme
                a las obligaciones del SG-SST. Esta autorización se otorga de forma
                <strong>voluntaria, libre y espontánea</strong>, conforme a la
                <strong>Ley 1581 de 2012</strong> y el <strong>Decreto 1377 de 2013</strong>.
                El titular podrá ejercer sus derechos de acceso, corrección y supresión
                escribiendo a: <strong>ghmip2026@gmail.com</strong>
            </p>
            <p style='font-size:13px; color:#555; margin-top:16px; text-align:center;'>
                Al hacer clic en <em>"Acepto y Continuar"</em> confirmo que he leído y entendido
                esta autorización.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Acepto y Continuar", use_container_width=True):
                st.session_state.paso = 1
                st.rerun()
        with col_b:
            if st.button("No Acepto / Salir", use_container_width=True):
                st.warning("Debes aceptar la autorización para continuar con el registro.")

    elif st.session_state.paso == 1:

        st.markdown(f"""
            <div style='background-color:#E3F2FD; border-left:5px solid #1E88E5;
                        padding:12px 16px; border-radius:6px; margin-bottom:1rem;'>
                📋 <strong>TEMA ACTUAL:</strong> {tema_actual}
            </div>
        """, unsafe_allow_html=True)

        df_maestro = obtener_datos()

        with st.form("form_cedula"):
            cedula_input = st.text_input(
                "Por favor, ingresa tu Cédula:",
                placeholder="Escribe tu número de cédula y presiona Buscar"
            ).strip()
            buscar = st.form_submit_button("🔍 Buscar", use_container_width=True)

        if buscar and cedula_input:
            st.session_state.cedula_buscada = cedula_input

        cedula = st.session_state.get("cedula_buscada", "")

        if cedula:
            res = (
                df_maestro[df_maestro["ID"].astype(str) == cedula]
                if df_maestro is not None else pd.DataFrame()
            )

            if not res.empty:
                st.session_state.persona = res.iloc[0].to_dict()
                st.session_state.cedula  = cedula
                st.success(f"✅ Hola, **{st.session_state.persona['Apellidos y Nombres']}**. ¡Bienvenido!")
                if st.button("Continuar al registro ➡️", use_container_width=True):
                    st.session_state.cedula_buscada = None
                    st.session_state.paso = 2
                    st.rerun()

            else:
                st.warning("⚠️ Cédula no encontrada. Si eres contratista o personal nuevo, regístrate:")
                with st.form("registro_nuevo_empleado"):
                    nombre_nuevo         = st.text_input("Nombres y Apellidos Completos:")
                    empresa_seleccionada = st.selectbox(
                        "Empresa:", ["MIP", "TEMPORAL / CONTRATISTA"]
                    )
                    empresa_externa = ""
                    if empresa_seleccionada == "TEMPORAL / CONTRATISTA":
                        empresa_externa = st.text_input("¿A qué empresa perteneces?")
                    cargo_nuevo = st.text_input("Tu Cargo:")

                    if st.form_submit_button("Registrarme y Continuar ➡️", use_container_width=True):
                        if nombre_nuevo and cargo_nuevo:
                            nom_emp = (
                                empresa_externa.upper()
                                if empresa_seleccionada == "TEMPORAL / CONTRATISTA" and empresa_externa
                                else empresa_seleccionada
                            )
                            st.session_state.persona = {
                                "Apellidos y Nombres": nombre_nuevo.upper(),
                                "Empresa": nom_emp,
                                "Cargo":   cargo_nuevo.upper(),
                            }
                            st.session_state.cedula = cedula
                            st.session_state.cedula_buscada = None
                            st.session_state.paso   = 2
                            st.rerun()
                        else:
                            st.error("Completa todos los campos.")

    elif st.session_state.paso == 2:
        st.markdown("### Captura de Identidad")
        st.markdown("<p style='color:#555;'>Tómate una foto para validar tu identidad.</p>",
                    unsafe_allow_html=True)
        foto = st.camera_input("Foto de validación")
        if foto:
            st.session_state.foto_data = foto
            if st.button("Ir a la firma"):
                st.session_state.paso = 3
                st.rerun()

    elif st.session_state.paso == 3:
    
        st.markdown("### Firma Digital")
        st.markdown(
            "<p style='color:#555;'>Dibuja tu firma en el recuadro blanco.</p>",
            unsafe_allow_html=True
        )
    
        canvas_res = st_canvas(
            stroke_width=3,
            stroke_color="#0A2A43",
            background_color="#ffffff",
            height=180,
            width=350,
            key="firma_final"
        )
    
        if st.button("ENVIAR ✅"):
    
            if canvas_res.image_data is None:
                st.warning("Debe firmar antes de continuar.")
                st.stop()
    
            alpha = canvas_res.image_data[:, :, 3]
    
            if int(alpha.sum()) < 3000:
                st.warning("Debe firmar antes de continuar.")
                st.stop()
    
            datos_asistencia = {
                "Fecha": datetime.now(pytz.timezone("America/Bogota")).strftime("%d/%m/%Y %H:%M:%S"),
                "ID": st.session_state.cedula,
                "Nombre": st.session_state.persona["Apellidos y Nombres"],
                "Empresa": st.session_state.persona.get("Empresa", "NO REGISTRA"),
                "Cargo": st.session_state.persona.get("Cargo", "NO REGISTRA"),
                "Tema": tema_actual,
                "Resumen": st.session_state.get("resumen_actual", ""),
                "Tipo":    tipo_actividad,
            }    
    
            with st.spinner("Guardando registro..."):
                guardado = guardar_en_google_sheets(datos_asistencia)
    
            if guardado:
    
                with st.spinner("Generando certificado..."):
    
                    foto_comprimida = None
    
                    if st.session_state.get("foto_data"):
                        try:
                            img_raw = Image.open(
                                st.session_state.get("foto_data")
                            ).convert("RGB")
    
                            img_raw.thumbnail((160, 160))
    
                            buf_foto = BytesIO()
    
                            img_raw.save(
                                buf_foto,
                                format="JPEG",
                                quality=75,
                                optimize=True
                            )
    
                            buf_foto.seek(0)
    
                            foto_comprimida = buf_foto
    
                        except Exception as ex:
                            print(f"[FOTO ERROR] {ex}")
    
                    firma_img = None
    
                    try:
                        firma_rgba = Image.fromarray(
                            canvas_res.image_data.astype("uint8"),
                            "RGBA"
                        )
                        
                        firma_img = Image.new("RGB", firma_rgba.size, "white")
                        firma_img.paste(firma_rgba, mask=firma_rgba.split()[3])
    
                    except Exception as ex:
                        print(f"[FIRMA ERROR] {ex}")
                        
                    pdf = generar_pdf(
                        datos_asistencia,
                        firma_img,
                        foto_comprimida,
                    )

                try:
                
                    fecha_archivo = datetime.now().strftime(
                        "%Y%m%d_%H%M%S"
                    )
                
                    nombre_pdf = (
                        f"Certificado_{datos_asistencia['ID']}_{fecha_archivo}.pdf"
                    )
                
                    pdf.seek(0)
                
                    archivo_drive = subir_pdf_drive(
                        pdf,
                        nombre_pdf
                    )
                
                    if archivo_drive:
                
                        print("✅ PDF subido a Drive")
                
                        datos_asistencia["LinkPDF"] = archivo_drive.get(
                            "webViewLink",
                            ""
                        )
                
                except Exception as ex:
                
                    print(f"[DRIVE ERROR] {ex}")
                
                pdf.seek(0)
                
                pdf_bytes = pdf.getvalue()

                try:
                
                    nombre_archivo_pdf = (
                        f"{datos_asistencia['Tema']}_"
                        f"{datos_asistencia['ID']}_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    )
                
                    nombre_archivo_pdf = (
                        nombre_archivo_pdf
                        .replace("/", "_")
                        .replace("\\", "_")
                        .replace(":", "_")
                    )
                
                    ruta_pdf = os.path.join(
                        CARPETA_CERTIFICADOS,
                        nombre_archivo_pdf
                    )
                
                    with open(ruta_pdf, "wb") as f:
                        f.write(pdf_bytes)
                
                    print(f"✅ PDF guardado localmente: {ruta_pdf}")
                
                    datos_asistencia["RutaPDF"] = ruta_pdf
                
                except Exception as ex:
                
                    print(f"❌ ERROR guardando PDF local: {ex}")
                
                enviar_respaldo_async(
                    datos_asistencia,
                    pdf_bytes
                )
                
                st.session_state.pdf_doc = pdf_bytes
                st.session_state.paso = 4
                
                st.rerun()

    elif st.session_state.paso == 4:
        st.markdown("""
            <div style='background-color:#E3F2FD; border:2px solid #1E88E5;
                        padding:20px; border-radius:10px; text-align:center;'>
                <h2 style='color:#0A2A43;'>¡Gracias por participar!</h2>
                <p>Tu asistencia ha sido registrada correctamente.</p>
            </div>
        """, unsafe_allow_html=True)

        if st.session_state.get("pdf_doc"):

            st.download_button(
                "Descargar mi Certificado (PDF)",
                st.session_state.pdf_doc,
                f"Certificado_{st.session_state.cedula}.pdf",
                "application/pdf"
            )

        if st.button("Realizar otro registro", use_container_width=True):
            for key in ["cedula", "persona", "pdf_doc", "foto_data",
                        "cedula_input", "firma_final", "correo_enviado"]:
                st.session_state.pop(key, None)
            st.session_state.paso   = 0
            st.session_state.modulo = "registro_asistencia"
            st.rerun()
