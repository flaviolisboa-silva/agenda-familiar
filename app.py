import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import os

# 1. Configuração Inicial da Página
st.set_page_config(
    page_title="Agenda Familiar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Estilização CSS para Ajustes de Layout Mobile e Redução do Espaço Superior
st.markdown("""
    <style>
        /* Reduz o espaço branco no topo da página */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Reduz o espaçamento entre elementos verticais */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.5rem !important;
        }
        
        /* Ajusta as colunas dos filtros para exibição lado a lado em telas menores */
        [data-testid="column"] {
            min-width: 0px !important;
            flex: 1 1 0% !important;
        }

        /* Oculta o menu padrão do Streamlit para visual limpo */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 3. Conexão com o Banco de Dados SQLite
DB_NAME = "agenda_familiar.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# 4. Verificação de Autenticação / Login
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    st.title("🔑 Agenda Familiar - Login")
    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        submit_login = st.form_submit_button("Entrar")
        
        if submit_login:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (usuario, hash_senha(senha)))
            user = c.fetchone()
            conn.close()
            
            if user:
                st.session_state["logado"] = True
                st.session_state["usuario"] = usuario
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# 5. Topo da Aplicação
st.title("📅 Agenda Familiar")

# Abas Principais
aba1, aba2, aba3 = st.tabs(["📅 Calendário", "📊 Relatórios", "⚙️ Administração"])

# ---------------------------------------------------------
# ABA 1: CALENDÁRIO / LINHA DO TEMPO
# ---------------------------------------------------------
with aba1:
    st.subheader("Linha do Tempo Familiar")
    
    if st.button("➕ Criar Evento", use_container_width=True):
        st.session_state["mostrar_novo_evento"] = True

    # Modal / Formulário para Novo Evento
    if st.session_state.get("mostrar_novo_evento", False):
        with st.expander("Cadastrar Novo Evento", expanded=True):
            with st.form("form_evento"):
                titulo = st.text_input("Título do Evento")
                data_evento = st.date_input("Data")
                integrante = st.selectbox("Integrante", ["Flávio", "Márcia", "Gabriel", "Giovanna", "Todos"])
                categoria = st.selectbox("Categoria", ["Saúde", "Escola", "Lazer", "Financeiro", "Outros"])
                descricao = st.text_area("Descrição")
                submit_salvar = st.form_submit_button("Salvar Evento")
                
                if submit_salvar:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO eventos (titulo, data, integrante, categoria, descricao)
                        VALUES (?, ?, ?, ?, ?)
                    """, (titulo, str(data_evento), integrante, categoria, descricao))
                    conn.commit()
                    conn.close()
                    st.success("Evento salvo com sucesso!")
                    st.session_state["mostrar_novo_evento"] = False
                    st.rerun()

    st.markdown("---")

    # FILTROS ORGANIZADOS LADO A LADO (4 Colunas na mesma linha)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ano_sel = st.selectbox("Ano", ["2026", "2025", "Todos"])
    with col2:
        mes_sel = st.selectbox("Mês", ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])
    with col3:
        integ_sel = st.selectbox("Integrante", ["Todos", "Flávio", "Márcia", "Gabriel", "Giovanna"])
    with col4:
        categ_sel = st.selectbox("Categoria", ["Todas", "Saúde", "Escola", "Lazer", "Financeiro", "Outros"])

    # Consulta dos Eventos com Filtros
    conn = get_connection()
    query = "SELECT id, titulo, data, integrante, categoria, descricao FROM eventos WHERE 1=1"
    params = []

    if ano_sel != "Todos":
        query += " AND strftime('%Y', data) = ?"
        params.append(ano_sel)
    if mes_sel != "Todos":
        query += " AND strftime('%m', data) = ?"
        params.append(mes_sel)
    if integ_sel != "Todos":
        query += " AND integrante = ?"
        params.append(integ_sel)
    if categ_sel != "Todas":
        query += " AND categoria = ?"
        params.append(categ_sel)

    query += " ORDER BY data DESC"
    
    df_eventos = pd.read_sql_query(query, conn, params=params)
    conn.close()

    # Exibição dos Eventos
    if not df_eventos.empty:
        for idx, row in df_eventos.iterrows():
            with st.container():
                st.markdown(f"### {row['titulo']} ({row['data']})")
                st.write(f"**Integrante:** {row['integrante']} | **Categoria:** {row['categoria']}")
                if row['descricao']:
                    st.write(f"_{row['descricao']}_")
                st.markdown("---")
    else:
        st.info("Nenhum evento encontrado para os filtros selecionados.")

# ---------------------------------------------------------
# ABA 2: RELATÓRIOS
# ---------------------------------------------------------
with aba2:
    st.subheader("Relatórios e Resumos")
    conn = get_connection()
    df_todos = pd.read_sql_query("SELECT * FROM eventos", conn)
    conn.close()

    if not df_todos.empty:
        st.write("Total de eventos cadastrados:", len(df_todos))
        st.bar_chart(df_todos['categoria'].value_counts())
    else:
        st.info("Sem dados suficientes para gerar relatórios.")

# ---------------------------------------------------------
# ABA 3: ADMINISTRAÇÃO
# ---------------------------------------------------------
with aba3:
    st.subheader("Configurações do Sistema")
    st.write(f"Usuário conectado: **{st.session_state.get('usuario', '')}**")
    if st.button("Sair / Logout"):
        st.session_state["logado"] = False
        st.rerun()
