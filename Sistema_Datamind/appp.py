from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyodbc
from functools import wraps # Importa wraps para o decorator

app = Flask(__name__)
app.secret_key = 'SECRET_KEY'  # É fundamental ter uma chave secreta para a sessão

# Configuração da conexão com o banco de dados (ajuste com suas credenciais)
def get_db_connection():
    try:
        conn = pyodbc.connect(
            'DRIVER=DB_HOST;'
            'SERVER=DB_HOST;'
            'DATABASE=DB_NAME;'
            'UID=DB_USER;'
            'PWD=DB_PASSWORD;'
        )
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Erro de conexão com o banco de dados: {sqlstate}")
        return None

# Decorator para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DE AUTENTICAÇÃO E DASHBOARD ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            # IMPORTANTE: Altere esta query para verificar na sua tabela de usuários
            cursor.execute("SELECT * FROM usuarios WHERE nome_usuario = ? AND senha = ?", (usuario, senha))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                session['usuario'] = usuario
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Usuário ou senha inválidos')
        else:
            return render_template('login.html', error='Erro de conexão com o banco de dados')
            
    # Se o usuário já estiver na sessão, redireciona para o dashboard
    if 'usuario' in session:
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # --- LÓGICA DE DADOS PARA O DASHBOARD ---
    # !! IMPORTANTE !!
    # Substitua os dados de exemplo abaixo pelas suas consultas reais ao banco de dados.
    
    conn = get_db_connection()
    # if conn:
        # cursor = conn.cursor()
        
        # Exemplo 1: Consultar o total de produtos com estoque baixo
        # cursor.execute("SELECT COUNT(*) FROM produtos WHERE estoque < estoque_minimo")
        # total_alertas_criticos = cursor.fetchone()[0]
    total_alertas_criticos = 15 # Valor de exemplo

    # Exemplo 2: Consultar solicitações de lojas com status 'pendente'
    # cursor.execute("SELECT COUNT(*) FROM solicitacoes WHERE status = 'pendente'")
    # solicitacoes_pendentes = cursor.fetchone()[0]
    solicitacoes_pendentes = 8 # Valor de exemplo
    
    # Exemplo 3: Calcular faturamento do dia
    # cursor.execute("SELECT SUM(valor) FROM vendas WHERE CAST(data_venda AS DATE) = CAST(GETDATE() AS DATE)")
    # faturamento_dia = cursor.fetchone()[0] or 0.0
    faturamento_dia = 12540.50 # Valor de exemplo

    # Exemplo 4: Dados para o gráfico de vendas da semana
    # Aqui você faria uma query com GROUP BY por dia para os últimos 7 dias.
    grafico_vendas_labels = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    grafico_vendas_values = [3200, 4500, 2800, 5300, 7100, 8900, 4200]
    
        # conn.close()
    # else:
        # # Valores padrão em caso de falha de conexão
        # total_alertas_criticos = 0
        # solicitacoes_pendentes = 0
        # faturamento_dia = 0.0
        # grafico_vendas_labels = []
        # grafico_vendas_values = []
        
    # Monta um dicionário para enviar os dados para o template
    dados_dashboard = {
        'total_alertas_criticos': total_alertas_criticos,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'faturamento_dia': faturamento_dia,
        'grafico_vendas': {
            'labels': grafico_vendas_labels,
            'values': grafico_vendas_values
        }
    }
    
    return render_template('dashboard.html', dados_dashboard=dados_dashboard)

@app.route('/logout')
def logout():
    session.pop('usuario', None) # Remove 'usuario' da sessão
    return redirect(url_for('login'))


# --- ROTAS EXISTENTES DO SEU SISTEMA (AGORA PROTEGIDAS) ---

@app.route('/pagina_principal')
@login_required
def pagina_principal():
    return render_template('pagina_principal.html')

@app.route('/relatorio')
@login_required
def relatorio():
    return render_template('relatorio.html')

@app.route('/consultas_avancadas')
@login_required
def consultas_avancadas():
    return render_template('consultas_avancadas.html')

@app.route('/suporte_logistico')
@login_required
def suporte_logistico():
    return render_template('suporte_logistico.html')
    
@app.route('/conferencia', methods=['GET', 'POST'])
@login_required
def conferencia():
    # Mantenha sua lógica original aqui
    return render_template('conferencia.html')

@app.route('/analise_vendas')
@login_required
def analise_vendas():
    return render_template('analise_vendas.html')

@app.route('/solicitacoes_loja')
@login_required
def solicitacoes_loja():
    return render_template('solicitacoes_loja.html')

@app.route('/alerta_lojas')
@login_required
def alerta_lojas():
    return render_template('alerta_lojas.html')

@app.route('/pda_romaneio')
@login_required
def pda_romaneio():
    return render_template('pda_romaneio.html')

@app.route('/cadastro_vagas')
@login_required
def cadastro_vagas():
    return render_template('cadastro_vagas.html')

@app.route('/cv_analise')
@login_required
def cv_analise():
    return render_template('cv_analise.html')

# Adicione aqui as outras rotas do seu sistema, sempre com @login_required
# Exemplo:
# @app.route('/sua_outra_rota')
# @login_required
# def sua_outra_rota():
#     # sua lógica
#     return render_template('sua_outra_rota.html')


if __name__ == '__main__':
    app.run(debug=True)
