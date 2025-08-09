import psycopg2
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    conn_params_raw = dj_database_url.parse(DATABASE_URL)
    
    # Lista de chaves válidas para psycopg2.connect()
    VALID_PG_KEYS = ['dbname', 'user', 'password', 'host', 'port']
    
    # Converte as chaves recebidas para minúsculas
    conn_params_lower = {key.lower(): value for key, value in conn_params_raw.items()}
    
    if 'name' in conn_params_lower:
        conn_params_lower['dbname'] = conn_params_lower.pop('name')
        
    # Filtra o dicionário, mantendo apenas as chaves válidas
    conn_params = {key: value for key, value in conn_params_lower.items() if key in VALID_PG_KEYS}

else:
    print("DATABASE_URL não encontrada, usando variáveis do .env para conexão local.")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")

    if not all([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT]):
        raise KeyError("Para desenvolvimento local, defina DB_NAME, DB_USER, etc. no seu arquivo .env")
    
    conn_params = {
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "host": DB_HOST,
        "port": DB_PORT,
    }

def conectar():
    try:
        conn = psycopg2.connect(**conn_params)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        raise e
    
def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nome TEXT NOT NULL UNIQUE)')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pagamentos (
            id SERIAL PRIMARY KEY, 
            cliente_id INTEGER REFERENCES clientes(id) ON DELETE CASCADE, 
            valor REAL, 
            data TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fiados (
            id SERIAL PRIMARY KEY, 
            cliente_id INTEGER REFERENCES clientes(id) ON DELETE CASCADE, 
            descricao TEXT, 
            valor REAL, 
            data TEXT,
            pagamento_id INTEGER REFERENCES pagamentos(id) ON DELETE SET NULL
        )
    ''')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL)')
    conn.commit()
    cursor.close()
    conn.close()

def inserir_usuario(username, password):
    conn = conectar()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        cursor.execute("INSERT INTO usuarios (username, password_hash) VALUES (%s, %s)", (username, password_hash))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def buscar_usuario_por_nome(username):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM usuarios WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def buscar_usuario_por_id(user_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def inserir_cliente(nome):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO clientes (nome) VALUES (%s)", (nome,))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def buscar_clientes():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM clientes ORDER BY nome")
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res

def buscar_cliente_por_id(cliente_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM clientes WHERE id = %s", (cliente_id,))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return res

def inserir_fiado(cliente_id, descricao, valor, data, pagamento_id=None):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO fiados (cliente_id, descricao, valor, data, pagamento_id) VALUES (%s, %s, %s, %s, %s)", (cliente_id, descricao, valor, data, pagamento_id))
    conn.commit()
    cursor.close()
    conn.close()

def registrar_pagamento(nome_cliente, valor):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM clientes WHERE nome = %s", (nome_cliente,))
        cliente = cursor.fetchone()
        if not cliente: return "Cliente não encontrado."
        cliente_id = cliente[0]
        
        cursor.execute("SELECT SUM(valor) FROM fiados WHERE cliente_id = %s AND pagamento_id IS NULL", (cliente_id,))
        total_devido = cursor.fetchone()[0] or 0.0
        
        if valor > total_devido:
            return f"Erro: Pagamento (R$ {valor:.2f}) é maior que o total devido (R$ {total_devido:.2f})."
        
        data_pagamento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("INSERT INTO pagamentos (cliente_id, valor, data) VALUES (%s, %s, %s) RETURNING id", (cliente_id, valor, data_pagamento))
        pagamento_id = cursor.fetchone()[0]

        cursor.execute("SELECT id, valor FROM fiados WHERE cliente_id = %s AND pagamento_id IS NULL ORDER BY data ASC", (cliente_id,))
        fiados_a_pagar = cursor.fetchall()
        
        valor_restante_do_pagamento = valor
        for fiado_id, fiado_valor in fiados_a_pagar:
            if valor_restante_do_pagamento <= 0: break
            
            if valor_restante_do_pagamento >= fiado_valor:
                cursor.execute("UPDATE fiados SET pagamento_id = %s WHERE id = %s", (pagamento_id, fiado_id))
                valor_restante_do_pagamento -= fiado_valor
            else:
                novo_valor_fiado = fiado_valor - valor_restante_do_pagamento
                cursor.execute("UPDATE fiados SET valor = %s WHERE id = %s", (novo_valor_fiado, fiado_id))
                valor_restante_do_pagamento = 0
        
        conn.commit()
        return None
    except Exception as e:
        conn.rollback()
        print(f"Erro em registrar_pagamento: {e}")
        return "Ocorreu um erro ao processar o pagamento."
    finally:
        cursor.close()
        conn.close()

def buscar_fiados_por_cliente(nome_cliente):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clientes WHERE nome = %s", (nome_cliente,))
    cliente = cursor.fetchone()
    if not cliente:
        return None, [], 0, None, 0
    cliente_id = cliente[0]
    
    cursor.execute("SELECT * FROM fiados WHERE cliente_id = %s AND pagamento_id IS NULL ORDER BY data DESC", (cliente_id,))
    fiados_pendentes = cursor.fetchall()
    
    total_devido = sum(f[3] for f in fiados_pendentes)
    
    cursor.execute("SELECT data, valor FROM pagamentos WHERE cliente_id = %s ORDER BY data DESC LIMIT 1", (cliente_id,))
    ultimo_pagamento = cursor.fetchone()
    conn.close()
    
    data_ultimo_pagamento = ultimo_pagamento[0] if ultimo_pagamento else None
    valor_ultimo_pagamento = ultimo_pagamento[1] if ultimo_pagamento else 0
    return cliente_id, fiados_pendentes, total_devido, data_ultimo_pagamento, valor_ultimo_pagamento

def buscar_fiados_pagos_por_cliente(cliente_id):
    conn = conectar()
    cursor = conn.cursor()
    query = """
        SELECT f.descricao, f.valor, p.data as data_pagamento
        FROM fiados f
        JOIN pagamentos p ON f.pagamento_id = p.id
        WHERE f.cliente_id = %s
        ORDER BY p.data DESC
    """
    cursor.execute(query, (cliente_id,))
    fiados_pagos = cursor.fetchall()
    cursor.close()
    conn.close()
    return fiados_pagos

def atualizar_cliente(cliente_id, novo_nome):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE clientes SET nome = %s WHERE id = %s", (novo_nome, cliente_id))
    conn.commit()
    cursor.close()
    conn.close()

def excluir_cliente(cliente_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM fiados WHERE cliente_id = %s AND pagamento_id IS NULL", (cliente_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return "Não é possível excluir clientes com dívidas pendentes."
    
    cursor.execute("DELETE FROM fiados WHERE cliente_id = %s", (cliente_id,))
    cursor.execute("DELETE FROM pagamentos WHERE cliente_id = %s", (cliente_id,))
    cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return None

def excluir_fiado(fiado_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fiados WHERE id = %s", (fiado_id,))
    conn.commit()
    cursor.close()
    conn.close()

def buscar_cliente_id_por_fiado(fiado_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT cliente_id FROM fiados WHERE id = %s", (fiado_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def get_dashboard_stats():
    conn = conectar()
    cursor = conn.cursor()
    
    # 1. Dívida total geral (sem alterações)
    cursor.execute("SELECT SUM(valor) FROM fiados WHERE pagamento_id IS NULL")
    total_debt = cursor.fetchone()[0] or 0.0
    
    # 2. Gráfico semanal (sem alterações)
    query_chart = """
        SELECT TO_CHAR(data::date, 'YYYY-MM-DD') as dia, COUNT(id) as quantidade
        FROM fiados WHERE data::date >= current_date - interval '7 days'
        GROUP BY dia ORDER BY dia ASC;
    """
    cursor.execute(query_chart)
    weekly_fiados = cursor.fetchall()
    
    # --- NOVOS STATS DO DIA ---
    
    # 3. Total em R$ de novos fiados criados hoje
    cursor.execute("SELECT COALESCE(SUM(valor), 0.0) FROM fiados WHERE data::date = CURRENT_DATE")
    valor_novos_fiados_hoje = cursor.fetchone()[0]
    
    # 4. Total em R$ de pagamentos recebidos hoje
    cursor.execute("SELECT COALESCE(SUM(valor), 0.0) FROM pagamentos WHERE data::date = CURRENT_DATE")
    valor_pago_hoje = cursor.fetchone()[0]

    # 5. Contagem (quantidade) de fiados criados hoje
    cursor.execute("SELECT COUNT(id) FROM fiados WHERE data::date = CURRENT_DATE")
    count_fiados_hoje = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    # Retorna um único dicionário com tudo organizado
    return {
        "total_debt": total_debt, 
        "weekly_fiados": weekly_fiados,
        "daily_stats": {
            "novos_fiados_valor": valor_novos_fiados_hoje,
            "pagamentos_valor": valor_pago_hoje,
            "novos_fiados_count": count_fiados_hoje,
            "balanco_dia": valor_pago_hoje - valor_novos_fiados_hoje
        }
    }

def get_all_data_for_backup():
    from psycopg2.extras import RealDictCursor
    conn = conectar()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM clientes ORDER BY id")
    clientes = cursor.fetchall()
    cursor.execute("SELECT * FROM fiados ORDER BY id")
    fiados = cursor.fetchall()
    cursor.execute("SELECT * FROM pagamentos ORDER BY id")
    pagamentos = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"clientes": clientes, "fiados": fiados, "pagamentos": pagamentos}

def buscar_pagamentos_por_cliente(cliente_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT valor, data FROM pagamentos WHERE cliente_id = %s ORDER BY data DESC", (cliente_id,))
    pagamentos = cursor.fetchall()
    cursor.close()
    conn.close()
    return pagamentos