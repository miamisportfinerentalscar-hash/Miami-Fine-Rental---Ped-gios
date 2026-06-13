"""
Miami Fine Rental — Servidor de Pedágios com Dashboard integrado
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
from io import StringIO
import urllib.request
from datetime import datetime
import os

app = Flask(__name__, static_folder=".")
CORS(app)

GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSkWlqiAqvE4DQCu9UV53_ssWwf5CEwodDc5oBRZL7Bpyy5qcy7yPlg-zk10LDO02B5QdUzpRqLbe7l/pub?output=csv"

def carregar_dados():
    try:
        with urllib.request.urlopen(GOOGLE_SHEETS_URL) as resp:
            csv_text = resp.read().decode("utf-8")
        df = pd.read_csv(StringIO(csv_text))
        df.columns = ["Veiculo","Invoice","Conta","Placa","Data","Descricao","Valor","Status","DataPagamento"]
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
        return df, None
    except Exception as e:
        return None, str(e)

@app.route("/api/dados")
def api_dados():
    df, erro = carregar_dados()
    if erro:
        return jsonify({"erro": erro}), 500
    total = round(df["Valor"].sum(), 2)
    total_transacoes = len(df)
    veiculo_maior = df.groupby("Veiculo")["Valor"].sum().idxmax()
    valor_maior = round(df.groupby("Veiculo")["Valor"].sum().max(), 2)
    por_veiculo = df.groupby("Veiculo").agg(total=("Valor","sum"),transacoes=("Valor","count")).reset_index().sort_values("total",ascending=False)
    por_veiculo["total"] = por_veiculo["total"].round(2)
    dias_ativos = df.groupby("Veiculo")["Data"].nunique()
    total_veiculo = df.groupby("Veiculo")["Valor"].sum()
    media_diaria = (total_veiculo/dias_ativos).round(2).reset_index()
    media_diaria.columns = ["Veiculo","media_diaria"]
    media_diaria["dias_ativos"] = dias_ativos.values
    media_diaria["total"] = total_veiculo.round(2).values
    media_diaria = media_diaria.sort_values("media_diaria",ascending=False)
    df["mes"] = df["Data"].dt.to_period("M").astype(str)
    por_mes = df.groupby("mes")["Valor"].sum().round(2).reset_index().sort_values("mes")
    dias_map = {"Monday":"Seg","Tuesday":"Ter","Wednesday":"Qua","Thursday":"Qui","Friday":"Sex","Saturday":"Sab","Sunday":"Dom"}
    df["dow"] = df["Data"].dt.day_name().map(dias_map)
    ordem = ["Seg","Ter","Qua","Qui","Sex","Sab","Dom"]
    por_dow = df.groupby("dow")["Valor"].sum().round(2).reindex(ordem).fillna(0).reset_index()
    df_clean = df[~df["Descricao"].str.contains("VALORES ANTERIORES",na=False)]
    top_rotas = df_clean.groupby("Descricao")["Valor"].sum().round(2).sort_values(ascending=False).head(10).reset_index()
    media_tx = df.groupby("Veiculo")["Valor"].mean().round(2).reset_index().sort_values("Valor",ascending=False)
    media_tx.columns = ["Veiculo","media_tx"]
    return jsonify({"atualizado_em":datetime.now().strftime("%d/%m/%Y %H:%M:%S"),"kpis":{"total":total,"total_transacoes":total_transacoes,"veiculo_maior":veiculo_maior,"valor_maior":valor_maior},"por_veiculo":por_veiculo.to_dict(orient="records"),"media_diaria":media_diaria.to_dict(orient="records"),"por_mes":por_mes.to_dict(orient="records"),"por_dow":por_dow.to_dict(orient="records"),"top_rotas":top_rotas.to_dict(orient="records"),"media_tx":media_tx.to_dict(orient="records")})

@app.route("/")
def index():
    return app.send_static_file("dashboard_live.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("Servidor rodando em http://localhost:" + str(port))
    app.run(debug=False, host="0.0.0.0", port=port)
