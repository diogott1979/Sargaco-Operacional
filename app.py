"""Sargaço Flutuante — aplicação operacional protegida."""
from pathlib import Path
from urllib.parse import urlsplit
import json
import hmac
import re
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Sargaço Flutuante | SALOC", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#f8fafc;color:#21324b}
.block-container{max-width:1550px;padding-top:1.4rem;padding-bottom:1rem}
[data-testid="stHeader"]{background:transparent}
</style>""", unsafe_allow_html=True)

st.title("🛡️ Sargaço Flutuante")
st.caption("Serviço Regional de Proteção Civil, IP-RAM · SALOC · Consulta cartográfica")

try:
    password = str(st.secrets["acesso"]["palavra_passe"])
    contacts = dict(st.secrets.get("contactos_municipios", {}))
except (KeyError, FileNotFoundError, AttributeError, TypeError):
    st.error("Falta configurar a palavra-passe no painel Secrets do Streamlit. Consulte o LEIA-ME.")
    st.stop()
if not password or len(password) < 12 or password == "ALTERAR_PALAVRA_PASSE":
    st.error("Defina uma palavra-passe institucional com pelo menos 12 caracteres nos Secrets.")
    st.stop()

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "falhas" not in st.session_state:
    st.session_state.falhas = 0

if not st.session_state.autenticado:
    st.subheader("Acesso reservado aos operadores autorizados")
    with st.form("entrar", clear_on_submit=True):
        entrada = st.text_input("Palavra-passe institucional", type="password")
        enviar = st.form_submit_button("Entrar", type="primary")
    if enviar:
        if st.session_state.falhas >= 8:
            st.error("Limite de tentativas nesta sessão atingido. Inicie uma nova sessão e contacte o responsável.")
        elif hmac.compare_digest(entrada.encode(), password.encode()):
            st.session_state.autenticado = True
            st.session_state.falhas = 0
            st.rerun()
        else:
            st.session_state.falhas += 1
            st.error("Palavra-passe incorreta.")
    st.info("Os dados públicos continuam disponíveis no mapa público. Os contactos municipais são disponibilizados apenas após autenticação nesta aplicação.")
    st.stop()

h1, h2 = st.columns([8,1], vertical_alignment="center")
with h1:
    st.success("Sessão autenticada · Consulta operacional")
with h2:
    if st.button("Terminar sessão"):
        st.session_state.autenticado = False
        st.rerun()

# Carregar a página original apenas após autenticação. Os dados públicos estão
# em /app/static/ e os telefones são injetados unicamente na sessão autenticada.
app_url = st.context.url
parts = urlsplit(app_url)
if parts.scheme not in ("http", "https") or not parts.netloc:
    st.error("Endereço de acesso inválido.")
    st.stop()
static_base = f"{parts.scheme}://{parts.netloc}/app/static/"
page = (ROOT / "map_template.html").read_text(encoding="utf-8")
# Mapear apenas os contactos permitidos. Os dados são divulgados ao operador
# autenticado no browser, como é inerente à sua consulta.
filtered_contacts = {str(k): str(v) for k, v in contacts.items() if str(v).strip()}
private_script = "<script>window.SARGACO_MUNICIPAL_CONTACTS = " + json.dumps(filtered_contacts, ensure_ascii=False).replace("<", "\\u003c") + ";</script>"
page = page.replace("<head>", '<head><base href="'+ static_base +'">', 1)
page = re.sub(r'<script\s+src="map\.js(?:\?[^" ]*)?"\s*></script>', lambda match: private_script + '<script src="map.js"></script>', page)
components.html(page, height=860, scrolling=False)
st.caption("A indicação de jurisdição é orientadora e não substitui a confirmação com a entidade competente. Os contactos devem ser validados operacionalmente.")
