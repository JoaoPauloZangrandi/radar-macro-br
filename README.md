# radar-macro-br

Plataforma pessoal de monitoramento de mercado para market risk no Brasil: curva de juros
(DI, DAP/inflação implícita), cupom cambial (DDI/FRC), câmbio, Treasuries, macro BR/EUA e
notícias que podem fazer preço em juros, inflação e câmbio. Entrega no celular (Android)
via Telegram (alertas por tópico + briefings 7h/18h) e site PWA.

Restrição de projeto: **custo zero**. Código comum faz coleta e alertas por regra; IA só
classifica notícias e escreve os briefings.

## Roadmap
1. ✅ Teste das fontes gratuitas (`fontes/teste_fontes.py`)
2. Bot Telegram com alertas de câmbio e macro (sem IA)
3. Curva completa (DI, DAP, DDI, FRC, Treasuries) com variação por vértice
4. IA: classificação de notícias + briefings 7h e 18h
5. Site PWA com gráficos

## Resultado do teste de fontes (30/10/2026, após o fechamento): 25/25 OK

| Grupo | Fonte | Uso |
|---|---|---|
| BR juros | API de cotação da B3: **DI1, DAP** | intraday + ajuste anterior (todos os vencimentos) |
| BR juros | ANBIMA ETTJ (pré, IPCA, implícita) | fechamento D-1 |
| BR cupom | API de cotação da B3: **DDI, FRC** | intraday + ajuste anterior |
| BR câmbio | B3 DOL, BCB PTAX, AwesomeAPI, Yahoo `BRL=X` | intraday |
| BR macro | BCB SGS, Focus (Olinda), IBGE SIDRA | eventos |
| EUA juros | US Treasury par curve (oficial), FRED; Yahoo `^TNX` | fechamento; intraday não oficial |
| EUA macro | FRED (CPI, payroll, Fed Funds) | eventos |
| Global | Yahoo DXY | intraday não oficial |
| Notícias | RSS InfoMoney, Google News (buscas), Fed, BCE | contínuo |

A API `cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/{ATIVO}` traz por vencimento: taxa
atual, ajuste anterior, abertura/mín/máx/média, melhor compra/venda, volume e contratos em
aberto. É a API que alimenta o site da B3; não é documentada oficialmente e pode mudar.

**Pendente:** medir o atraso real dessa API durante o pregão (o teste rodou com o mercado
fechado).

## Rodar
```
pip install requests
python fontes/teste_fontes.py
```
