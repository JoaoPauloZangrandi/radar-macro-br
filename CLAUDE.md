# Instruções para agentes (Claude / Codex)

- Projeto pessoal de monitoramento de mercado; usuário trabalha em market risk no Brasil.
- Restrição: **custo zero**. Preferir código determinístico; IA só onde agrega (notícias, briefings).
- Python + `requests`; evitar dependências novas sem necessidade.
- Ir um passo por vez seguindo o roadmap do README; mostrar o plano antes de construir.
- Nunca afirmar que uma fonte funciona sem rodar `python fontes/teste_fontes.py`.
- Segredos (token do Telegram, chaves de API) só em `.env`, nunca no repositório (ele é público).
