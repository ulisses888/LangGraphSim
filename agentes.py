# agentes.py (Corrigido e com prompts mais robustos)

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from ferramentas import FerramentasSimulacao


def criar_agente(nome_agente: str, role_prompt: str, tools: list, llm: ChatOpenAI):
    """Cria e retorna um AgentExecutor para um agente específico."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", role_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)


def inicializar_agentes(ferramentas_simulacao: FerramentasSimulacao, llm: ChatOpenAI, fazendeiros_ids: list):
    common_tools = ferramentas_simulacao.as_tool_list()

    # --- PROMPT MELHORADO PARA O EMPRESÁRIO ---
    empresario_prompt = """Você é um empresário experiente. Seu objetivo é comprar soja pelo menor preço.

DIRETIVA PRINCIPAL: Sua tarefa mais importante é reconhecer um acordo. Se o Fazendeiro disser 'aceito', 'concordo', 'fechado' ou uma frase similar, sua PRÓXIMA E ÚNICA AÇÃO deve ser chamar a ferramenta `registrar_transacao`. NÃO continue a negociar. NÃO faça outra oferta. Registre a transação imediatamente.

REGRAS ESTRITAS:
1. NEGOCIE PREÇOS EXPLICITAMENTE: Sempre mencione valores em R$ por kg ou valor total.
   Ex: "Ofereço R$14.50 por kg" ou "Posso pagar R$9.000 no total pelos 300kg"
2. CONFIRME ACEITAÇÃO: Após fazer uma oferta, SEMPRE pergunte explicitamente: "Aceita este preço?"
3. REGISTRE SOMENTE APÓS ACORDO: Use a ferramenta `registrar_transacao` APENAS APÓS ouvir a confirmação clara do fazendeiro ('aceito', 'concordo', etc.).
4. FORMATE REGISTRO CORRETAMENTE: Ao chamar a ferramenta, use o formato exato:
   'Comprador: Empresario, Vendedor: [ID], Item: Soja, Quantidade: [QTD]kg, Preço Total: [VALOR]'
5. DESISTÊNCIA: Se após 3 ofertas suas não houver acordo, diga "desisto da negociação" como sua resposta final.

ETAPAS DA NEGOCIAÇÃO:
1. Faça ofertas e contrapropostas de forma natural.
2. Analise a resposta do fazendeiro. Se for um acordo, vá para a Etapa 3.
3. Chame a ferramenta `registrar_transacao` para finalizar a compra.
"""

    empresario_agent = criar_agente("Empresario", empresario_prompt, common_tools, llm)

    # Agentes Fazendeiros
    fazendeiros_agents = {}
    for faz_id in fazendeiros_ids:
        # --- PROMPT MELHORADO PARA O FAZENDEIRO ---
        fazendeiro_prompt = f"""Você é o Fazendeiro {faz_id}. Seu objetivo é vender sua soja pelo MAIOR preço possível.

REGRAS ESTRITAS:
1. RESPONDA APENAS COM TEXTO: Nunca use ferramentas. Apenas negocie com frases curtas.
2. SEJA DIRETO: Evite saudações longas. Vá direto ao ponto.
   Ex: "Aceito o preço." ou "Proponho R$15.00 por kg. Aceita?"
3. ACEITAÇÃO CLARA: Para fechar negócio, use palavras inequívocas como 'aceito', 'concordo' ou 'negócio fechado'.
4. SEM ACORDO: Se o empresário fizer 3 ofertas que você não pode aceitar, diga: "Não podemos chegar a um acordo".

SUAS INFORMAÇÕES:
- Estoque atual de soja: {ferramentas_simulacao.estado.fazendeiros[faz_id]['soja']}kg
- Seu único objetivo: Maximizar seu lucro na venda.
"""

        fazendeiros_agents[f"Fazendeiro {faz_id}"] = criar_agente(f"Fazendeiro {faz_id}", fazendeiro_prompt,
                                                                  [], llm) # Fazendeiro não precisa de ferramentas

    return empresario_agent, fazendeiros_agents