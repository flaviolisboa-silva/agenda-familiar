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
    
    # Tabela de Eventos
    cursor.execute('''
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
    ''')
    
    # Migrações automáticas
    cursor.execute("PRAGMA table_info(eventos)")
    colunas_tabela = [col[1] for col in cursor.fetchall()]
    if "criado_por" not in colunas_tabela:
        cursor.execute("ALTER TABLE eventos ADD COLUMN criado_por TEXT DEFAULT 'Administrador'")
    if "dias_duracao" not in colunas_tabela:
        cursor.execute("ALTER TABLE eventos ADD COLUMN dias_duracao INTEGER DEFAULT 1")
    
    # Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nome_completo TEXT NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    ''')
    
    # Tabela de Categorias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        senha_padrao = hash_senha("123456")
        cursor.execute('''
            INSERT INTO usuarios (username, nome_completo, senha, perfil)
            VALUES (?, ?, ?, ?)
        ''', ("flavio", "Flávio Lisboa", senha_padrao, "admin"))
        
    cursor.execute("SELECT COUNT(*) FROM categorias")
    if cursor.fetchone()[0] == 0:
        cats_iniciais = ["Aniversário", "Igreja", "Viagem", "Futebol", "Médico/Saúde", "Escola/Estudo", "Trabalho", "Lazer", "Outro"]
        for cat in cats_iniciais:
            cursor.execute("INSERT OR IGNORE INTO categorias (nome) VALUES (?)", (cat,))

    conn.commit()
    conn.close()

def limpar_historico_antigo():
    limite = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT anexo_path FROM eventos WHERE data_evento < ?", (limite,))
    anexos = cursor.fetchall()
    for item in anexos:
        caminho = item[0]
        if caminho and isinstance(caminho, str) and os.path.exists(caminho):
            try:
                os.remove(caminho)
            except Exception:
                pass
    cursor.execute("DELETE FROM eventos WHERE data_evento < ?", (limite,))
    conn.commit()
    conn.close()

init_db()
limpar_historico_antigo()

# --- ESTILIZAÇÃO CSS MOBILE ---
st.markdown("""
    <style>
    .stApp { max-width: 100%; }
    div[data-testid="stExpander"] { background-color: #f9f9f9; border-radius: 8px; margin-bottom: 8px; }
    button[kind="primary"] { width: 100%; }
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
    st.title("🔒 Agenda Familiar - Acesso")
    st.write("Por favor, faça login para continuar.")
    
    with st.form("form_login"):
        username = st.text_input("Usuário").strip().lower()
        senha = st.text_input("Senha", type="password")
        submit_login = st.form_submit_button("Entrar", use_container_width=True)
        
        if submit_login:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username, nome_completo, senha, perfil FROM usuarios WHERE username = ?", (username,))
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
df_usuarios = pd.read_sql_query("SELECT nome_completo FROM usuarios", conn)
df_cat_db = pd.read_sql_query("SELECT nome FROM categorias ORDER BY nome ASC", conn)
conn.close()

INTEGRANTES = df_usuarios["nome_completo"].tolist()
CATEGORIAS = df_cat_db["nome"].tolist()

MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# --- BARRA LATERAL ---
with st.sidebar:
    st.write(f"👤 Logado como: **{st.session_state.name}**")
    st.caption(f"Perfil: {'Administrador 🛠️' if st.session_state.role == 'admin' else 'Membro 👨‍👩‍👧‍👦'}")
    if st.button("🚪 Sair / Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.name = None
        st.session_state.role = None
        st.session_state.modo_criacao = False
        st.session_state.evento_editando_id = None
        st.rerun()

st.title("📅 Agenda Familiar")

# --- DEFINIÇÃO DE ABAS ---
if st.session_state.role == "admin":
    tab1, tab2, tab3 = st.tabs(["📆 Calendário", "📊 Relatórios", "⚙️ Administração"])
else:
    tab1, tab2 = st.tabs(["📆 Calendário", "📊 Relatórios"])

# --- ABA 1: CALENDÁRIO (TELA INICIAL) ---
with tab1:
    if st.session_state.modo_criacao or st.session_state.evento_editando_id is not None:
        is_edicao = st.session_state.evento_editando_id is not None
        st.subheader("✏️ Editar Compromisso" if is_edicao else "➕ Novo Compromisso")
        
        ev_dados = {}
        if is_edicao:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT titulo, categoria, participantes, data_evento, dias_duracao, hora_inicio, hora_fim, local, descricao FROM eventos WHERE id = ?", (st.session_state.evento_editando_id,))
            res = cursor.fetchone()
            conn.close()
            if res:
                ev_dados = {
                    "titulo": res[0], "categoria": res[1], "participantes": res[2].split(", "),
                    "data": datetime.strptime(res[3], "%Y-%m-%d").date(),
                    "dias": res[4] if res[4] else 1,
                    "h_in": datetime.strptime(res[5], "%H:%M").time(), "h_fim": datetime.strptime(res[6], "%H:%M").time(),
                    "local": res[7], "desc": res[8]
                }
        
        with st.form("form_evento_cadastro"):
            titulo = st.text_input("Título do Evento*", value=ev_dados.get("titulo", ""), placeholder="Ex: Viagem de Férias, Acampamento...")
            
            col_cat, col_part = st.columns(2)
            with col_cat:
                cat_atual = ev_dados.get("categoria", CATEGORIAS[0] if CATEGORIAS else "")
                idx_cat = CATEGORIAS.index(cat_atual) if cat_atual in CATEGORIAS else 0
                categoria = st.selectbox("Categoria*", CATEGORIAS, index=idx_cat)
            with col_part:
                part_atual = ev_dados.get("participantes", ["Família Toda"])
                participantes_sel = st.multiselect("Quem participa?*", INTEGRANTES + ["Família Toda"], default=part_atual)
                
            col_d, col_qtd = st.columns(2)
            with col_d:
                data_ev = st.date_input("Data de Início*", value=ev_dados.get("data", date.today()), format="DD/MM/YYYY")
            with col_qtd:
                dias_duracao = st.number_input("Duração (Dias)*", min_value=1, max_value=365, value=int(ev_dados.get("dias", 1)))
                
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                h_in = st.time_input("Início*", value=ev_dados.get("h_in", time(9, 0)))
            with col_h2:
                h_fim = st.time_input("Término*", value=ev_dados.get("h_fim", time(10, 0)))
                
            local_ev = st.text_input("Local", value=ev_dados.get("local", ""), placeholder="Ex: Endereço, Destino...")
            desc_ev = st.text_area("Observações / Detalhes", value=ev_dados.get("desc", ""), placeholder="Instruções, lembretes...")
            arquivo_anexo = st.file_uploader("Anexo (Foto do ingresso, convite, PDF...)", type=["png", "jpg", "jpeg", "pdf"])
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                salvar = st.form_submit_button("💾 Salvar na Agenda", use_container_width=True)
            with col_b2:
                cancelar = st.form_submit_button("↩️ Cancelar", use_container_width=True)
                
            if cancelar:
                st.session_state.modo_criacao = False
                st.session_state.evento_editando_id = None
                st.rerun()
                
            if salvar:
                if not titulo:
                    st.error("Por favor, preencha o título do evento.")
                elif not participantes_sel:
                    st.error("Selecione pelo menos um participante.")
                elif h_in >= h_fim:
                    st.error("O horário de término deve ser após o de início.")
                else:
                    caminho_anexo = None
                    if arquivo_anexo is not None:
                        nome_salvo = f"{int(datetime.now().timestamp())}_{arquivo_anexo.name}"
                        caminho_anexo = os.path.join(UPLOAD_DIR, nome_salvo)
                        with open(caminho_anexo, "wb") as f:
                            f.write(arquivo_anexo.getbuffer())
                    
                    part_str = ", ".join(participantes_sel)
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    if is_edicao:
                        if caminho_anexo:
                            cursor.execute('''
                                UPDATE eventos SET titulo=?, categoria=?, participantes=?, data_evento=?, dias_duracao=?, hora_inicio=?, hora_fim=?, local=?, descricao=?, anexo_path=?
                                WHERE id=?
                            ''', (titulo, categoria, part_str, data_ev.strftime("%Y-%m-%d"), int(dias_duracao), h_in.strftime("%H:%M"), h_fim.strftime("%H:%M"), local_ev, desc_ev, caminho_anexo, st.session_state.evento_editando_id))
                        else:
                            cursor.execute('''
                                UPDATE eventos SET titulo=?, categoria=?, participantes=?, data_evento=?, dias_duracao=?, hora_inicio=?, hora_fim=?, local=?, descricao=?
                                WHERE id=?
                            ''', (titulo, categoria, part_str, data_ev.strftime("%Y-%m-%d"), int(dias_duracao), h_in.strftime("%H:%M"), h_fim.strftime("%H:%M"), local_ev, desc_ev, st.session_state.evento_editando_id))
                        st.success("Evento atualizado com sucesso!")
                    else:
                        cursor.execute('''
                            INSERT INTO eventos (titulo, categoria, participantes, data_evento, dias_duracao, hora_inicio, hora_fim, local, descricao, anexo_path, criado_por)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (titulo, categoria, part_str, data_ev.strftime("%Y-%m-%d"), int(dias_duracao), h_in.strftime("%H:%M"), h_fim.strftime("%H:%M"), local_ev, desc_ev, caminho_anexo, st.session_state.name))
                        st.success(f"Evento '{titulo}' cadastrado com sucesso!")
                        
                    conn.commit()
                    conn.close()
                    st.session_state.modo_criacao = False
                    st.session_state.evento_editando_id = None
                    st.rerun()
                    
    else:
        col_cab1, col_cab2 = st.columns([2, 1])
        with col_cab1:
            st.subheader("Linha do Tempo Familiar")
        with col_cab2:
            if st.button("➕ Criar Evento", type="primary", use_container_width=True):
                st.session_state.modo_criacao = True
                st.rerun()
        
        conn = get_connection()
        df_eventos = pd.read_sql_query("SELECT * FROM eventos ORDER BY data_evento ASC, hora_inicio ASC", conn)
        conn.close()
        
        if df_eventos.empty:
            st.info("Nenhum evento agendado até o momento.")
        else:
            linhas_expandidas = []
            for _, row in df_eventos.iterrows():
                dt_ini = datetime.strptime(row["data_evento"], "%Y-%m-%d").date()
                dias = int(row["dias_duracao"]) if "dias_duracao" in row and pd.notna(row["dias_duracao"]) else 1
                for i in range(dias):
                    dt_atual = dt_ini + timedelta(days=i)
                    r_copia = row.copy()
                    r_copia["data_calculada"] = dt_atual.strftime("%Y-%m-%d")
                    r_copia["dt_obj"] = pd.to_datetime(dt_atual)
                    linhas_expandidas.append(r_copia)
            
            df_expandido = pd.DataFrame(linhas_expandidas)
            
            anos_disponiveis = sorted(df_expandido['dt_obj'].dt.year.unique(), reverse=True)
            
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                filtro_ano = st.selectbox("Ano", ["Todos"] + [str(a) for a in anos_disponiveis])
            
            df_temp_mes = df_expandido if filtro_ano == "Todos" else df_expandido[df_expandido['dt_obj'].dt.year == int(filtro_ano)]
            meses_com_eventos = sorted(df_temp_mes['dt_obj'].dt.month.unique())
            meses_opcoes = ["Todos"] + [MESES_NOME[m] for m in meses_com_eventos]
            
            mes_corrente_nome = MESES_NOME.get(date.today().month)
            default_mes_idx = meses_opcoes.index(mes_corrente_nome) if mes_corrente_nome in meses_opcoes else 0
            
            with col_f2:
                filtro_mes = st.selectbox("Mês", meses_opcoes, index=default_mes_idx)
            with col_f3:
                filtro_membro = st.selectbox("Integrante", ["Todos"] + INTEGRANTES + ["Família Toda"])
            with col_f4:
                filtro_cat = st.selectbox("Categoria", ["Todas"] + CATEGORIAS)
                
            df_filtrado = df_expandido.copy()
            if filtro_ano != "Todos":
                df_filtrado = df_filtrado[df_filtrado['dt_obj'].dt.year == int(filtro_ano)]
            if filtro_mes != "Todos":
                num_mes = [k for k, v in MESES_NOME.items() if v == filtro_mes][0]
                df_filtrado = df_filtrado[df_filtrado['dt_obj'].dt.month == num_mes]
            if filtro_membro != "Todos":
                df_filtrado = df_filtrado[df_filtrado["participantes"].str.contains(filtro_membro, na=False)]
            if filtro_cat != "Todas":
                df_filtrado = df_filtrado[df_filtrado["categoria"] == filtro_cat]
                
            df_filtrado = df_filtrado.drop_duplicates(subset=["id"])
            
            if df_filtrado.empty:
                st.warning("Nenhum compromisso encontrado para os filtros selecionados.")
            else:
                for idx, row in df_filtrado.iterrows():
                    dt_ini_obj = datetime.strptime(row["data_evento"], "%Y-%m-%d").date()
                    dias_dur = int(row["dias_duracao"]) if "dias_duracao" in row and pd.notna(row["dias_duracao"]) else 1
                    
                    if dias_dur > 1:
                        dt_fim_obj = dt_ini_obj + timedelta(days=dias_dur - 1)
                        data_str = f"{dt_ini_obj.strftime('%d/%m/%Y')} até {dt_fim_obj.strftime('%d/%m/%Y')} ({dias_dur} dias)"
                    else:
                        data_str = dt_ini_obj.strftime('%d/%m/%Y')
                        
                    titulo_expander = f"📆 {data_str} | {row['hora_inicio']} às {row['hora_fim']} | {row['titulo']}"
                    
                    with st.expander(titulo_expander):
                        st.write(f"**🏷️ Categoria:** {row['categoria']}")
                        st.write(f"**👥 Participantes:** {row['participantes']}")
                        st.write(f"**✍️ Criado por:** {row['criado_por']}")
                        if dias_dur > 1:
                            st.write(f"**⏱️ Duração:** {dias_dur} dias consecutivos")
                        if row["local"]:
                            st.write(f"**📍 Local:** {row['local']}")
                        if row["descricao"]:
                            st.write(f"**📝 Observações:** {row['descricao']}")
                        
                        anexo_path = row["anexo_path"]
                        if pd.notna(anexo_path) and isinstance(anexo_path, str) and os.path.exists(anexo_path):
                            st.divider()
                            ext = anexo_path.split(".")[-1].lower()
                            if ext in ["jpg", "jpeg", "png"]:
                                st.image(anexo_path, caption="Anexo da Imagem", use_container_width=True)
                            elif ext == "pdf":
                                with open(anexo_path, "rb") as pdf_file:
                                    st.download_button(
                                        label="📄 Baixar Documento PDF",
                                        data=pdf_file,
                                        file_name=os.path.basename(anexo_path),
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key=f"dl_{row['id']}"
                                    )
                        
                        pode_gerenciar = (st.session_state.role == "admin") or (st.session_state.name == row["criado_por"])
                        
                        if pode_gerenciar:
                            st.divider()
                            col_ed1, col_ed2 = st.columns(2)
                            with col_ed1:
                                if st.button("✏️ Editar Evento", key=f"edit_{row['id']}", use_container_width=True):
                                    st.session_state.evento_editando_id = row['id']
                                    st.rerun()
                            with col_ed2:
                                if st.button("❌ Excluir Evento", key=f"del_{row['id']}", use_container_width=True):
                                    if pd.notna(anexo_path) and isinstance(anexo_path, str) and os.path.exists(anexo_path):
                                        try:
                                            os.remove(anexo_path)
                                        except Exception:
                                            pass
                                    conn = get_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM eventos WHERE id = ?", (row['id'],))
                                    conn.commit()
                                    conn.close()
                                    st.success("Evento excluído com sucesso!")
                                    st.rerun()

# --- ABA 2: RELATÓRIOS ---
with tab2:
    st.subheader("Análise da Agenda & Ocupação")
    
    conn = get_connection()
    df_rep = pd.read_sql_query("SELECT * FROM eventos", conn)
    conn.close()
    
    if df_rep.empty:
        st.info("Cadastre eventos para visualizar as estatísticas.")
    else:
        st.markdown("### 📊 Eventos por Categoria")
        cat_counts = df_rep["categoria"].value_counts()
        st.bar_chart(cat_counts)
        
        st.markdown("---")
        st.markdown("### 🔍 Consultar Ocupação em uma Data")
        
        col_rep_a, col_rep_m, col_rep_d = st.columns(3)
        hoje = date.today()
        with col_rep_a:
            a_rep = st.selectbox("Ano Consulta", list(range(hoje.year - 1, hoje.year + 3)), index=1, key="rep_a")
        with col_rep_m:
            m_rep_nome = st.selectbox("Mês Consulta", list(MESES_NOME.values()), index=hoje.month - 1, key="rep_m")
            m_rep_num = [k for k, v in MESES_NOME.items() if v == m_rep_nome][0]
        with col_rep_d:
            d_rep = st.selectbox("Dia Consulta", list(range(1, 32)), index=hoje.day - 1, key="rep_d")
            
        try:
            data_busca = date(a_rep, m_rep_num, d_rep)
            
            eventos_no_dia = []
            for _, r in df_rep.iterrows():
                dt_ini = datetime.strptime(r["data_evento"], "%Y-%m-%d").date()
                dias = int(r["dias_duracao"]) if "dias_duracao" in r and pd.notna(r["dias_duracao"]) else 1
                dt_fim = dt_ini + timedelta(days=dias - 1)
                
                if dt_ini <= data_busca <= dt_fim:
                    eventos_no_dia.append(r)
                    
            if not eventos_no_dia:
                st.success(f"🟢 **Dia Livre!** Não há compromissos para {data_busca.strftime('%d/%m/%Y')}.")
            else:
                st.warning(f"🟡 **Dia Ocupado ({len(eventos_no_dia)} compromisso(s)):**")
                for r in eventos_no_dia:
                    st.write(f"• **{r['hora_inicio']} - {r['hora_fim']}**: {r['titulo']} ({r['participantes']})")
        except ValueError:
            st.error("Data selecionada é inválida.")

# --- ABA 3: ADMINISTRAÇÃO (EXCLUSIVO ADMIN) ---
if st.session_state.role == "admin":
    with tab3:
        st.subheader("⚙️ Painel de Administração")
        
        adm_tab1, adm_tab2, adm_tab3 = st.tabs(["👥 Usuários & Senhas", "🏷️ Gerenciar Categorias", "🔑 Alterar Senha"])
        
        with adm_tab1:
            with st.form("form_novo_usuario", clear_on_submit=True):
                st.markdown("#### ➕ Cadastrar Novo Integrante / Usuário")
                novo_user = st.text_input("Nome de Usuário (login sem espaços, ex: marcia)").strip().lower()
                novo_nome_completo = st.text_input("Nome Completo (ex: Márcia Lisboa)").strip()
                nova_senha = st.text_input("Senha inicial", type="password")
                novo_perfil = st.selectbox("Perfil de Acesso", ["membro", "admin"])
                
                btn_criar_user = st.form_submit_button("Salvar Novo Usuário", use_container_width=True)
                
                if btn_criar_user:
                    if not novo_user or not novo_nome_completo or not nova_senha:
                        st.error("Preencha todos os campos do usuário.")
                    else:
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO usuarios (username, nome_completo, senha, perfil)
                                VALUES (?, ?, ?, ?)
                            ''', (novo_user, novo_nome_completo, hash_senha(nova_senha), novo_perfil))
                            conn.commit()
                            conn.close()
                            st.success(f"Usuário '{novo_nome_completo}' cadastrado com sucesso! Atualize a página.")
                        except sqlite3.IntegrityError:
                            st.error("Este nome de usuário (login) já existe. Escolha outro.")

            st.markdown("---")
            st.markdown("#### 👥 Usuários Cadastrados no Sistema")
            conn = get_connection()
            df_cadastrados = pd.read_sql_query("SELECT id, username, nome_completo, perfil FROM usuarios", conn)
            conn.close()
            st.dataframe(df_cadastrados, use_container_width=True)

        with adm_tab2:
            with st.form("form_nova_categoria", clear_on_submit=True):
                st.markdown("#### ➕ Cadastrar Nova Categoria")
                nova_cat_nome = st.text_input("Nome da Categoria (ex: Reunião, Show...)").strip()
                btn_criar_cat = st.form_submit_button("Salvar Categoria", use_container_width=True)
                
                if btn_criar_cat:
                    if not nova_cat_nome:
                        st.error("Digite o nome da categoria.")
                    else:
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO categorias (nome) VALUES (?)", (nova_cat_nome,))
                            conn.commit()
                            conn.close()
                            st.success(f"Categoria '{nova_cat_nome}' cadastrada com sucesso! Atualize a página.")
                        except sqlite3.IntegrityError:
                            st.error("Esta categoria já existe.")

            st.markdown("---")
            st.markdown("#### 🗑️ Excluir Categoria Existente")
            conn = get_connection()
            df_cats_del = pd.read_sql_query("SELECT id, nome FROM categorias ORDER BY nome ASC", conn)
            conn.close()
            
            if df_cats_del.empty:
                st.info("Nenhuma categoria cadastrada.")
            else:
                cat_opcoes_del = {row['nome']: row['id'] for _, row in df_cats_del.iterrows()}
                cat_escolhida_del = st.selectbox("Selecione a categoria para apagar", list(cat_opcoes_del.keys()))
                
                if st.button("❌ Excluir Categoria Selecionada", use_container_width=True):
                    cat_id_alvo = cat_opcoes_del[cat_escolhida_del]
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM categorias WHERE id = ?", (cat_id_alvo,))
                    conn.commit()
                    conn.close()
                    st.success(f"Categoria '{cat_escolhida_del}' removida com sucesso! Atualize a página.")

        with adm_tab3:
            with st.form("form_mudar_senha", clear_on_submit=True):
                st.markdown("#### 🔑 Alterar Senha de Usuário")
                conn = get_connection()
                df_users_list = pd.read_sql_query("SELECT username, nome_completo FROM usuarios", conn)
                conn.close()
                
                user_opcoes = {f"{row['nome_completo']} ({row['username']})": row['username'] for _, row in df_users_list.iterrows()}
                
                selecao_usuario = st.selectbox("Selecione o usuário para alterar a senha", list(user_opcoes.keys()))
                nova_senha_input = st.text_input("Nova Senha", type="password")
                
                btn_mudar_senha = st.form_submit_button("🔄 Atualizar Senha", use_container_width=True)
                
                if btn_mudar_senha:
                    if not nova_senha_input:
                        st.error("Digite a nova senha.")
                    else:
                        username_alvo = user_opcoes[selecao_usuario]
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET senha = ? WHERE username = ?", (hash_senha(nova_senha_input), username_alvo))
                        conn.commit()
                        conn.close()
                        st.success(f"Senha do usuário '{selecao_usuario}' atualizada com sucesso!")
