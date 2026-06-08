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
import base64
import zlib
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
    page_icon="🏢"
)

# =============================================================================
# SESSION STATE
# =============================================================================
TOTAL_PAGINAS = 4
st.session_state.setdefault("rol", None)
st.session_state.setdefault("paso", 0)
st.session_state.setdefault("tema_actual", None)
st.session_state.setdefault("modulo", None)
st.session_state.setdefault("esperando_clave", False)
st.session_state.setdefault("resumen_actual", "")

# =============================================================================
# CSS CORPORATIVO – MIP
# =============================================================================
CSS_CORPORATIVO = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700;800&display=swap');

    * {
        font-family: 'Century Gothic', 'Nunito', sans-serif !important;
    }

    .stApp { 
        background-color: #F4F7FA; 
    }

    [data-testid="stSidebar"] { 
        background-color: #0A2A43; 
    }
    [data-testid="stSidebar"] * { 
        color: #FFFFFF !important; 
    }

    .stButton > button {
        background-color: #0A2A43 !important; 
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
        background-color: #1E88E5 !important;
        color: #FFFFFF !important;
    }

    h1, h2, h3 {
        color: #0A2A43;
        font-weight: 800 !important;
        letter-spacing: 1px;
    }

    .stTextInput > div > div > input {
        border: 2px solid #0A2A43;
        border-radius: 6px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #1E88E5;
        box-shadow: 0 0 0 2px rgba(30,136,229,0.3);
    }

    .hero-logos img {
        height: 65px !important;
        width: auto !important;
        object-fit: contain;
    }

    .hero-gerencia {
        background: linear-gradient(135deg,#0A2A43,#1E88E5,#42A5F5) !important;
        border-radius: 26px !important;
        padding: 28px 25px !important;
        margin-bottom: 20px !important;
        text-align: center !important;
        box-shadow: 0 18px 40px rgba(0,0,0,.16) !important;
    }

    .hero-gerencia h1 {
        color: white !important;
        font-size: 32px !important;
        font-weight: 800 !important;
    }

    .hero-mini {
        font-size: 11px !important;
        color: rgba(255, 255, 255, 0.9) !important;
        margin-top: 15px !important;
    }

    footer { visibility: hidden; }
</style>
"""
st.markdown(CSS_CORPORATIVO, unsafe_allow_html=True)

# =============================================================================
# CONEXIÓN A DATOS
# =============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

EMAIL_USER = "ghmip2026@gmail.com"
EMAIL_PASS = "xitl gjvj reek ydxc"
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
# UTILIDADES
# =============================================================================
def descomprimir_resumen(texto):
    try:
        texto_bytes = base64.urlsafe_b64decode(texto.encode())
        return zlib.decompress(texto_bytes).decode("utf-8")
    except:
        return ""

params = st.query_params

tema_desde_url = unquote(params.get("tema", ""))
if tema_desde_url:
    st.session_state.tema_actual = tema_desde_url.strip().upper()
if not st.session_state.get("tema_actual"):
    st.session_state.tema_actual = "CAPACITACIÓN GENERAL"

resumen_comprimido = params.get("resumen", "")
if resumen_comprimido:
    st.session_state.resumen_actual = descomprimir_resumen(resumen_comprimido).strip()
if not st.session_state.get("resumen_actual"):
    st.session_state.resumen_actual = ""

tipo_desde_url = unquote(params.get("tipo", ""))
if tipo_desde_url:
    st.session_state.tipo_actividad = tipo_desde_url.strip()
if not st.session_state.get("tipo_actividad"):
    st.session_state.tipo_actividad = "CAPACITACIÓN"

@st.cache_resource(show_spinner=False)
def cargar_logos():
    logos = {}
    if os.path.exists(EMPRESA_ACTIVA["logo1"]):
        logos["logo1"] = Image.open(EMPRESA_ACTIVA["logo1"]).copy()
    if os.path.exists(EMPRESA_ACTIVA["logo2"]):
        logos["logo2"] = Image.open(EMPRESA_ACTIVA["logo2"]).copy()
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
        except:
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def leer_asistencias():
    try:
        df = conn.read(worksheet="Hoja")
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def guardar_en_google_sheets(datos):
    try:
        nueva_fila = pd.DataFrame([datos])
        for _ in range(4):
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
            except:
                time.sleep(random.uniform(1, 4))
        return False
    except:
        return False

# =============================================================================
# ENVÍO DE CORREO CORPORATIVO MIP
# =============================================================================
def enviar_respaldo_async(datos, pdf_bytes):

    def _proceso_envio():
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USER
            msg['To'] = EMAIL_USER
            msg['Subject'] = f"📄 Registro de Asistencia - {datos['Nombre']}"

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
                <small>Enviado automáticamente por MEZCLAS INTEGRALES PROGRAMADAS S.A.S.</small>
            </body>
            </html>
            """

            msg.attach(MIMEText(cuerpo, 'html'))

            adj = MIMEBase('application', 'octet-stream')
            adj.set_payload(pdf_bytes)
            encoders.encode_base64(adj)
            adj.add_header('Content-Disposition', f"attachment; filename=Certificado_{datos['ID']}.pdf")
            msg.attach(adj)

            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, [EMAIL_USER], msg.as_string())
            server.quit()

        except Exception as e:
            print("❌ Error enviando correo:", e)

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

        media = MediaIoBaseUpload(pdf_buffer, mimetype='application/pdf', resumable=True)

        archivo = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        return archivo

    except Exception as e:
        print("❌ Error subiendo PDF a Drive:", e)
        return None

# =============================================================================
# GENERACIÓN DE PDF CORPORATIVO MIP (AZUL)
# =============================================================================
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))

def generar_pdf(datos, imagen_firma, imagen_foto):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    azul  = hex_to_rgb("#0A2A43")
    azul2 = hex_to_rgb("#1E88E5")
    azul3 = hex_to_rgb("#42A5F5")
    gris  = (0.96, 0.96, 0.96)

    # Fondo
    p.setFillColorRGB(1, 1, 1)
    p.rect(0, 0, width, height, fill=1, stroke=0)

    # Marco
    p.setStrokeColorRGB(*azul)
    p.setLineWidth(1.4)
    p.roundRect(20, 20, width - 40, height - 40, 14)

    # Encabezado
    p.setFillColorRGB(*azul)
    p.roundRect(20, height - 125, width - 40, 105, 14, fill=1, stroke=0)

    p.setFillColorRGB(*azul3)
    p.rect(20, height - 125, width - 40, 5, fill=1, stroke=0)

    # Logos
    for clave, x in [("logo1", 35), ("logo2", width - 130)]:
        if clave in LOGOS:
            try:
                img_logo = LOGOS[clave].convert("RGBA")
                buf_logo = BytesIO()
                img_logo.save(buf_logo, format="PNG")
                buf_logo.seek(0)
                p.drawImage(ImageReader(buf_logo), x, height - 112, width=95, height=72, preserveAspectRatio=True, mask='auto')
            except:
                pass

    # Título
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width / 2, height - 80, "CERTIFICADO DE ASISTENCIA")

    # Datos principales
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, 610, "Se certifica que:")

    p.setFillColorRGB(*azul)
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, 575, datos["Nombre"].upper())

    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, 545, f"Identificado(a) con documento No. {datos['ID']} asistió a:")

    # Bloque resumen
    resumen = datos.get("Resumen", "")
    tipo    = datos.get("Tipo", "CAPACITACIÓN")
    alto_rect = 125 if resumen else 100

    p.setFillColorRGB(*gris)
    p.roundRect(60, 405, width - 120, alto_rect, 10, fill=1, stroke=0)

    p.setFillColorRGB(*azul)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(80, 405 + alto_rect - 14, f"{tipo}:")

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

    # Datos finales
    p.setFont("Helvetica", 11)
    p.drawString(80, 385, f"Empresa: {datos['Empresa']}")
    p.drawString(80, 365, f"Cargo: {datos.get('Cargo', 'NO REGISTRA')}")
    p.drawString(80, 345, f"Fecha Registro: {datos['Fecha']}")

    # Foto
    base_y = 185
    if imagen_foto is not None:
        try:
            img = Image.open(imagen_foto).convert("RGB")
            img.thumbnail((150, 150))
            p.drawImage(ImageReader(img), 75, base_y, width=110, height=110)
            p.setFont("Helvetica", 8)
            p.drawCentredString(130, base_y - 12, "Validación de Registro")
        except:
            pass

    # Firma
    if imagen_firma is not None:
        try:
            p.drawImage(ImageReader(imagen_firma), width - 255, base_y + 28, width=145, height=55, preserveAspectRatio=True)
        except:
            pass

    p.setStrokeColorRGB(*azul)
    p.line(width - 275, base_y + 18, width - 95, base_y + 18)
    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(width - 185, base_y + 3, "Firma Autorizada")

    # Pie
    p.setFillColorRGB(*azul2)
    p.roundRect(20, 20, width - 40, 25, 0, fill=1, stroke=0)

    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica", 8)
    p.drawCentredString(width / 2, 30, "Documento digital emitido por MEZCLAS INTEGRALES PROGRAMADAS S.A.S.")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# =============================================================================
# LOGIN INICIAL CORPORATIVO MIP
# =============================================================================
if "rol" not in st.session_state:
    st.session_state.rol = None

rol_url = st.query_params.get("rol", None)
if rol_url and rol_url.lower() == "empleado":
    st.session_state.rol = "Empleado"

if st.session_state.get("rol") is None:

    def logo_to_base64(img):
        try:
            buf = BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
        except:
            return None

    logo1 = logo_to_base64(LOGOS["logo1"]) if "logo1" in LOGOS else None
    logo2 = logo_to_base64(LOGOS["logo2"]) if "logo2" in LOGOS else None

    paso = st.session_state.get("paso", 0)
    texto_pagina = f" | Página: {paso} de {TOTAL_PAGINAS}" if paso > 0 else ""

    st.markdown(f"""
    <div class="hero-gerencia">
        <div class="hero-logos">
            <img src="data:image/png;base64,{logo1}" class="hero-logo-img">
            <img src="data:image/png;base64,{logo2}" class="hero-logo-img">
        </div>
        <h1>REGISTRO ASISTENCIA DIGITAL</h1>
        <div class="hero-mini">
            MEZCLAS INTEGRALES PROGRAMADAS S.A.S.{texto_pagina}
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<h3 style="text-align:center;color:#0A2A43;">Acceso Corporativo</h3>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("COLABORADOR", use_container_width=True):
                st.session_state.rol = "Empleado"
                st.session_state.paso = 0
                st.rerun()

        with c2:
            if st.button("ADMINISTRADOR", use_container_width=True):
                st.session_state.esperando_clave = True
                st.rerun()

    if st.session_state.get("esperando_clave"):
        with st.form("login_admin", clear_on_submit=False):
            clave = st.text_input("🔑 Ingrese Clave de Administrador:", type="password")
            entrar = st.form_submit_button("Entrar")
            if entrar and clave == ADMIN_PASS:
                st.session_state.rol = "Admin"
                st.session_state.esperando_clave = False
                st.rerun()
        st.stop()

# =============================================================================
# FLUJO COMPLETO DEL EMPLEADO
# =============================================================================
if st.session_state.rol == "Empleado":

    # ───────────────────────────────────────────────────────────────
    # PASO 0 → AUTORIZACIÓN DE USO DE IMAGEN
    # ───────────────────────────────────────────────────────────────
    if st.session_state.paso == 0:
        st.markdown("### 📋 Autorización de Uso de Imagen y Datos")
        st.info(
            "Autorizo a MEZCLAS INTEGRALES PROGRAMADAS S.A.S. para recolectar mi fotografía, "
            "firma y datos biométricos con la única finalidad de registrar y validar mi asistencia "
            "a la actividad de capacitación."
        )

        acepta = st.checkbox("He leído y acepto los términos de la autorización de datos.")

        if st.button("Siguiente ➡️", disabled=not acepta, use_container_width=True):
            st.session_state.paso = 1
            st.rerun()

    # ───────────────────────────────────────────────────────────────
    # PASO 1 → VALIDACIÓN DE CÉDULA
    # ───────────────────────────────────────────────────────────────
    elif st.session_state.paso == 1:
        st.markdown("### 🆔 Validación de Identidad")
        cedula_input = st.text_input("Ingrese su número de cédula:", key="cedula_field")

        if st.button("Verificar 🔍", use_container_width=True):
            if cedula_input.strip():
                df_empleados = obtener_datos()
                cedula_str = str(cedula_input.strip())

                if not df_empleados.empty and "ID" in df_empleados.columns:
                    match = df_empleados[df_empleados["ID"].astype(str) == cedula_str]

                    if not match.empty:
                        st.session_state.cedula = cedula_str
                        st.session_state.persona = {
                            "Nombre": match.iloc[0]["Nombre"],
                            "Empresa": match.iloc[0].get("Empresa", EMPRESA_ACTIVA["nombre"]),
                            "Cargo": match.iloc[0].get("Cargo", "NO REGISTRA")
                        }
                        st.session_state.paso = 2
                        st.rerun()
                    else:
                        st.error("⚠️ La cédula no se encuentra registrada.")
                else:
                    st.warning("⚠️ Base de datos no disponible. Registro manual activado.")
                    st.session_state.cedula = cedula_str
                    st.session_state.persona = {
                        "Nombre": "REGISTRO MANUAL",
                        "Empresa": EMPRESA_ACTIVA["nombre"],
                        "Cargo": "NO ASIGNADO"
                    }
                    st.session_state.paso = 2
                    st.rerun()

    # ───────────────────────────────────────────────────────────────
    # PASO 2 → CAPTURA DE FOTO
    # ───────────────────────────────────────────────────────────────
    elif st.session_state.paso == 2:
        st.markdown("### 📸 Evidencia Fotográfica")
        st.write(f"Colaborador: **{st.session_state.persona['Nombre']}**")

        foto = st.camera_input("Capture una foto para validar su asistencia:")

        if foto is not None:
            st.session_state.foto_data = foto
            if st.button("Confirmar Foto y Continuar ➡️", use_container_width=True):
                st.session_state.paso = 3
                st.rerun()

    # ───────────────────────────────────────────────────────────────
    # PASO 3 → FIRMA DIGITAL Y PROCESAMIENTO
    # ───────────────────────────────────────────────────────────────
    elif st.session_state.paso == 3:
        st.markdown("### ✍️ Firma Digital del Asistente")
        st.write("Dibuje su firma dentro del recuadro:")

        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=150,
            width=400,
            drawing_mode="freedraw",
            key="canvas_firma"
        )

        if st.button("Registrar Asistencia 📋", use_container_width=True):
            if canvas_result.image_data is not None:
                img_firma = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')

                tz = pytz.timezone('America/Bogota')
                fecha_actual = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

                datos_asistencia = {
                    "Fecha": fecha_actual,
                    "ID": st.session_state.cedula,
                    "Nombre": st.session_state.persona["Nombre"],
                    "Empresa": st.session_state.persona["Empresa"],
                    "Cargo": st.session_state.persona["Cargo"],
                    "Tema": st.session_state.get("tema_actual", "CAPACITACIÓN GENERAL"),
                    "Resumen": st.session_state.get("resumen_actual", ""),
                    "Tipo": st.session_state.get("tipo_actividad", "CAPACITACIÓN")
                }

                with st.spinner("Procesando registro..."):
                    pdf_buffer = generar_pdf(datos_asistencia, img_firma, st.session_state.foto_data)
                    pdf_bytes = pdf_buffer.getvalue()

                    nombre_pdf = f"Certificado_{st.session_state.cedula}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    drive_res = subir_pdf_drive(BytesIO(pdf_bytes), nombre_pdf)

                    link_drive = drive_res.get("webViewLink", "") if drive_res else ""
                    datos_asistencia["LinkPDF"] = link_drive
                    datos_asistencia["RutaPDF"] = nombre_pdf

                    guardado_ok = guardar_en_google_sheets(datos_asistencia)

                    if guardado_ok:
                        enviar_respaldo_async(datos_asistencia, pdf_bytes)
                        st.session_state.pdf_doc = pdf_bytes
                        st.session_state.paso = 4
                        st.rerun()
                    else:
                        st.error("❌ Error al guardar en Google Sheets. Intente nuevamente.")

    # ───────────────────────────────────────────────────────────────
    # PASO 4 → CONFIRMACIÓN FINAL
    # ───────────────────────────────────────────────────────────────
    elif st.session_state.paso == 4:
        st.balloons()
        st.markdown("""
            <div style='background-color:#E3F2FD; border:2px solid #0A2A43;
                        padding:25px; border-radius:15px; text-align:center; margin-bottom: 20px;'>
                <h2 style='color:#0A2A43; margin:0;'>¡Registro Exitoso!</h2>
                <p style='color:#1E88E5; font-size:16px;'>Tu asistencia ha sido verificada y almacenada correctamente.</p>
            </div>
        """, unsafe_allow_html=True)

        if st.session_state.get("pdf_doc"):
            st.download_button(
                label="📥 Descargar Certificado (PDF)",
                data=st.session_state.pdf_doc,
                file_name=f"Certificado_Asistencia_{st.session_state.cedula}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        if st.button("🔄 Registrar otra persona", use_container_width=True):
            for key in ["cedula", "persona", "pdf_doc", "foto_data", "canvas_firma", "paso"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.paso = 0
            st.rerun()

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
    # MÓDULO: GENERAR ENLACE Y QR
    # ───────────────────────────────────────────────────────────────
    if opcion_admin == "Generar Enlace / QR":
        st.markdown("### 🔗 Generar Enlace y Código QR")

        tema_input = st.text_input("Tema de la capacitación:")
        tipo_act = st.selectbox("Tipo de actividad:", ["CAPACITACIÓN", "INDUCCIÓN", "REENTRENAMIENTO", "CHARLA", "REUNIÓN"])
        resumen_input = st.text_area("Resumen del contenido:")

        if st.button("Generar Enlace y QR 🚀", use_container_width=True):
            if tema_input.strip():
                resumen_bytes = resumen_input.strip().encode('utf-8')
                resumen_comp = zlib.compress(resumen_bytes)
                resumen_b64 = base64.urlsafe_b64encode(resumen_comp).decode('utf-8')

                url_base = st.secrets.get("base_url", "https://asistencias-mip.streamlit.app/")
                url_final = f"{url_base}?rol=Empleado&tema={quote(tema_input.strip().upper())}&tipo={quote(tipo_act)}&resumen={resumen_b64}"

                st.success("Enlace generado:")
                st.code(url_final)

                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(url_final)
                qr.make(fit=True)
                img_qr = qr.make_image(fill_color="black", back_color="white")

                buf_qr = BytesIO()
                img_qr.save(buf_qr, format="PNG")

                st.image(buf_qr.getvalue(), width=300)
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
