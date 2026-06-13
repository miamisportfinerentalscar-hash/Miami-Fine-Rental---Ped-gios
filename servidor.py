"""
Miami Fine Rental — Servidor de Dados de Pedágios
Lê a planilha do Google Sheets e serve os dados processados via API REST.

Como usar:
  1. Instale as dependências: pip install flask flask-cors pandas
  2. Cole a URL do Google Sheets na variável GOOGLE_SHEETS_URL abaixo
  3. Execute: python servidor.py
  4. Abra o dashboard.html no navegador
"""

from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
from io import StringIO
import urllib.request
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================================
# COLE AQUI A URL DO GOOGLE SHEETS (formato CSV publicado)
# Arquivo > Compartilhar > Publicar na web > CSV > Publicar
# ============================================================
GOOGLE_SHEETS_URL = "COLE_SUA_URL_AQUI"
# ============================================================

def carregar_dados():
    try:
        with urllib.request.urlopen(GOOGLE_SHEETS_URL) as resp:
            csv_text = resp.read().decode("utf-8")
        df = pd.read_csv(StringIO(csv_text))
    except Exception as e:
        return None, str(e)

    df.columns = ["Veiculo", "Invoice", "Conta", "Placa", "Data", "Descricao", "Valor", "Status", "DataPagamento"]
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    return df, None


@app.route("/api/dados")
def api_dados():
    df, erro = carregar_dados()
    if erro:
        return jsonify({"erro": erro}), 500

    # KPIs
    total = round(df["Valor"].sum(), 2)
    total_transacoes = len(df)
    veiculo_maior = df.groupby("Veiculo")["Valor"].sum().idxmax()
    valor_maior = round(df.groupby("Veiculo")["Valor"].sum().max(), 2)

    # Por veículo
    por_veiculo = (
        df.groupby("Veiculo")
        .agg(total=("Valor", "sum"), transacoes=("Valor", "count"))
        .reset_index()
        .sort_values("total", ascending=False)
    )
    por_veiculo["total"] = por_veiculo["total"].round(2)

    # Média diária por veículo
    dias_ativos = df.groupby("Veiculo")["Data"].nunique()
    total_veiculo = df.groupby("Veiculo")["Valor"].sum()
    media_diaria = (total_veiculo / dias_ativos).round(2).reset_index()
    media_diaria.columns = ["Veiculo", "media_diaria"]
    media_diaria["dias_ativos"] = dias_ativos.values
    media_diaria["total"] = total_veiculo.round(2).values
    media_diaria = media_diaria.sort_values("media_diaria", ascending=False)

    # Por mês
    df["mes"] = df["Data"].dt.to_period("M").astype(str)
    por_mes = (
        df.groupby("mes")["Valor"].sum().round(2).reset_index()
        .sort_values("mes")
    )

    # Por dia da semana
    dias_map = {"Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua",
                "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb", "Sunday": "Dom"}
    df["dow"] = df["Data"].dt.day_name().map(dias_map)
    ordem = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    por_dow = (
        df.groupby("dow")["Valor"].sum().round(2)
        .reindex(ordem).fillna(0).reset_index()
    )

    # Top rodovias (excl. saldos anteriores)
    df_clean = df[~df["Descricao"].str.contains("VALORES ANTERIORES", na=False)]
    top_rotas = (
        df_clean.groupby("Descricao")["Valor"].sum().round(2)
        .sort_values(ascending=False).head(10).reset_index()
    )

    # Média por transação
    media_tx = (
        df.groupby("Veiculo")["Valor"].mean().round(2)
        .reset_index().sort_values("Valor", ascending=False)
    )
    media_tx.columns = ["Veiculo", "media_tx"]

    return jsonify({
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "kpis": {
            "total": total,
            "total_transacoes": total_transacoes,
            "veiculo_maior": veiculo_maior,
            "valor_maior": valor_maior,
        },
        "por_veiculo": por_veiculo.to_dict(orient="records"),
        "media_diaria": media_diaria.to_dict(orient="records"),
        "por_mes": por_mes.to_dict(orient="records"),
        "por_dow": por_dow.to_dict(orient="records"),
        "top_rotas": top_rotas.to_dict(orient="records"),
        "media_tx": media_tx.to_dict(orient="records"),
    })


@app.route("/")
def index():
    return "<h3>Servidor Miami Fine Rental ativo ✅ — Abra o dashboard.html no navegador.</h3>"


if __name__ == "__main__":
    print("=" * 55)
    print("  Miami Fine Rental — Servidor de Pedágios")
    print("  Rodando em: http://localhost:5000")
    print("  Dashboard: abra o arquivo dashboard.html")
    print("=" * 55)
    app.run(debug=False, port=5000)
