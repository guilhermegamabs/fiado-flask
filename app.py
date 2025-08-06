from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import db as database

app = Flask(__name__)
# É importante para o Flask gerenciar sessões e mostrar mensagens (flash).
app.secret_key = 'uma-chave-secreta-bem-dificil' 

# Garante que as tabelas sejam criadas ao iniciar a aplicação.
with app.app_context():
    database.criar_tabelas()

@app.route("/")
def listar_clientes():
    """Página inicial: mostra formulário de cadastro e lista de clientes."""
    clientes = database.buscar_clientes()
    return render_template("clientes.html", clientes=clientes)

@app.route("/cliente/adicionar", methods=["POST"])
def cadastrar_cliente():
    """Processa o formulário de cadastro de novo cliente."""
    nome = request.form.get("nome", "").strip()
    if nome:
        database.inserir_cliente(nome)
        flash(f"Cliente '{nome}' cadastrado com sucesso!", "success")
    else:
        flash("O nome do cliente não pode ser vazio.", "error")
    return redirect(url_for('listar_clientes'))

@app.route("/fiado/registrar")
def registrar_fiado_form():
    """Mostra o formulário para registrar um novo fiado."""
    clientes = database.buscar_clientes()
    if not clientes:
        flash("Cadastre um cliente antes de registrar um fiado.", "warning")
        return redirect(url_for('listar_clientes'))
    return render_template("fiados.html", clientes=clientes, context='registrar')

@app.route("/fiado/registrar", methods=["POST"])
def registrar_fiado_action():
    """Processa o formulário de registro de novo fiado."""
    cliente_id = request.form.get("cliente_id")
    descricao = request.form.get("descricao", "").strip()
    valor_str = request.form.get("valor", "0").replace(',', '.')
    
    try:
        valor = float(valor_str)
        if not cliente_id or not descricao or valor <= 0:
            flash("Todos os campos são obrigatórios e o valor deve ser positivo.", "error")
            return redirect(url_for('registrar_fiado_form'))
        
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        database.inserir_fiado(int(cliente_id), descricao, valor, data)
        flash("Fiado registrado com sucesso!", "success")
    except ValueError:
        flash("Valor inválido. Use apenas números.", "error")
        return redirect(url_for('registrar_fiado_form'))

    return redirect(url_for('listar_clientes'))

@app.route("/cliente/<nome_cliente>")
def listar_fiados(nome_cliente):
    """Página que detalha os fiados e pagamentos de um cliente específico."""
    fiados, total, ultima_data, valor_ultimo = database.buscar_fiados_por_cliente(nome_cliente)
    return render_template("fiados.html",
                           nome_cliente=nome_cliente,
                           fiados=fiados,
                           total_devido=total,
                           ultimo_pagamento=ultima_data,
                           valor_ultimo_pagamento=valor_ultimo,
                           context='visualizar')

@app.route("/cliente/<nome_cliente>/pagar", methods=["POST"])
def realizar_pagamento(nome_cliente):
    """Processa o formulário de pagamento de um cliente."""
    valor_pago_str = request.form.get("valor_pago", "0").replace(',', '.')
    try:
        valor_pago = float(valor_pago_str)
        if valor_pago > 0:
            erro = database.registrar_pagamento(nome_cliente, valor_pago)
            if erro:
                flash(erro, "error")
            else:
                flash(f"Pagamento de R$ {valor_pago:.2f} registrado com sucesso!", "success")
        else:
            flash("O valor do pagamento deve ser positivo.", "error")
    except ValueError:
        flash("Valor de pagamento inválido.", "error")
    
    return redirect(url_for('listar_fiados', nome_cliente=nome_cliente))

if __name__ == '__main__':
    # debug=True faz o servidor reiniciar automaticamente quando você salva o arquivo.
    # NUNCA use debug=True em um ambiente de produção (online).
    app.run(host="0.0.0.0", port=5000, debug=True)