"""Sargaço Flutuante — aplicação operacional protegida."""
from pathlib import Path
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

# A versão incorporada é autónoma: todos os estilos e scripts públicos
# são incluídos no HTML entregue APENAS a uma sessão autenticada.
# Evita falhas de caminhos relativos /app/static/ dentro do iframe do Streamlit.
@st.cache_data(show_spinner=False)
def criar_mapa_autonomo():
    pagina = (ROOT / "map_template.html").read_text(encoding="utf-8")
    pasta_publica = (ROOT / "static").resolve()

    def carregar_recurso(caminho):
        recurso = (pasta_publica / caminho.split("?", 1)[0]).resolve()
        if not recurso.is_relative_to(pasta_publica) or not recurso.is_file():
            raise FileNotFoundError(f"Recurso cartográfico não encontrado: {caminho}")
        return recurso.read_text(encoding="utf-8")

    def substituir_estilo(resultado):
        endereco = resultado.group(1)
        css = carregar_recurso(endereco)
        return "<style>\n" + css + "\n</style>"

    def substituir_script(resultado):
        endereco = resultado.group(1)
        js = carregar_recurso(endereco)
        # Os recursos utilizados não incluem fechos literais de <script>.
        if re.search(r"</script\s*>", js, flags=re.I):
            raise ValueError(f"Fecho HTML inesperado no JavaScript: {endereco}")
        return "<script>\n" + js + "\n</script>"

    pagina = re.sub(
        r'<link\s+rel="stylesheet"\s+href="([^"]+)"\s*/?>',
        substituir_estilo, pagina,
    )
    pagina = re.sub(
        r'<script\s+src="([^"]+)"\s*></script>',
        substituir_script, pagina,
    )
    return pagina

try:
    pagina = criar_mapa_autonomo()
except (OSError, ValueError) as exc:
    st.error(f"Não foi possível carregar os recursos do mapa: {exc}")
    st.stop()

# Os contactos municipais NÃO estão nos ficheiros cartográficos públicos.
# Só são incorporados depois de validada a palavra-passe, na sessão atual.
contactos_permitidos = {str(k): str(v) for k, v in contacts.items() if str(v).strip()}
dados_contactos = json.dumps(contactos_permitidos, ensure_ascii=False).replace("<", "\\u003c")
script_privado = (
    "<script>window.SARGACO_MUNICIPAL_CONTACTS = "
    + dados_contactos + ";</script>"
)
pagina = pagina.replace("</head>", script_privado + "</head>", 1)

components.html(pagina, height=900, scrolling=False)
st.caption("A jurisdição indicada é orientadora; confirme com a entidade competente. Valide os contactos antes de os utilizar operacionalmente.")
