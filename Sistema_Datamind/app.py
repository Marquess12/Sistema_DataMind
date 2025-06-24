
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from datetime import datetime, timedelta
import mysql.connector
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import pandas as pd 
from io import BytesIO
from functools import wraps
import requests
import logging
import numpy as np
from scipy import stats
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import request, render_template
import os
from werkzeug.utils import secure_filename

# Carrega variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Configura a chave da API do Groq
os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')

# Configurar o modelo Grok via API do Groq
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError(
        "GROQ_API_KEY não está configurada. Configure a variável de ambiente.")

# Usando o modelo Grok via Groq
llm = ChatGroq(model="llama3-70b-8192", api_key=groq_api_key)

# Definir o prompt para gerar perguntas no formato JSON
prompt = ChatPromptTemplate.from_template(
    "Você é um especialista em entrevistas de emprego. "
    "Gere exatamente 10 perguntas para um candidato à vaga de {titulo_vaga} com base nos requisitos: {requisitos}. "
    "O nível de senioridade da vaga é {senioridade}, então as perguntas devem ser adequadas para esse nível (Júnior: perguntas mais básicas; Pleno: perguntas intermediárias com foco prático; Sênior: perguntas avançadas com foco em arquitetura e liderança). "
    "Cada pergunta deve ser um objeto JSON com os seguintes campos: "
    "- 'pergunta': uma string com a pergunta (máximo 200 caracteres). "
    "- 'alternativas': uma lista com exatamente 3 opções no formato ['a) texto', 'b) texto', 'c) texto'], onde cada texto tem no máximo 100 caracteres. "
    "- 'correta': a letra da alternativa correta, que deve ser 'a', 'b' ou 'c'. "
    "As perguntas devem abordar diretamente os requisitos da vaga e refletir o nível de senioridade. "
    "Retorne as perguntas como uma lista de objetos JSON, no seguinte formato: "
    "["
    "{"
    "\"pergunta\": \"Qual é a sua experiência com Python?\", "
    "\"alternativas\": [\"a) Nenhuma\", \"b) 1-2 anos\", \"c) Mais de 2 anos\"], "
    "\"correta\": \"b\""
    "}, "
    "{"
    "\"pergunta\": \"Você tem conhecimento em Flask?\", "
    "\"alternativas\": [\"a) Sim\", \"b) Não\", \"c) Parcialmente\"], "
    "\"correta\": \"a\""
    "}"
    "]"
)
# Configurar o parser para garantir que a saída seja JSON
parser = JsonOutputParser()
# Criar a chain
perguntas_chain = LLMChain(llm=llm, prompt=prompt, output_parser=parser)

# Criar um prompt para gerar sugestões
prompt_template = PromptTemplate(
    input_variables=["titulo"],
    template=""" 
    Com base no título da vaga '{titulo}', gere sugestões para os seguintes campos de uma vaga de emprego:

    - Benefícios: Liste 3-5 benefícios comuns para essa vaga em formato de lista (ex.: "Vale-refeição, Plano de saúde, Trabalho remoto").
    - Descrição da Vaga: Escreva uma descrição clara e detalhada das responsabilidades e expectativas para a vaga, com 2-3 frases.
    - Requisitos: Liste 5-7 requisitos necessários para a vaga em formato de lista (ex.: "Python, 2 anos de experiência, Boa comunicação").

    Retorne as sugestões no formato:
    Benefícios: [lista de benefícios]
    Descrição: [descrição da vaga]
    Requisitos: [lista de requisitos]

    Certifique-se de que as sugestões sejam concisas e relevantes para o título da vaga fornecido.
    """
)

# Criar uma cadeia para processar o prompt com o Grok (via Groq)
suggestion_chain = LLMChain(llm=llm, prompt=prompt_template)

# Função para conectar ao banco


def get_db_connection():
    return mysql.connector.connect(**db_config)

# Decorador para proteger rotas


def login_required(f):
    def wrap(*args, **kwargs):
        print(f"Verificando sessão: {session}")
        if 'user' not in session:
            print("Usuário não autenticado. Redirecionando para login.")
            return redirect(url_for('login_page'))
        print(f"Usuário autenticado: {session['user']}")
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Rotas do sistema


@app.route('/login', methods=['GET'])
def login_page():
    print(f"Verificando sessão na rota /login (GET): {session}")
    if 'user' in session:
        print("Usuário já autenticado. Redirecionando para index.")
        return redirect(url_for('index'))
    print("Renderizando página de login.")
    return render_template('login.html')



@app.route('/login', methods=['POST'])
def login():
    print("Recebendo requisição POST para /login")
    data = request.get_json()
    print(f"Dados recebidos: {data}")
    matricula = data.get('matricula')
    senha = data.get('senha')
    device_type = data.get('deviceType')

    if not matricula or not senha:
        print("Matrícula ou senha não fornecidos.")
        return jsonify({'success': False, 'message': 'Matrícula e senha são obrigatórios'}), 400

    if not device_type:
        print("deviceType não fornecido, assumindo 'desktop' como padrão.")
        device_type = 'desktop'

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        print(f"Buscando usuário com matrícula: {matricula}")
        cur.execute('SELECT * FROM usuarios WHERE matricula = %s', (matricula,))
        user = cur.fetchone()
        print(f"Usuário encontrado: {user}")
        if not user:
            print(f"Usuário com matrícula {matricula} não encontrado.")
            return jsonify({'success': False, 'message': 'Matrícula ou senha inválidos'}), 401

        stored_password = user['senha']
        print(f"Senha armazenada: {stored_password}")
        print(f"Verificando senha para matrícula {matricula}")
        if senha == stored_password:
            print(f"Login bem-sucedido para matrícula {matricula}.")
            session['user'] = {
                'matricula': user['matricula'], 'nome': user['nome'], 'device_type': device_type
            }
            print(f"Sessão atualizada: {session}")
            redirect_url = url_for('pagina_principal') if device_type.lower(
            ) == 'desktop' else url_for('pda_principal')
            print(f"Redirecionando para: {redirect_url}")
            return jsonify({'success': True, 'redirect': redirect_url})
        else:
            print(f"Senha incorreta para matrícula {matricula}.")
            return jsonify({'success': False, 'message': 'Matrícula ou senha inválidos'}), 401
    except mysql.connector.Error as db_err:
        print(f"Erro no banco de dados: {db_err}")
        return jsonify({'success': False, 'message': f'Erro no banco de dados: {str(db_err)}'}), 500
    except Exception as e:
        print(f"Erro ao fazer login: {e}")
        return jsonify({'success': False, 'message': f'Erro ao fazer login: {str(e)}'}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()








logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/dados_pedidos', methods=['GET'], endpoint='get_dados_pedidos_endpoint')
@login_required
def get_dados_pedidos():
    loja = request.args.get('loja')
    grupo = request.args.get('grupo')  # Optional, for future filtering if needed
    erro = None
    dados = {}

    try:
        # Lista de filiais
        filiais = [
            {"codigo": "1", "nome": "Ponta Negra"},
            {"codigo": "2", "nome": "Alecrim"},
            {"codigo": "7", "nome": "SAC - Centro VI"},
            {"codigo": "100", "nome": "Lagoa Nova"},
            {"codigo": "121", "nome": "Norte Shopping"},
            {"codigo": "122", "nome": "Parnamirim"},
            {"codigo": "131", "nome": "ZN2"},
            {"codigo": "137", "nome": "Macaíba"},
            {"codigo": "140", "nome": "Maria Lacerda"},
            {"codigo": "141", "nome": "Igapó"}
        ]

        # Validate loja parameter
        if not loja:
            return jsonify({"erro": "Parâmetro 'loja' é obrigatório."}), 400

        # Find the store in filiais
        filial = next((f for f in filiais if f["codigo"] == loja), None)
        if not filial:
            return jsonify({"erro": f"Loja com código {loja} não encontrada."}), 404

        # Set up the API request
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1.0, status_forcelist=[500, 502, 503, 504], raise_on_status=False)
        session.mount('http://', HTTPAdapter(max_retries=retries))

        # Calculate the date range: last 7 days from today
        final_date = datetime.now().date()  # Current date (e.g., 2025-06-05)
        inicio_date = final_date - timedelta(days=6)  # 6 days prior (e.g., 2025-05-29)
        inicio_str = inicio_date.strftime('%Y-%m-%d')  # Format as YYYY-MM-DD
        final_str = final_date.strftime('%Y-%m-%d')    # Format as YYYY-MM-DD
        logger.debug(f"Date range for API: inicio={inicio_str}, final={final_str}")

        # Fetch orders from origem=999, filter by destino in the backend
        url_pedidos = f"http://appunica.sacolao.com:8480/ws/api_sacolao?operacao=pedido_loja&operador=999&inicio={inicio_str}&final={final_str}&token=s4c0140_$b4tm4n_r0b1n_790883_000103&loja=999"
        resp_pedidos = session.get(url_pedidos, timeout=50)
        resp_pedidos.raise_for_status()
        dados_pedidos = resp_pedidos.json().get("dados", [])
        logger.debug(f"API Response for loja {loja}: {dados_pedidos}")

        # Initialize order counts
        total_pedidos = 0
        pedidos_por_status = {
            0: 0,  # Aberto
            1: 0,  # Acatado
            2: 0,  # Separando
            3: 0,  # Conferência
            4: 0,  # Despachado
            5: 0,  # Recebido
            6: 0,  # Cancelado
            8: 0   # Em Andamento
        }

        # Filter orders by destino and categorize by status
        loja_id = filial["codigo"]
        for pedido in dados_pedidos:
            destino = str(pedido.get("destino", ""))
            logger.debug(f"Pedido - destino: {destino}, loja_id: {loja_id}, status: {pedido.get('status', 0)}")
            if destino == loja_id:
                status = pedido.get("status", 0)
                if status in pedidos_por_status:
                    pedidos_por_status[status] += 1
                    total_pedidos += 1

        # Prepare response data
        dados = {
            "nome_filial": filial["nome"],
            "pedidos_por_status": pedidos_por_status,
            "total_pedidos": total_pedidos
        }
        logger.debug(f"Dados preparados para loja {loja}: {dados}")

    except requests.Timeout:
        erro = "Erro ao consultar a API: A requisição excedeu o tempo limite."
        logger.error(erro)
        return jsonify({"erro": erro}), 504
    except requests.RequestException as e:
        erro = f"Erro ao consultar a API: Falha na conexão com o servidor. {str(e)}"
        logger.error(erro)
        return jsonify({"erro": erro}), 503
    except Exception as e:
        erro = f"Ocorreu um erro inesperado: {str(e)}"
        logger.error(erro)
        return jsonify({"erro": erro}), 500

    return jsonify(dados)




@app.route('/alerta_lojas', methods=['GET', 'POST'])
@login_required
def alerta_lojas():
    produtos_faltando = []
    erro = None
    loja = None
    grupo = None
    fornecedor = None
    saldo_min_cd = None  # Novo parâmetro para saldo mínimo no CD
    saldo_max_loja = None  # Novo parâmetro para saldo máximo na loja
    dados_pizza = {}
    dados_ranking = []
    fornecedores = []
    rupturas = []
    total_skus_cd_com_saldo = 0
    total_skus_loja_zerados = 0
    total_skus_cd_com_saldo_sem_loja = 0

    if request.method == 'POST':
        loja = request.form.get('loja', '').strip()
        grupo = request.form.get('grupo', '').strip()
        fornecedor = request.form.get('fornecedor', '').strip()
        saldo_min_cd = request.form.get('saldo_min_cd', '').strip()  # Removido o valor padrão '0'
        saldo_max_loja = request.form.get('saldo_max_loja', '').strip()  # Removido o valor padrão '9999'

        # Definir valores padrão para os filtros de saldo
        if not saldo_min_cd and not saldo_max_loja:
            # Se ambos os campos de saldo não forem preenchidos, aplicar o padrão: est_cd > 0 e est_loja <= 0
            saldo_min_cd = 1  # Para garantir est_cd > 0
            saldo_max_loja = 0  # Para garantir est_loja <= 0
        else:
            # Converter os valores de saldo para números, usando valores padrão se necessário
            try:
                saldo_min_cd = float(saldo_min_cd) if saldo_min_cd else 0.0
                saldo_max_loja = float(saldo_max_loja) if saldo_max_loja else 9999.0
            except ValueError:
                erro = "Os valores de saldo devem ser numéricos."
                saldo_min_cd = 0.0
                saldo_max_loja = 9999.0

                # Formatar para inteiro se for um número inteiro
                if saldo_min_cd.is_integer():
                    saldo_min_cd = int(saldo_min_cd)
                if saldo_max_loja.is_integer():
                    saldo_max_loja = int(saldo_max_loja)

        # Validação: Loja é obrigatória
        if not loja:
            erro = "Por favor, informe a loja."
        elif not loja.isdigit():
            erro = "Loja deve ser um número válido."
        else:
            try:
                session = requests.Session()
                retries = Retry(total=5, backoff_factor=1.0, status_forcelist=[500, 502, 503, 504], raise_on_status=False)
                session.mount('http://', HTTPAdapter(max_retries=retries))

                # Construir URLs considerando os parâmetros preenchidos
                # Consulta de produtos com filtro de fornecedor na API
                url_dados = f"http://appunica.sacolao.com:8480/ws/api_sacolao?operacao=produtos&operador=999&token=s4c0140_$b4tm4n_r0b1n_790883_000103&loja={999}"
                if grupo:
                    url_dados += f"&grupo={grupo}"
                if fornecedor:
                    url_dados += f"&fornecedor={fornecedor}"  # Adicionando filtro de fornecedor na URL
                resp_dados = session.get(url_dados, timeout=1500)
                resp_dados.raise_for_status()
                dados_produtos = resp_dados.json().get("dados", [])

                # Se a API não suportar o filtro de fornecedor, aplicamos localmente como fallback
                if fornecedor and not dados_produtos:
                    url_dados_sem_fornecedor = f"http://appunica.sacolao.com:8480/ws/api_sacolao?operacao=produtos&operador=999&token=s4c0140_$b4tm4n_r0b1n_790883_000103&loja={loja}"
                    if grupo:
                        url_dados_sem_fornecedor += f"&grupo={grupo}"
                    resp_dados_sem_fornecedor = session.get(url_dados_sem_fornecedor, timeout=1500)
                    resp_dados_sem_fornecedor.raise_for_status()
                    dados_produtos = resp_dados_sem_fornecedor.json().get("dados", [])
                    dados_produtos = [p for p in dados_produtos if 'fornecedor' in p and isinstance(p['fornecedor'], str) and fornecedor.lower() in p['fornecedor'].lower()]
                
                produtos_dict = {str(p.get('codigo', '')): p for p in dados_produtos if 'codigo' in p and 'fornecedor' in p}

                # Log para depuração dos dados retornados
                logging.debug(f"Dados de produtos retornados: {dados_produtos}")

                # Consulta de estoque na loja
                url_estoque = f"http://appunica.sacolao.com:8480/ws/api_sacolao?operacao=estoque&operador=999&token=s4c0140_$b4tm4n_r0b1n_790883_000103&loja={loja}"
                if grupo:
                    url_estoque += f"&grupo={grupo}"
                resp_estoque = session.get(url_estoque, timeout=1500)
                resp_estoque.raise_for_status()
                dados_estoque = resp_estoque.json().get("dados", [])

                # Consulta de estoque no CD
                url_estoque_cd = f"http://appunica.sacolao.com:8480/ws/api_sacolao?operacao=estoque&operador=999&token=s4c0140_$b4tm4n_r0b1n_790883_000103&loja=999"
                if grupo:
                    url_estoque_cd += f"&grupo={grupo}"
                resp_estoque_cd = session.get(url_estoque_cd, timeout=1500)
                resp_estoque_cd.raise_for_status()
                dados_estoque_cd = resp_estoque_cd.json().get("dados", [])

                # Criar dicionário de estoque do CD
                estoque_cd_dict = {}
                for p in dados_estoque_cd:
                    if 'produto' not in p or 'estoque' not in p:
                        continue
                    cod = str(p.get('produto', ''))
                    estoque_value = p.get('estoque')
                    est_cd = 0.0 if estoque_value is None else float(estoque_value)
                    if cod in produtos_dict:
                        estoque_cd_dict[cod] = est_cd

                # Calcular total de SKUs no CD com saldo positivo (após filtros)
                total_skus_cd_com_saldo = sum(1 for est_cd in estoque_cd_dict.values() if est_cd > 0)

                # Construir lista de produtos faltando e calcular métricas
                total_skus_cd_com_saldo_sem_loja = 0
                rupturas_count = 0
                fornecedor_rupturas = {}

                for item in dados_estoque:
                    if 'produto' not in item or 'estoque' not in item:
                        continue
                    cod = str(item.get('produto', ''))
                    if cod not in produtos_dict:
                        continue

                    estoque_value_loja = item.get('estoque')
                    est_loja = 0.0 if estoque_value_loja is None else float(estoque_value_loja)
                    est_cd = estoque_cd_dict.get(cod, 0.0)

                    # Filtrar produtos com base nos novos parâmetros de saldo
                    if est_cd >= saldo_min_cd and est_loja <= saldo_max_loja:
                        total_skus_cd_com_saldo_sem_loja += 1
                        produto_info = produtos_dict.get(cod, {})
                        produto_fornecedor = produto_info.get('fornecedor', 'Desconhecido')

                        rupturas_count += 1
                        fornecedor_rupturas[produto_fornecedor] = fornecedor_rupturas.get(produto_fornecedor, 0) + 1

                        est_loja_formatado = int(est_loja) if est_loja.is_integer() else est_loja
                        est_cd_formatado = int(est_cd) if est_cd.is_integer() else est_cd
                        preco_formatado = float(produto_info.get('preco', 0.0)) if produto_info.get('preco') else 0.0
                        custo_formatado = float(produto_info.get('custo', 0.0)) if produto_info.get('custo') else 0.0
                        produtos_faltando.append({
                            'grupo': produto_info.get('grupo', ''),
                            'codigo': cod,
                            'descricao': produto_info.get('descricao', 'Sem descrição'),
                            'und': produto_info.get('und', ''),
                            'marca': produto_info.get('marca', ''),
                            'fornecedor': produto_fornecedor,
                            'localizacao': produto_info.get('localizacao', ''),
                            'estoque_cd': est_cd_formatado,
                            'estoque_loja': est_loja_formatado,
                            'preco': preco_formatado,  # Novo campo
                            'custo': custo_formatado   # Novo campo
                        })
                    else:
                        logging.debug(f"Produto {cod} excluído: est_loja={est_loja}, est_cd={est_cd}")

                # Calcular total de SKUs zerados na loja (após filtros)
                total_skus_loja_zerados = sum(1 for item in dados_estoque if 'produto' in item and 'estoque' in item and str(item['produto']) in produtos_dict and (item['estoque'] is None or float(item['estoque']) <= 0))

                # Dados para o gráfico de pizza (baseado apenas em rupturas)
                percentual_ruptura = (rupturas_count / total_skus_cd_com_saldo * 100) if total_skus_cd_com_saldo > 0 else 0
                percentual_com_estoque = 100 - percentual_ruptura if total_skus_cd_com_saldo > 0 else 100
                dados_pizza = {
                    'rupturas': round(percentual_ruptura, 2),
                    'com_estoque': round(percentual_com_estoque, 2)
                }

                # Dados para o gráfico de ranking (baseado apenas em rupturas)
                dados_ranking = [
                    {'fornecedor': fornecedor, 'rupturas': count}
                    for fornecedor, count in sorted(fornecedor_rupturas.items(), key=lambda x: x[1], reverse=True)[:10]
                ]
                fornecedores = [item['fornecedor'] for item in dados_ranking]
                rupturas = [item['rupturas'] for item in dados_ranking]

                if not produtos_faltando:
                    erro = "Nenhum produto encontrado com os critérios de saldo especificados."

            except requests.Timeout:
                erro = "Erro ao consultar a API: A requisição excedeu o tempo limite."
            except requests.RequestException as e:
                erro = f"Erro ao consultar a API: Falha na conexão com o servidor. {str(e)}"
            except Exception as e:
                logging.error(f"Erro inesperado: {e}")
                erro = f"Ocorreu um erro inesperado: {str(e)}"

        # Renderiza o template para ambos GET e POST
        return render_template(
            'alerta_lojas.html',
            produtos=produtos_faltando,
            erro=erro,
            loja=loja,
            grupo=grupo,
            fornecedor=fornecedor,
            saldo_min_cd=saldo_min_cd,
            saldo_max_loja=saldo_max_loja,
            dados_pizza=dados_pizza if dados_pizza else None,
            dados_ranking=dados_ranking if dados_ranking else None,
            fornecedores=fornecedores if fornecedores else None,
            rupturas=rupturas if rupturas else None,
            total_skus_cd_com_saldo=total_skus_cd_com_saldo,
            total_skus_loja_zerados=total_skus_loja_zerados,
            total_skus_cd_com_saldo_sem_loja=total_skus_cd_com_saldo_sem_loja
        )

    # Método GET: Renderiza o template inicial
    return render_template(
        'alerta_lojas.html',
        produtos=produtos_faltando,
        erro=erro,
        loja=loja,
        grupo=grupo,
        fornecedor=fornecedor,
        saldo_min_cd=saldo_min_cd,
        saldo_max_loja=saldo_max_loja,
        dados_pizza=dados_pizza,
        dados_ranking=dados_ranking,
        fornecedores=fornecedores,
        rupturas=rupturas,
        total_skus_cd_com_saldo=total_skus_cd_com_saldo,
        total_skus_loja_zerados=total_skus_loja_zerados,
        total_skus_cd_com_saldo_sem_loja=total_skus_cd_com_saldo_sem_loja
    )
    

# Função para montar o mapeamento Loja → Banco dinamicamente
def get_loja_para_banco():
    loja_map = {}
    for key in os.environ:
        if key.startswith("LOJA_"):
            loja_id = key.split("_")[1]
            banco = os.getenv(key)
            loja_map[loja_id] = banco
    return loja_map

LOJA_PARA_BANCO = get_loja_para_banco()

@app.route('/analise_vendas', methods=['GET'])
def analise_vendas():
    # Esta rota renderiza o template HTML
    return render_template('analise_vendas.html')


@app.route('/api/vendas', methods=['GET'])
def get_vendas():
    id_loja = request.args.get('id_loja')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    if not id_loja or id_loja not in LOJA_PARA_BANCO:
        return jsonify({"erro": "ID de loja inválido ou não mapeado."}), 400

    banco = LOJA_PARA_BANCO[id_loja]

    # Mapeamento de id_loja para o nome da tabela
    TABELA_POR_LOJA = {
        "1": "vendas_pn",      # PONTA NEGRA
        "2": "vendas_alecrim", # ALECRIM
        "7": "vendas_sac6",    # SAC - CENTRO VI
        "100": "vendas_ln",    # LAGOA NOVA
        "121": "vendas_nshop", # NORTE SHOPPING
        "122": "vendas_parna", # PARNAMIRIM
        "131": "vendas_zn2",   # ZN2
        "137": "vendas_mac",   # MACAIBA
        "140": "vendas_ml",    # MARIA LACERDA
        "141": "vendas_igapo"  # IGAPO
    }

    tabela_vendas = TABELA_POR_LOJA.get(id_loja, f"vendas_{id_loja}")  # Fallback caso id_loja não esteja mapeado

    db_config = {
        'host': os.getenv("DB_HOST"),
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASSWORD"),
        'database': banco
    }

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        query = f"""
        SELECT 
            grupo,
            produto,
            fornecedor,
            DATE_FORMAT(COALESCE(data_hora, '1970-01-01'), '%Y-%m-%d') AS data,
            SUM(qtd * preco) AS faturamento,
            SUM(qtd) AS quantidade_vendida,
            SUM((preco - custo) * qtd) AS lucro
        FROM {tabela_vendas}
        WHERE 1=1
        """

        if data_inicio:
            query += f" AND data_hora >= '{data_inicio} 00:00:00'"
        if data_fim:
            query += f" AND data_hora <= '{data_fim} 23:59:59'"

        query += f" GROUP BY grupo, produto, fornecedor, DATE_FORMAT(COALESCE(data_hora, '1970-01-01'), '%Y-%m-%d') ORDER BY faturamento DESC"

        print(f"Executando query em {banco}.{tabela_vendas}: {query}")  # Log para depuração
        cursor.execute(query)
        results = cursor.fetchall()

        print(f"Dados retornados para loja {id_loja}: {results}")  # Log para depuração

        cursor.close()
        conn.close()

        return jsonify(results)

    except Exception as e:
        error_msg = f"Erro ao consultar o banco de dados: {str(e)}"
        print(error_msg)  # Log no servidor
        return jsonify({"erro": error_msg}), 500







# Rota protegida: /pda_romaneio
@app.route('/pda_romaneio')
@login_required
def pda_romaneio():
    return render_template('pda_romaneio.html')


@app.route('/pda_conferencia/<romaneio_id>')
def pda_conferencia(romaneio_id):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM romaneios WHERE id = %s", (romaneio_id,))
        romaneio = cursor.fetchone()
        if not romaneio:
            print(f"Romaneio {romaneio_id} não encontrado")
            return "Romaneio não encontrado", 404

        # Formatar as datas para exibir no formato DD/MM/YYYY HH:MM
        data_inicio = romaneio['data_inicio'].strftime("%d/%m/%Y %H:%M") if romaneio['data_inicio'] else "N/A"
        data_fim = romaneio['data_fim'].strftime("%d/%m/%Y %H:%M") if romaneio['data_fim'] else "N/A"

        return render_template('pda_conferencia.html',
                              romaneio_id=romaneio['id'],
                              conferente=romaneio['conferente'],
                              motorista=romaneio['nome_motorista'],
                              filial=romaneio['nome_filial'],
                              placa=romaneio['placa_caminhao'],
                              data_inicio=data_inicio,
                              data_fim=data_fim)
    except Exception as e:
        print(f"Erro ao buscar romaneio: {str(e)}")
        return f"Erro ao carregar romaneio: {str(e)}", 500
    finally:
        cursor.close()
        db.close()

# Variáveis de ambiente
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )




@app.route('/processar_romaneio', methods=['POST'])
def processar_romaneio():
    print(f"Sessão atual: {session}")
    if 'user' not in session:
        print("Usuário não encontrado na sessão, redirecionando para login")
        return redirect(url_for('login'))

    user = session['user']
    matricula_conferente = user.get('matricula')
    if not matricula_conferente:
        print("Matrícula do conferente não encontrada nos dados da sessão, redirecionando para login")
        return redirect(url_for('login'))

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Busca nome do conferente
        cursor.execute("SELECT nome FROM usuarios WHERE matricula = %s", (matricula_conferente,))
        usuario = cursor.fetchone()
        if not usuario:
            print(f"Matrícula {matricula_conferente} não encontrada no banco")
            return redirect(url_for('login'))
        conferente_nome = usuario['nome']
        print(f"Conferente identificado: {conferente_nome}")
    except Exception as e:
        print(f"Erro ao consultar conferente: {str(e)}")
        return redirect(url_for('login'))
    finally:
        cursor.close()

    motorista_id = request.form.get('motorista_id')
    filial_id1 = request.form.get('filial_id1')
    placa_caminhao = request.form.get('placa_caminhao')

    print(f"Recebido: motorista_id={motorista_id}, filial_id1={filial_id1}, placa_caminhao={placa_caminhao}, matricula_conferente={matricula_conferente}")

    if not motorista_id or not filial_id1 or not placa_caminhao:
        return "Dados incompletos", 400

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT nome FROM usuarios WHERE matricula = %s", (motorista_id,))
        motorista = cursor.fetchone()
        if not motorista:
            print(f"Matrícula do motorista {motorista_id} não encontrada")
            return "Matrícula do motorista inválida", 400
        nome_motorista = motorista['nome']
    except Exception as e:
        print(f"Erro ao consultar motorista: {str(e)}")
        return f"Erro ao consultar motorista: {str(e)}", 500

    try:
        cursor.execute("SELECT filial_nome1 FROM filiais WHERE filial_id1 = %s", (filial_id1,))
        filial = cursor.fetchone()
        if not filial:
            print(f"Filial com ID {filial_id1} não encontrada")
            return "Filial inválida", 400
        nome_filial = filial['filial_nome1']
    except Exception as e:
        print(f"Erro ao consultar filial: {str(e)}")
        return f"Erro ao consultar filial: {str(e)}", 500

    # Gera a data atual
    data_hoje = datetime.now().strftime("%Y%m%d")

    # Busca o maior sequencial globalmente
    sql_busca_sequencial = "SELECT MAX(id) as max_id FROM romaneios"
    cursor.execute(sql_busca_sequencial)
    resultado = cursor.fetchone()

    ultimo_sequencial = 0
    if resultado and resultado['max_id']:
        try:
            ultimo_sequencial = int(resultado['max_id'].split("-")[1])
        except (IndexError, ValueError):
            ultimo_sequencial = 0

    novo_sequencial = ultimo_sequencial + 1
    romaneio_id = f"RMN{data_hoje}-{str(novo_sequencial).zfill(3)}"

    data_inicio = datetime.now()

    try:
        sql_insert = """
            INSERT INTO romaneios 
                (id, motorista_id, filial_id1, placa_caminhao, conferente, nome_motorista, nome_filial, status, data_inicio, data_fim) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'em_andamento', %s, NULL)
        """
        valores = (
            romaneio_id,
            motorista_id,
            filial_id1,
            placa_caminhao,
            conferente_nome,
            nome_motorista,
            nome_filial,
            data_inicio
        )

        cursor.execute(sql_insert, valores)
        db.commit()
        print(f"Romaneio {romaneio_id} inserido com sucesso")
    except Exception as e:
        print(f"Erro ao salvar romaneio: {str(e)}")
        db.rollback()
        return f"Erro ao iniciar romaneio: {str(e)}", 500
    finally:
        cursor.close()
        db.close()

    return redirect(url_for('pda_conferencia', romaneio_id=romaneio_id))



@app.route('/registrar_volume', methods=['POST'])
def registrar_volume():
    romaneio_id = request.form.get('romaneio_id')
    codigo_barra_completo = request.form.get('codigo_volume')
    
    if not romaneio_id or not codigo_barra_completo:
        return jsonify({"status": "error", "msg": "Dados incompletos"}), 400

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Verifica se o romaneio existe
        cursor.execute("SELECT id FROM romaneios WHERE id = %s", (romaneio_id,))
        romaneio_atual = cursor.fetchone()
        if not romaneio_atual:
            return jsonify({"status": "error", "msg": f"Romaneio {romaneio_id} não encontrado."}), 400

        # Extrair informações do código de barras
        partes = codigo_barra_completo.split('-')
        numero_pedido = partes[0]
        volume_info = partes[1].split('/')
        volume_numero = int(volume_info[0])
        total_volumes = int(volume_info[1])

        # Buscar filial_id do romaneio
        cursor.execute("SELECT filial_id1 FROM romaneios WHERE id = %s", (romaneio_id,))
        filial_data = cursor.fetchone()
        filial_id_romaneio = filial_data['filial_id1'] if filial_data else None

        if not filial_id_romaneio:
            return jsonify({"status": "error", "msg": "Filial do romaneio não encontrada."}), 400

        # Verificar se esse pedido já foi usado em outro romaneio
        cursor.execute("""
            SELECT p.numero_pedido, r.id AS romaneio_id, r.nome_filial
            FROM pedidos p
            JOIN romaneios r ON p.romaneio_id = r.id
            WHERE p.numero_pedido = %s AND p.romaneio_id != %s
        """, (numero_pedido, romaneio_id))
        pedido_em_outro_romaneio = cursor.fetchone()

        if pedido_em_outro_romaneio:
            return jsonify({
                "status": "warning",
                "msg": f"Pedido {pedido_em_outro_romaneio['numero_pedido']} já está no romaneio {pedido_em_outro_romaneio['romaneio_id']} da filial {pedido_em_outro_romaneio['nome_filial']}."
            })

        # Verificar se o pedido já existe neste romaneio
        cursor.execute("SELECT id FROM pedidos WHERE numero_pedido = %s AND romaneio_id = %s", (numero_pedido, romaneio_id))
        pedido_existente = cursor.fetchone()

        if not pedido_existente:
            # Criar pedido com filial_id do romaneio
            sql_criar_pedido = """
                INSERT INTO pedidos 
                    (numero_pedido, romaneio_id, filial_id, total_volumes, status)
                VALUES (%s, %s, %s, %s, 'pendente')
            """
            cursor.execute(sql_criar_pedido, (numero_pedido, romaneio_id, filial_id_romaneio, total_volumes))
            pedido_id = cursor.lastrowid

            # Criar todos os volumes como 'pendente'
            for i in range(1, total_volumes + 1):
                codigo_barra = f"{numero_pedido}-{i}/{total_volumes}"
                sql_criar_volume = """
                    INSERT INTO volumes 
                        (romaneio_id, pedido_id, codigo_barra, status)
                    VALUES (%s, %s, %s, 'pendente')
                """
                cursor.execute(sql_criar_volume, (romaneio_id, pedido_id, codigo_barra))
        else:
            pedido_id = pedido_existente['id']

        # Verificar se o volume já foi escaneado
        cursor.execute("""
            SELECT id, status FROM volumes 
            WHERE pedido_id = %s AND codigo_barra = %s
        """, (pedido_id, codigo_barra_completo))
        volume_atual = cursor.fetchone()

        if volume_atual and volume_atual['status'] == 'escaneado':
            return jsonify({
                "status": "warning",
                "msg": f"Volume {codigo_barra_completo} já foi escaneado."
            })
        elif volume_atual and volume_atual['status'] == 'pendente':
            cursor.execute("""
                UPDATE volumes SET 
                    data_conferencia = NOW(),
                    status = 'escaneado'
                WHERE id = %s
            """, (volume_atual['id'],))
        else:
            cursor.execute("""
                INSERT INTO volumes 
                    (romaneio_id, pedido_id, codigo_barra, data_conferencia, status)
                VALUES (%s, %s, %s, NOW(), 'escaneado')
            """, (romaneio_id, pedido_id, codigo_barra_completo))

        # Atualizar status do pedido
        cursor.execute("""
            SELECT COUNT(*) AS total, SUM(CASE WHEN status = 'escaneado' THEN 1 ELSE 0 END) AS escaneados
            FROM volumes
            WHERE pedido_id = %s
        """, (pedido_id,))
        stats = cursor.fetchone()

        if stats['total'] == stats['escaneados']:
            cursor.execute("UPDATE pedidos SET status = 'ok' WHERE id = %s", (pedido_id,))
        else:
            cursor.execute("UPDATE pedidos SET status = 'pendente' WHERE id = %s", (pedido_id,))

        db.commit()
        return jsonify({
            "status": "ok",
            "volume": codigo_barra_completo,
            "msg": "Volume registrado com sucesso!"
        })

    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar volume: {str(e)}")
        return jsonify({"status": "error", "msg": str(e)}), 500

    finally:
        cursor.close()
        db.close()


@app.route('/get_pedidos/<romaneio_id>', methods=['GET'])
def get_pedidos(romaneio_id):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Consulta para obter pedidos e status atualizados
        sql_pedidos = """
            SELECT 
                p.id AS pedido_id,
                p.numero_pedido,
                p.total_volumes,
                COUNT(v.id) AS volumes_escaneados,
                CASE 
                    WHEN COUNT(v.id) = p.total_volumes THEN 'ok'
                    ELSE 'pendente'
                END AS status
            FROM pedidos p
            LEFT JOIN volumes v ON p.id = v.pedido_id AND v.romaneio_id = %s AND v.status = 'escaneado'
            WHERE p.romaneio_id = %s
            GROUP BY p.id, p.numero_pedido, p.total_volumes
        """
        cursor.execute(sql_pedidos, (romaneio_id, romaneio_id))
        pedidos = cursor.fetchall()

        return jsonify({"status": "ok", "pedidos": pedidos})

    except Exception as e:
        print(f"Erro ao buscar pedidos: {str(e)}")
        return jsonify({"status": "error", "msg": str(e)}), 500

    finally:
        cursor.close()
        db.close()


@app.route('/criar_pedido', methods=['POST'])
def criar_pedido():
    romaneio_id = request.form.get('romaneio_id')
    numero_pedido = request.form.get('numero_pedido')
    filial_id = request.form.get('filial_id')
    total_volumes = request.form.get('total_volumes')

    if not romaneio_id or not numero_pedido or not filial_id or not total_volumes:
        return jsonify({"status": "error", "msg": "Todos os campos são obrigatórios."}), 400

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Verifica se o romaneio existe
        cursor.execute("SELECT id FROM romaneios WHERE id = %s", (romaneio_id,))
        romaneio = cursor.fetchone()
        if not romaneio:
            return jsonify({"status": "error", "msg": f"Romaneio {romaneio_id} não encontrado."}), 400

        # Insere o pedido com filial_id
        sql = """
            INSERT INTO pedidos 
                (numero_pedido, romaneio_id, filial_id, total_volumes, status)
            VALUES (%s, %s, %s, %s, 'pendente')
        """
        cursor.execute(sql, (numero_pedido, romaneio_id, filial_id, total_volumes))
        db.commit()

        return jsonify({"status": "ok", "msg": "Pedido criado com sucesso."})

    except Exception as e:
        db.rollback()
        print(f"Erro ao criar pedido: {str(e)}")
        return jsonify({"status": "error", "msg": str(e)}), 500

    finally:
        cursor.close()
        db.close()



@app.route('/excluir_pedido', methods=['POST'])
def excluir_pedido():
    pedido_id = request.form.get('pedido_id')

    if not pedido_id:
        return jsonify({"status": "error", "msg": "ID do pedido não fornecido"}), 400

    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Remover volumes primeiro (por causa da FK)
        cursor.execute("DELETE FROM volumes WHERE pedido_id = %s", (pedido_id,))
        
        # Remover pedido
        cursor.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
        db.commit()

        return jsonify({"status": "ok", "msg": "Pedido excluído com sucesso."})

    except Exception as e:
        db.rollback()
        print(f"Erro ao excluir pedido: {str(e)}")
        return jsonify({"status": "error", "msg": str(e)}), 500

    finally:
        cursor.close()
        db.close()
        

@app.route('/finalizar_romaneio/<romaneio_id>', methods=['POST'])
def finalizar_romaneio(romaneio_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Atualiza o status do romaneio e define data_fim como NOW()
        cursor.execute("""
            UPDATE romaneios 
            SET status = 'concluido', data_fim = NOW() 
            WHERE id = %s
        """, (romaneio_id,))
        db.commit()

        # Após finalizar, redirecione para a tela de resumo do romaneio
        return redirect(url_for('pda_resumo_romaneio', romaneio_id=romaneio_id))

    except Exception as e:
        db.rollback()
        print(f"Erro ao finalizar romaneio: {str(e)}")
        return f"<script>alert('Erro ao finalizar romaneio: {str(e)}'); window.location='javascript:history.back()';</script>", 500

    finally:
        cursor.close()
        db.close()




@app.route('/get_volumes/<pedido_id>', methods=['GET'])
def get_volumes(pedido_id):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Consulta para obter volumes do pedido
        sql_volumes = """
            SELECT 
                v.codigo_barra,
                v.data_conferencia,
                v.status
            FROM volumes v
            WHERE v.pedido_id = %s
        """
        cursor.execute(sql_volumes, (pedido_id,))
        volumes = cursor.fetchall()

        # Consulta para obter informações do pedido
        sql_pedido = """
            SELECT 
                id,
                numero_pedido,
                total_volumes
            FROM pedidos
            WHERE id = %s
        """
        cursor.execute(sql_pedido, (pedido_id,))
        pedido = cursor.fetchone()

        return jsonify({"status": "ok", "pedido": pedido, "volumes": volumes})

    except Exception as e:
        print(f"Erro ao buscar volumes: {str(e)}")
        return jsonify({"status": "error", "msg": str(e)}), 500

    finally:
        cursor.close()
        db.close()




@app.route('/pda_resumo_romaneio/<romaneio_id>')
@login_required
def pda_resumo_romaneio(romaneio_id):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Dados do Romaneio
        cursor.execute("SELECT * FROM romaneios WHERE id = %s", (romaneio_id,))
        romaneio = cursor.fetchone()

        if not romaneio:
            return "Romaneio não encontrado", 404

        data_inicio = romaneio['data_inicio'].strftime("%d/%m/%Y %H:%M") if romaneio['data_inicio'] else "-"
        data_fim = romaneio['data_fim'].strftime("%d/%m/%Y %H:%M") if romaneio.get('data_fim') else "-"

        # Buscar pedidos + nome da filial corretamente
        sql_pedidos = """
    SELECT 
        p.id AS pedido_id,
        p.numero_pedido,
        p.filial_id,
        COALESCE(f.filial_nome1, '-') AS destinatario,  -- Garante que exibe '-' se for NULL
        p.total_volumes,
        COUNT(v.id) AS volumes_escaneados
    FROM pedidos p
    LEFT JOIN volumes v ON p.id = v.pedido_id AND v.status = 'escaneado'
    LEFT JOIN filiais f ON p.filial_id = f.filial_id1
    WHERE p.romaneio_id = %s
    GROUP BY p.id, p.numero_pedido, p.filial_id, f.filial_nome1, p.total_volumes
"""
        cursor.execute(sql_pedidos, (romaneio_id,))
        pedidos = cursor.fetchall()

        return render_template(
            'pda_imprimir_romaneio.html',
            romaneio=romaneio,
            data_inicio=data_inicio,
            data_fim=data_fim,
            pedidos=pedidos
        )

    except Exception as e:
        print(f"Erro ao carregar resumo do romaneio: {str(e)}")
        return f"Erro ao carregar resumo do romaneio: {str(e)}", 500

    finally:
        cursor.close()
        db.close()







@app.route('/pda')
@login_required
def pda_index():
    print("Acessando rota /pda (interface simplificada)")
    # Nova página simplificada para PDA
    return render_template('pda_index.html')


@app.route('/pda_principal')
@login_required
def pda_principal():
    print("Acessando rota /pda_principal")
    return render_template('pda_principal.html')




@app.route('/logout', methods=['GET'])
@login_required
def logout():
    print("Executando logout")
    session.pop('user', None)
    print("Usuário deslogado. Redirecionando para login.")
    return redirect(url_for('login_page'))


@app.route('/index')
@login_required
def index():
    print("Acessando rota /index (Gestão de Estoque)")
    return render_template('index.html')


@app.route('/')
@login_required
def pagina_principal():
    print("Acessando rota / (pagina_principal)")
    return render_template('pagina_principal.html')


@app.route('/relatorio', methods=['GET'])
@login_required
def relatorio_page():
    print("Acessando rota /relatorio")
    return render_template('relatorio.html')





@app.route('/notificacoes/count', methods=['GET'])
@login_required
def notificacoes_count():
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'count': 0}), 500

        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS count FROM solicitacoes WHERE status = 'Pendente'")
        result = cur.fetchone()
        count = result['count'] if result else 0

        cur.close()
        conn.close()
        return jsonify({'count': count})
    except Exception as e:
        print(f"Erro ao contar notificações: {str(e)}")
        return jsonify({'count': 0}), 500


@app.route('/acomp_solic_deposito')
def acomp_solic_deposito():
    print("Acessando rota /acomp_solic_deposito")
    filial_id = request.args.get('filial_id', '')
    status_filtrado = request.args.get('status', '')
    format_type = request.args.get('format', '')
    erro = None
    solicitacoes = []
    filiais = []

    try:
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            erro = "Erro ao conectar ao banco de dados"
            if format_type == 'json':
                return jsonify({'solicitacoes': [], 'erro': erro})
            return render_template('acomp_solic_deposito.html', solicitacoes=[], erro=erro, filiais=[], filial_id=filial_id, status_filtrado=status_filtrado)

        cur = conn.cursor(dictionary=True)

        # Buscar lista de filiais
        print("Buscando filiais...")
        cur.execute("SELECT DISTINCT filial_id1, filial_nome1 FROM filiais ORDER BY filial_nome1")
        filiais = cur.fetchall()
        print(f"Filiais encontradas: {filiais}")

        # Consulta com JOIN para garantir nome da filial atualizado
        query = '''
            SELECT s.id, s.numero_solicitacao, s.filial_id, f.filial_nome1 AS filial_nome,
                   s.tipo_solicitacao, s.titulo, s.descricao,
                   s.quantidade, s.data_hora, s.matricula, s.nome_usuario, s.status
            FROM solicitacoes s
            JOIN filiais f ON s.filial_id = f.filial_id1
            WHERE 1=1
        '''
        params = []

        if filial_id and filial_id.isdigit():
            query += ' AND s.filial_id = %s'
            params.append(filial_id)
        if status_filtrado:
            query += ' AND s.status = %s'
            params.append(status_filtrado)

        query += ' ORDER BY s.data_hora DESC'

        print(f"Executando consulta: {query} com parâmetros: {params}")
        cur.execute(query, params)
        solicitacoes = cur.fetchall()
        print(f"Solicitações encontradas: {len(solicitacoes)}")
        print(f"Dados das solicitações: {solicitacoes}")

        cur.close()
        conn.close()

        if format_type == 'json':
            return jsonify({'solicitacoes': solicitacoes})

        print("Tentando renderizar o template...")
        return render_template(
            'acomp_solic_deposito.html',
            solicitacoes=solicitacoes,
            erro=erro,
            filiais=filiais,
            filial_id=filial_id,
            status_filtrado=status_filtrado
        )

    except Exception as e:
        print(f"Erro ao buscar solicitações: {str(e)}")
        erro = f"Ocorreu um erro ao carregar as solicitações: {str(e)}"
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        if format_type == 'json':
            return jsonify({'solicitacoes': [], 'erro': erro})
        return render_template(
            'acomp_solic_deposito.html',
            solicitacoes=[],
            erro=erro,
            filiais=[],
            filial_id=filial_id,
            status_filtrado=status_filtrado

        )


@app.route('/salvar_resposta', methods=['POST'])
def salvar_resposta():
    print("Recebida requisição para salvar resposta")
    try:
        data = request.get_json()
        print(f"Dados recebidos: {data}")
        solicitacao_id = str(data.get('solicitacao_id')).strip()
        mensagem = data.get('mensagem')

        if not solicitacao_id or not mensagem:
            print("solicitacao_id ou mensagem não fornecidos")
            return jsonify({'success': False, 'error': 'solicitacao_id e mensagem são obrigatórios'}), 400

        # Conectar ao banco
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        # Garantir que a conexão não está em modo autocommit falso
        conn.autocommit = True
        cur = conn.cursor(dictionary=True)
        print(f"Conexão ao banco estabelecida. Database: {conn.database}")

        # Depuração: listar todas as solicitações visíveis
        cur.execute("SELECT numero_solicitacao, data_hora, data_liberacao FROM solicitacoes")
        all_solicitacoes = cur.fetchall()
        print(f"Todas as solicitações visíveis: {all_solicitacoes}")

        # Validar a solicitação
        query = """
            SELECT s.id, s.numero_solicitacao, s.data_hora, s.data_liberacao
            FROM solicitacoes s
            JOIN filiais f ON s.filial_id = f.filial_id1
            WHERE CAST(s.numero_solicitacao AS CHAR) = %s
        """
        cur.execute(query, (solicitacao_id,))
        solicitacao = cur.fetchone()
        print(f"Resultado da consulta: {solicitacao}")

        if not solicitacao:
            print(f"Solicitação com numero_solicitacao {solicitacao_id} não encontrada")
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': f'Solicitação com numero_solicitacao {solicitacao_id} não encontrada'}), 404

        # Obter data atual
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Data atual do sistema: {data_atual}")

        # Obter o nome do usuário logado da sessão
        user_session = session.get('user')
        nome_usuario = user_session['nome'] if user_session and 'nome' in user_session else 'Usuário Desconhecido'
        print(f"Usuário logado: {nome_usuario}")

        filial_nome = "Depósito Central"
        print(f"Filial: {filial_nome}")

        # Inserir a resposta
        query = """
            INSERT INTO respostas (solicitacao_id, mensagem, data_hora, nome_filial, nome_usuario)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (solicitacao_id, mensagem, data_atual, filial_nome, nome_usuario)
        print(f"Executando query: {query} com parâmetros: {params}")
        cur.execute(query, params)
        conn.commit()

        # Verificar se a inserção foi bem-sucedida
        cur.execute("SELECT * FROM respostas WHERE solicitacao_id = %s AND data_hora = %s", (solicitacao_id, data_atual))
        inserted_resposta = cur.fetchone()
        if not inserted_resposta:
            print("Falha ao verificar a inserção da resposta")
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Falha ao salvar a resposta no banco'}), 500

        print(f"Resposta salva com sucesso para solicitação {solicitacao_id}: {inserted_resposta}")
        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Resposta salva com sucesso'})
    except mysql.connector.Error as sql_error:
        print(f"Erro de banco de dados: {str(sql_error)}")
        return jsonify({'success': False, 'error': f'Erro de banco de dados: {str(sql_error)}'}), 500
    except Exception as e:
        print(f"Erro genérico: {str(e)}")
        return jsonify({'success': False, 'error': f'Erro ao processar: {str(e)}'}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


@app.route('/historico/<solicitacao_id>', methods=['GET'])
def historico(solicitacao_id):
    print(f"Buscando histórico para solicitação {solicitacao_id}")
    try:
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cur = conn.cursor(dictionary=True)
        query = """
            SELECT mensagem, data_hora, nome_filial, nome_usuario
            FROM respostas
            WHERE solicitacao_id = %s
            ORDER BY data_hora ASC
        """
        cur.execute(query, (solicitacao_id,))
        historico = cur.fetchall()
        print(f"Histórico encontrado: {historico}")

        cur.close()
        conn.close()
        return jsonify({'success': True, 'historico': historico})
    except mysql.connector.Error as sql_error:
        print(f"Erro de banco de dados: {str(sql_error)}")
        return jsonify({'success': False, 'error': f'Erro de banco de dados: {str(sql_error)}'}), 500
    except Exception as e:
        print(f"Erro genérico: {str(e)}")
        return jsonify({'success': False, 'error': f'Erro ao processar: {str(e)}'}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()



@app.route('/aprovar_solicitacao/<int:id>', methods=['POST'])
def aprovar_solicitacao(id):
    print(f"Recebida requisição para aprovar solicitação ID: {id}")
    try:
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cur = conn.cursor()

        cur.execute("SELECT id FROM solicitacoes WHERE id = %s", (id,))
        if not cur.fetchone():
            print(f"Solicitação ID {id} não encontrada")
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Solicitação não encontrada'}), 404

        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Data atual: {data_atual}")

        cur.execute("SHOW COLUMNS FROM solicitacoes LIKE 'data_liberacao'")
        data_liberacao_exists = cur.fetchone() is not None
        print(f"Coluna data_liberacao existe: {data_liberacao_exists}")

        # Obter o nome do usuário logado da sessão
        user_session = session.get('user')
        if not user_session or 'nome' not in user_session:
            print("Nenhuma sessão de usuário encontrada ou nome ausente")
            usuario = 'Usuário Desconhecido'
        else:
            usuario = user_session['nome']
        print(f"Usuário logado: {usuario}")

        query = "UPDATE solicitacoes SET status = %s"
        params = ['Aprovada']
        if data_liberacao_exists:
            query += ", data_liberacao = %s"
            params.append(data_atual)
        query += ", usuario_aprovou = %s WHERE id = %s"
        params.extend([usuario, id])

        print(f"Executando query: {query} com parâmetros: {params}")
        cur.execute(query, params)
        conn.commit()
        print(f"Solicitação {id} aprovada com sucesso em {data_atual} por {usuario}")

        cur.execute("SELECT status FROM solicitacoes WHERE id = %s", (id,))
        updated_status = cur.fetchone()[0]
        print(f"Status atualizado verificado: {updated_status}")

        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Solicitação aprovada com sucesso'})
    except mysql.connector.Error as sql_error:
        print(f"Erro de banco de dados ao aprovar solicitação: {str(sql_error)}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'error': f'Erro de banco de dados: {str(sql_error)}'}), 500
    except Exception as e:
        print(f"Erro genérico ao aprovar solicitação: {str(e)}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'error': f'Erro ao processar a solicitação: {str(e)}'}), 500

@app.route('/cancelar_solicitacao/<int:id>', methods=['POST'])
def cancelar_solicitacao(id):
    print(f"Recebida requisição para cancelar solicitação ID: {id}")
    try:
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cur = conn.cursor()

        cur.execute("SELECT id, status FROM solicitacoes WHERE id = %s", (id,))
        solicitacao = cur.fetchone()
        if not solicitacao:
            print(f"Solicitação ID {id} não encontrada")
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Solicitação não encontrada'}), 404

        current_status = solicitacao[1]
        if current_status == 'Cancelada':
            print(f"Solicitação ID {id} já está cancelada")
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Solicitação já está cancelada'}), 400

        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Data atual: {data_atual}")

        cur.execute("SHOW COLUMNS FROM solicitacoes LIKE 'data_liberacao'")
        data_liberacao_exists = cur.fetchone() is not None
        print(f"Coluna data_liberacao existe: {data_liberacao_exists}")

        # Obter o nome do usuário logado da sessão
        user_session = session.get('user')
        if not user_session or 'nome' not in user_session:
            print("Nenhuma sessão de usuário encontrada ou nome ausente")
            usuario = 'Usuário Desconhecido'
        else:
            usuario = user_session['nome']
        print(f"Usuário logado: {usuario}")

        query = "UPDATE solicitacoes SET status = %s"
        params = ['Cancelada']
        if data_liberacao_exists:
            query += ", data_liberacao = %s"
            params.append(data_atual)
        query += ", usuario_aprovou = %s WHERE id = %s"
        params.extend([usuario, id])

        print(f"Executando query: {query} com parâmetros: {params}")
        cur.execute(query, params)
        conn.commit()
        print(f"Solicitação {id} cancelada com sucesso em {data_atual} por {usuario}")

        cur.execute("SELECT status FROM solicitacoes WHERE id = %s", (id,))
        updated_status = cur.fetchone()[0]
        print(f"Status atualizado verificado: {updated_status}")

        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Solicitação cancelada com sucesso'})
    except mysql.connector.Error as sql_error:
        print(f"Erro de banco de dados ao cancelar solicitação: {str(sql_error)}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'error': f'Erro de banco de dados: {str(sql_error)}'}), 500
    except Exception as e:
        print(f"Erro genérico ao cancelar solicitação: {str(e)}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'error': f'Erro ao processar a solicitação: {str(e)}'}), 500







@app.route('/solicitacoes_loja', methods=['GET'])
def solicitacoes_loja():
    print("Acessando rota /solicitacoes_loja")
    filial = request.args.get('filial', '')
    erro = None
    solicitacoes = []
    respostas = []

    try:
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            erro = "Erro ao conectar ao banco de dados"
            return render_template('solicitacoes_loja.html', solicitacoes=[], respostas=[], erro=erro, filial=filial)

        cur = conn.cursor(dictionary=True)
        # Buscar solicitações
        query_solicitacoes = '''
            SELECT s.id, s.numero_solicitacao, s.filial_id, f.filial_nome1 AS filial_nome, s.tipo_solicitacao, s.titulo, s.descricao, 
                   s.quantidade, s.data_hora, s.matricula, s.nome_usuario, s.status
            FROM solicitacoes s
            JOIN filiais f ON s.filial_id = f.filial_id1
            WHERE 1=1
        '''
        params = []

        if filial and filial.isdigit():
            query_solicitacoes += ' AND s.filial_id = %s'
            params.append(filial)

        query_solicitacoes += ' ORDER BY s.data_hora DESC'
        print(f"Executando consulta de solicitações: {query_solicitacoes} com parâmetros: {params}")
        cur.execute(query_solicitacoes, params)
        solicitacoes = cur.fetchall()
        print(f"Solicitações encontradas: {len(solicitacoes)}")
        print(f"Dados das solicitações: {solicitacoes}")

        # Buscar respostas usando solicitacao_id
        query_respostas = '''
            SELECT r.solicitacao_id, r.mensagem, r.data_hora, r.nome_usuario
            FROM respostas r
            WHERE 1=1
        '''
        if filial and filial.isdigit():
            query_respostas += ' AND r.solicitacao_id IN (SELECT id FROM solicitacoes WHERE filial_id = %s)'
            params = [filial]
        else:
            params = []

        query_respostas += ' ORDER BY r.data_hora ASC'
        print(f"Executando consulta de respostas: {query_respostas} com parâmetros: {params}")
        cur.execute(query_respostas, params)
        respostas = cur.fetchall()
        print(f"Respostas encontradas: {len(respostas)}")
        print(f"Dados das respostas: {respostas}")

        cur.close()
        conn.close()
        return render_template('solicitacoes_loja.html', solicitacoes=solicitacoes, respostas=respostas, erro=erro, filial=filial)
    except Exception as e:
        print(f"Erro ao buscar solicitações e respostas: {str(e)}")
        erro = "Ocorreu um erro ao carregar as solicitações e respostas"
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return render_template('solicitacoes_loja.html', solicitacoes=[], respostas=[], erro=erro, filial=filial) 


    

@app.route('/responder_solicitacao/<int:id>', methods=['POST'])
def responder_solicitacao(id):
    print(f"Acessando rota /responder_solicitacao/{id}")
    try:
        data = request.get_json()
        mensagem = data.get('mensagem')  # Ajustado para 'mensagem' para alinhar com o banco

        if not mensagem:
            print("Erro: Mensagem é obrigatória")
            return jsonify({'success': False, 'error': 'Mensagem é obrigatória'}), 400

        conn = get_db_connection()
        if conn is None:
            print("Erro: Falha ao conectar ao banco de dados")
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM solicitacoes WHERE id = %s", (id,))
        solicitacao = cur.fetchone()
        if not solicitacao:
            cur.close()
            conn.close()
            print(f"Erro: Solicitação ID {id} não encontrada")
            return jsonify({'success': False, 'error': 'Solicitação não encontrada'}), 404

        user_session = session.get('user', {})
        nome_usuario = user_session.get('nome', 'Depósito Desconhecido')
        print(f"Usuário da sessão: {nome_usuario}")

        query = '''
            INSERT INTO respostas (solicitacao_id, mensagem, data_hora, nome_usuario)
            VALUES (%s, %s, %s, %s)
        '''
        params = (id, mensagem, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), nome_usuario)
        print(f"Executando query: {query} com parâmetros: {params}")
        cur.execute(query, params)
        conn.commit()

        cur.close()
        conn.close()
        print("Resposta enviada com sucesso")
        return jsonify({'success': True, 'message': 'Resposta enviada com sucesso'})
    except Exception as e:
        print(f"Erro ao responder solicitação: {str(e)}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500





    
@app.route('/atualizar_solicitacao/<int:id>', methods=['POST'])
def atualizar_solicitacao(id):
    print(f"Acessando rota /atualizar_solicitacao/{id}")
    try:
        data = request.get_json()
        titulo = data.get('titulo')
        descricao = data.get('descricao')

        if not all([titulo, descricao]):
            return jsonify({'success': False, 'error': 'Título e descrição são obrigatórios'}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cur = conn.cursor()
        query = '''
            UPDATE solicitacoes SET titulo = %s, descricao = %s WHERE id = %s
        '''
        params = (titulo, descricao, id)
        print(f"Executando query: {query} com parâmetros: {params}")
        cur.execute(query, params)
        conn.commit()

        if cur.rowcount == 0:
            return jsonify({'success': False, 'error': 'Solicitação não encontrada'}), 404

        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Solicitação atualizada com sucesso'})
    except Exception as e:
        print(f"Erro ao atualizar solicitação: {str(e)}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/criar_solicitacao', methods=['POST'])
def criar_solicitacao():
    print("Acessando rota /criar_solicitacao")
    try:
        data = request.get_json()
        filial_id = data.get('filial_id')
        tipo_solicitacao = data.get('tipo_solicitacao')
        quantidade = data.get('quantidade')
        titulo = data.get('titulo')
        descricao = data.get('descricao')

        if not all([filial_id, tipo_solicitacao, quantidade, titulo, descricao]):
            return jsonify({'success': False, 'error': 'Todos os campos são obrigatórios'}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cur = conn.cursor()
        cur.execute("SELECT MAX(numero_solicitacao) FROM solicitacoes")
        max_numero = cur.fetchone()[0]
        numero_solicitacao = str(int(max_numero) + 1) if max_numero else '1'

        user_session = session.get('user', {})
        matricula = user_session.get('matricula', '12345')
        nome_usuario = user_session.get('nome', 'Usuário Teste')

        query = '''
            INSERT INTO solicitacoes (numero_solicitacao, filial_id, tipo_solicitacao, titulo, descricao, quantidade, data_hora, matricula, nome_usuario, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        params = (
            numero_solicitacao,
            filial_id,
            tipo_solicitacao,
            titulo,
            descricao,
            quantidade,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            matricula,
            nome_usuario,
            'Pendente'
        )
        print(f"Executando query: {query} com parâmetros: {params}")
        cur.execute(query, params)
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Solicitação criada com sucesso', 'numero_solicitacao': numero_solicitacao})
    except Exception as e:
        print(f"Erro ao criar solicitação: {str(e)}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500












@app.route('/consultas_avancadas')
@login_required
def consultas_avancadas_page():
    print("Acessando rota /consultas_avancadas/page")
    return render_template('consultas_avancadas.html')


@app.route('/consultas_avancadas/dados')
@login_required
def consultas_avancadas_dados():
    grupo = request.args.get('grupo')
    fornecedor = request.args.get('fornecedor')
    codigoBarra = request.args.get('codigoBarra')
    comSaldo = request.args.get('comSaldo', 'false') == 'true'
    semSaldo = request.args.get('semSaldo', 'false') == 'true'

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        query = 'SELECT * FROM produtos'
        params = []
        conditions = []

        if grupo:
            conditions.append('grupo = %s')
            params.append(grupo)
        if fornecedor:
            conditions.append('nu_fornecedor= %s')
            params.append(fornecedor)
        if codigoBarra:
            conditions.append('(codigo = %s OR barras = %s)')
            params.extend([codigoBarra, codigoBarra])
        if comSaldo and not semSaldo:
            conditions.append('saldo > 0')
        elif semSaldo and not comSaldo:
            conditions.append('saldo = 0')

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
            

        print(f"Executando consulta: {query} com parâmetros: {params}")
        cur.execute(query, params)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(data)
    except mysql.connector.Error as db_err:
        print(f"Erro no banco de dados: {db_err}")
        return jsonify({'error': 'Erro ao carregar consultas'}), 500

    return jsonify({'error': 'Erro ao carregar filtros'}), 500

@app.route('/consultas_avancadas/filtros')
@login_required
def consultas_avancadas_filtros():
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Modifique esta query para ordenar por nome_fantasia
        query = """
        SELECT DISTINCT nu_fornecedor, nome_fantasia, grupo 
        FROM produtos 
        WHERE nome_fantasia IS NOT NULL 
        ORDER BY nome_fantasia ASC
        """
        
        cur.execute(query)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(data)
    except Exception as e:
        print(f"Erro: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/credito_debito')
@login_required
def credito_debito():
    print("Acessando rota /credito_debito")
    try:
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            return render_template('credito_debito.html', usuarios=[], total_pedidos=0, total_skus=0,
                                   pedidos_com_divergencia=0, pedidos_sem_divergencia=0, total_a_pagar=0.0)

        cur = conn.cursor(dictionary=True)

        # Buscar separadores e conferentes únicos com contagem de pedidos
        query_usuarios = '''
            SELECT 
                separador AS nome, 
                'Separador' AS tipo,
                COUNT(DISTINCT numero_pedido) AS total_pedidos,
                0 AS percentual_acertos
            FROM conferencia
            WHERE separador IS NOT NULL AND status != 'EM CONFERENCIA'
            GROUP BY separador
            
            UNION
            
            SELECT 
                conferente AS nome, 
                'Conferente' AS tipo,
                COUNT(DISTINCT numero_pedido) AS total_pedidos,
                0 AS percentual_acertos
            FROM conferencia
            WHERE conferente IS NOT NULL AND status != 'EM CONFERENCIA'
            GROUP BY conferente
        '''
        cur.execute(query_usuarios)
        usuarios = cur.fetchall()

        # Calcular métricas detalhadas para cada usuário
        for usuario in usuarios:
            nome = usuario['nome']
            tipo = usuario['tipo']
            coluna = 'separador' if tipo == 'Separador' else 'conferente'

            # Buscar todos os pedidos do usuário
            query_pedidos = f'''
                SELECT DISTINCT numero_pedido, status
                FROM conferencia
                WHERE {coluna} = %s AND status != 'EM CONFERENCIA'
            '''
            cur.execute(query_pedidos, (nome,))
            pedidos = cur.fetchall()

            total_credito = 0
            total_debito = 0
            pedidos_ok = 0
            total_itens = 0
            itens_ok = 0

            # Inicializar contadores de divergências para o usuário
            usuario['pedidos_com_divergencia'] = 0
            usuario['pedidos_sem_divergencia'] = 0

            # Calcular pedidos com e sem divergência usando a coluna 'divergencia'
            query_divergencias_usuario = f'''
                SELECT 
                    numero_pedido,
                    MAX(divergencia) as tem_divergencia
                FROM conferencia
                WHERE {coluna} = %s AND status != 'EM CONFERENCIA'
                GROUP BY numero_pedido
            '''
            cur.execute(query_divergencias_usuario, (nome,))
            resultados_usuario = cur.fetchall()

            usuario['pedidos_com_divergencia'] = sum(
                1 for r in resultados_usuario if r['tem_divergencia'] > 0)
            usuario['pedidos_sem_divergencia'] = sum(
                1 for r in resultados_usuario if r['tem_divergencia'] == 0)

            for pedido in pedidos:
                numero_pedido = pedido['numero_pedido']

                # Buscar itens do pedido
                query_itens = '''
                    SELECT 
                        quantidade_pedida, 
                        COALESCE(quantidade_conferida, 0) as quantidade_conferida,
                        divergencia
                    FROM conferencia
                    WHERE numero_pedido = %s
                '''
                cur.execute(query_itens, (numero_pedido,))
                itens = cur.fetchall()

                # Contar total de itens (independente do tipo de usuário)
                total_itens += len(itens)

                # Verificar pedidos para separadores
                if tipo == 'Separador':
                    pedido_ok = all(
                        item['quantidade_pedida'] == item['quantidade_conferida'] for item in itens)
                    if pedido_ok:
                        total_credito += 10.0  # R$ 10 por pedido OK
                        pedidos_ok += 1
                    else:
                        total_debito += 10.0  # R$ 10 por pedido com divergência

                # Verificar itens para conferentes
                if tipo == 'Conferente':
                    divergencias_valor = 0
                    for item in itens:
                        if item['quantidade_pedida'] == item['quantidade_conferida']:
                            itens_ok += 1
                        else:
                            divergencia = item['quantidade_conferida'] - \
                                item['quantidade_pedida']
                            divergencias_valor += abs(divergencia)

                    total_credito += divergencias_valor * 1.0  # R$ 1 por unidade de divergência

            # Calcular percentual de acertos
            if tipo == 'Separador' and usuario['total_pedidos'] > 0:
                usuario['percentual_acertos'] = round(
                    (pedidos_ok / usuario['total_pedidos']) * 100, 2)
            elif tipo == 'Conferente' and total_itens > 0:
                usuario['percentual_acertos'] = round(
                    (itens_ok / total_itens) * 100, 2)

            usuario['credito'] = round(total_credito, 2)
            usuario['debito'] = round(total_debito, 2)
            usuario['saldo'] = round(total_credito - total_debito, 2)

            # Adicionar métricas específicas
            if tipo == 'Separador':
                # Simplificação
                usuario['pedidos_30dias'] = usuario['total_pedidos']
                usuario['skus_separados'] = total_itens
                usuario['total_skus'] = total_itens
            else:
                usuario['pedidos_conferidos'] = usuario['total_pedidos']
                usuario['total_skus'] = total_itens

        # Calcular totais gerais
        query_totais = '''
            SELECT 
                COUNT(DISTINCT numero_pedido) as total_pedidos,
                COUNT(*) as total_skus,
                SUM(CASE WHEN divergencia > 0 THEN 1 ELSE 0 END) as total_divergencias
            FROM conferencia
            WHERE status != 'EM CONFERENCIA'
        '''
        cur.execute(query_totais)
        totais = cur.fetchone()

        total_pedidos = totais['total_pedidos'] if totais else 0
        total_skus = totais['total_skus'] if totais else 0

        # Pedidos com/sem divergência (global)
        query_divergencias = '''
            SELECT 
                numero_pedido,
                MAX(divergencia) as tem_divergencia
            FROM conferencia
            WHERE status != 'EM CONFERENCIA'
            GROUP BY numero_pedido
        '''
        cur.execute(query_divergencias)
        resultados = cur.fetchall()

        pedidos_com_divergencia = sum(
            1 for r in resultados if r['tem_divergencia'] > 0)
        pedidos_sem_divergencia = sum(
            1 for r in resultados if r['tem_divergencia'] == 0)

        # Total a pagar (soma dos saldos positivos)
        total_a_pagar = round(
            sum(usuario['saldo'] for usuario in usuarios if usuario['saldo'] > 0), 2)

        cur.close()
        conn.close()

        print("Dados processados:", {
            "usuarios": usuarios,
            "totais": {
                "pedidos": total_pedidos,
                "skus": total_skus,
                "divergencias": pedidos_com_divergencia,
                "sem_divergencias": pedidos_sem_divergencia,
                "total_pagar": total_a_pagar
            }
        })

        return render_template('credito_debito.html',
                               usuarios=usuarios,
                               total_pedidos=total_pedidos,
                               total_skus=total_skus,
                               pedidos_com_divergencia=pedidos_com_divergencia,
                               pedidos_sem_divergencia=pedidos_sem_divergencia,
                               total_a_pagar=total_a_pagar)

    except Exception as e:
        print(f"Erro ao processar dados: {str(e)}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return render_template('credito_debito.html', usuarios=[], total_pedidos=0, total_skus=0,
                               pedidos_com_divergencia=0, pedidos_sem_divergencia=0, total_a_pagar=0.0)


@app.route('/atualizar_dados')
@login_required
def atualizar_dados():
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500

        cur = conn.cursor(dictionary=True)

        # Busca apenas os dados necessários para atualização
        query = '''
            SELECT 
                conferente as nome, 
                'Conferente' as tipo,
                COUNT(DISTINCT numero_pedido) as total_pedidos
            FROM conferencia
            WHERE conferente IS NOT NULL AND status != 'EM CONFERENCIA'
            GROUP BY conferente
            UNION
            SELECT 
                separador as nome,
                'Separador' as tipo,
                COUNT(DISTINCT numero_pedido) as total_pedidos
            FROM conferencia
            WHERE separador IS NOT NULL AND status != 'EM CONFERENCIA'
            GROUP BY separador
        '''
        cur.execute(query)
        usuarios = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({"usuarios": usuarios})
    except Exception as e:
        print(f"Erro ao atualizar dados: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/separador')
@login_required
def separador():
    print("Acessando rota /separador")
    try:
        conn = get_db_connection()
        if conn is None:
            print(
                "Falha na conexão com o banco de dados - Verifique as credenciais e o servidor MySQL")
            return render_template('separador.html', pedidos=[])

        # Verificar a estrutura da tabela para depuração
        cur = conn.cursor()
        cur.execute("DESCRIBE conferencia")
        columns = [row[0] for row in cur.fetchall()]
        print("Colunas da tabela conferencia:", columns)

        # Verificar se há dados na tabela
        cur.execute("SELECT COUNT(*) FROM conferencia")
        row_count = cur.fetchone()[0]
        print("Número de registros na tabela conferencia:", row_count)

        cur = conn.cursor(dictionary=True)
        query = '''
            
            SELECT DISTINCT numero_pedido, status, separador, lojas_tag
FROM conferencia
ORDER BY numero_pedido ASC
        '''
        print("Executando consulta SQL:", query)
        cur.execute(query)
        pedidos = cur.fetchall()
        print("Número de registros retornados:", len(pedidos))
        print("Dados retornados:", pedidos)
        cur.close()
        conn.close()
        return render_template('separador.html', pedidos=pedidos)
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return render_template('separador.html', pedidos=[])


@app.route('/detalhe_pedidos', methods=['GET'])
@login_required
def detalhe_pedidos():
    numero_pedido = request.args.get('numero_pedido')
    print(f"Acessando rota /detalhe_pedidos com numero_pedido={numero_pedido}")
    if not numero_pedido:
        print("Número do pedido não fornecido")
        return render_template('detalhe_pedidos.html', numero_pedido=None, itens=[])

    try:
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            return render_template('detalhe_pedidos.html', numero_pedido=numero_pedido, itens=[])

        cur = conn.cursor(dictionary=True)
        query = '''
            SELECT id, numero_pedido, codigo, descricao, quantidade_pedida, quantidade_conferida, divergencia
            FROM conferencia
            WHERE numero_pedido = %s
        '''
        print("Executando consulta SQL:", query,
              "com número do pedido:", numero_pedido)
        cur.execute(query, (numero_pedido,))
        itens = cur.fetchall()
        print("Itens retornados:", itens)
        cur.close()
        conn.close()
        return render_template('detalhe_pedidos.html', numero_pedido=numero_pedido, itens=itens)
    except Exception as e:
        print(f"Erro ao buscar itens: {e}")
        return render_template('detalhe_pedidos.html', numero_pedido=numero_pedido, itens=[])


# @app.route('/separador')
# def separador():
#     return render_template('separador.html')

@app.route('/suporte_logistico')
def suporte_logistico():
    return render_template('suporte_logistico.html')

# Rota para a página de conferência


@app.route('/conferencia')
@login_required
def conferencia_page():
    print("Acessando rota /conferencia")
    try:
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            return render_template('Conferencia.html', dados=[])

        cur = conn.cursor(dictionary=True)
        query = '''
            SELECT id, numero_pedido, codigo, codigo_barras, descricao, unidade, 
                   quantidade_pedida, quantidade_conferida, divergencia, corretor, 
                   credito, debito, caixa, operador_fechou_caixa, status, data_hora, 
                   conferente, separador, status_grupo 
            FROM conferencia
            ORDER BY numero_pedido ASC
        '''
        print("Executando consulta SQL:", query)
        cur.execute(query)
        dados = cur.fetchall()
        print("Número de registros retornados:", len(dados))
        print("Dados retornados:", dados)
        cur.close()
        conn.close()
        return render_template('Conferencia.html', dados=dados)
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return render_template('Conferencia.html', dados=[])


@app.route('/conferencia/buscar', methods=['POST'])
@login_required
def buscar_conferencia():
    numero_pedido = request.form.get('numero_pedido')
    print("Buscando por número de pedido:", numero_pedido)
    try:
        conn = get_db_connection()
        if conn is None:
            print("Falha na conexão com o banco de dados")
            return render_template('Conferencia.html', dados=[])

        cur = conn.cursor(dictionary=True)
        query = '''
            SELECT id, numero_pedido, codigo, codigo_barras, descricao, unidade, 
                   quantidade_pedida, quantidade_conferida, divergencia, corretor, 
                   credito, debito, caixa, operador_fechou_caixa, status, data_hora, 
                   conferente, separador, status_grupo 
            FROM conferencia
            WHERE numero_pedido = %s
            ORDER BY numero_pedido ASC
        '''
        cur.execute(query, (numero_pedido,))
        dados = cur.fetchall()
        print("Resultados da busca:", dados)
        cur.close()
        conn.close()
        return render_template('Conferencia.html', dados=dados)
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return render_template('Conferencia.html', dados=[])


@app.route('/produto/<codigo>', methods=['GET'])
@login_required
def get_produto(codigo):
    print(f"Recebendo requisição GET para /produto/{codigo}")
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        print(f"Buscando produto com código: {codigo}")
        cur.execute(
            'SELECT codigo, descricao, saldo, barras, localizacao1, localizacao2, grupo, nome_fantasia, nu_fornecedor FROM produtos WHERE codigo = %s OR barras = %s',
            (codigo, codigo)
        )
        produto = cur.fetchone()
        if not produto:
            print(
                f"Produto não encontrado. Inserindo novo produto com código: {codigo}")
            cur.execute(
                'INSERT INTO produtos (codigo, barras, descricao, saldo, localizacao1, localizacao2, grupo, nome_fantasia, nu_fornecedor) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                (codigo, None, 'Produto Exemplo - Descrição Padrão',
                 10, 'N/A', 'N/A', '1', 'N/A')
            )
            conn.commit()
            cur.execute(
                'SELECT codigo, descricao, saldo, barras, localizacao1, localizacao2, grupo, nome_fantasia, nu_fornecedor FROM produtos WHERE codigo = %s',
                (codigo,)
            )
            produto = cur.fetchone()
        print(f"Produto encontrado: {produto}")
        cur.close()
        conn.close()
        return jsonify(produto)
    except Exception as e:
        cur.close()
        conn.close()
        print(f"Erro ao buscar produto: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/ajustar-estoque-automatico', methods=['POST'])
def ajustar_estoque_automatico():
    print("Recebendo requisição POST para /ajustar-estoque-automatico")

    if 'user' not in session:
        return jsonify({'error': 'Usuário não está logado'}), 401

    user = session['user']
    if 'matricula' not in user or 'nome' not in user:
        return jsonify({'error': 'Dados do usuário na sessão estão incompletos'}), 500

    matricula = user['matricula']
    nome_usuario = user['nome']

    data = request.get_json()
    numero_ajuste = data.get('numero_ajuste')
    codigo_produto = data.get('codigo_produto')
    quantidade = data.get('quantidade')
    ajuste_menos = data.get('ajuste_menos', False)

    if not codigo_produto:
        return jsonify({'error': 'Código do produto é obrigatório'}), 400

    if not numero_ajuste:
        return jsonify({'error': 'Número do ajuste é obrigatório'}), 400

    try:
        numero_ajuste = int(numero_ajuste)
    except (ValueError, TypeError):
        return jsonify({'error': 'Número do ajuste deve ser um número inteiro'}), 400

    try:
        quantidade = int(quantidade) if quantidade is not None else 0
    except (ValueError, TypeError):
        quantidade = 0

    if quantidade == 0:
        quantidade = -1 if ajuste_menos else 1

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Verificar a última atualização do ajuste pendente (para evitar duplicatas)
        cur.execute('''
            SELECT data FROM ajustes 
            WHERE numero_ajuste = %s AND codigo_produto = %s AND TRIM(UPPER(status)) = %s LIMIT 1
        ''', (numero_ajuste, codigo_produto, 'PENDENTE'))
        ajuste = cur.fetchone()

        if ajuste:
            ultima_atualizacao = ajuste[0]
            from datetime import datetime, timedelta
            if ultima_atualizacao and (datetime.now() - ultima_atualizacao) < timedelta(milliseconds=500):
                print(
                    f"Ajuste ignorado - atualização recente detectada para numero_ajuste={numero_ajuste}, codigo_produto={codigo_produto}")
                cur.close()
                conn.close()
                return jsonify({'message': 'Ajuste ignorado - atualização recente detectada'}), 200

        # Buscar o produto
        cur.execute('''
            SELECT saldo, descricao FROM produtos 
            WHERE codigo = %s OR barras = %s LIMIT 1
        ''', (codigo_produto, codigo_produto))
        produto = cur.fetchone()

        if not produto:
            cur.close()
            conn.close()
            return jsonify({'error': 'Produto não encontrado'}), 404

        saldo = produto[0]
        descricao = produto[1]

        novo_saldo = saldo + quantidade

        # Atualizar o saldo do produto
        cur.execute('''
            UPDATE produtos SET saldo = %s 
            WHERE codigo = %s OR barras = %s
        ''', (novo_saldo, codigo_produto, codigo_produto))

        # Verificar se o ajuste pendente existe
        cur.execute('''
            SELECT quantidade FROM ajustes 
            WHERE numero_ajuste = %s AND codigo_produto = %s AND TRIM(UPPER(status)) = %s LIMIT 1
        ''', (numero_ajuste, codigo_produto, 'PENDENTE'))
        ajuste = cur.fetchone()

        if not ajuste:
            cur.close()
            conn.close()
            return jsonify({'error': 'Ajuste pendente não encontrado para o número e código do produto fornecidos'}), 404

        nova_quantidade = ajuste[0] + quantidade
        cur.execute('''
            UPDATE ajustes 
            SET quantidade = %s, matricula = %s, nome_usuario = %s, data = NOW()
            WHERE numero_ajuste = %s AND codigo_produto = %s AND TRIM(UPPER(status)) = %s
        ''', (nova_quantidade, matricula, nome_usuario, numero_ajuste, codigo_produto, 'PENDENTE'))

        conn.commit()
        cur.close()
        conn.close()
        print(
            f"Ajuste atualizado com sucesso: numero_ajuste={numero_ajuste}, codigo_produto={codigo_produto}, nova_quantidade={nova_quantidade}")
        return jsonify({
            'message': 'Ajuste pendente atualizado com sucesso',
            'saldo': novo_saldo,
            'codigo_produto': codigo_produto,
            'descricao': descricao,
            'quantidade': nova_quantidade,
            'numero_ajuste': numero_ajuste
        }), 200
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print(f"Erro ao ajustar estoque automaticamente: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/ajustar-estoque', methods=['POST'])
@login_required
def ajustar_estoque():
    try:
        data = request.get_json()
        ajustes = data.get('ajustes')

        if not ajustes:
            return jsonify({'error': 'Nenhum ajuste fornecido'}), 400

        if 'matricula' not in session['user'] or 'nome' not in session['user']:
            return jsonify({'error': 'Dados do usuário na sessão estão incompletos'}), 500

        matricula = session['user']['matricula']
        nome_usuario = session['user']['nome']

        conn = get_db_connection()
        cur = conn.cursor()
        resultados = []

        for ajuste in ajustes:
            numero_ajuste = ajuste.get('numero_ajuste')
            codigo = ajuste.get('codigo')
            quantidade = ajuste.get('quantidade')

            if (numero_ajuste is None or str(numero_ajuste).strip() == '' or
                codigo is None or str(codigo).strip() == '' or
                    quantidade is None):
                return jsonify({'error': 'Número do ajuste, código e quantidade são obrigatórios'}), 400

            try:
                quantidade = int(quantidade)
            except (ValueError, TypeError):
                return jsonify({'error': 'Quantidade deve ser um número inteiro'}), 400

            cur.execute(
                "SELECT saldo FROM produtos WHERE codigo = %s", (codigo,))
            produto = cur.fetchone()
            if not produto:
                return jsonify({'error': f'Produto com código {codigo} não encontrado'}), 404

            novo_saldo = produto[0] + quantidade
            cur.execute(
                "UPDATE produtos SET saldo = %s WHERE codigo = %s", (novo_saldo, codigo))
            cur.execute("""
                INSERT INTO ajustes (numero_ajuste, produto_codigo, descricao, ajuste, data_hora, matricula, nome_usuario)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (numero_ajuste, codigo, ajuste.get('descricao'), quantidade, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), matricula, nome_usuario))
            # cur.execute(
            #     "DELETE FROM ajustes_pendentes WHERE numero_ajuste = %s AND codigo_produto = %s", (numero_ajuste, codigo))
            # resultados.append({'codigo': codigo, 'saldo': novo_saldo})

        conn.commit()
        return jsonify({'success': True, 'numero_ajuste': numero_ajuste, 'resultados': resultados})
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Erro ao ajustar estoque: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/adicionar-ajuste-pendente', methods=['POST'])
@login_required
def adicionar_ajuste_pendente():
    try:
        data = request.get_json()
        print("Dados recebidos:", data)  # Log para depuração

        numero_ajuste = data.get('numero_ajuste')
        codigo = data.get('codigo')
        descricao = data.get('descricao')
        quantidade = data.get('quantidade')

        if (numero_ajuste is None or str(numero_ajuste).strip() == '' or
            codigo is None or str(codigo).strip() == '' or
                quantidade is None):
            return jsonify({'error': 'Número do ajuste, código e quantidade são obrigatórios'}), 400

        try:
            numero_ajuste = int(numero_ajuste)
            quantidade = int(quantidade)
        except (ValueError, TypeError):
            return jsonify({'error': 'Número do ajuste e quantidade devem ser números inteiros'}), 400

        if quantidade == 0:
            return jsonify({'error': 'Quantidade deve ser diferente de zero'}), 400

        if 'matricula' not in session['user'] or 'nome' not in session['user']:
            return jsonify({'error': 'Dados do usuário na sessão estão incompletos'}), 500

        matricula = session['user']['matricula']
        nome_usuario = session['user']['nome']
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Verifica se já existe um ajuste pendente com o mesmo numero_ajuste e codigo_produto
        cur.execute("""
            SELECT id, quantidade FROM ajustes 
            WHERE numero_ajuste = %s AND codigo_produto = %s AND status = 'PENDENTE'
        """, (numero_ajuste, codigo))
        existing_ajuste = cur.fetchone()
        print("Ajuste existente:", existing_ajuste)

        if existing_ajuste:
            # Se existe, atualiza a quantidade somando
            nova_quantidade = existing_ajuste['quantidade'] + quantidade
            cur.execute("""
                UPDATE ajustes 
                SET quantidade = %s, data = %s, matricula = %s, nome_usuario = %s
                WHERE id = %s
            """, (nova_quantidade, data_atual, matricula, nome_usuario, existing_ajuste['id']))
            message = f"Quantidade atualizada! Nova quantidade: {nova_quantidade}"
        else:
            # Se não existe, insere um novo ajuste
            cur.execute("""
                INSERT INTO ajustes (numero_ajuste, codigo_produto, descricao, quantidade, matricula, nome_usuario, data, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDENTE')
            """, (numero_ajuste, codigo, descricao, quantidade, matricula, nome_usuario, data_atual))
            message = f"Ajuste criado com sucesso! Quantidade: {quantidade}"

        conn.commit()
        print("Ajuste gravado com sucesso")
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Erro ao adicionar ajuste pendente: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

            # Rota para a página de monitoramento de fornecedores


@app.route('/monitoramento_fornecedores')
@login_required
def monitoramento_fornecedores():
    print("Acessando rota /monitoramento_fornecedores")
    return render_template('monitoramento_fornecedores.html')

# Rota para buscar dados do dashboard


@app.route('/dados_monitoramento_fornecedores', methods=['GET'])
@login_required
def dados_monitoramento_fornecedores():
    print("Acessando rota /dados_monitoramento_fornecedores")
    try:
        # Obtém o parâmetro de filtro
        filtro = request.args.get('filtro', '').strip()
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Condição de filtro para as consultas
        filtro_condition = ""
        filtro_param = None
        if filtro:
            if filtro.isdigit():  # Se for um número, busca por nu_fornecedor (número do fornecedor)
                filtro_condition = " WHERE p.nu_fornecedor = %s"
                filtro_param = filtro  # Mantém como string para compatibilidade com nu_fornecedor
            else:  # Se for texto, busca por nome_fantasia (nome do fornecedor)
                filtro_condition = " WHERE p.nome_fantasia COLLATE utf8mb4_0900_ai_ci LIKE %s COLLATE utf8mb4_0900_ai_ci"
                filtro_param = f"%{filtro}%"
            print(f"Filtro aplicado: {filtro_param}")  # Log para depuração

        # 1. Estoque total por fornecedor
        query_estoque = f'''
            SELECT p.nu_fornecedor AS fornecedor, SUM(p.saldo) as estoque_total
            FROM produtos p
            {filtro_condition}
            GROUP BY p.nu_fornecedor
            HAVING estoque_total > 0
            ORDER BY estoque_total DESC
        '''
        if filtro:
            cur.execute(query_estoque, (filtro_param,))
        else:
            cur.execute(query_estoque)
        estoque_fornecedores = cur.fetchall()
        # Log dos resultados
        print(f"Resultados estoque: {estoque_fornecedores}")

        # 2. Item que mais sai (baseado na tabela conferencia, considerando quantidade_pedida)
        query_item_mais_sai = f'''
            SELECT p.codigo, p.descricao, p.nu_fornecedor, SUM(c.quantidade_pedida) as total_saida
            FROM conferencia c
            JOIN produtos p ON c.codigo COLLATE utf8mb4_0900_ai_ci = p.codigo COLLATE utf8mb4_0900_ai_ci
            {filtro_condition}
            GROUP BY p.codigo, p.descricao, p.nu_fornecedor
            ORDER BY total_saida DESC
            LIMIT 1
        '''
        if filtro:
            cur.execute(query_item_mais_sai, (filtro_param,))
        else:
            cur.execute(query_item_mais_sai)
        item_mais_sai = cur.fetchone()
        # Log dos resultados
        print(f"Resultado item mais sai: {item_mais_sai}")

        # 3. Itens com saldo baixo (saldo < 11)
        saldo_baixo_condition = " p.saldo < 11 AND p.saldo > 0"
        where_clause = f" WHERE {saldo_baixo_condition}" if not filtro else f"{filtro_condition} AND {saldo_baixo_condition}"
        query_itens_saldo_baixo = f'''
            SELECT p.codigo, p.descricao, p.nu_fornecedor, p.saldo
            FROM produtos p
            {where_clause}
            ORDER BY p.saldo ASC
        '''
        if filtro:
            cur.execute(query_itens_saldo_baixo, (filtro_param,))
        else:
            cur.execute(query_itens_saldo_baixo)
        itens_saldo_baixo = cur.fetchall()
        # Log dos resultados
        print(f"Resultados saldo baixo: {itens_saldo_baixo}")

        cur.close()
        conn.close()

        return jsonify({
            'estoque_fornecedores': estoque_fornecedores,
            'item_mais_sai': item_mais_sai,
            'itens_saldo_baixo': itens_saldo_baixo
        })
    except Exception as e:
        print(f"Erro ao buscar dados de monitoramento: {str(e)}")
        return jsonify({'error': str(e)}), 500
    

# Nova rota para sugestões de autocompletar


@app.route('/sugestoes_fornecedores', methods=['GET'])
@login_required
def sugestoes_fornecedores():
    try:
        termo = request.args.get('termo', '').strip()
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        query = '''
            SELECT DISTINCT nu_fornecedor, nome_fantasia
            FROM produtos 
            WHERE nu_fornecedor LIKE %s OR nome_fantasia LIKE %s
            LIMIT 10
        '''
        cur.execute(query, (f"%{termo}%", f"%{termo}%"))
        sugestoes = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{'nu_fornecedor': s['nu_fornecedor'], 'nome_fantasia': s['nome_fantasia']} for s in sugestoes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/ultimo-ajuste-usuario', methods=['GET'])
@login_required
def get_ultimo_ajuste_usuario():
    try:
        matricula = session['user']['matricula']
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        query = '''
            SELECT numero_ajuste
            FROM ajustes
            WHERE matricula = %s AND TRIM(UPPER(status)) = %s
            ORDER BY numero_ajuste DESC
            LIMIT 1
        '''
        cur.execute(query, (matricula, 'PENDENTE'))
        ajuste = cur.fetchone()

        cur.close()
        conn.close()

        if ajuste:
            return jsonify({'ultimo_ajuste': ajuste['numero_ajuste']})
        else:
            return jsonify({'ultimo_ajuste': None})
    except Exception as e:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        print(f"Erro ao buscar último ajuste: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/proximo-numero-ajuste', methods=['GET'])
@login_required
def proximo_numero_ajuste():
    print("Recebendo requisição GET para /proximo-numero-ajuste")
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Obtém o próximo numero_ajuste
        print("Executando query para obter o próximo número de ajuste...")
        cur.execute(
            'SELECT COALESCE(MAX(numero_ajuste), 0) + 1 as next_numero_ajuste FROM ajustes')
        result = cur.fetchone()
        print(f"Resultado da query: {result}")

        if not result or 'next_numero_ajuste' not in result:
            print("Erro: Não foi possível obter o próximo número de ajuste.")
            return jsonify({'error': 'Não foi possível obter o próximo número de ajuste', 'success': False}), 500

        numero_ajuste = result['next_numero_ajuste']
        print(f"Número de ajuste gerado: {numero_ajuste}")

        # Obtém dados do usuário da sessão
        matricula = session['user']['matricula']
        nome_usuario = session['user']['nome']
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Insere um registro inicial na tabela ajustes
        cur.execute("""
            INSERT INTO ajustes (numero_ajuste, matricula, nome_usuario, data, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (numero_ajuste, matricula, nome_usuario, data_atual, 'PENDENTE'))
        conn.commit()

        print(
            f"Registro inicial do ajuste {numero_ajuste} inserido com sucesso para matrícula {matricula}")

        cur.close()
        conn.close()
        return jsonify({'numero_ajuste': numero_ajuste, 'success': True})
    except mysql.connector.Error as db_err:
        conn.rollback()
        cur.close()
        conn.close()
        print(
            f"Erro no banco de dados ao obter próximo número de ajuste: {db_err}")
        return jsonify({'error': f'Erro no banco de dados: {str(db_err)}', 'success': False}), 500
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print(f"Erro ao obter próximo número de ajuste: {e}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/liberar-ajustes', methods=['GET'])
@login_required
def liberar_ajustes_page():
    print("Acessando rota /liberar-ajustes")
    return render_template('liberar_ajustes.html')


@app.route('/cancelar-ajuste/<int:numero_ajuste>', methods=['POST'])
@login_required
def cancelar_ajuste(numero_ajuste):
    print(f"Recebendo requisição POST para /cancelar-ajuste/{numero_ajuste}")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Verificar se o ajuste existe e está pendente
        cur.execute('''
            SELECT status FROM ajustes
            WHERE numero_ajuste = %s AND TRIM(UPPER(status)) = %s
            LIMIT 1
        ''', (numero_ajuste, 'PENDENTE'))
        ajuste = cur.fetchone()

        if not ajuste:
            cur.close()
            conn.close()
            return jsonify({'error': 'Ajuste não encontrado ou não está pendente'}), 404

        # Atualizar o status para "Cancelado"
        cur.execute('''
            UPDATE ajustes
            SET status = %s
            WHERE numero_ajuste = %s
        ''', ('CANCELADO', numero_ajuste))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({'message': 'Ajuste cancelado com sucesso'}), 200
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print(f"Erro ao cancelar ajuste: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/ajustes-pendentes', methods=['GET'])
@login_required
def get_ajustes_pendentes():
    print("Recebendo requisição GET para /ajustes-pendentes")
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute('''
            SELECT numero_ajuste, MAX(data) AS data,
                   (SELECT matricula FROM ajustes a2 
                    WHERE a2.numero_ajuste = a1.numero_ajuste 
                    AND TRIM(UPPER(a2.status)) = %s 
                    LIMIT 1) AS matricula,
                   (SELECT nome_usuario FROM ajustes a2 
                    WHERE a2.numero_ajuste = a1.numero_ajuste 
                    AND TRIM(UPPER(a2.status)) = %s 
                    LIMIT 1) AS nome_usuario
            FROM ajustes a1
            WHERE TRIM(UPPER(status)) = %s
            GROUP BY numero_ajuste
            ORDER BY numero_ajuste DESC
        ''', ('PENDENTE', 'PENDENTE', 'PENDENTE'))
        ajustes = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{
            'numero_ajuste': item['numero_ajuste'],
            'data_hora': item['data'].strftime('%d/%m/%Y - %H:%M') if item['data'] else 'N/A',
            'matricula': item['matricula'],
            'nome_usuario': item['nome_usuario']
        } for item in ajustes])
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/ajustes-pendentes/<numero_ajuste>', methods=['GET'])
@login_required
def get_ajustes_pendentes_by_numero(numero_ajuste):
    print(f"Recebendo requisição GET para /ajustes-pendentes/{numero_ajuste}")
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute('''
            SELECT numero_ajuste, codigo_produto AS codigo, descricao, quantidade, status
            FROM ajustes
            WHERE numero_ajuste = %s AND TRIM(UPPER(status)) = %s
        ''', (numero_ajuste, 'PENDENTE'))
        ajustes = cur.fetchall()

        print(
            f"Ajustes encontrados para numero_ajuste {numero_ajuste}: {ajustes}")
        cur.close()
        conn.close()
        return jsonify(ajustes)
    except Exception as e:
        cur.close()
        conn.close()
        print(f"Erro ao buscar ajustes pendentes: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/liberar-ajuste/<numero_ajuste>', methods=['POST'])
@login_required
def liberar_ajuste(numero_ajuste):
    print(f"Recebendo requisição POST para /liberar-ajuste/{numero_ajuste}")
    if 'user' not in session or 'nome' not in session['user']:
        print("Erro: Usuário não autenticado na sessão.")
        return jsonify({'error': 'Usuário não autenticado. Faça login novamente.'}), 401

    usuario_liberou = session['user']['nome']
    print(f"Usuário que está liberando: {usuario_liberou}")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) FROM ajustes WHERE numero_ajuste = %s AND status = 'PENDENTE'", (numero_ajuste,))
        count = cur.fetchone()[0]
        if count == 0:
            print(f"Ajuste {numero_ajuste} não encontrado ou já liberado")
            return jsonify({'error': 'Ajuste não encontrado ou já liberado'}), 404

        cur.execute(
            "UPDATE ajustes SET status = 'LIBERADO', usuario_liberou = %s WHERE numero_ajuste = %s",
            (usuario_liberou, numero_ajuste)
        )
        conn.commit()
        print(f"Ajuste {numero_ajuste} liberado por {usuario_liberou}")
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print(f"Erro ao liberar ajuste {numero_ajuste}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/historico', methods=['GET'])
@login_required
def get_historico():
    print("Recebendo requisição GET para /historico")
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        print("Buscando histórico de ajustes...")
        cur.execute('SELECT * FROM ajustes ORDER BY data DESC')
        historico = cur.fetchall()
        print(f"Histórico encontrado: {historico}")
        cur.close()
        conn.close()
        return jsonify([
            {
                'id': item['numero_ajuste'],
                'produto_codigo': item['codigo_produto'],
                'ajuste': item['quantidade'],
                'data_hora': item['data'].strftime('%d/%m/%Y - %H:%M'),
                'matricula': item['matricula'],
                'nome_usuario': item['nome_usuario'],
                'descricao': item['descricao']
            } for item in historico
        ])
    except Exception as e:
        cur.close()
        conn.close()
        print(f"Erro ao carregar histórico: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/ajustes_realizados', methods=['GET'])
@login_required
def ajustes_realizados():
    return render_template('ajustes_realizados.html')


@app.route('/ajustes-realizados-dados', methods=['GET'])
@login_required
def get_ajustes_realizados():
    print("Recebendo requisição GET para /ajustes-realizados-dados")
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute('''
            SELECT numero_ajuste, MAX(data) AS data, matricula, nome_usuario, usuario_liberou
            FROM ajustes
            WHERE TRIM(UPPER(status)) = %s
            GROUP BY numero_ajuste, matricula, nome_usuario, usuario_liberou
            ORDER BY numero_ajuste DESC
        ''', ('LIBERADO',))
        ajustes = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{
            'numero_ajuste': ajuste['numero_ajuste'],
            'data_hora': ajuste['data'].strftime('%d/%m/%Y - %H:%M') if ajuste['data'] else 'N/A',
            'matricula': ajuste['matricula'],
            'nome_usuario': ajuste['nome_usuario'],
            'usuario_liberou': ajuste['usuario_liberou']
        } for ajuste in ajustes])
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/detalhes-ajuste/<numero_ajuste>', methods=['GET'])
@login_required
def get_detalhes_ajuste(numero_ajuste):
    print(f"Recebendo requisição GET para /detalhes-ajuste/{numero_ajuste}")
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute('''
            SELECT a.*, p.custo
            FROM ajustes a
            LEFT JOIN produtos p ON a.codigo_produto = p.codigo
            WHERE a.numero_ajuste = %s
        ''', (numero_ajuste,))
        ajustes = cur.fetchall()
        print(f"Dados brutos do banco para ajuste {numero_ajuste}: {ajustes}")
        if not ajustes:
            return jsonify({'error': 'Ajuste não encontrado'}), 404

        ajustes_formatados = [{
            'numero_ajuste': ajuste['numero_ajuste'],
            'produto_codigo': ajuste['codigo_produto'],
            'descricao': ajuste['descricao'],
            'quantidade': ajuste['quantidade'],
            'custo': float(str(ajuste['custo']).replace(',', '.')) if ajuste['custo'] is not None else 0.0,
            'data_hora': ajuste['data'].strftime('%d/%m/%Y - %H:%M'),
            'matricula': ajuste['matricula'],
            'nome_usuario': ajuste['nome_usuario'],
            'usuario_liberou': ajuste['usuario_liberou'],
            'status': ajuste['status']
        } for ajuste in ajustes]
        print(
            f"Dados formatados para ajuste {numero_ajuste}: {ajustes_formatados}")

        cur.close()
        conn.close()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(ajustes_formatados)
        else:
            return render_template('detalhes_ajuste.html', numero_ajuste=numero_ajuste)
    except Exception as e:
        cur.close()
        conn.close()
        print(f"Erro ao buscar detalhes do ajuste {numero_ajuste}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/relatorio-dados', methods=['GET'])
@login_required
def get_relatorio_dados():
    print("Recebendo requisição GET para /relatorio-dados")
    print(f"Sessão atual: {session}")
    if 'user' not in session:
        print("Usuário não autenticado na rota /relatorio-dados.")
        return jsonify({'error': 'Usuário não autenticado. Faça login novamente.'}), 401

    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    matricula = request.args.get('matricula')
    numero_ajuste = request.args.get('numero_ajuste')

    print(
        f"Parâmetros recebidos - data_inicio: {data_inicio}, data_fim: {data_fim}, matricula: {matricula}, numero_ajuste: {numero_ajuste}")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        query = '''
            SELECT a.*, p.custo AS custo
            FROM ajustes a
            LEFT JOIN produtos p ON a.codigo_produto = p.codigo
            WHERE 1=1
        '''
        params = []

        
        if data_inicio:
            query += ' AND data >= %s'
            # Ajustado para YYYY-MM-DD
            params.append(datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query += ' AND data <= %s'
            data_fim_dt = datetime.strptime(
                # Final do dia: 23:59:59
                data_fim, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            params.append(data_fim_dt)
        if matricula:
            query += ' AND matricula = %s'
            params.append(matricula)
        if numero_ajuste:
            query += ' AND numero_ajuste = %s'
            params.append(numero_ajuste)

        query += ' ORDER BY numero_ajuste, data DESC'
        print(f"Executando consulta: {query} com parâmetros: {params}")
        cur.execute(query, params)
        ajustes = cur.fetchall()
        print(f"Ajustes encontrados: {ajustes}")

        cur.close()
        conn.close()
        return jsonify([{
            'numero_ajuste': item['numero_ajuste'],
            'produto_codigo': item['codigo_produto'],
            'descricao': item['descricao'],
            'quantidade': item['quantidade'],
            'custo': float(str(item['custo']).replace(',', '.')) if item['custo'] is not None else 0.0,
            'data_hora': item['data'].strftime('%d/%m/%Y - %H:%M'),
            'matricula': item['matricula'],
            'nome_usuario': item['nome_usuario']
        } for item in ajustes])
    except Exception as e:
        cur.close()
        conn.close()
        print(f"Erro ao carregar dados do relatório: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/exportar-relatorio-excel', methods=['GET'])
@login_required
def exportar_relatorio_excel():
    print("Recebendo requisição GET para /exportar-relatorio-excel")
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    matricula = request.args.get('matricula')
    numero_ajuste = request.args.get('numero_ajuste')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        query = '''
            SELECT a.*, p.custo AS custo
            FROM ajustes a
            LEFT JOIN produtos p ON a.codigo_produto = p.codigo
            WHERE 1=1
        '''
        params = []

        if data_inicio:
            query += ' AND data >= %s'
            params.append(data_inicio)
        if data_fim:
            query += ' AND data <= %s'
            params.append(data_fim)
        if matricula:
            query += ' AND matricula = %s'
            params.append(matricula)
        if numero_ajuste:
            query += ' AND numero_ajuste = %s'
            params.append(numero_ajuste)

        query += ' ORDER BY numero_ajuste, data DESC'
        print(f"Executando consulta: {query} com parâmetros: {params}")
        cur.execute(query, params)
        ajustes = cur.fetchall()
        print(f"Ajustes encontrados: {ajustes}")

        data = [{
            'Número do Ajuste': item['numero_ajuste'],
            'Código do Produto': item['codigo_produto'],
            'Descrição': item['descricao'],
            'Quantidade': item['quantidade'] if item['quantidade'] is not None else 0,  # Trata None como 0
            'Custo Unitário (R$)': float(str(item['custo']).replace(',', '.')) if item['custo'] is not None else 0.0,
            'Data/Hora': item['data'].strftime('%d/%m/%Y - %H:%M'),
            'Matrícula': item['matricula'],
            'Nome do Usuário': item['nome_usuario']
        } for item in ajustes]

        df = pd.DataFrame(data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Relatório de Ajustes')
        output.seek(0)

        cur.close()
        conn.close()
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio_ajustes_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    except Exception as e:
        cur.close()
        conn.close()
        print(f"Erro ao exportar relatório para Excel: {e}")
        return jsonify({'error': str(e)}), 500

# Módulo CV-Análise


@app.route('/cv_analise')
@login_required
def cv_analise():
    print("Acessando rota /cv_analise")
    return render_template('cv_analise.html')


@app.route('/buscar_curriculos', methods=['GET'])
@login_required
def buscar_curriculos():
    print("Recebendo requisição GET para /buscar_curriculos")
    nome = request.args.get('nome', '')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, nome FROM curriculos WHERE nome LIKE %s LIMIT 10"
    cursor.execute(query, ('%' + nome + '%',))
    curriculos = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(curriculos)


@app.route('/curriculo_detalhes/<candidato_id>', methods=['GET'])
@login_required
def curriculo_detalhes(candidato_id):
    print(
        f"[DEBUG] Recebendo requisição GET para /curriculo_detalhes/{candidato_id}")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM curriculos WHERE id = %s",
                       (candidato_id,))
        curriculo = cursor.fetchone()
        if not curriculo:
            cursor.close()
            conn.close()
            print(f"[DEBUG] Currículo ID {candidato_id} não encontrado")
            return "Currículo não encontrado", 404

        cursor.close()
        conn.close()
        print(f"[DEBUG] Currículo encontrado: {curriculo}")
        print(f"[DEBUG] Renderizando template curriculo_detalhes.html")
        return render_template('curriculo_detalhes.html', curriculo=curriculo)
    except Exception as e:
        cursor.close()
        conn.close()
        print(
            f"[DEBUG] Erro ao buscar detalhes do currículo {candidato_id}: {str(e)}")
        return f"Erro ao buscar currículo: {str(e)}", 500


@app.route('/vagas', methods=['GET'])
@login_required
def get_vagas():
    try:
        print("Acessando rota /vagas")  # Log para depuração
        conn = get_db_connection()
        print("Conexão com o banco de dados estabelecida")  # Log para depuração
        cursor = conn.cursor()
        cursor.execute("SELECT id, titulo, requisitos FROM vagas")
        vagas = cursor.fetchall()
        print(f"Vagas encontradas: {vagas}")  # Log para depuração
        cursor.close()
        conn.close()

        vagas_list = [{'id': vaga[0], 'titulo': vaga[1],
                       'requisitos': vaga[2]} for vaga in vagas]
        return jsonify(vagas_list)
    except Exception as e:
        print(f"Erro ao carregar vagas: {str(e)}")  # Log para depuração
        return jsonify({'error': f'Erro ao carregar vagas: {str(e)}'}), 500


@app.route('/buscar-candidatos', methods=['GET'])
@login_required
def buscar_candidatos():
    nome = request.args.get('nome', '').strip()
    vaga_id = request.args.get('vaga_id', '')

    if not vaga_id:
        return jsonify({'error': 'ID da vaga é obrigatório'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT * FROM curriculos WHERE vaga_id = %s AND (status IS NULL OR status != 'aprovado')"
        params = [vaga_id]
        if nome:
            query += " AND nome LIKE %s"
            params.append(f"%{nome}%")
        cursor.execute(query, params)
        curriculos = cursor.fetchall()
        cursor.close()
        conn.close()

        print(f"Candidatos encontrados: {curriculos}")
        return jsonify(curriculos)
    except Exception as e:
        cursor.close()
        conn.close()
        print(f"Erro ao buscar candidatos: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/aprovar-candidatos', methods=['POST'])
@login_required
def aprovar_candidatos():
    print("[DEBUG] Recebendo requisição POST para /aprovar-candidatos")
    data = request.get_json()
    candidatos = data.get('candidatos', [])

    if not candidatos:
        return jsonify({'error': 'Nenhum candidato selecionado'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for candidato_id in candidatos:
            cursor.execute(
                "UPDATE curriculos SET status = 'Aprovado', etapa = 1 WHERE id = %s", (candidato_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[DEBUG] Candidatos aprovados: {candidatos}")
        return jsonify({'success': True})
    except Exception as e:
        cursor.close()
        conn.close()
        print(f"[DEBUG] Erro ao aprovar candidatos: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/reprovar_candidato/<int:candidato_id>', methods=['POST'])
@login_required
def reprovar_candidato(candidato_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Verificar se o candidato existe
        cursor.execute(
            "SELECT id FROM curriculos WHERE id = %s", (candidato_id,))
        candidato = cursor.fetchone()
        if not candidato:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        # Atualizar o status para "reprovado"
        cursor.execute(
            "UPDATE curriculos SET status = 'Reprovado' WHERE id = %s", (candidato_id,))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({'message': 'Candidato reprovado com sucesso'})
    except Exception as e:
        cursor.close()
        conn.close()
        print(f"[DEBUG] Erro ao reprovar candidato: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/avancar_etapa/<int:candidato_id>', methods=['POST'])
@login_required
def avancar_etapa(candidato_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Verificar se o candidato existe e obter a etapa atual
        cursor.execute(
            "SELECT etapa FROM curriculos WHERE id = %s", (candidato_id,))
        candidato = cursor.fetchone()
        if not candidato:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        # Incrementar a etapa (máximo 6)
        etapa_atual = candidato[0]
        nova_etapa = etapa_atual + 1 if etapa_atual < 6 else 6

        # Atualizar a etapa no banco de dados
        cursor.execute(
            "UPDATE curriculos SET etapa = %s WHERE id = %s", (nova_etapa, candidato_id))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({'message': 'Etapa avançada com sucesso'})
    except Exception as e:
        cursor.close()
        conn.close()
        print(f"[DEBUG] Erro ao avançar etapa: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/gerar_questionario/<int:candidato_id>')
@login_required
def gerar_questionario(candidato_id):
    return render_template('gerar_questionario.html', candidato_id=candidato_id)


@app.route('/get_candidate_name/<int:candidato_id>')
@login_required
def get_candidate_name(candidato_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT nome FROM curriculos WHERE id = %s", (candidato_id,))
        candidato = cursor.fetchone()
        if not candidato:
            return jsonify({'error': 'Candidato não encontrado'}), 404
        return jsonify({'nome': candidato[0]})
    finally:
        cursor.close()
        conn.close()


@app.route('/gerar_perguntas/<int:candidato_id>', methods=['GET'])
@login_required
def gerar_perguntas(candidato_id):
    print(
        f"[DEBUG] Iniciando geração de perguntas para candidato_id: {candidato_id}")
    if 'user' not in session:
        print(
            f"[DEBUG] Usuário não autenticado ao acessar /gerar_perguntas/{candidato_id}")
        return jsonify({'error': 'Usuário não autenticado'}), 401

    # Perguntas padrão (fallback) ajustadas para diferentes níveis de senioridade
    fallback_perguntas_junior = [
        {"pergunta": "Qual é a sua experiência na área da vaga?", "alternativas": [
            "a) Nenhuma", "b) 1-2 anos", "c) Mais de 2 anos"], "correta": "b"},
        {"pergunta": "Você tem conhecimento nos requisitos da vaga?", "alternativas": [
            "a) Sim", "b) Não", "c) Parcialmente"], "correta": "a"},
        {"pergunta": "O que é uma variável em programação?", "alternativas": [
            "a) Um valor fixo", "b) Um espaço para armazenar dados", "c) Um tipo de função"], "correta": "b"},
        {"pergunta": "Qual é a função do print() em Python?", "alternativas": [
            "a) Ler um arquivo", "b) Exibir uma mensagem", "c) Criar uma variável"], "correta": "b"},
        {"pergunta": "O que significa um erro de sintaxe?", "alternativas": [
            "a) Erro de lógica", "b) Erro na escrita do código", "c) Erro de execução"], "correta": "b"},
        {"pergunta": "Qual é o operador para igualdade em Python?",
            "alternativas": ["a) =", "b) ==", "c) :="], "correta": "b"},
        {"pergunta": "O que é uma lista em Python?", "alternativas": [
            "a) Um tipo de loop", "b) Uma coleção ordenada", "c) Uma função"], "correta": "b"},
        {"pergunta": "Como você inicia um loop for em Python?", "alternativas": [
            "a) for i in range()", "b) while i in range()", "c) loop i in range()"], "correta": "a"},
        {"pergunta": "Qual é o propósito de um if em programação?", "alternativas": [
            "a) Repetir um código", "b) Tomar decisões", "c) Definir uma função"], "correta": "b"},
        {"pergunta": "O que faz o método append() em uma lista?", "alternativas": [
            "a) Remove um item", "b) Adiciona um item", "c) Altera um item"], "correta": "b"}
    ]

    fallback_perguntas_pleno = [
        {"pergunta": "Como você gerencia dependências em Python?", "alternativas": [
            "a) Usando pip", "b) Editando o código", "c) Usando print()"], "correta": "a"},
        {"pergunta": "O que é uma rota em Flask?", "alternativas": [
            "a) Um banco de dados", "b) Um endpoint URL", "c) Um tipo de variável"], "correta": "b"},
        {"pergunta": "Qual é a diferença entre list e tuple?", "alternativas": [
            "a) List é imutável", "b) Tuple é mutável", "c) List é mutável, tuple é imutável"], "correta": "c"},
        {"pergunta": "Como você lida com exceções em Python?", "alternativas": [
            "a) Usando if", "b) Usando try/except", "c) Usando for"], "correta": "b"},
        {"pergunta": "O que é o método GET em Flask?", "alternativas": [
            "a) Salva dados", "b) Busca dados", "c) Deleta dados"], "correta": "b"},
        {"pergunta": "O que é um decorador em Python?", "alternativas": [
            "a) Uma função que modifica outra", "b) Um loop", "c) Um tipo de variável"], "correta": "a"},
        {"pergunta": "Como você cria uma API REST com Flask?", "alternativas": [
            "a) Definindo rotas", "b) Usando loops", "c) Criando variáveis"], "correta": "a"},
        {"pergunta": "O que é o Flask Blueprint?", "alternativas": [
            "a) Um template", "b) Um módulo para organizar rotas", "c) Um banco de dados"], "correta": "b"},
        {"pergunta": "Qual é a função do jsonify no Flask?", "alternativas": [
            "a) Converte para JSON", "b) Cria uma página HTML", "c) Salva no banco"], "correta": "a"},
        {"pergunta": "O que é um ORM em Python?", "alternativas": [
            "a) Um gerenciador de rotas", "b) Um mapeador objeto-relacional", "c) Um tipo de loop"], "correta": "b"}
    ]

    fallback_perguntas_senior = [
        {"pergunta": "Como você otimiza o desempenho de uma app Flask?", "alternativas": [
            "a) Usando loops", "b) Cache e async", "c) Aumentando variáveis"], "correta": "b"},
        {"pergunta": "O que é uma arquitetura de microsserviços?", "alternativas": [
            "a) Um único servidor", "b) Serviços independentes", "c) Um banco de dados"], "correta": "b"},
        {"pergunta": "Como você implementa autenticação em Flask?", "alternativas": [
            "a) Usando JWT", "b) Usando print()", "c) Usando loops"], "correta": "a"},
        {"pergunta": "O que é o GIL em Python?", "alternativas": [
            "a) Um gerenciador de rotas", "b) Um lock global", "c) Um tipo de lista"], "correta": "b"},
        {"pergunta": "Como você lida com concorrência em Flask?", "alternativas": [
            "a) Usando Gunicorn", "b) Usando if", "c) Usando variáveis"], "correta": "a"},
        {"pergunta": "O que é o conceito de SOLID em programação?", "alternativas": [
            "a) Um tipo de loop", "b) Princípios de design", "c) Um banco de dados"], "correta": "b"},
        {"pergunta": "Como você testa uma API Flask?", "alternativas": [
            "a) Usando unittest", "b) Usando print()", "c) Usando variáveis"], "correta": "a"},
        {"pergunta": "O que é o design pattern MVC?", "alternativas": [
            "a) Um loop", "b) Modelo-Visão-Controlador", "c) Um tipo de variável"], "correta": "b"},
        {"pergunta": "Como você gerencia migrations em Flask?", "alternativas": [
            "a) Usando Flask-Migrate", "b) Usando loops", "c) Usando print()"], "correta": "a"},
        {"pergunta": "O que é o conceito de CI/CD?", "alternativas": [
            "a) Um tipo de variável", "b) Integração e entrega contínua", "c) Um banco de dados"], "correta": "b"}
    ]

    conn = None
    cursor = None
    try:
        print(
            f"[DEBUG] Tentando conectar ao banco de dados para candidato_id: {candidato_id}")
        conn = get_db_connection()
        if conn is None:
            print(
                f"[DEBUG] Falha ao conectar ao banco de dados para candidato_id: {candidato_id}")
            return jsonify({'error': 'Erro ao conectar ao banco de dados'}), 500

        cursor = conn.cursor()
        print(
            f"[DEBUG] Executando consulta SQL para candidato_id: {candidato_id}")
        cursor.execute("""
            SELECT v.titulo, v.requisitos, v.senioridade
            FROM curriculos c
            JOIN vagas v ON c.vaga_id = v.id
            WHERE c.id = %s
        """, (candidato_id,))
        vaga = cursor.fetchone()
        if not vaga:
            print(
                f"[DEBUG] Candidato ou vaga não encontrado para candidato_id: {candidato_id}")
            return jsonify({'error': 'Candidato ou vaga não encontrado'}), 404

        titulo_vaga, requisitos, senioridade = vaga
        print(
            f"[DEBUG] Vaga encontrada para candidato_id {candidato_id}: título={titulo_vaga}, requisitos={requisitos}, senioridade={senioridade}")

        if not titulo_vaga or not requisitos or not senioridade:
            print(
                f"[DEBUG] Título, requisitos ou senioridade da vaga não encontrados para candidato_id: {candidato_id}")
            return jsonify({'error': 'Título, requisitos ou senioridade da vaga não encontrados'}), 400

        # Escolher o conjunto de perguntas padrão baseado na senioridade
        if senioridade.lower() == "júnior":
            fallback_perguntas = fallback_perguntas_junior
        elif senioridade.lower() == "pleno":
            fallback_perguntas = fallback_perguntas_pleno
        else:  # Sênior ou qualquer outro valor
            fallback_perguntas = fallback_perguntas_senior

        print(
            f"[DEBUG] Gerando perguntas com a IA para candidato_id: {candidato_id}")
        print(
            f"[DEBUG] Dados de entrada para a IA: titulo_vaga={titulo_vaga}, requisitos={requisitos}, senioridade={senioridade}")
        try:
            perguntas_geradas = perguntas_chain.invoke({
                "titulo_vaga": titulo_vaga,
                "requisitos": requisitos,
                "senioridade": senioridade
            })
            print(
                f"[DEBUG] Perguntas geradas para candidato_id {candidato_id}: {perguntas_geradas}")
        except Exception as e:
            print(
                f"[DEBUG] Erro ao gerar perguntas com a IA para candidato_id {candidato_id}: {str(e)}")
            print("[DEBUG] Usando perguntas padrão (fallback) devido ao erro na IA.")
            perguntas_geradas = fallback_perguntas

        # Verificar se a saída é uma lista de perguntas no formato correto
        if not isinstance(perguntas_geradas, list):
            print(
                f"[DEBUG] Saída da IA não é uma lista para candidato_id {candidato_id}: {perguntas_geradas}")
            print(
                "[DEBUG] Usando perguntas padrão (fallback) devido ao formato inválido.")
            perguntas_geradas = fallback_perguntas

        # Validar cada pergunta
        perguntas_validadas = []
        for pergunta in perguntas_geradas:
            if not isinstance(pergunta, dict) or not all(
                key in pergunta for key in ['pergunta', 'alternativas', 'correta']
            ):
                print(
                    f"[DEBUG] Formato inválido de pergunta para candidato_id {candidato_id}: {pergunta}")
                continue
            if not isinstance(pergunta['alternativas'], list) or len(pergunta['alternativas']) != 3:
                print(
                    f"[DEBUG] Alternativas inválidas para candidato_id {candidato_id}: {pergunta['alternativas']}")
                continue
            if pergunta['correta'] not in ['a', 'b', 'c']:
                print(
                    f"[DEBUG] Alternativa correta inválida para candidato_id {candidato_id}: {pergunta['correta']}")
                continue
            perguntas_validadas.append(pergunta)

        # Se menos de 10 perguntas válidas foram geradas, completar com o fallback
        if len(perguntas_validadas) < 10:
            print(
                f"[DEBUG] Apenas {len(perguntas_validadas)} perguntas válidas geradas para candidato_id {candidato_id}. Completando com perguntas padrão.")
            perguntas_validadas.extend(
                fallback_perguntas[:10 - len(perguntas_validadas)])

        # Garantir que haja exatamente 10 perguntas
        perguntas_validadas = perguntas_validadas[:10]

        print(
            f"[DEBUG] Retornando perguntas para candidato_id: {candidato_id}")
        return jsonify({'perguntas': perguntas_validadas})
    except Exception as e:
        print(
            f"[DEBUG] Erro ao gerar perguntas para candidato_id {candidato_id}: {str(e)}")
        print("[DEBUG] Usando perguntas padrão (fallback) devido a erro geral.")
        return jsonify({'perguntas': fallback_perguntas[:10]})
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/salvar_questionario/<int:candidato_id>', methods=['POST'])
@login_required
def salvar_questionario(candidato_id):
    print(f"[DEBUG] Acessando rota /salvar_questionario/{candidato_id}")
    try:
        data = request.get_json()
        perguntas = data.get('perguntas', [])
        if not perguntas:
            print(
                f"[DEBUG] Nenhuma pergunta fornecida para candidato_id: {candidato_id}")
            return jsonify({'error': 'Nenhuma pergunta fornecida'}), 400

        conn = get_db_connection()
        if conn is None:
            print(
                f"[DEBUG] Falha ao conectar ao banco de dados para salvar questionário do candidato_id: {candidato_id}")
            return jsonify({'error': 'Erro ao conectar ao banco de dados'}), 500

        cursor = conn.cursor()
        try:
            # Inserir ou atualizar o questionário no banco
            cursor.execute("""
                INSERT INTO questionarios (candidato_id, perguntas)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE perguntas = %s, criado_em = NOW()
            """, (candidato_id, json.dumps(perguntas), json.dumps(perguntas)))
            conn.commit()
            print(
                f"[DEBUG] Questionário salvo com sucesso para candidato_id: {candidato_id}")
            return jsonify({'message': 'Questionário salvo com sucesso'})
        except Exception as e:
            print(
                f"[DEBUG] Erro ao executar query para salvar questionário do candidato_id {candidato_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(
            f"[DEBUG] Erro ao salvar questionário para candidato_id {candidato_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/analisar-candidatos', methods=['POST'])
@login_required
def analisar_candidatos():
    try:
        print("Acessando rota /analisar-candidatos")  # Log para depuração
        data = request.get_json()
        candidatos_ids = data.get('candidatos', [])
        vaga_id = data.get('vaga_id')

        # Log para depuração
        print(
            f"Dados recebidos: candidatos_ids={candidatos_ids}, vaga_id={vaga_id}")

        if not candidatos_ids or not vaga_id:
            print("Erro: Candidatos ou vaga não fornecidos")
            return jsonify({'error': 'Candidatos e vaga são obrigatórios'}), 400

        # Garantir que candidatos_ids seja uma lista de inteiros
        try:
            candidatos_ids = [int(candidato_id)
                              for candidato_id in candidatos_ids]
        except ValueError as e:
            print(f"Erro: IDs de candidatos inválidos - {str(e)}")
            return jsonify({'error': 'IDs de candidatos inválidos'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar a vaga
        cursor.execute(
            "SELECT id, titulo, requisitos FROM vagas WHERE id = %s", (vaga_id,))
        vaga = cursor.fetchone()
        if not vaga:
            cursor.close()
            conn.close()
            print("Erro: Vaga não encontrada")
            return jsonify({'error': 'Vaga não encontrada'}), 404

        requisitos_vaga = vaga['requisitos'].split(
            ', ') if vaga['requisitos'] else []
        print(f"Requisitos da vaga: {requisitos_vaga}")  # Log para depuração

        # Buscar os candidatos selecionados na tabela curriculos
        placeholders = ','.join(['%s'] * len(candidatos_ids))
        query = f"SELECT id, nome, conteudo FROM curriculos WHERE id IN ({placeholders})"
        print(f"Query a ser executada: {query}")  # Log para depuração
        print(f"Parâmetros: {candidatos_ids}")  # Log para depuração

        cursor.execute(query, tuple(candidatos_ids))
        candidatos = cursor.fetchall()

        print(f"Candidatos encontrados: {candidatos}")  # Log para depuração

        cursor.close()
        conn.close()

        if not candidatos:
            print("Erro: Nenhum candidato encontrado")
            return jsonify({'error': 'Nenhum candidato encontrado'}), 404

        # Lógica de análise (comparar habilidades, calcular pontuação e gerar observações)
        resultados = []
        for candidato in candidatos:
            candidato_id = candidato['id']
            nome = candidato['nome']
            conteudo = candidato['conteudo']
            habilidades_candidato = conteudo.split(', ') if conteudo else []
            # Log para depuração
            print(f"Habilidades do candidato {nome}: {habilidades_candidato}")

            # Calcular a compatibilidade com a vaga
            compatibilidade = 0
            requisitos_atendidos = []
            requisitos_faltantes = []

            for req in requisitos_vaga:
                encontrado = False
                for habilidade in habilidades_candidato:
                    if req.lower() in habilidade.lower():
                        compatibilidade += 1
                        requisitos_atendidos.append(req)
                        encontrado = True
                        break
                if not encontrado:
                    requisitos_faltantes.append(req)

            compatibilidade_percentual = (
                compatibilidade / len(requisitos_vaga)) * 100 if requisitos_vaga else 0
            # Log para depuração
            print(
                f"Compatibilidade de {nome}: {compatibilidade}/{len(requisitos_vaga)} = {compatibilidade_percentual}%")

            # Gerar observações
            observacoes = []
            if compatibilidade_percentual == 100:
                observacoes.append(
                    "Candidato atende a todos os requisitos da vaga, sendo uma excelente escolha.")
            else:
                if requisitos_atendidos:
                    observacoes.append(
                        f"Possui habilidades relevantes: {', '.join(requisitos_atendidos)}.")
                if requisitos_faltantes:
                    observacoes.append(
                        f"Faltam os seguintes requisitos: {', '.join(requisitos_faltantes)}.")
                else:
                    observacoes.append(
                        "Não possui nenhuma das habilidades requeridas pela vaga.")

            # Considerar experiência (se aplicável)
            experiencia_requerida = None
            for req in requisitos_vaga:
                if "anos de experiência" in req.lower():
                    try:
                        # Ex.: "2" em "2 anos de experiência"
                        experiencia_requerida = int(req.split()[0])
                        break
                    except (ValueError, IndexError):
                        continue

            if experiencia_requerida:
                experiencia_encontrada = False
                for habilidade in habilidades_candidato:
                    if "anos de" in habilidade.lower():
                        try:
                            # Ex.: "3" em "3 anos de desenvolvimento"
                            anos_candidato = int(habilidade.split()[0])
                            if anos_candidato >= experiencia_requerida:
                                observacoes.append(
                                    f"Possui experiência suficiente ({anos_candidato} anos), atendendo ao requisito de {experiencia_requerida} anos.")
                            else:
                                observacoes.append(
                                    f"Possui {anos_candidato} anos de experiência, mas o requisito é de {experiencia_requerida} anos.")
                            experiencia_encontrada = True
                            break
                        except (ValueError, IndexError):
                            continue
                if not experiencia_encontrada:
                    observacoes.append(
                        f"Não foi possível verificar a experiência do candidato em relação ao requisito de {experiencia_requerida} anos.")

            # Log para depuração
            print(f"Observações geradas para {nome}: {observacoes}")

            # Pontuação final (baseada na compatibilidade)
            pontuacao_final = compatibilidade_percentual

            resultados.append({
                'id': candidato_id,
                'nome': nome,
                'habilidades': conteudo if conteudo else 'N/A',
                'compatibilidade': round(compatibilidade_percentual, 2),
                'pontuacao_final': round(pontuacao_final, 2),
                'observacoes': observacoes  # Certificar que observações estão sendo incluídas
            })

        # Ordenar por pontuação final (maior para menor)
        resultados.sort(key=lambda x: x['pontuacao_final'], reverse=True)

        # Determinar o melhor candidato
        melhor_candidato = resultados[0] if resultados else None

        print(f"Resultados da análise: {resultados}")  # Log para depuração
        print(f"Melhor candidato: {melhor_candidato}")  # Log para depuração

        return jsonify({
            'resultados': resultados,
            'melhor_candidato': melhor_candidato
        }), 200
    except mysql.connector.Error as e:
        # Log para depuração
        print(f"Erro ao analisar candidatos (MySQL): {str(e)}")
        return jsonify({'error': f'Erro ao analisar candidatos: {str(e)}'}), 500
    except Exception as e:
        # Log para depuração
        print(f"Erro inesperado ao analisar candidatos: {str(e)}")
        return jsonify({'error': f'Erro inesperado ao analisar candidatos: {str(e)}'}), 500


@app.route('/selecionar_candidatos', methods=['GET'])
@login_required
def selecionar_candidatos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Buscar todas as vagas
        cursor.execute("SELECT id, titulo FROM vagas")
        vagas = cursor.fetchall()

        # Para cada vaga, buscar os candidatos aprovados
        for vaga in vagas:
            cursor.execute(
                """
                SELECT id, nome, etapa, status
                FROM curriculos
                WHERE vaga_id = %s AND status = 'aprovado' AND etapa IS NOT NULL
                ORDER BY etapa
                """,
                (vaga['id'],)
            )
            vaga['candidatos'] = cursor.fetchall()

        cursor.close()
        conn.close()

        # Determinar a etapa atual (baseado no candidato mais avançado)
        etapa_atual = 1
        for vaga in vagas:
            for candidato in vaga['candidatos']:
                if candidato['etapa'] and candidato['etapa'] > etapa_atual:
                    etapa_atual = candidato['etapa']

        print(
            f"[DEBUG] Dados para selecionar_candidatos: {vagas}, Etapa atual: {etapa_atual}")
        return render_template('selecionar_candidatos.html', vagas=vagas, etapa_atual=etapa_atual)
    except Exception as e:
        cursor.close()
        conn.close()
        print(f"[DEBUG] Erro ao buscar candidatos para seleção: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/sugerir_detalhes_vaga', methods=['POST'])
@login_required
def sugerir_detalhes_vaga():
    try:
        data = request.get_json()
        titulo = data.get('titulo', '').lower().strip()

        if not titulo:
            return jsonify({'error': 'Título da vaga é obrigatório'}), 400

        print(f"Gerando sugestões para o título: {titulo}")

        # Gerar sugestões diretamente com o Grok
        suggestion_result = suggestion_chain.run(titulo=titulo)

        # Parsear o resultado do Grok
        sugestoes = {
            'beneficios': '',
            'descricao': '',
            'requisitos': ''
        }

        for line in suggestion_result.split('\n'):
            if line.startswith('Benefícios:'):
                sugestoes['beneficios'] = line.replace(
                    'Benefícios:', '').strip()
            elif line.startswith('Descrição:'):
                sugestoes['descricao'] = line.replace('Descrição:', '').strip()
            elif line.startswith('Requisitos:'):
                sugestoes['requisitos'] = line.replace(
                    'Requisitos:', '').strip()

        # Valores padrão caso o Grok não retorne informações completas
        if not sugestoes['beneficios']:
            sugestoes['beneficios'] = "Vale-refeição, Plano de saúde, Horário flexível"
        if not sugestoes['descricao']:
            sugestoes['descricao'] = "Atuar no desenvolvimento de projetos relacionados à área, colaborando com a equipe."
        if not sugestoes['requisitos']:
            sugestoes['requisitos'] = "Conhecimentos técnicos relevantes, Experiência na área, Boa comunicação"

        print(f"Sugestões geradas: {sugestoes}")

        return jsonify(sugestoes), 200
    except Exception as e:
        print(f"Erro ao sugerir detalhes da vaga: {str(e)}")
        return jsonify({'error': f'Erro ao sugerir detalhes da vaga: {str(e)}'}), 500


@app.route('/cadastro_vagas')
@login_required
def cadastro_vagas():
    print("Acessando a rota /cadastro_vagas")  # Log para depuração
    return render_template('cadastro_vagas.html')


@app.route('/cadastrar_vaga', methods=['POST'])
@login_required
def cadastrar_vaga():
    try:
        data = request.get_json()
        print(f"Dados recebidos para cadastro de vaga: {data}")

        # Extrair os dados do formulário
        titulo = data.get('titulo')
        senioridade = data.get('senioridade')
        tipo_contrato = data.get('tipo_contrato')
        localizacao = data.get('localizacao')
        modalidade = data.get('modalidade')
        faixa_salarial = data.get('faixa_salarial')
        beneficios = data.get('beneficios')
        descricao = data.get('descricao')
        requisitos = data.get('requisitos')  # String separada por vírgulas
        status = data.get('status', 'Aberta')
        categoria = data.get('categoria')
        prioridade = data.get('prioridade', 'Média')

        if not titulo:
            return jsonify({'error': 'O título da vaga é obrigatório'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Inserir a nova vaga
        query = """
            INSERT INTO vagas (titulo, senioridade, tipo_contrato, localizacao, modalidade, faixa_salarial, beneficios, descricao, requisitos, status, categoria, prioridade, data_criacao)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        params = (titulo, senioridade, tipo_contrato, localizacao, modalidade,
                  faixa_salarial, beneficios, descricao, requisitos, status, categoria, prioridade)
        cursor.execute(query, params)
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'message': 'Vaga cadastrada com sucesso!'}), 201
    except mysql.connector.Error as e:
        print(f"Erro ao cadastrar vaga (MySQL): {str(e)}")
        return jsonify({'error': f'Erro ao cadastrar vaga: {str(e)}'}), 500
    except Exception as e:
        print(f"Erro inesperado ao cadastrar vaga: {str(e)}")
        return jsonify({'error': f'Erro inesperado ao cadastrar vaga: {str(e)}'}), 500


@app.route('/vagas', methods=['GET'])
@login_required
def listar_vagas():
    print("[DEBUG] Recebendo requisição GET para /vagas")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM vagas")
        vagas = cursor.fetchall()
        cursor.close()
        conn.close()
        print(f"[DEBUG] Vagas encontradas: {vagas}")
        return jsonify(vagas)
    except Exception as e:
        cursor.close()
        conn.close()
        print(f"[DEBUG] Erro ao buscar vagas: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/analisar_curriculos', methods=['POST'])
@login_required
def analisar_curriculos():
    print("Recebendo requisição POST para /analisar_curriculos")
    data = request.get_json()
    print(f"Dados recebidos: {data}")
    vaga_id = data.get('vaga_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Busca requisitos da vaga
    cursor.execute("SELECT requisitos FROM vagas WHERE id = %s", (vaga_id,))
    vaga = cursor.fetchone()
    if not vaga:
        cursor.close()
        conn.close()
        print(f"Vaga ID {vaga_id} não encontrada")
        return jsonify({'error': 'Vaga não encontrada'}), 404

    requisitos = vaga['requisitos']
    print(f"Requisitos da vaga: {requisitos}")

    # Busca todos os currículos
    cursor.execute("SELECT id, nome, conteudo FROM curriculos")
    curriculos = cursor.fetchall()
    print(f"Currículos encontrados: {len(curriculos)}")

    # Inicializa o modelo Groq (usando Grok)
    llm = ChatGroq(
        model="grok",
        temperature=0.2,
        max_retries=2
    )

    # Define o parser para garantir saída JSON
    parser = JsonOutputParser()

    # Prompt para análise
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Você é um especialista em RH. Analise o currículo fornecido e calcule uma pontuação de compatibilidade (0 a 100) com base nos requisitos da vaga. Retorne apenas um JSON com a estrutura: {{ "id": id_curriculo, "nome": nome_curriculo, "pontuacao": pontuacao }}.
        Currículo: {curriculo}
        Requisitos da vaga: {requisitos}"""),
        ("human", "Analise o currículo e retorne a pontuação.")
    ])

    # Cria a cadeia LangChain
    chain = prompt | llm | parser

    resultados = []
    for curriculo in curriculos:
        try:
            resultado = chain.invoke({
                "curriculo": curriculo['conteudo'],
                "requisitos": requisitos
            })
            resultados.append({
                "id": curriculo['id'],
                "nome": curriculo['nome'],
                "pontuacao": resultado.get('pontuacao', 0)
            })
            print(f"Análise do currículo {curriculo['nome']}: {resultado}")
        except Exception as e:
            print(f"Erro ao analisar currículo {curriculo['nome']}: {e}")

    # Ordena por pontuação e limita a 10
    resultados = sorted(
        resultados, key=lambda x: x['pontuacao'], reverse=True)[:10]
    print(f"Resultados finais: {resultados}")

    cursor.close()
    conn.close()
    return jsonify(resultados)

# ... (outras importações)

# Defina a lista de filiais em um local acessível pela rota
FILIAIS = [
    {"codigo": "1", "nome": "Ponta Negra"},
    {"codigo": "2", "nome": "Alecrim"},
    {"codigo": "7", "nome": "SAC - Centro VI"},
    {"codigo": "100", "nome": "Lagoa Nova"},
    {"codigo": "121", "nome": "Norte Shopping"},
    {"codigo": "122", "nome": "Parnamirim"},
    {"codigo": "131", "nome": "ZN2"},
    {"codigo": "137", "nome": "Macaíba"},
    {"codigo": "140", "nome": "Maria Lacerda"},
    {"codigo": "141", "nome": "Igapó"}
]

# Configure uma pasta para uploads
app.config['UPLOAD_FOLDER'] = 'static/uploads/promotores'
# Garanta que o diretório de uploads exista
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/cadastro_promotores', methods=['GET', 'POST'])
def cadastro_promotores():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        conn = None
        try:
            # --- 1. Coletar dados do Promotor e Gestor ---
            nome_promotor = request.form['nome_promotor']
            marca_fornecedor = request.form['marca_fornecedor']
            email_promotor = request.form['email_promotor']
            telefone_promotor = request.form['telefone_promotor']
            
            nome_gestor = request.form['nome_gestor']
            email_gestor = request.form['email_gestor']
            telefone_gestor = request.form['telefone_gestor']

            # --- 2. Lidar com o Upload da Foto ---
            foto_promotor = request.files.get('foto_promotor')
            nome_arquivo_foto = None
            if foto_promotor and foto_promotor.filename != '':
                # Garante um nome de arquivo seguro
                filename = secure_filename(foto_promotor.filename)
                # Salva o arquivo
                caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto_promotor.save(caminho_arquivo)
                nome_arquivo_foto = filename # Guarda apenas o nome para salvar no DB
            
            # --- 3. Inserir Promotor no Banco e Obter a ID ---
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # ATENÇÃO: Ajuste o SQL para sua tabela real
            sql_promotor = """
                INSERT INTO tbl_promotores 
                (Nome, MarcaFornecedor, Email, Telefone, NomeGestor, EmailGestor, TelefoneGestor, Foto)
                OUTPUT INSERTED.ID
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """
            
            promotor_id = cursor.execute(
                sql_promotor, 
                nome_promotor, marca_fornecedor, email_promotor, telefone_promotor,
                nome_gestor, email_gestor, telefone_gestor, nome_arquivo_foto
            ).fetchval() # fetchval() é específico do pyodbc para pegar o valor de OUTPUT

            # --- 4. Processar e Inserir Rotas ---
            for filial in FILIAIS:
                codigo_loja = filial['codigo']
                
                # O .getlist() pega todos os valores com o mesmo 'name'
                dias_semana = request.form.getlist(f'loja_{codigo_loja}_dia_semana[]')
                entradas = request.form.getlist(f'loja_{codigo_loja}_entrada[]')
                saidas = request.form.getlist(f'loja_{codigo_loja}_saida[]')
                intervalos = request.form.getlist(f'loja_{codigo_loja}_intervalo[]')

                # Itera sobre os horários adicionados para essa loja
                for i in range(len(dias_semana)):
                    dia = dias_semana[i]
                    entrada = entradas[i]
                    saida = saidas[i]
                    # Garante que o intervalo tenha um valor, mesmo que vazio
                    intervalo = intervalos[i] if i < len(intervalos) and intervalos[i] else None

                    if dia and entrada and saida: # Garante que os dados essenciais existem
                        sql_rota = """
                            INSERT INTO tbl_rotas_promotores 
                            (ID_Promotor, CodigoLoja, DiaSemana, HorarioEntrada, HorarioSaida, HorarioIntervalo)
                            VALUES (?, ?, ?, ?, ?, ?);
                        """
                        cursor.execute(sql_rota, promotor_id, codigo_loja, dia, entrada, saida, intervalo)

            conn.commit()
            flash('Promotor e suas rotas cadastrados com sucesso!', 'success')

        except Exception as e:
            logging.error(f"Erro no cadastro do promotor: {e}")
            flash(f'Ocorreu um erro ao cadastrar: {e}', 'danger')
        
        finally:
            if conn:
                conn.close()

        return redirect(url_for('cadastro_promotores'))

    # Para método GET, apenas renderiza a página passando a lista de filiais
    return render_template('cadastro_promotores.html', filiais=FILIAIS)

if __name__ == '__main__':
    print("Iniciando o servidor Flask...")
    app.run(debug=True, host='0.0.0.0', port=5000)

