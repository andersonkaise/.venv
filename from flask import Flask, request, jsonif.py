from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

app = Flask(__name__)

# Configuração do banco de dados PostgreSQL
DB_CONFIG = {
    "host": "54.166.24.15",
    "database": "granpic-sp",
    "user": "postgres",
    "password": "Kalisba987",
    "port": 5432  # Porta padrão do PostgreSQL
}

# Configuração da API do WhatsApp Business
WHATSAPP_API_URL = " https://graph.facebook.com/v22.0/556235320911649/messages"  # Substituir pelo seu ID do WhatsApp Business
WHATSAPP_ACCESS_TOKEN = "EAAJMhYNVCLYBO6Tpw6n91qne2IyNOUrtTsgRKXCozlEptZCfD4U1bZAfEqQEjP6inyclEczjKLG6kOJO6RMdw81R7CbgJacYKXtqQHPwKZCZA3K1YeS8LOnBVCZC3PhJA2wSQmfOzIBGU5KPxIBiqG99PdwVK6jwazl7MGv24BdPij9Fib2F9wZA8dTFUxgf7h"

# Conectar ao banco de dados
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

# Webhook para receber mensagens do WhatsApp Business
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        verify_token = "TRUMP"
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if mode and token:
            if mode == "subscribe" and token == verify_token:
                return challenge, 200
            else:
                return jsonify({"error": "Token inválido"}), 403
    
    if request.method == "POST":
        data = request.get_json()
        
        if "entry" in data:
            for entry in data["entry"]:
                for change in entry["changes"]:
                    if "messages" in change["value"]:
                        mensagem_recebida = change["value"]["messages"][0]["text"]["body"]
                        numero_whatsapp = change["value"]["messages"][0]["from"]
                        
                        if "relatorio" in mensagem_recebida.lower():
                            enviar_vendas_whatsapp(numero_whatsapp)
        
        return jsonify({"status": "Mensagem recebida"}), 200

# Rota para buscar as vendas e enviar pelo WhatsApp Business
@app.route("/enviar_vendas_whatsapp", methods=["POST"])
def enviar_vendas_whatsapp(numero_whatsapp):
    mes = request.json.get("mes", None)  # Exemplo: "2024-02"
    
    if not numero_whatsapp:
        return jsonify({"error": "Número do WhatsApp é obrigatório"}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT vendedor_nome, SUM(tot_item) as total_vendas, SUM(comissao) as total_comissao
        FROM (
        -- Aqui entra a QUERY fornecida pelo usuário
        ) AS vendas
        """
        
        params = []
        if mes:
            query += " WHERE mes = %s AND ano = date_part('year', CURRENT_DATE)"
            params.append(mes)
        
        query += " GROUP BY vendedor_nome ORDER BY total_vendas DESC"
        cur.execute(query, params)
        vendas = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Construir a mensagem para WhatsApp
        mensagem = "📊 *Relatório de Vendas* \n\n"
        for venda in vendas:
            mensagem += f"👤 *Vendedor:* {venda['vendedor_nome']}\n"
            mensagem += f"💰 *Total Vendido:* R$ {venda['total_vendas']:.2f}\n"
            mensagem += f"📈 *Comissão:* R$ {venda['total_comissao']:.2f}\n\n"
        
        # Enviar mensagem via API do WhatsApp Business
        whatsapp_payload = {
            "messaging_product": "whatsapp",
            "to": numero_whatsapp,
            "type": "text",
            "text": {"body": mensagem}
        }
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        response = requests.post(WHATSAPP_API_URL, json=whatsapp_payload, headers=headers)
        
        if response.status_code == 200:
            return jsonify({"message": "Mensagem enviada com sucesso pelo WhatsApp Business!"})
        else:
            return jsonify({"error": "Falha ao enviar mensagem", "details": response.json()}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
