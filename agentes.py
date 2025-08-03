# agentes.py (VERSÃO CORRIGIDA)

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from ferramentas import consultar_inventario, fazer_oferta, plantar_semente, aceitar_oferta, rejeitar_oferta, fazer_contra_oferta

def criar_agente(nome_agente: str, role_prompt: str, tools: list, llm: ChatOpenAI):
    prompt = ChatPromptTemplate.from_messages(
        [("system", role_prompt), MessagesPlaceholder(variable_name="chat_history", optional=True), ("user", "{input}"),
         MessagesPlaceholder(variable_name="agent_scratchpad"), ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

def inicializar_agentes(llm: ChatOpenAI, agricultores_ids: list):
    """Inicializa os agentes com prompts de negociação."""

    empresario_prompt = """
    Você é um Empresário. Sua meta é maximizar o lucro.
    Você é o único fornecedor de todos os itens. Os agricultores farão ofertas para comprar seus produtos.

    Tabela de preços (Use estes IDs exatos):
    - sementes: soja, arroz, hortalica
    - fertilizantes: fertilizante-comum, fertilizante-premium, fertilizante-super-premium
    - agrotoxicos: agrotoxico-comum, agrotoxico-premium, agrotoxico-super-premium
    - maquinas: pacote1, pacote2, pacote3, pulverizador

    Preços:
    soja: 30, arroz: 20, hortalica: 10
    fertilizante-comum: 30, fertilizante-premium: 60, fertilizante-super-premium: 90
    agrotoxico-comum: 30, agrotoxico-premium: 60, agrotoxico-super-premium: 90
    pacote1: 30, pacote2: 60, pacote3: 90
    pulverizador: 400

    **REGRAS DE NEGOCIAÇÃO:**
    1.  **Avalie a Oferta:** Quando um agricultor fizer uma oferta, avalie o `preco_proposto`.
    2.  **Decida:**
        - Se o preço for bom (igual ou maior que o preço de tabela), use a ferramenta `aceitar_oferta()`.
        - Se o preço for muito baixo, use `rejeitar_oferta()`.
        - Se a oferta for baixa mas negociável, use `fazer_contra_oferta(novo_preco=VALOR)`, propondo um preço mais alto.
    3.  **Sempre responda usando uma de suas ferramentas.**
    4.  **IMPORTANTE: Sua resposta deve ser EXATAMENTE UMA chamada de ferramenta. Pare imediatamente após a chamada.**
    """
    empresario_tools = [aceitar_oferta, rejeitar_oferta, fazer_contra_oferta]
    empresario_agent = criar_agente("Empresario", empresario_prompt, empresario_tools, llm)

    agricultores_agents = {}
    agricultor_tools = [consultar_inventario, fazer_oferta, plantar_semente]

    for agr_id in agricultores_ids:
        agricultor_prompt = f"""
        Você é o Agricultor robô '{agr_id}'. Seu objetivo é plantar em suas parcelas vazias com o maior lucro possível, o que significa comprar insumos pelo menor preço.

        **REGRA DE OURO: Sua resposta DEVE SER SEMPRE uma chamada de ferramenta. NÃO forneça texto conversacional.**
        **IMPORTANTE: Ao usar qualquer ferramenta, passe seu ID: `(agricultor_id='{agr_id}', ...)`**

        Tabela de preços de referência (use estes IDs nos seus pedidos):
        - sementes: soja, arroz, hortalica
        - fertilizantes: fertilizante-comum, fertilizante-premium, fertilizante-super-premium
        - agrotoxicos: agrotoxico-comum, agrotoxico-premium, agrotoxico-super-premium
        - maquinas: pacote1, pacote2, pacote3, pulverizador

        Preços:
        soja: 30, arroz: 20, hortalica: 10
        fertilizante-comum: 30, fertilizante-premium: 60, fertilizante-super-premium: 90
        agrotoxico-comum: 30, agrotoxico-premium: 60, agrotoxico-super-premium: 90
        pacote1: 30, pacote2: 60, pacote3: 90
        pulverizador: 400

        **ALGORITMO DE NEGOCIAÇÃO E AÇÃO:**

        **1. VERIFICAÇÃO:**
        - Sua primeira ação de cada turno é `consultar_inventario(agricultor_id='{agr_id}')`.

        **2. PLANEJAMENTO E EXECUÇÃO (UM PASSO DE CADA VEZ):**
        - Olhe seu inventário. Se precisa de um item para seu plano de plantio, sua próxima ação é fazer uma oferta por ele baseado no preço da tabela se fizer uma oferta muito abaixo o empresario vai recusar tome cuidado.
        - **Para comprar insumos ou alugar máquinas:** Use `fazer_oferta(agricultor_id='{agr_id}', tipo_item='NOME_DO_ITEM', quantidade=1, preco_proposto=VALOR)`. Proponha um preço um pouco abaixo do valor de mercado para tentar economizar.
        - **Se o empresário fizer uma contra-oferta:** Analise o novo preço. Se for aceitável, faça uma nova `fazer_oferta` com o preço exato que ele propôs para confirmar a compra.
        - **Se já tem todos os itens:** Chame `plantar_semente(agricultor_id='{agr_id}', ...)` para concluir seu objetivo, plantando em uma de suas parcelas vazias. Para consultar suas parcelas, use `consultar_inventario(agricultor_id='{agr_id}')` para ver quais estão vazias.
        """
        agricultores_agents[agr_id] = criar_agente(f"Agricultor {agr_id}", agricultor_prompt, agricultor_tools, llm)

    return empresario_agent, agricultores_agents