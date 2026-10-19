import streamlit as st
import asyncio
import os
import edge_tts
import whisper
from google import genai
from moviepy.editor import AudioFileClip, ImageClip, VideoFileClip, TextClip, CompositeVideoClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Configuración de la página
st.set_page_config(
    page_title="Estudio Automatizado de YouTube",
    page_icon="🚀",
    layout="wide"
)

os.makedirs("temp", exist_ok=True)

st.title("🚀 Estudio Automatizado de YouTube con IA")
st.write("Genera guiones, crea videos con voces y subtítulos, y súbelos directamente a tu canal.")

# --- BARRA LATERAL: Configuración General y Credenciales ---
st.sidebar.header("🔑 Credenciales y Configuración")
gemini_api_key = st.sidebar.text_input("API Key de Gemini", type="password", help="Obtén tu clave en Google AI Studio")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configuración de Audio")
VOCES_DISPONIBLES = {
    "Español (México) - Dalia (Femenino)": "es-MX-DaliaNeural",
    "Español (México) - Jorge (Masculino)": "es-MX-JorgeNeural",
    "Español (España) - Alvaro (Masculino)": "es-ES-AlvaroNeural",
    "Español (Colombia) - Gonzalo (Masculino)": "es-CO-GonzaloNeural",
}
voz_seleccionada = st.sidebar.selectbox("Voz de Narración:", options=list(VOCES_DISPONIBLES.keys()))
voice_id = VOCES_DISPONIBLES[voz_seleccionada]

# --- PESTAÑAS DE LA APLICACIÓN ---
tab1, tab2, tab3 = st.tabs(["1. ✍️ Generador de Guion", "2. 🎬 Editor y Renderizado", "3. 📤 Subir a YouTube"])

# --- PESTAÑA 1: GENERADOR DE GUIÓN CON GEMINI ---
with tab1:
    st.header("Generador Automático de Guiones")
    tema_guion = st.text_input("¿De qué tratará el video?", placeholder="Ej: 5 datos curiosos sobre el espacio exterior que te dejarán sin aliento")
    tono_guion = st.selectbox("Tono del video:", ["Divertido y Dinámico", "Educativo / Documental", "Misterioso / Suspenso", "Motivacional"])
    
    if st.button("✨ Generar Guion con IA", use_container_width=True):
        if not gemini_api_key:
            st.error("⚠️ Por favor ingresa tu API Key de Gemini en la barra lateral.")
        elif not tema_guion:
            st.error("⚠️ Ingresa un tema para el video.")
        else:
            with st.spinner("🤖 Escribiendo guion optimizado para YouTube..."):
                try:
                    client = genai.Client(api_key=gemini_api_key)
                    prompt = f"Escribe un guion para un video corto de YouTube sobre: '{tema_guion}'. El tono debe ser {tono_guion}. Hazlo atractivo, con gancho inicial (hook) y llamada a la acción al final. No pongas acotaciones de escena entre corchetes, solo el texto narrativo directo."
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    st.session_state['guion_generado'] = response.text
                    st.success("¡Guion generado con éxito! Ve a la pestaña 'Editor y Renderizado' para usarlo.")
                except Exception as e:
                    st.error(f"Error al generar guion: {e}")

    if 'guion_generado' in st.session_state:
        st.text_area("Guion Actual:", value=st.session_state['guion_generado'], height=200)

# --- PESTAÑA 2: EDITOR Y RENDERIZADO (Con Subtítulos Opción 1) ---
with tab2:
    st.header("Ensamblaje y Renderizado de Video")
    
    # Cargar guion previo si existe
    guion_por_defecto = st.session_state.get('guion_generado', '')
    guion_texto = st.text_area("Guion final para narrar:", value=guion_por_defecto, height=150)
    
    col_a, col_b = st.columns(2)
    with col_a:
        tipo_fondo = st.radio("Fondo visual:", ["Imagen", "Video"], horizontal=True)
        archivo_fondo = st.file_uploader(f"Sube tu archivo de {tipo_fondo.lower()}:", type=["jpg", "png", "mp4"])
    with col_b:
        st.write("### Opciones de Edición")
        incluir_subtitulos = st.checkbox("🔤 Generar subtítulos automáticos (Whisper)", value=False, help="Puede tardar unos segundos extra según la duración.")

    if st.button("🚀 Renderizar Video Final", type="primary", use_container_width=True):
        if not guion_texto.strip():
            st.error("⚠️ El guion está vacío.")
        elif not archivo_fondo:
            st.error("⚠️ Sube un archivo multimedia de fondo.")
        else:
            output_video_path = "temp/video_final.mp4"
            audio_path = "temp/narracion.mp3"
            
            # 1. Generar Audio con Edge-TTS
            with st.spinner("🎙️ Generando voz en off..."):
                async def generate_tts(text, voice, output_path):
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(output_path)
                asyncio.run(generate_tts(guion_texto, voice_id, audio_path))

            # 2. Ensamblar Video con MoviePy
            with st.spinner("🎬 Procesando video y aplicando efectos..."):
                try:
                    fondo_path = os.path.join("temp", archivo_fondo.name)
                    with open(fondo_path, "wb") as f:
                        f.write(archivo_fondo.getbuffer())

                    audio_clip = AudioFileClip(audio_path)
                    duracion = audio_clip.duration

                    if tipo_fondo == "Imagen":
                        video_clip = ImageClip(fondo_path).set_duration(duracion)
                    else:
                        video_clip = VideoFileClip(fondo_path)
                        if video_clip.duration < duracion:
                            video_clip = video_clip.loop(duration=duracion)
                        else:
                            video_clip = video_clip.subclip(0, duracion)

                    video_final = video_clip.set_audio(audio_clip)

                    # Subtítulos automáticos con Whisper (Opción 1)
                    if incluir_subtitulos:
                        st.info("🔄 Transcribiendo audio para subtítulos con Whisper...")
                        model = whisper.load_model("base")
                        result = model.transcribe(audio_path, language="es")
                        
                        txt_clips = [video_final]
                        for segment in result["segments"]:
                            start = segment["start"]
                            end = segment["end"]
                            text = segment["text"].strip()
                            
                            # Crear clip de texto para cada segmento
                            txt_clip = TextClip(text, fontsize=32, color='white', bg_color='rgba(0,0,0,0.6)', font='Arial-Bold', size=(video_final.w - 100, None), method='caption')
                            txt_clip = txt_clip.set_start(start).set_end(end).set_position(('center', 'bottom'))
                            txt_clips.append(txt_clip)
                        
                        video_final = CompositeVideoClip(txt_clips)

                    video_final.write_videofile(
                        output_video_path,
                        fps=24,
                        codec="libx264",
                        audio_codec="aac"
                    )

                    audio_clip.close()
                    video_clip.close()

                    st.success("🎉 ¡Video renderizado correctamente!")
                    st.session_state['video_listo'] = output_video_path
                    st.video(output_video_path)

                    with open(output_video_path, "rb") as file:
                        st.download_button("📥 Descargar Video", data=file, file_name="youtube_auto.mp4", mime="video/mp4", use_container_width=True)

                except Exception as e:
                    st.error(f"❌ Error en el renderizado: {str(e)}")

# --- PESTAÑA 3: SUBIDA DIRECTA A YOUTUBE (Opción 3) ---
with tab3:
    st.header("Subida Automática a YouTube")
    st.write("Sube el video generado directamente a tu canal utilizando la YouTube Data API.")
    
    yt_titulo = st.text_input("Título del Video en YouTube", value="Video automático con IA")
    yt_descripcion = st.text_area("Descripción", value="Creado automáticamente con Python y Streamlit.")
    yt_privacidad = st.selectbox("Estado de Privacidad:", ["private", "unlisted", "public"])
    
    client_secrets_file = st.file_uploader("Sube tu archivo de credenciales de Google Cloud (`client_secret.json`):", type=["json"])

    if st.button("🚀 Subir a YouTube", type="primary", use_container_width=True):
        if 'video_listo' not in st.session_state or not os.path.exists(st.session_state['video_listo']):
            st.error("⚠️ Primero debes generar y renderizar un video en la pestaña anterior.")
        elif not client_secrets_file:
            st.error("⚠️ Sube tu archivo `client_secret.json` de Google Cloud Console.")
        else:
            with st.spinner("📤 Conectando con YouTube y subiendo el archivo..."):
                try:
                    # Guardar temporalmente el archivo de secretos
                    secret_path = "temp/client_secret.json"
                    with open(secret_path, "wb") as f:
                        f.write(client_secrets_file.getbuffer())

                    from google_auth_oauthlib.flow import InstalledAppFlow
                    
                    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
                    
                    # Nota en entorno local abrirá flujo de autenticación en consola/navegador
                    flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
                    credentials = flow.run_local_server(port=0)
                    
                    youtube = build("youtube", "v3", credentials=credentials)

                    body = {
                        "snippet": {
                            "title": yt_titulo,
                            "description": yt_descripcion,
                            "tags": ["ia", "shorts", "automatizado"],
                            "categoryId": "22"  # People & Blogs
                        },
                        "status": {
                            "privacyStatus": yt_privacidad
                        }
                    }

                    media = MediaFileUpload(st.session_state['video_listo'], chunksize=-1, resumable=True)
                    request = youtube.videos().insert(
                        part="snippet,status",
                        body=body,
                        media_body=media
                    )

                    response = None
                    while response is None:
                        status, response = request.next_chunk()

                    st.success(f"🎉 ¡Video subido con éxito! ID del video: {response.get('id')}")
                    st.markdown(f"🔗 [Ver en YouTube](https://youtu.be/{response.get('id')})")

                except Exception as e:
                    st.error(f"❌ Error al subir a YouTube: {str(e)}")
