"""Passo 1: testa quais fontes gratuitas de dados respondem e com que frescor.

Uso:  python fontes/teste_fontes.py
Saida: tabela no terminal + fontes/resultado_teste.json
"""
import json
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import requests

HOJE = date.today()
ONTEM_UTIL = HOJE - timedelta(days=3 if HOJE.weekday() == 0 else 1)
HEADERS = {"User-Agent": "Mozilla/5.0 (radar-macro-br; teste de fontes)"}
TIMEOUT = 20


def get(url, **kw):
    return requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kw)


# ---------- cada teste devolve (amostra_texto, data_mais_recente) ----------

def bcb_sgs(codigo):
    def f():
        r = get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json")
        r.raise_for_status()
        d = r.json()[-1]
        return f"{d['valor']}", d["data"]
    return f


def bcb_ptax():
    ini = (HOJE - timedelta(days=7)).strftime("%m-%d-%Y")
    fim = HOJE.strftime("%m-%d-%Y")
    url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
           "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
           f"?@moeda='USD'&@dataInicial='{ini}'&@dataFinalCotacao='{fim}'&$format=json")
    r = get(url)
    r.raise_for_status()
    d = r.json()["value"][-1]
    return f"{d['tipoBoletim']} venda={d['cotacaoVenda']}", d["dataHoraCotacao"]


def bcb_focus():
    url = ("https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
           "?$top=1&$filter=Indicador%20eq%20'IPCA'&$orderby=Data%20desc&$format=json")
    r = get(url)
    r.raise_for_status()
    d = r.json()["value"][0]
    return f"IPCA {d['DataReferencia']} mediana={d['Mediana']}", d["Data"]


def ibge_ipca():
    r = get("https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/last%201")
    r.raise_for_status()
    d = r.json()[1]
    return f"IPCA mensal={d['V']}%", d["D3N"]


def awesome_usdbrl():
    r = get("https://economia.awesomeapi.com.br/json/last/USD-BRL")
    r.raise_for_status()
    d = r.json()["USDBRL"]
    return f"bid={d['bid']} ask={d['ask']}", d["create_date"]


def b3_intraday(ativo):
    def f():
        r = get(f"https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/{ativo}")
        r.raise_for_status()
        d = r.json()
        scty = d["Scty"]
        venc = [s for s in scty if s.get("SctyQtn", {}).get("curPrc")]
        s = venc[0] if venc else scty[0]
        qtn = s.get("SctyQtn", {})
        return f"{len(scty)} vencimentos; {s['symb']} ult={qtn.get('curPrc')}", d.get("Msg", {}).get("dtTm", "?")
    return f


def anbima_ettj():
    dia = ONTEM_UTIL
    r = requests.post("https://www.anbima.com.br/informacoes/est-termo/CZ-down.asp",
                      data={"Idioma": "PT", "Dt_Ref": f"{dia:%d/%m/%Y}", "saida": "csv"},
                      headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    txt = r.content.decode("latin-1")
    if "Vertices" not in txt and "Vértices" not in txt:
        raise ValueError("CSV sem tabela de vertices")
    return f"CSV {len(txt.splitlines())} linhas (pre, IPCA, implicita)", str(dia)


def treasury_curva():
    url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"
           f"{HOJE.year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={HOJE.year}&_format=csv")
    r = get(url)
    r.raise_for_status()
    linhas = r.text.splitlines()
    cab, ult = linhas[0].split(","), linhas[1].split(",")
    d = dict(zip(cab, ult))
    return f"{len(cab)-1} vertices; 2Y={d.get('\"2 Yr\"')} 10Y={d.get('\"10 Yr\"')}", d["Date"]


def fred(serie):
    def f():
        r = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie}")
        r.raise_for_status()
        ult = [l for l in r.text.splitlines()[1:] if not l.endswith(",.")][-1]
        dt, v = ult.split(",")
        return f"{serie}={v}", dt
    return f


def yahoo_intraday(ticker):
    def f():
        r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=1d")
        r.raise_for_status()
        m = r.json()["chart"]["result"][0]["meta"]
        return f"{ticker} preco={m.get('regularMarketPrice')}", time.strftime(
            "%Y-%m-%d %H:%M", time.localtime(m.get("regularMarketTime", 0)))
    return f


def rss(url):
    def f():
        r = get(url)
        r.raise_for_status()
        raiz = ET.fromstring(r.content)
        itens = raiz.findall(".//item") or raiz.findall(".//{http://www.w3.org/2005/Atom}entry")
        if not itens:
            raise ValueError("feed sem itens")
        it = itens[0]
        titulo = (it.findtext("title") or it.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        dt = (it.findtext("pubDate") or it.findtext("{http://www.w3.org/2005/Atom}updated") or "?").strip()
        return f"{len(itens)} itens; '{titulo[:60]}'", dt
    return f


FONTES = [
    # (grupo, nome, tipo, funcao)
    # A API de cotacao da B3 traz curPrc (taxa atual) e prvsDayAdjstmntPric (ajuste anterior),
    # entao cobre intraday E fechamento; as paginas antigas de TxRef/ajustes deram 404.
    ("BR juros", "B3 DI1 intraday (site B3)", "intraday", b3_intraday("DI1")),
    ("BR juros", "B3 DAP intraday (cupom IPCA)", "intraday", b3_intraday("DAP")),
    ("BR juros", "ANBIMA ETTJ (pre/IPCA/implicita)", "fechamento", anbima_ettj),
    ("BR juros", "BCB Selic meta (SGS 432)", "evento", bcb_sgs(432)),
    ("BR cupom", "B3 DDI intraday (site B3)", "intraday", b3_intraday("DDI")),
    ("BR cupom", "B3 FRC intraday (FRA de cupom)", "intraday", b3_intraday("FRC")),
    ("BR cambio", "B3 DOL intraday (dolar futuro)", "intraday", b3_intraday("DOL")),
    ("BR cambio", "BCB PTAX (boletins do dia)", "intraday", bcb_ptax),
    ("BR cambio", "AwesomeAPI USDBRL spot", "intraday", awesome_usdbrl),
    ("BR cambio", "Yahoo USDBRL (nao oficial)", "intraday", yahoo_intraday("BRL=X")),
    ("BR macro", "IBGE IPCA (SIDRA 1737)", "evento", ibge_ipca),
    ("BR macro", "BCB Focus IPCA", "evento", bcb_focus),
    ("BR macro", "BCB IPCA (SGS 433)", "evento", bcb_sgs(433)),
    ("EUA juros", "US Treasury curva par (oficial)", "fechamento", treasury_curva),
    ("EUA juros", "FRED DGS10", "fechamento", fred("DGS10")),
    ("EUA juros", "Yahoo ^TNX 10Y (nao oficial)", "intraday", yahoo_intraday("^TNX")),
    ("EUA macro", "FRED CPI (CPIAUCSL)", "evento", fred("CPIAUCSL")),
    ("EUA macro", "FRED Payroll (PAYEMS)", "evento", fred("PAYEMS")),
    ("EUA macro", "FRED Fed Funds (DFF)", "evento", fred("DFF")),
    ("Global", "Yahoo DXY (nao oficial)", "intraday", yahoo_intraday("DX-Y.NYB")),
    ("Noticias", "InfoMoney RSS", "intraday", rss("https://www.infomoney.com.br/feed/")),
    ("Noticias", "Google News 'copom OR selic'", "intraday",
     rss("https://news.google.com/rss/search?q=copom+OR+selic&hl=pt-BR&gl=BR&ceid=BR:pt-419")),
    ("Noticias", "Google News 'fiscal haddad'", "intraday",
     rss("https://news.google.com/rss/search?q=fiscal+haddad&hl=pt-BR&gl=BR&ceid=BR:pt-419")),
    ("Noticias", "Fed press releases RSS", "evento", rss("https://www.federalreserve.gov/feeds/press_all.xml")),
    ("Noticias", "ECB press RSS", "evento", rss("https://www.ecb.europa.eu/rss/press.html")),
]


def main():
    resultados = []
    for grupo, nome, tipo, f in FONTES:
        t0 = time.time()
        try:
            amostra, data_ref = f()
            ok, erro = True, ""
        except Exception as e:  # noqa: BLE001 - teste exploratorio, queremos ver qualquer falha
            amostra, data_ref, ok, erro = "", "", False, f"{type(e).__name__}: {str(e)[:80]}"
        ms = int((time.time() - t0) * 1000)
        resultados.append(dict(grupo=grupo, fonte=nome, tipo=tipo, ok=ok, ms=ms,
                               data_ref=str(data_ref), amostra=amostra, erro=erro))
        status = "OK  " if ok else "FALHA"
        print(f"[{status}] {grupo:10} | {nome:42} | {tipo:10} | {ms:5} ms | "
              f"{(str(data_ref) or '-')[:19]:19} | {amostra or erro}")

    saida = Path(__file__).with_name("resultado_teste.json")
    saida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    n_ok = sum(r["ok"] for r in resultados)
    print(f"\n{n_ok}/{len(resultados)} fontes OK. Detalhes em {saida}")


if __name__ == "__main__":
    main()
