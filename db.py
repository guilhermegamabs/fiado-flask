import sqlite3
from datetime import datetime

def conectar():
    """Conecta ao banco de dados SQLite."""
    return sqlite3.connect("fiado.db")

def criar_tabelas():
    """Garante que todas as tabelas necessárias existam no banco."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fiados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            descricao TEXT,
            valor REAL,
            data TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            valor REAL,
            data TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')
    conn.commit()
    conn.close()

def inserir_cliente(nome):
    """Insere um novo cliente no banco de dados, evitando duplicatas."""
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO clientes (nome) VALUES (?)", (nome,))
        conn.commit()
    except sqlite3.IntegrityError:
        # Cliente com este nome já existe, não faz nada.
        pass
    conn.close()

def buscar_clientes():
    """Retorna uma lista de todos os clientes (id, nome)."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM clientes ORDER BY nome")
    res = cursor.fetchall()
    conn.close()
    return res

def inserir_fiado(cliente_id, descricao, valor, data):
    """Registra um novo item de fiado para um cliente."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO fiados (cliente_id, descricao, valor, data) VALUES (?, ?, ?, ?)",
        (cliente_id, descricao, valor, data)
    )
    conn.commit()
    conn.close()

def buscar_fiados_por_cliente(nome_cliente):
    """Busca todos os fiados, o total devido e o último pagamento de um cliente."""
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM clientes WHERE nome = ?", (nome_cliente,))
    cliente = cursor.fetchone()
    if not cliente:
        conn.close()
        return [], 0, None, 0
    cliente_id = cliente[0]

    cursor.execute("SELECT * FROM fiados WHERE cliente_id = ? ORDER BY data DESC", (cliente_id,))
    fiados = cursor.fetchall()

    total = sum(f[3] for f in fiados)  # f[3] é o campo 'valor'

    cursor.execute(
        "SELECT data, valor FROM pagamentos WHERE cliente_id = ? ORDER BY data DESC LIMIT 1",
        (cliente_id,)
    )
    ultimo_pagamento = cursor.fetchone()
    conn.close()

    data_ultimo_pagamento = ultimo_pagamento[0] if ultimo_pagamento else None
    valor_ultimo_pagamento = ultimo_pagamento[1] if ultimo_pagamento else 0
    
    return fiados, total, data_ultimo_pagamento, valor_ultimo_pagamento

def registrar_pagamento(nome_cliente, valor):
    """Registra um pagamento e atualiza a lista de fiados, começando pelos mais antigos."""
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM clientes WHERE nome = ?", (nome_cliente,))
    cliente = cursor.fetchone()
    if not cliente:
        conn.close()
        return "Cliente não encontrado."
    cliente_id = cliente[0]

    cursor.execute("SELECT SUM(valor) FROM fiados WHERE cliente_id = ?", (cliente_id,))
    total_devido = cursor.fetchone()[0] or 0.0

    if valor > total_devido:
        conn.close()
        return f"Erro: Pagamento (R$ {valor:.2f}) é maior que o total devido (R$ {total_devido:.2f})."

    data_pagamento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO pagamentos (cliente_id, valor, data) VALUES (?, ?, ?)",
        (cliente_id, valor, data_pagamento)
    )

    cursor.execute("SELECT id, valor FROM fiados WHERE cliente_id = ? ORDER BY data ASC", (cliente_id,))
    fiados_a_pagar = cursor.fetchall()

    valor_restante_do_pagamento = valor
    for fiado_id, fiado_valor in fiados_a_pagar:
        if valor_restante_do_pagamento <= 0:
            break
        if valor_restante_do_pagamento >= fiado_valor:
            cursor.execute("DELETE FROM fiados WHERE id = ?", (fiado_id,))
            valor_restante_do_pagamento -= fiado_valor
        else:
            novo_valor_fiado = fiado_valor - valor_restante_do_pagamento
            cursor.execute("UPDATE fiados SET valor = ? WHERE id = ?", (novo_valor_fiado, fiado_id))
            valor_restante_do_pagamento = 0
    
    conn.commit()
    conn.close()
    return None # Significa que não houve erro