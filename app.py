from streamlit_calendar import calendar
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta
import os
import hashlib

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Agenda Familiar",
    page_icon="📅",
    layout="centered",
    initial_sidebar_state="collapsed"
)

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

DB_NAME = "agenda_familiar.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            participantes TEXT NOT NULL,
            data_evento DATE NOT NULL,
            dias_duracao INTEGER DEFAULT 1,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            local TEXT,
            descricao TEXT,
            anexo_path TEXT,
            criado_por TEXT DEFAULT 'Administrador',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("PRAGMA table_info(eventos)")
    colunas_tabela = [col[1] for col in cursor.fetchall()]

    if "criado_por" not in colunas_tabela:
        cursor.execute(
            "ALTER TABLE eventos ADD COLUMN criado_por TEXT DEFAULT 'Administrador'"
        )

    if "dias_duracao" not in colunas_tabela:
        cursor.execute(
            "ALTER TABLE eventos ADD COLUMN dias_duracao INTEGER DEFAULT 1"
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nome_completo TEXT NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM usuarios")

    if cursor.fetchone()[0] == 0:
        senha_padrao = hash_senha("123456")

        cursor.execute("""
            INSERT INTO usuarios
                (username, nome_completo, senha, perfil)
            VALUES (?, ?, ?, ?)
        """, ("flavio", "Flávio Lisboa", senha_padrao, "admin"))

    cursor.execute("SELECT COUNT(*) FROM categorias")

    if cursor.fetchone()[0] == 0:
        cats_iniciais = [
            "Aniversário", "Igreja", "Viagem", "Futebol",
            "Médico/Saúde", "Escola/Estudo", "Trabalho",
            "Lazer", "Outro"
        ]

        for cat in cats_iniciais:
            cursor.execute(
                "INSERT OR IGNORE INTO categorias (nome) VALUES (?)",
                (cat,)
            )

    conn.commit()
    conn.close()


def limpar_historico_antigo():
    limite = (
        date.today() - timedelta(days=365)
    ).strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT anexo_path FROM eventos WHERE data_evento < ?",
        (limite,)
    )

    anexos = cursor.fetchall()

    for item in anexos:
        caminho = item[0]

        if caminho and isinstance(caminho, str) and os.path.exists(caminho):
            try:
                os.remove(caminho)
            except Exception:
                pass

    cursor.execute(
        "DELETE FROM eventos WHERE data_evento < ?",
        (limite,)
    )

    conn.commit()
    conn.close()


init_db()
limpar_historico_antigo()


# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
        .stApp {
            max-width: 100%;
            overflow-x: hidden !important;
        }

        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 6rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        div[data-testid="stSelectbox"] {
            margin-top: -6px !important;
            margin-bottom: -6px !important;
            min-width: 0 !important;
            width: 100% !important;
        }

        hr {
            margin-top: -12px !important;
            margin-bottom: 12px !important;
            border-color: #e2e8f0 !important;
        }

        div[data-testid="stExpander"] {
            background-color: #ffffff;
            border-radius: 10px;
            margin-bottom: 6px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }

        .st-key-filtros_duas_colunas {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            overflow-x: clip !important;
        }

        .st-key-filtros_duas_colunas [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: flex-start !important;
            gap: 8px !important;
            width: 100% !important;
            min-width: 0 !important;
        }

        .st-key-filtros_duas_colunas [data-testid="column"] {
            display: block !important;
            flex: 1 1 0% !important;
            width: 50% !important;
            min-width: 0 !important;
            max-width: 50% !important;
            padding: 0 !important;
        }

        .st-key-filtros_duas_colunas [data-testid="stSelectbox"],
        .st-key-filtros_duas_colunas [data-testid="stSelectbox"] > div {
            width: 100% !important;
            min-width: 0 !important;
            max-width: 100% !important;
        }

        .st-key-filtros_duas_colunas [data-testid="stSelectbox"] label {
            font-size: 0.85rem !important;
        }

        .st-key-filtros_duas_colunas [data-baseweb="select"] {
            min-width: 0 !important;
            max-width: 100% !important;
        }

        .st-key-filtros_duas_colunas [data-baseweb="select"] > div {
            min-width: 0 !important;
            max-width: 100% !important;
        }

        .st-key-filtros_duas_colunas [data-baseweb="select"] span {
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
        }

        .st-key-botao_flutuante_evento {
            position: fixed !important;
            right: 16px !important;
            left: auto !important;
            bottom: 24px !important;
            width: 60px !important;
            min-width: 60px !important;
            max-width: 60px !important;
            margin: 0 !important;
            padding: 0 !important;
            z-index: 99999 !important;
        }

        .st-key-botao_flutuante_evento button {
            width: 60px !important;
            height: 60px !important;
            min-height: 60px !important;
            border-radius: 50% !important;
            border: none !important;
            background-color: #16a34a !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
            font-size: 28px !important;
            font-weight: 600 !important;
        }

        .st-key-botao_flutuante_evento button:hover {
            background-color: #15803d !important;
            color: white !important;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        .stApp {
            overflow-x: hidden !important;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 8px !important;
            flex-wrap: nowrap !important;
        }

        div[data-testid="stColumn"] {
            min-width: 0 !important;
            width: 50% !important;
            flex: 1 1 0% !important;
            overflow: hidden !important;
        }

        div[data-testid="stSelectbox"] {
            min-width: 0 !important;
            width: 100% !important;
        }

        div[data-testid="stSelectbox"] > div {
            min-width: 0 !important;
            width: 100% !important;
        }

        div[data-testid="stSelectbox"] label {
            font-size: 13px !important;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] {
            min-width: 0 !important;
            width: 100% !important;
            font-size: 12px !important;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            min-width: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)


# --- CONTROLE DE SESSÃO / LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.name = None
    st.session_state.role = None

if "modo_criacao" not in st.session_state:
    st.session_state.modo_criacao = False

if "evento_editando_id" not in st.session_state:
    st.session_state.evento_editando_id = None


def tela_login():
    st.markdown("### 🔒 Agenda Familiar")
    st.write("Por favor, faça login para continuar.")

    with st.form("form_login"):
        username = st.text_input("Usuário").strip().lower()
        senha = st.text_input("Senha", type="password")

        submit_login = st.form_submit_button(
            "Entrar",
            use_container_width=True
        )

        if submit_login:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT username, nome_completo, senha, perfil
                FROM usuarios
                WHERE username = ?
                """,
                (username,)
            )

            user_data = cursor.fetchone()
            conn.close()

            if user_data and user_data[2] == hash_senha(senha):
                st.session_state.logged_in = True
                st.session_state.user = user_data[0]
                st.session_state.name = user_data[1]
                st.session_state.role = user_data[3]

                st.success(f"Bem-vindo, {user_data[1]}!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")


if not st.session_state.logged_in:
    tela_login()
    st.stop()


# --- CARREGA DADOS DINÂMICOS DO BANCO ---
conn = get_connection()

df_usuarios = pd.read_sql_query(
    "SELECT nome_completo FROM usuarios",
    conn
)

df_cat_db = pd.read_sql_query("""
    SELECT nome
    FROM categorias
    ORDER BY
        CASE WHEN nome LIKE 'Outro%' THEN 1 ELSE 0 END,
        nome ASC
""", conn)

conn.close()

INTEGRANTES = df_usuarios["nome_completo"].tolist()
CATEGORIAS = df_cat_db["nome"].tolist()

MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março",
    4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro",
    10: "Outubro", 11: "Novembro", 12: "Dezembro"
}


# --- BARRA LATERAL ---
with st.sidebar:
    st.write(f"👤 Logado como: **{st.session_state.name}**")

    st.caption(
        f"Perfil: {'Administrador 🛠️' if st.session_state.role == 'admin' else 'Membro 👨‍👩‍👧‍👦'}"
    )

    if st.button("🚪 Sair / Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.name = None
        st.session_state.role = None
        st.session_state.modo_criacao = False
        st.session_state.evento_editando_id = None
        st.rerun()

# --- TÍTULO PRINCIPAL ---
st.markdown("### 📅 Agenda Familiar")

# --- NAVEGAÇÃO ENTRE SEÇÕES ---
if st.session_state.role == "admin":
    secoes = [
        "📆 Calendário",
        "📊 Relatórios",
        "⚙️ Admin",
    ]
else:
    secoes = [
        "📆 Calendário",
        "📊 Relatórios",
    ]

if "secao_agenda" not in st.session_state:
    st.session_state.secao_agenda = "📆 Calendário"

secao = st.segmented_control(
    "Navegação",
    options=secoes,
    default="📆 Calendário",
    key="secao_agenda",
    selection_mode="single",
    label_visibility="collapsed",
)
# --- AJUSTES DE ESPAÇAMENTO PARA CELULAR ---
st.markdown(
    """
    <style>
    /* Reduz o espaço entre os elementos da tela */
    div[data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }

    /* Remove margens extras da navegação */
    div[data-testid="stSegmentedControl"] {
        margin-bottom: 0 !important;
    }

    /* Aproxima o título do conteúdo anterior */
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3 {
        line-height: 1.4 !important;
        overflow: visible !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.4rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# --- ABA 1: CALENDÁRIO ---
@st.dialog("⚠️ Já existe evento nesta data")
def mostrar_alerta_eventos_existentes(eventos):
    st.write("Encontramos os seguintes eventos que coincidem com a data:")

    for evento in eventos:
        st.markdown(f"**📌 {evento['titulo']}**")
        st.write(f"📅 Data: {evento['data']}")
        st.write(
            f"🕒 Horário: {evento['hora_inicio']} às {evento['hora_fim']}"
        )
        st.write(f"🏷️ Categoria: {evento['categoria']}")
        st.divider()

    if st.button("OK", use_container_width=True):
        st.rerun()
if secao == "📆 Calendário":
    if (
        st.session_state.modo_criacao
        or st.session_state.evento_editando_id is not None
    ):
        is_edicao = st.session_state.evento_editando_id is not None

        st.subheader(
            "✏️ Editar Evento" if is_edicao else "➕ Novo Evento"
        )

        ev_dados = {}

        if is_edicao:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT titulo, categoria, participantes, data_evento,
                       dias_duracao, hora_inicio, hora_fim, local, descricao
                FROM eventos
                WHERE id = ?
            """, (st.session_state.evento_editando_id,))

            res = cursor.fetchone()
            conn.close()

            if res:
                ev_dados = {
                    "titulo": res[0],
                    "categoria": res[1],
                    "participantes": res[2].split(", "),
                    "data": datetime.strptime(
                        res[3], "%Y-%m-%d"
                    ).date(),
                    "dias": res[4] if res[4] else 1,
                    "h_in": datetime.strptime(
                        res[5], "%H:%M"
                    ).time(),
                    "h_fim": datetime.strptime(
                        res[6], "%H:%M"
                    ).time(),
                    "local": res[7],
                    "desc": res[8]
                }

        with st.form("form_evento_cadastro"):
            titulo = st.text_input(
                "Título*",
                value=ev_dados.get("titulo", ""),
                placeholder="Ex: Viagem, Reunião..."
            )

            col_cat, col_part = st.columns(2)

            with col_cat:
                cat_atual = ev_dados.get(
                    "categoria",
                    CATEGORIAS[0] if CATEGORIAS else ""
                )

                idx_cat = (
                    CATEGORIAS.index(cat_atual)
                    if cat_atual in CATEGORIAS
                    else 0
                )

                categoria = st.selectbox(
                    "Categoria*",
                    CATEGORIAS,
                    index=idx_cat
                )

            with col_part:
                part_atual = ev_dados.get(
                    "participantes",
                    ["Família Toda"]
                )

                participantes_sel = st.multiselect(
                    "Quem?*",
                    INTEGRANTES + ["Família Toda"],
                    default=part_atual
                )

            col_d, col_qtd = st.columns(2)

            with col_d:
                data_ev = st.date_input(
                    "Início*",
                    value=ev_dados.get("data", date.today()),
                    format="DD/MM/YYYY"
                )

            with col_qtd:
                dias_duracao = st.number_input(
                    "Dias*",
                    min_value=1,
                    max_value=365,
                    value=int(ev_dados.get("dias", 1))
                )

            col_h1, col_h2 = st.columns(2)

            with col_h1:
                h_in = st.time_input(
                    "Hora Início*",
                    value=ev_dados.get("h_in", time(9, 0))
                )

            with col_h2:
                h_fim = st.time_input(
                    "Hora Fim*",
                    value=ev_dados.get("h_fim", time(10, 0))
                )

            local_ev = st.text_input(
                "Local",
                value=ev_dados.get("local", ""),
                placeholder="Local ou endereço..."
            )

            desc_ev = st.text_area(
                "Observações",
                value=ev_dados.get("desc", ""),
                placeholder="Detalhes..."
            )

            arquivo_anexo = st.file_uploader(
                "Anexo (Foto/PDF)",
                type=["png", "jpg", "jpeg", "pdf"]
            )

            col_b1, col_b2 = st.columns(2)

            with col_b1:
                salvar = st.form_submit_button(
                    "💾 Salvar",
                    use_container_width=True
                )

            with col_b2:
                cancelar = st.form_submit_button(
                    "↩️ Cancelar",
                    use_container_width=True
                )

        if cancelar:
            st.session_state.modo_criacao = False
            st.session_state.evento_editando_id = None
            st.rerun()

        if salvar:
            if not titulo.strip():
                st.error("Preencha o título.")
            elif not participantes_sel:
                st.error("Selecione os participantes.")
            elif h_in >= h_fim:
                st.error("Horário de término deve ser após o início.")
            else:
                data_inicio_nova = data_ev
                data_fim_nova = data_ev + timedelta(
                    days=int(dias_duracao) - 1
                )
                eventos_conflitantes = []

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, titulo, categoria, data_evento,
                           dias_duracao, hora_inicio, hora_fim
                    FROM eventos
                """)

                eventos_existentes = cursor.fetchall()

                for evento in eventos_existentes:
                    (
                        evento_id,
                        titulo_existente,
                        categoria_existente,
                        data_existente,
                        dias_existentes,
                        hora_inicio_existente,
                        hora_fim_existente
                    ) = evento

                    # Ao editar, ignora o próprio evento.
                    if (
                        is_edicao
                        and evento_id == st.session_state.evento_editando_id
                    ):
                        continue

                    data_inicio_existente = datetime.strptime(
                        data_existente, "%Y-%m-%d"
                    ).date()

                    data_fim_existente = data_inicio_existente + timedelta(
                        days=max(int(dias_existentes or 1), 1) - 1
                    )

                    # Detecta sobreposição de datas, inclusive
                    # quando os eventos duram vários dias.
                    if (
                        data_inicio_nova <= data_fim_existente
                        and data_fim_nova >= data_inicio_existente
                    ):
                        eventos_conflitantes.append({
                            "titulo": titulo_existente,
                            "categoria": categoria_existente,
                            "data": (
                                f"{data_inicio_existente.strftime('%d/%m/%Y')} a "
                                f"{data_fim_existente.strftime('%d/%m/%Y')}"
                                if data_fim_existente != data_inicio_existente
                                else data_inicio_existente.strftime("%d/%m/%Y")
                            ),
                            "hora_inicio": hora_inicio_existente,
                            "hora_fim": hora_fim_existente,
                        })

                try:
                    caminho_anexo = None

                    if arquivo_anexo is not None:
                        nome_salvo = (
                            f"{int(datetime.now().timestamp())}_"
                            f"{os.path.basename(arquivo_anexo.name)}"
                        )
                        caminho_anexo = os.path.join(
                            UPLOAD_DIR, nome_salvo
                        )

                        with open(caminho_anexo, "wb") as f:
                            f.write(arquivo_anexo.getbuffer())

                    part_str = ", ".join(participantes_sel)

                    if is_edicao:
                        if caminho_anexo:
                            cursor.execute("""
                                UPDATE eventos
                                SET titulo=?, categoria=?, participantes=?,
                                    data_evento=?, dias_duracao=?, hora_inicio=?,
                                    hora_fim=?, local=?, descricao=?, anexo_path=?
                                WHERE id=?
                            """, (
                                titulo.strip(), categoria, part_str,
                                data_ev.strftime("%Y-%m-%d"),
                                int(dias_duracao),
                                h_in.strftime("%H:%M"),
                                h_fim.strftime("%H:%M"),
                                local_ev, desc_ev, caminho_anexo,
                                st.session_state.evento_editando_id
                            ))
                        else:
                            cursor.execute("""
                                UPDATE eventos
                                SET titulo=?, categoria=?, participantes=?,
                                    data_evento=?, dias_duracao=?, hora_inicio=?,
                                    hora_fim=?, local=?, descricao=?
                                WHERE id=?
                            """, (
                                titulo.strip(), categoria, part_str,
                                data_ev.strftime("%Y-%m-%d"),
                                int(dias_duracao),
                                h_in.strftime("%H:%M"),
                                h_fim.strftime("%H:%M"),
                                local_ev, desc_ev,
                                st.session_state.evento_editando_id
                            ))
                    else:
                        cursor.execute("""
                            INSERT INTO eventos (
                                titulo, categoria, participantes, data_evento,
                                dias_duracao, hora_inicio, hora_fim, local,
                                descricao, anexo_path, criado_por
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            titulo.strip(), categoria, part_str,
                            data_ev.strftime("%Y-%m-%d"),
                            int(dias_duracao),
                            h_in.strftime("%H:%M"),
                            h_fim.strftime("%H:%M"),
                            local_ev, desc_ev, caminho_anexo,
                            st.session_state.name
                        ))

                    conn.commit()

                except Exception as e:
                    conn.rollback()
                    st.error(f"Erro ao salvar o evento: {e}")
                    conn.close()
                    st.stop()

                conn.close()

                st.session_state.modo_criacao = False
                st.session_state.evento_editando_id = None

                if eventos_conflitantes:
                    # Guarda o alerta para exibi-lo após a gravação.
                    st.session_state.eventos_conflitantes_alerta = (
                        eventos_conflitantes
                    )
                    st.session_state.mensagem_salvamento = (
                        "Evento atualizado!" if is_edicao
                        else "Evento cadastrado!"
                    )
                    st.rerun()
                else:
                    st.success(
                        "Evento atualizado!" if is_edicao
                        else "Evento cadastrado!"
                    )
                    st.rerun()

    else:
        # --- LISTAGEM DOS EVENTOS ---
        conn = get_connection()

        df_eventos = pd.read_sql_query("""
            SELECT *
            FROM eventos
            ORDER BY data_evento ASC, hora_inicio ASC
        """, conn)

        conn.close()

        if not df_eventos.empty:
            linhas_expandidas = []

            for _, row in df_eventos.iterrows():
                dt_ini = datetime.strptime(
                    row["data_evento"], "%Y-%m-%d"
                ).date()

                dias = (
                    int(row["dias_duracao"])
                    if "dias_duracao" in row
                    and pd.notna(row["dias_duracao"])
                    else 1
                )

                for i in range(max(dias, 1)):
                    dt_atual = dt_ini + timedelta(days=i)
                    r_copia = row.copy()
                    r_copia["data_calculada"] = dt_atual.strftime(
                        "%Y-%m-%d"
                    )
                    r_copia["dt_obj"] = pd.to_datetime(dt_atual)
                    linhas_expandidas.append(r_copia)

            df_expandido = pd.DataFrame(linhas_expandidas)

            anos_disponiveis = sorted(
                df_expandido["dt_obj"].dt.year.unique(),
                reverse=True
            )

            # --- FILTROS RESPONSIVOS EM DUAS COLUNAS ---
            with st.container(key="filtros_duas_colunas"):
                col_ano, col_mes = st.columns(2, gap="small")

                with col_ano:
                    filtro_ano = st.selectbox(
                        "Ano",
                        ["Todos"] + [
                            str(a) for a in anos_disponiveis
                        ],
                        key="filtro_ano"
                    )

                df_temp_mes = (
                    df_expandido
                    if filtro_ano == "Todos"
                    else df_expandido[
                        df_expandido["dt_obj"].dt.year
                        == int(filtro_ano)
                    ]
                )

                meses_com_eventos = sorted(
                    df_temp_mes["dt_obj"].dt.month.unique()
                )

                meses_opcoes = ["Todos"] + [
                    MESES_NOME[m] for m in meses_com_eventos
                ]

                mes_corrente_nome = MESES_NOME.get(date.today().month)

                default_mes_idx = (
                    meses_opcoes.index(mes_corrente_nome)
                    if mes_corrente_nome in meses_opcoes
                    else 0
                )

                with col_mes:
                    filtro_mes = st.selectbox(
                        "Mês",
                        meses_opcoes,
                        index=default_mes_idx,
                        key="filtro_mes"
                    )

                col_quem, col_categoria = st.columns(2, gap="small")

                with col_quem:
                    filtro_membro = st.selectbox(
                        "Quem",
                        ["Todos"] + INTEGRANTES + ["Família Toda"],
                        key="filtro_membro"
                    )

                with col_categoria:
                    filtro_cat = st.selectbox(
                        "Categoria",
                        ["Todas"] + CATEGORIAS,
                        key="filtro_categoria"
                    )

            # --- APLICAÇÃO DOS FILTROS ---
            df_filtrado = df_expandido.copy()

            if filtro_ano != "Todos":
                df_filtrado = df_filtrado[
                    df_filtrado["dt_obj"].dt.year == int(filtro_ano)
                ]

            if filtro_mes != "Todos":
                num_mes = [
                    k for k, v in MESES_NOME.items()
                    if v == filtro_mes
                ][0]

                df_filtrado = df_filtrado[
                    df_filtrado["dt_obj"].dt.month == num_mes
                ]

            if filtro_membro != "Todos":
                df_filtrado = df_filtrado[
                    df_filtrado["participantes"].str.contains(
                        filtro_membro,
                        na=False,
                        regex=False
                    )
                ]

            if filtro_cat != "Todas":
                df_filtrado = df_filtrado[
                    df_filtrado["categoria"] == filtro_cat
                ]

            df_filtrado = df_filtrado.drop_duplicates(subset=["id"])

            st.markdown("---")

            if df_filtrado.empty:
                st.info("Nenhum compromisso encontrado.")
            else:
                for idx, row in df_filtrado.iterrows():
                    dt_ini_obj = datetime.strptime(
                        row["data_evento"], "%Y-%m-%d"
                    ).date()

                    dias_dur = (
                        int(row["dias_duracao"])
                        if "dias_duracao" in row
                        and pd.notna(row["dias_duracao"])
                        else 1
                    )

                    if dias_dur > 1:
                        dt_fim_obj = dt_ini_obj + timedelta(
                            days=dias_dur - 1
                        )

                        data_str = (
                            f"{dt_ini_obj.strftime('%d/%m/%Y')} a "
                            f"{dt_fim_obj.strftime('%d/%m/%Y')}"
                        )
                    else:
                        data_str = dt_ini_obj.strftime("%d/%m/%Y")

                    titulo_expander = (
                        f"📅 {data_str} | "
                        f"{row['hora_inicio']} | {row['titulo']}"
                    )

                    with st.expander(titulo_expander):
                        st.write(f"**🏷️ Categoria:** {row['categoria']}")
                        st.write(
                            f"**👥 Participantes:** {row['participantes']}"
                        )
                        st.write(f"**✍️ Criado por:** {row['criado_por']}")

                        if row["local"]:
                            st.write(f"**📍 Local:** {row['local']}")

                        if row["descricao"]:
                            st.write(f"**📝 Obs:** {row['descricao']}")

                        anexo_path = row["anexo_path"]

                        if (
                            pd.notna(anexo_path)
                            and isinstance(anexo_path, str)
                            and os.path.exists(anexo_path)
                        ):
                            st.divider()
                            ext = anexo_path.split(".")[-1].lower()

                            if ext in ["jpg", "jpeg", "png"]:
                                st.image(
                                    anexo_path,
                                    caption="Anexo",
                                    use_container_width=True
                                )
                            elif ext == "pdf":
                                with open(anexo_path, "rb") as pdf_file:
                                    st.download_button(
                                        label="📄 Baixar PDF",
                                        data=pdf_file,
                                        file_name=os.path.basename(anexo_path),
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key=f"dl_{row['id']}"
                                    )

                        pode_gerenciar = (
                            st.session_state.role == "admin"
                            or st.session_state.name == row["criado_por"]
                        )

                        if pode_gerenciar:
                            st.divider()
                            col_ed1, col_ed2 = st.columns(2)

                            with col_ed1:
                                if st.button(
                                    "✏️ Editar",
                                    key=f"edit_{row['id']}",
                                    use_container_width=True
                                ):
                                    st.session_state.evento_editando_id = (
                                        row["id"]
                                    )
                                    st.rerun()

                            with col_ed2:
                                if st.button(
                                    "❌ Excluir",
                                    key=f"del_{row['id']}",
                                    use_container_width=True
                                ):
                                    if (
                                        pd.notna(anexo_path)
                                        and isinstance(anexo_path, str)
                                        and os.path.exists(anexo_path)
                                    ):
                                        try:
                                            os.remove(anexo_path)
                                        except Exception:
                                            pass

                                    conn = get_connection()
                                    cursor = conn.cursor()

                                    cursor.execute(
                                        "DELETE FROM eventos WHERE id = ?",
                                        (row["id"],)
                                    )

                                    conn.commit()
                                    conn.close()

                                    st.success("Excluído!")
                                    st.rerun()

        else:
            st.markdown("---")
            st.info("Nenhum evento cadastrado.")


# --- ALERTA PENDENTE APÓS SALVAMENTO ---
if "eventos_conflitantes_alerta" in st.session_state:
    eventos_alerta = st.session_state.pop(
        "eventos_conflitantes_alerta"
    )
    mensagem = st.session_state.pop(
        "mensagem_salvamento",
        "Evento salvo!"
    )

    st.toast(mensagem)
    mostrar_alerta_eventos_existentes(eventos_alerta)


# --- BOTÃO FLUTUANTE: NOVO EVENTO ---
if (
    st.session_state.get("logged_in")
    and not st.session_state.get("modo_criacao")
    and st.session_state.get("evento_editando_id") is None
):
    with st.container(key="botao_flutuante_evento"):
        if st.button(
            "＋",
            key="btn_novo_evento_flutuante",
            type="primary",
            help="Cadastrar novo evento"
        ):
            st.session_state.modo_criacao = True
            st.rerun()

# --- ABA 2: RELATÓRIOS ---
if secao == "📊 Relatórios":
    conn = get_connection()
    df_rep = pd.read_sql_query("SELECT * FROM eventos", conn)
    conn.close()

    if df_rep.empty:
        st.info("Sem dados para estatísticas.")
    else:
        # --- OCUPAÇÃO POR DATA ---
        st.markdown("### 🔍 Ocupação por Data")
        st.caption(
            "🔴 Dia ocupado. "

        )

        # Preparação dos eventos
        eventos_calendario = []
        eventos_por_data = {}

        for _, r in df_rep.iterrows():
            try:
                dt_ini = pd.to_datetime(r["data_evento"]).date()

                dias = (
                    int(r["dias_duracao"])
                    if "dias_duracao" in r
                    and pd.notna(r["dias_duracao"])
                    else 1
                )
                dias = max(dias, 1)

                # FullCalendar usa data final exclusiva
                dt_fim = dt_ini + timedelta(days=dias)

                titulo = str(r.get("titulo", "Evento"))
                participantes = str(
                    r.get("participantes", "Não informado")
                )
                hora = str(r.get("hora_inicio", "Não informado"))

                evento = {
                    "title": titulo,
                    "start": dt_ini.isoformat(),
                    "end": dt_fim.isoformat(),
                    "allDay": True,
                    "backgroundColor": "#D9534F",
                    "borderColor": "#B52B27",
                    "textColor": "#FFFFFF",
                    "extendedProps": {
                        "titulo_original": titulo,
                        "participantes": participantes,
                        "horario": hora,
                    },
                }

                eventos_calendario.append(evento)

                # Registra todas as datas ocupadas
                for i in range(dias):
                    dia = dt_ini + timedelta(days=i)
                    chave = dia.isoformat()

                    eventos_por_data.setdefault(
                        chave, []
                    ).append({
                        "titulo": titulo,
                        "participantes": participantes,
                        "horario": hora,
                    })

            except (ValueError, TypeError, OverflowError):
                continue

        # CSS d
        css_calendario = """
            .fc-daygrid-day.fc-day-today {
                background-color: #FFF3CD !important;
            }

            .fc-event {
                cursor: pointer;
                border-radius: 4px;
                padding: 2px;
            }

            .fc-event-title {
                font-weight: 600;
            }

            .fc-toolbar-title {
                text-transform: capitalize;
                font-size: 18px !important;
            }

            .fc-daygrid-day-number {
                padding: 5px;
            }
        """

        # Opções compactas do calendário
        calendario_opcoes = {
            "initialView": "dayGridMonth",
            "initialDate": date.today().isoformat(),
            "locale": "pt-br",
            "firstDay": 1,
            "height": 460,
            "contentHeight": 410,
            "aspectRatio": 1.8,
            "expandRows": True,
            "headerToolbar": {
                "left": "prev,next",
                "center": "title",
                "right": "today",
            },
            "buttonText": {
                "today": "Hoje",
                "month": "Mês",
                "list": "Lista",
            },
            "navLinks": True,
            "dayMaxEvents": 2,
        }

        # Renderiza o calendário de ocupação
        retorno_calendario = calendar(
            events=eventos_calendario,
            options=calendario_opcoes,
            key="calendario_ocupacao",
        )

        # Identifica qual interação ocorreu
        callback = (
            retorno_calendario.get("callback")
            if isinstance(retorno_calendario, dict)
            else None
        )

        # Exibe os detalhes do evento clicado
        if (
            callback == "eventClick"
            or (
                isinstance(retorno_calendario, dict)
                and "eventClick" in retorno_calendario
            )
        ):
            dados = retorno_calendario.get(
                "eventClick", {}
            ).get("event", {})

            detalhes = dados.get("extendedProps", {})

            st.markdown("#### 📌 Detalhes do evento")
            st.write(
                "**Título:** "
                + str(detalhes.get(
                    "titulo_original",
                    dados.get("title", "Evento")
                ))
            )
            st.write(
                "**Horário:** "
                + str(detalhes.get(
                    "horario", "Não informado"
                ))
            )
            st.write(
                "**Participantes:** "
                + str(detalhes.get(
                    "participantes", "Não informado"
                ))
            )

        # Consulta os compromissos ao clicar na data
        elif (
            callback == "dateClick"
            or (
                isinstance(retorno_calendario, dict)
                and "dateClick" in retorno_calendario
            )
        ):
            dados_data = retorno_calendario.get(
                "dateClick", {}
            )
            data_texto = dados_data.get("date", "")[:10]

            try:
                data_selecionada = date.fromisoformat(data_texto)

                st.markdown(
                    "#### 📅 "
                    + data_selecionada.strftime("%d/%m/%Y")
                )

                eventos_dia = eventos_por_data.get(
                    data_texto, []
                )

                if not eventos_dia:
                    st.success("🟢 Dia livre!")
                else:
                    st.warning(
                        f"🔴 {len(eventos_dia)} compromisso(s)"
                    )

                    for evento in eventos_dia:
                        st.write(
                            f"**{evento['titulo']}** — "
                            f"{evento['horario']} — "
                            f"{evento['participantes']}"
                        )

            except ValueError:
                pass

        # Detalhes ao passar o mouse sobre o evento
        elif (
            callback == "eventMouseEnter"
            or (
                isinstance(retorno_calendario, dict)
                and "eventMouseEnter" in retorno_calendario
            )
        ):
            dados = retorno_calendario.get(
                "eventMouseEnter", {}
            ).get("event", {})

            detalhes = dados.get("extendedProps", {})

            st.markdown("#### 📌 Evento sob o mouse")
            st.write(
                "**Título:** "
                + str(detalhes.get(
                    "titulo_original",
                    dados.get("title", "Evento")
                ))
            )
            st.write(
                "**Horário:** "
                + str(detalhes.get(
                    "horario", "Não informado"
                ))
            )
            st.write(
                "**Participantes:** "
                + str(detalhes.get(
                    "participantes", "Não informado"
                ))
            )

        # --- EVENTOS POR CATEGORIA ---
        st.markdown("---")
        st.markdown("### 📊 Eventos por Categoria")

        cat_counts = df_rep["categoria"].value_counts()
        st.bar_chart(cat_counts)

# --- ABA 3: ADMINISTRAÇÃO ---
if (
    st.session_state.role == "admin"
    and secao == "⚙️ Admin"
):
        adm_tab1, adm_tab2 = st.tabs([
            "👥 Usuários",
            "🏷️ Categorias"
        ])

        # =========================================
        # USUÁRIOS: CRIAR, EDITAR, EXCLUIR E SENHA
        # =========================================
        with adm_tab1:
            st.subheader("👥 Gerenciamento de Usuários")

            operacao = st.selectbox(
                "O que deseja fazer?",
                [
                    "Criar usuário",
                    "Editar usuário",
                    "Excluir usuário",
                    "Alterar senha"
                ],
                key="operacao_usuarios"
            )

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, username, nome_completo, perfil
                FROM usuarios
                ORDER BY nome_completo
            """)

            usuarios_cadastrados = cursor.fetchall()
            conn.close()

            # --- CRIAR USUÁRIO ---
            if operacao == "Criar usuário":
                st.markdown("#### ➕ Novo usuário")

                with st.form("form_novo_usuario", clear_on_submit=True):
                    novo_user = st.text_input(
                        "Login (ex: marcia)"
                    ).strip().lower()

                    novo_nome_completo = st.text_input(
                        "Nome completo"
                    ).strip()

                    nova_senha = st.text_input(
                        "Senha",
                        type="password"
                    )

                    novo_perfil = st.selectbox(
                        "Perfil",
                        ["membro", "admin"],
                        format_func=lambda x: (
                            "Administrador" if x == "admin" else "Membro"
                        )
                    )

                    btn_criar_user = st.form_submit_button(
                        "💾 Criar usuário",
                        use_container_width=True
                    )

                if btn_criar_user:
                    if (
                        not novo_user
                        or not novo_nome_completo
                        or not nova_senha
                    ):
                        st.error("Preencha todos os campos.")
                    elif len(nova_senha) < 6:
                        st.error(
                            "A senha deve ter pelo menos 6 caracteres."
                        )
                    else:
                        conn = get_connection()

                        try:
                            conn.execute("""
                                INSERT INTO usuarios
                                    (username, nome_completo, senha, perfil)
                                VALUES (?, ?, ?, ?)
                            """, (
                                novo_user,
                                novo_nome_completo,
                                hash_senha(nova_senha),
                                novo_perfil
                            ))

                            conn.commit()
                            st.success("Usuário criado com sucesso!")
                            st.rerun()

                        except sqlite3.IntegrityError:
                            st.error(
                                "Esse login já existe. Escolha outro."
                            )
                        finally:
                            conn.close()

            # --- EDITAR USUÁRIO ---
            elif operacao == "Editar usuário":
                st.markdown("#### ✏️ Editar cadastro")

                if not usuarios_cadastrados:
                    st.info("Não há usuários cadastrados.")
                else:
                    opcoes_usuarios = {
                        f"{u[2]} (@{u[1]})": u[0]
                        for u in usuarios_cadastrados
                    }

                    usuario_escolhido = st.selectbox(
                        "Selecione o usuário",
                        list(opcoes_usuarios.keys()),
                        key="usuario_editar_selecao"
                    )

                    usuario_id = opcoes_usuarios[usuario_escolhido]

                    usuario_atual = next(
                        u for u in usuarios_cadastrados
                        if u[0] == usuario_id
                    )

                    with st.form("form_editar_usuario"):
                        editar_login = st.text_input(
                            "Login",
                            value=usuario_atual[1]
                        ).strip().lower()

                        editar_nome = st.text_input(
                            "Nome completo",
                            value=usuario_atual[2]
                        ).strip()

                        editar_perfil = st.selectbox(
                            "Perfil",
                            ["membro", "admin"],
                            index=1 if usuario_atual[3] == "admin" else 0,
                            format_func=lambda x: (
                                "Administrador" if x == "admin" else "Membro"
                            )
                        )

                        salvar_edicao = st.form_submit_button(
                            "💾 Salvar alterações",
                            use_container_width=True
                        )

                    if salvar_edicao:
                        if not editar_login or not editar_nome:
                            st.error("Login e nome são obrigatórios.")
                        else:
                            conn = get_connection()
                            cursor = conn.cursor()

                            try:
                                cursor.execute("""
                                    SELECT COUNT(*)
                                    FROM usuarios
                                    WHERE perfil = 'admin'
                                """)

                                total_admins = cursor.fetchone()[0]

                                if (
                                    usuario_atual[3] == "admin"
                                    and editar_perfil != "admin"
                                    and total_admins <= 1
                                ):
                                    st.error(
                                        "Não é possível rebaixar o único "
                                        "administrador do sistema."
                                    )
                                else:
                                    cursor.execute("""
                                        UPDATE usuarios
                                        SET username = ?,
                                            nome_completo = ?,
                                            perfil = ?
                                        WHERE id = ?
                                    """, (
                                        editar_login,
                                        editar_nome,
                                        editar_perfil,
                                        usuario_id
                                    ))

                                    conn.commit()

                                    if (
                                        usuario_atual[1]
                                        == st.session_state.user
                                    ):
                                        st.session_state.user = editar_login
                                        st.session_state.name = editar_nome
                                        st.session_state.role = editar_perfil

                                    st.success("Cadastro atualizado!")
                                    st.rerun()

                            except sqlite3.IntegrityError:
                                st.error(
                                    "Esse login já está sendo utilizado."
                                )
                            finally:
                                conn.close()

            # --- EXCLUIR USUÁRIO ---
            elif operacao == "Excluir usuário":
                st.markdown("#### 🗑️ Excluir usuário")

                if not usuarios_cadastrados:
                    st.info("Não há usuários cadastrados.")
                else:
                    opcoes_usuarios = {
                        f"{u[2]} (@{u[1]})": u[0]
                        for u in usuarios_cadastrados
                    }

                    usuario_excluir = st.selectbox(
                        "Selecione o usuário que deseja excluir",
                        list(opcoes_usuarios.keys()),
                        key="usuario_excluir_selecao"
                    )

                    usuario_id = opcoes_usuarios[usuario_excluir]

                    dados_excluir = next(
                        u for u in usuarios_cadastrados
                        if u[0] == usuario_id
                    )

                    st.warning(
                        f"Você selecionou: **{dados_excluir[2]}** "
                        f"(@{dados_excluir[1]})."
                    )

                    if dados_excluir[1] == st.session_state.user:
                        st.error(
                            "Não é permitido excluir o próprio usuário conectado."
                        )
                    else:
                        confirmar_exclusao = st.checkbox(
                            "Confirmo que desejo excluir este usuário.",
                            key="confirmar_exclusao_usuario"
                        )

                        if st.button(
                            "❌ Excluir usuário",
                            use_container_width=True,
                            disabled=not confirmar_exclusao
                        ):
                            conn = get_connection()
                            cursor = conn.cursor()

                            try:
                                cursor.execute(
                                    "SELECT perfil FROM usuarios WHERE id = ?",
                                    (usuario_id,)
                                )

                                usuario_banco = cursor.fetchone()

                                if usuario_banco is None:
                                    st.error("Usuário não encontrado.")

                                elif usuario_banco[0] == "admin":
                                    cursor.execute("""
                                        SELECT COUNT(*)
                                        FROM usuarios
                                        WHERE perfil = 'admin'
                                    """)

                                    total_admins = cursor.fetchone()[0]

                                    if total_admins <= 1:
                                        st.error(
                                            "Não é possível excluir o último "
                                            "administrador."
                                        )
                                    else:
                                        cursor.execute(
                                            "DELETE FROM usuarios WHERE id = ?",
                                            (usuario_id,)
                                        )

                                        conn.commit()
                                        st.success("Usuário excluído!")
                                        st.rerun()
                                else:
                                    cursor.execute(
                                        "DELETE FROM usuarios WHERE id = ?",
                                        (usuario_id,)
                                    )

                                    conn.commit()
                                    st.success("Usuário excluído!")
                                    st.rerun()

                            finally:
                                conn.close()

            # --- ALTERAR SENHA ---
            elif operacao == "Alterar senha":
                st.markdown("#### 🔑 Alterar senha")

                if not usuarios_cadastrados:
                    st.info("Não há usuários cadastrados.")
                else:
                    opcoes_usuarios = {
                        f"{u[2]} (@{u[1]})": u[1]
                        for u in usuarios_cadastrados
                    }

                    usuario_senha = st.selectbox(
                        "Selecione o usuário",
                        list(opcoes_usuarios.keys()),
                        key="usuario_alterar_senha"
                    )

                    with st.form(
                        "form_mudar_senha",
                        clear_on_submit=True
                    ):
                        nova_senha_input = st.text_input(
                            "Nova senha",
                            type="password"
                        )

                        confirmar_senha = st.text_input(
                            "Confirmar nova senha",
                            type="password"
                        )

                        atualizar_senha = st.form_submit_button(
                            "🔄 Atualizar senha",
                            use_container_width=True
                        )

                    if atualizar_senha:
                        if not nova_senha_input or not confirmar_senha:
                            st.error("Preencha os dois campos.")
                        elif len(nova_senha_input) < 6:
                            st.error(
                                "A senha deve ter pelo menos 6 caracteres."
                            )
                        elif nova_senha_input != confirmar_senha:
                            st.error("As senhas não são iguais.")
                        else:
                            conn = get_connection()

                            conn.execute("""
                                UPDATE usuarios
                                SET senha = ?
                                WHERE username = ?
                            """, (
                                hash_senha(nova_senha_input),
                                opcoes_usuarios[usuario_senha]
                            ))

                            conn.commit()
                            conn.close()

                            st.success("Senha atualizada com sucesso!")
                            st.rerun()

            # --- LISTAGEM DE USUÁRIOS ---
            st.divider()
            st.markdown("#### 📋 Usuários cadastrados")

            conn = get_connection()

            df_cadastrados = pd.read_sql_query("""
                SELECT
                    username AS Login,
                    nome_completo AS Nome,
                    CASE
                        WHEN perfil = 'admin' THEN 'Administrador'
                        ELSE 'Membro'
                    END AS Perfil
                FROM usuarios
                ORDER BY nome_completo
            """, conn)

            conn.close()

            if df_cadastrados.empty:
                st.info("Nenhum usuário cadastrado.")
            else:
                st.dataframe(
                    df_cadastrados,
                    use_container_width=True,
                    hide_index=True
                )
        # =========================================
        # CATEGORIAS: CRIAR, EDITAR E EXCLUIR
        # =========================================
        with adm_tab2:
            st.subheader("🏷️ Gerenciar categorias")

            operacao_categoria = st.selectbox(
                "O que deseja fazer?",
                [
                    "Criar categoria",
                    "Editar categoria",
                    "Excluir categoria"
                ],
                key="operacao_categoria"
            )

            # Busca as categorias; "Outro" e "Outros" ficam por último.
            conn = get_connection()

            df_categorias = pd.read_sql_query("""
                SELECT id, nome
                FROM categorias
                ORDER BY
                    CASE
                        WHEN LOWER(TRIM(nome)) LIKE 'outro%' THEN 1
                        ELSE 0
                    END,
                    nome COLLATE NOCASE
            """, conn)

            conn.close()

            # --- CRIAR CATEGORIA ---
            if operacao_categoria == "Criar categoria":
                with st.form(
                    "form_criar_categoria",
                    clear_on_submit=True
                ):
                    nome_categoria = st.text_input(
                        "Nome da nova categoria"
                    ).strip()

                    salvar_categoria = st.form_submit_button(
                        "➕ Criar categoria",
                        use_container_width=True
                    )

                if salvar_categoria:
                    nomes_existentes = [
                        str(nome).strip().casefold()
                        for nome in df_categorias["nome"].tolist()
                    ]

                    if not nome_categoria:
                        st.warning("Informe o nome da categoria.")
                    elif nome_categoria.casefold() in nomes_existentes:
                        st.warning("Essa categoria já existe.")
                    else:
                        conn = get_connection()

                        try:
                            conn.execute(
                                "INSERT INTO categorias (nome) VALUES (?)",
                                (nome_categoria,)
                            )

                            conn.commit()
                            st.success("Categoria criada com sucesso!")
                            st.rerun()

                        except sqlite3.IntegrityError:
                            st.error("Essa categoria já existe.")
                        finally:
                            conn.close()

            # --- EDITAR CATEGORIA ---
            elif operacao_categoria == "Editar categoria":
                if df_categorias.empty:
                    st.info("Não existem categorias cadastradas.")
                else:
                    categorias_dict = dict(
                        zip(
                            df_categorias["nome"],
                            df_categorias["id"]
                        )
                    )

                    categoria_selecionada = st.selectbox(
                        "Selecione a categoria",
                        list(categorias_dict.keys()),
                        key="categoria_editar"
                    )

                    categoria_id = categorias_dict[
                        categoria_selecionada
                    ]

                    with st.form("form_editar_categoria"):
                        novo_nome = st.text_input(
                            "Novo nome da categoria",
                            value=categoria_selecionada
                        ).strip()

                        salvar_edicao_categoria = st.form_submit_button(
                            "💾 Salvar alterações",
                            use_container_width=True
                        )

                    if salvar_edicao_categoria:
                        nomes_existentes = [
                            str(nome).strip().casefold()
                            for nome in df_categorias["nome"].tolist()
                            if str(nome).strip().casefold()
                            != categoria_selecionada.strip().casefold()
                        ]

                        if not novo_nome:
                            st.warning("Informe o novo nome.")
                        elif novo_nome.casefold() in nomes_existentes:
                            st.warning(
                                "Já existe uma categoria com esse nome."
                            )
                        else:
                            conn = get_connection()
                            cursor = conn.cursor()

                            try:
                                # Atualiza os eventos antigos vinculados
                                # à categoria pelo nome.
                                cursor.execute(
                                    """
                                    UPDATE eventos
                                    SET categoria = ?
                                    WHERE categoria = ?
                                    """,
                                    (novo_nome, categoria_selecionada)
                                )

                                cursor.execute(
                                    """
                                    UPDATE categorias
                                    SET nome = ?
                                    WHERE id = ?
                                    """,
                                    (novo_nome, categoria_id)
                                )

                                conn.commit()
                                st.success(
                                    "Categoria atualizada com sucesso!"
                                )
                                st.rerun()

                            except sqlite3.IntegrityError:
                                conn.rollback()
                                st.error(
                                    "Já existe uma categoria com esse nome."
                                )
                            finally:
                                conn.close()

            # --- EXCLUIR CATEGORIA ---
            elif operacao_categoria == "Excluir categoria":
                if df_categorias.empty:
                    st.info("Não existem categorias cadastradas.")
                else:
                    categorias_dict = dict(
                        zip(
                            df_categorias["nome"],
                            df_categorias["id"]
                        )
                    )

                    categoria_excluir = st.selectbox(
                        "Selecione a categoria que deseja excluir",
                        list(categorias_dict.keys()),
                        key="categoria_excluir"
                    )

                    confirmar_exclusao_categoria = st.checkbox(
                        f'Confirmo que desejo excluir a categoria "{categoria_excluir}".',
                        key="confirmar_exclusao_categoria"
                    )

                    if st.button(
                        "❌ Excluir categoria",
                        disabled=not confirmar_exclusao_categoria,
                        use_container_width=True
                    ):
                        conn = get_connection()
                        cursor = conn.cursor()

                        try:
                            cursor.execute(
                                """
                                SELECT COUNT(*)
                                FROM eventos
                                WHERE categoria = ?
                                """,
                                (categoria_excluir,)
                            )

                            categoria_em_uso = cursor.fetchone()[0] > 0

                            if categoria_em_uso:
                                st.error(
                                    "Não é possível excluir esta categoria "
                                    "porque ela está vinculada a um ou mais "
                                    "eventos. Edite esses eventos e escolha "
                                    "outra categoria antes de excluí-la."
                                )
                            else:
                                cursor.execute(
                                    "DELETE FROM categorias WHERE id = ?",
                                    (categorias_dict[categoria_excluir],)
                                )

                                conn.commit()
                                st.success(
                                    "Categoria excluída com sucesso!"
                                )
                                st.rerun()

                        finally:
                            conn.close()

            # --- LISTAGEM DE CATEGORIAS ---
            st.divider()
            st.subheader("📋 Categorias cadastradas")

            # Atualiza a listagem para refletir mudanças realizadas.
            conn = get_connection()

            df_categorias_lista = pd.read_sql_query("""
                SELECT nome
                FROM categorias
                ORDER BY
                    CASE
                        WHEN LOWER(TRIM(nome)) LIKE 'outro%' THEN 1
                        ELSE 0
                    END,
                    nome COLLATE NOCASE
            """, conn)

            conn.close()

            if df_categorias_lista.empty:
                st.info("Nenhuma categoria cadastrada.")
            else:
                st.dataframe(
                    df_categorias_lista,
                    hide_index=True,
                    use_container_width=True
                )
