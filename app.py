from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import db as database
import click
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'uma-chave-secreta-bem-dificil-e-longa-para-seguranca'

# --- Configuração do Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "warning"

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    user_data = database.buscar_usuario_por_id(user_id)
    if user_data:
        return User(id=user_data[0], username=user_data[1], password_hash=user_data[2])
    return None

with app.app_context():
    database.criar_tabelas()

# --- Rotas de Autenticação ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_data = database.buscar_usuario_por_nome(username)
        user_obj = User(id=user_data[0], username=user_data[1], password_hash=user_data[2]) if user_data else None

        if user_obj and user_obj.check_password(password):
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'success')
    return redirect(url_for('login'))

# --- Rotas do Dashboard e Backup ---
@app.route("/dashboard")
@login_required
def dashboard():
    stats = database.get_dashboard_stats()
    return render_template("dashboard.html", stats=stats)

@app.route("/backup/download")
@login_required
def download_backup():
    backup_data = database.get_all_data_for_backup()
    response = jsonify(backup_data)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    response.headers["Content-Disposition"] = f"attachment; filename=backup_fiados_{timestamp}.json"
    return response

# --- Rotas da Aplicação ---
@app.route("/")
@login_required
def home():
    return redirect(url_for('dashboard'))

@app.route("/clientes")
@login_required
def listar_clientes():
    clientes = database.buscar_clientes()
    return render_template("clientes.html", clientes=clientes)

@app.route("/cliente/adicionar", methods=["POST"])
@login_required
def cadastrar_cliente():
    nome = request.form.get("nome", "").strip()
    if nome:
        database.inserir_cliente(nome)
        flash(f"Cliente '{nome}' cadastrado com sucesso!", "success")
    else:
        flash("O nome do cliente não pode ser vazio.", "error")
    return redirect(url_for('listar_clientes'))

@app.route("/fiado/registrar")
@login_required
def registrar_fiado_form():
    clientes = database.buscar_clientes()
    if not clientes:
        flash("Cadastre um cliente antes de registrar um fiado.", "warning")
        return redirect(url_for('listar_clientes'))
    return render_template("fiados.html", clientes=clientes, context='registrar')

@app.route("/fiado/registrar", methods=["POST"])
@login_required
def registrar_fiado_action():
    cliente_id = request.form.get("cliente_id")
    descricao = request.form.get("descricao", "").strip()
    valor_str = request.form.get("valor", "0").replace(',', '.')
    
    try:
        valor = float(valor_str)
        if not cliente_id or not descricao or valor <= 0:
            flash("Todos os campos são obrigatórios e o valor deve ser positivo.", "error")
            return redirect(url_for('registrar_fiado_form'))
        
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Inserir fiado sem pagamento_id
        database.inserir_fiado(int(cliente_id), descricao, valor, data, None)
        flash("Fiado registrado com sucesso!", "success")
        
        cliente_info = database.buscar_cliente_por_id(cliente_id)
        if cliente_info:
            return redirect(url_for('listar_fiados', nome_cliente=cliente_info[1]))
            
    except ValueError:
        flash("Valor inválido. Use apenas números.", "error")
        return redirect(url_for('registrar_fiado_form'))

    return redirect(url_for('listar_clientes'))

@app.route("/cliente/<nome_cliente>")
@login_required
def listar_fiados(nome_cliente):
    # Busca os itens PENDENTES e o total devido
    cliente_id, fiados_pendentes, total_devido, ultima_data, valor_ultimo = database.buscar_fiados_por_cliente(nome_cliente)
    
    # Busca os itens PAGOS e o histórico de pagamentos
    historico_pagamentos = database.buscar_pagamentos_por_cliente(cliente_id) if cliente_id else []
    itens_pagos = database.buscar_fiados_pagos_por_cliente(cliente_id) if cliente_id else []

    return render_template("fiados.html",
                           cliente_id=cliente_id,
                           nome_cliente=nome_cliente,
                           fiados=fiados_pendentes,
                           total_devido=total_devido,
                           ultimo_pagamento=ultima_data,
                           valor_ultimo_pagamento=valor_ultimo,
                           historico_pagamentos=historico_pagamentos,
                           itens_pagos=itens_pagos,
                           context='visualizar')

@app.route("/cliente/<nome_cliente>/pagar", methods=["POST"])
@login_required
def realizar_pagamento(nome_cliente):
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

@app.route("/cliente/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_required
def editar_cliente(cliente_id):
    if request.method == "POST":
        novo_nome = request.form.get("nome", "").strip()
        if novo_nome:
            database.atualizar_cliente(cliente_id, novo_nome)
            flash("Nome do cliente atualizado com sucesso!", "success")
            return redirect(url_for('listar_fiados', nome_cliente=novo_nome))
        else:
            flash("O nome não pode ser vazio.", "error")
    
    cliente = database.buscar_cliente_por_id(cliente_id)
    if not cliente:
        flash("Cliente não encontrado.", "error")
        return redirect(url_for('listar_clientes'))
    
    return render_template("editar_cliente.html", cliente=cliente)

@app.route("/cliente/<int:cliente_id>/excluir", methods=["POST"])
@login_required
def excluir_cliente(cliente_id):
    cliente_nome_original = database.buscar_cliente_por_id(cliente_id)
    erro = database.excluir_cliente(cliente_id)
    if erro:
        flash(erro, "error")
        if cliente_nome_original:
             return redirect(url_for('listar_fiados', nome_cliente=cliente_nome_original[1]))
    else:
        flash("Cliente excluído com sucesso!", "success")
    
    return redirect(url_for('listar_clientes'))

@app.route("/fiado/<int:fiado_id>/excluir", methods=["POST"])
@login_required
def excluir_fiado(fiado_id):
    cliente_id = database.buscar_cliente_id_por_fiado(fiado_id)
    database.excluir_fiado(fiado_id)
    flash("Item de fiado excluído com sucesso.", "success")
    
    if cliente_id:
        cliente = database.buscar_cliente_por_id(cliente_id)
        return redirect(url_for('listar_fiados', nome_cliente=cliente[1]))

    return redirect(url_for('listar_clientes'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)