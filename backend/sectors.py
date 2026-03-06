"""
Multi-sector configuration for BidIQ procurement search.

Each sector defines a keyword set and exclusion list used by filter.py
to identify relevant procurement opportunities in PNCP data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set

from filter import KEYWORDS_UNIFORMES, KEYWORDS_EXCLUSAO


@dataclass(frozen=True)
class SectorConfig:
    """Configuration for a procurement sector."""

    id: str
    name: str
    description: str
    keywords: Set[str]
    exclusions: Set[str] = field(default_factory=set)
    # Tier-based keyword scoring (optional — if keywords_a is empty, uses flat keywords as tier A)
    keywords_a: Set[str] = field(default_factory=set)  # Unambiguous (weight 1.0)
    keywords_b: Set[str] = field(default_factory=set)  # Strong (weight 0.7)
    keywords_c: Set[str] = field(default_factory=set)  # Ambiguous (weight 0.3)
    threshold: float = 0.6  # Minimum score to approve


SECTORS: Dict[str, SectorConfig] = {
    # EPI-only contextual rule: handled at filter level via EPI_ONLY_KEYWORDS.
    # When calling filter_licitacao for vestuario, pass epi_only_keywords=EPI_ONLY_KEYWORDS
    # to reject procurements matching ONLY generic EPI terms without clothing context.
    "vestuario": SectorConfig(
        id="vestuario",
        name="Vestuário e Uniformes",
        description="Uniformes, fardamentos, roupas profissionais, EPIs de vestuário",
        keywords=KEYWORDS_UNIFORMES,
        exclusions=KEYWORDS_EXCLUSAO,
        keywords_a={
            "uniforme", "uniformes", "fardamento", "fardamentos", "farda", "fardas",
            "jaleco", "jalecos", "camiseta", "camisetas",
            "calça", "calças", "vestuario", "vestimenta", "vestimentas",
            "roupa", "roupas", "roupa profissional", "vestuario profissional",
            "indumentaria", "guarda-pó", "guarda-pós",
            "uniforme escolar", "uniforme hospitalar", "uniforme administrativo",
            "uniforme esportivo", "uniformes esportivos", "uniforme profissional",
            "fardamento militar", "fardamento escolar",
            "kit uniforme", "conjunto uniforme",
            "confecção de uniforme", "confecção de uniformes",
            "confeccao de uniforme", "confeccao de uniformes",
            "aquisição de uniforme", "aquisição de uniformes",
            "fornecimento de uniforme", "fornecimento de uniformes",
            "aquisição de vestuario", "fornecimento de vestuario",
            "aquisição de fardamento", "fornecimento de fardamento",
            "macacão", "macacoes",
            "bermuda", "bermudas", "saia", "saias",
            "sapato", "sapatos",
        },
        keywords_b={
            "camisa", "camisas", "camisa polo", "camisas polo",
            "blusa", "blusas",
            "agasalho", "agasalhos",
            "jaqueta", "jaquetas",
            "gandola", "gandolas",
            "jardineira", "jardineiras",
            "boné", "bonés",
            "confecção de camiseta", "confecção de camisetas",
            "confeccao de camiseta", "confeccao de camisetas",
            "epi vestuario", "epi vestimenta",
        },
        keywords_c={
            "epi", "epis",
            "equipamento de protecao individual", "equipamentos de protecao individual",
            "confecção", "confecções", "confeccao", "confeccoes",
            "costura",
            "bota", "botas",
            "meia", "meias",
            "avental", "aventais",
            "colete", "coletes",
        },
    ),
    "alimentos": SectorConfig(
        id="alimentos",
        name="Alimentos e Merenda",
        description="Gêneros alimentícios, merenda escolar, refeições, rancho",
        keywords={
            "genero alimenticio", "generos alimenticios",
            "gênero alimentício", "gêneros alimentícios",
            "merenda", "merenda escolar",
            "refeição", "refeicao", "refeições", "refeicoes",
            "rancho militar",
            "cesta basica", "cesta básica",
            "kit alimentação", "kit alimentacao",
            "fornecimento de alimentação", "fornecimento de alimentacao",
            "serviço de alimentação", "servico de alimentacao",
            "aquisição de alimentos", "aquisicao de alimentos",
            "carne bovina", "carne suina", "carne suína",
            "leite", "laticinio", "laticinios", "laticínio", "laticínios",
            "arroz", "feijão", "feijao", "farinha",
            "açúcar", "acucar",
            "hortifruti", "hortifrutigranjeiro",
            "água mineral", "agua mineral",
            "biscoito", "biscoitos", "bolacha", "bolachas",
            "macarrão", "macarrao",
            "conserva", "conservas", "enlatado", "enlatados",
            "congelado", "congelados",
            "sal", "óleo", "oleo", "café", "cafe",
            "fruta", "frutas", "verdura", "verduras", "legume", "legumes",
            "carne", "frango", "peixe",
            "pão", "pao", "pães", "paes",
            "bebida", "bebidas", "suco", "sucos",
        },
        keywords_a={
            "genero alimenticio", "generos alimenticios",
            "gênero alimentício", "gêneros alimentícios",
            "merenda", "merenda escolar",
            "cesta basica", "cesta básica",
            "carne bovina", "carne suina", "carne suína",
            "arroz",
            "kit alimentação", "kit alimentacao",
            "fornecimento de alimentação", "fornecimento de alimentacao",
            "serviço de alimentação", "servico de alimentacao",
            "aquisição de alimentos", "aquisicao de alimentos",
            "rancho militar",
            "hortifruti", "hortifrutigranjeiro",
            "açúcar", "acucar",
            "água mineral", "agua mineral",
            "congelado", "congelados",
            "conserva", "conservas", "enlatado", "enlatados",
        },
        keywords_b={
            "leite", "laticinio", "laticinios", "laticínio", "laticínios",
            "feijão", "feijao", "farinha",
            "biscoito", "biscoitos", "bolacha", "bolachas",
            "macarrão", "macarrao",
            "refeição", "refeicao", "refeições", "refeicoes",
            "suco", "sucos",
            "verdura", "verduras", "legume", "legumes",
            # Standalone food terms — legitimate when alone (FPs guarded by exclusions)
            "café", "cafe",
            "óleo", "oleo",
            "sal",
            "carne", "frango", "peixe",
            "bebida", "bebidas",
            "fruta", "frutas",
            "pão", "pao", "pães", "paes",
        },
        keywords_c=set(),  # No tier C for alimentos — exclusions handle FPs
        exclusions={
            # "alimentação" in non-food context
            "alimentação de dados",
            "alimentação elétrica", "alimentacao eletrica",
            "alimentação de energia", "alimentacao de energia",
            "alimentação ininterrupta", "alimentacao ininterrupta",
            "fonte de alimentação", "fonte de alimentacao",
            # "sal" in non-food context
            "sal de audiência", "sal de audiencia",
            "salário", "salario",
            # "óleo" in non-food context
            "óleo lubrificante", "oleo lubrificante",
            "óleo diesel", "oleo diesel",
            "óleo hidráulico", "oleo hidraulico",
            "troca de óleo", "troca de oleo",
            # "oleo" in automotive context (complement existing)
            "oleo de motor", "óleo de motor",
            "oleo 2 tempos", "óleo 2 tempos",
            "oleo dois tempos", "óleo dois tempos",
            "oleo de motosserra", "óleo de motosserra",
            "oleo de rocadeira", "óleo de roçadeira",
            # "cafe" as equipment (not food)
            "moinho para cafe", "moinho para café",
            "moinho de cafe", "moinho de café",
            "maquina de cafe", "máquina de café",
            "cafeteira",
            # "bebida" — exclude non-procurement
            "bebida alcoólica", "bebida alcoolica",
        },
    ),
    "informatica": SectorConfig(
        id="informatica",
        name="Informática e Tecnologia",
        description="Computadores, servidores, software, periféricos, redes",
        keywords={
            "computador", "computadores",
            "notebook", "notebooks",
            "desktop", "desktops",
            "impressora", "impressoras",
            "scanner", "scanners",
            "teclado", "teclados",
            "nobreak", "nobreaks",
            "software", "softwares",
            "licença de software", "licenca de software",
            "sistema operacional",
            "antivirus", "antivírus",
            "firewall",
            "roteador", "roteadores",
            "cabo de rede", "cabeamento estruturado",
            "memória ram", "memoria ram",
            "processador", "processadores",
            "tablet", "tablets",
            "toner", "toners", "cartucho", "cartuchos",
            "informática", "informatica",
            "tecnologia da informação", "tecnologia da informacao",
            "equipamento de informatica", "equipamento de informática",
            "servidor", "servidores",
            "monitor", "monitores",
            "mouse", "mouses",
            "switch", "switches",
            "hd", "ssd", "storage",
            "projetor", "projetores",
            "placa de video", "placa de vídeo",
        },
        keywords_a={
            "notebook", "notebooks", "impressora", "impressoras",
            "software", "softwares", "licença de software", "licenca de software",
            "toner", "toners", "cartucho", "cartuchos",
            "nobreak", "nobreaks", "firewall",
            "roteador", "roteadores",
            "informática", "informatica",
            "tecnologia da informação", "tecnologia da informacao",
            "equipamento de informatica", "equipamento de informática",
            "cabo de rede", "cabeamento estruturado",
            "memória ram", "memoria ram",
            "processador", "processadores",
            "sistema operacional",
            "teclado", "teclados",
            "placa de video", "placa de vídeo",
        },
        keywords_b={
            "computador", "computadores",
            "desktop", "desktops",
            "scanner", "scanners",
            "tablet", "tablets",
            "antivirus", "antivírus",
            "mouse", "mouses",
        },
        keywords_c={
            "servidor", "servidores",
            "monitor", "monitores",
            "switch", "switches",
            "hd", "ssd", "storage",
            "projetor", "projetores",
        },
        exclusions={
            "informática educativa",
            # "servidor" in non-IT context (people, not machines)
            "servidor público", "servidor publico",
            "servidores públicos", "servidores publicos",
            "servidor municipal", "servidores municipais",
            "servidor efetivo", "servidores efetivos",
            "servidor estadual", "servidores estaduais",
            "servidor federal", "servidores federais",
            "servidor comissionado", "servidores comissionados",
            "servidor temporário", "servidor temporario",
            "servidores temporários", "servidores temporarios",
            "servidor ativo", "servidores ativos",
            "servidor inativo", "servidores inativos",
            "remuneração dos servidores", "remuneracao dos servidores",
            "salário dos servidores", "salario dos servidores",
            "pagamento dos servidores",
            "folha de pagamento dos servidores",
            "servidores e colaboradores",
            "proteção dos servidores", "protecao dos servidores",
            # "servidores" in beneficiary/professional context
            "destinados aos servidores", "destinado aos servidores",
            "para os servidores", "para servidores",
            "dos servidores", "aos servidores",
            "servidores e vereadores", "vereadores e servidores",
            "servidores das secretarias",
            "servidores da prefeitura",
            "servidores da camara", "servidores da câmara",
            "servidores do municipio", "servidores do município",
            "uso dos servidores",
            "consumo dos servidores",
            "servidores que trabalham",
            "servidores que realizam",
            "formacao de servidores", "formação de servidores",
            "capacitacao de servidores", "capacitação de servidores",
            "qualificacao de servidores", "qualificação de servidores",
            "treinamento de servidores",
            # "monitor" in non-IT context
            "monitor de aluno", "monitor de alunos",
            "monitor de pátio", "monitor de patio",
            "monitor de transporte",
            "monitor social",
            # "monitor" in medical/health context
            "monitor de glicose",
            "monitor de pressao", "monitor de pressão",
            "glicosimetro", "glicosímetro",
            # "monitor" in education context
            "monitor escolar",
            "monitores escolares",
            # "switch" in non-IT context (unlikely but guard)
            "switch grass",
        },
    ),
    "limpeza": SectorConfig(
        id="limpeza",
        name="Produtos de Limpeza",
        description="Materiais de limpeza, higienização, saneantes, descartáveis",
        keywords={
            "material de limpeza", "materiais de limpeza",
            "produto de limpeza", "produtos de limpeza",
            "detergente", "detergentes",
            "desinfetante", "desinfetantes",
            "alvejante", "alvejantes",
            "água sanitária", "agua sanitaria",
            "saneante", "saneantes",
            "papel higienico", "papel higiênico",
            "papel toalha",
            "saco de lixo", "sacos de lixo",
            "luva de limpeza", "luvas de limpeza",
            "vassoura", "vassouras",
            "rodo", "rodos",
            "pano de chão", "pano de chao",
            "esponja", "esponjas",
            "desengordurante",
            "limpa vidro",
            "material de higienização", "material de higienizacao",
            "serviço de limpeza", "servico de limpeza",
            "limpeza e conservação", "limpeza e conservacao",
            "limpeza predial",
            "limpeza",
            "sabão", "sabao", "sabonete",
            "cloro",
            "balde", "baldes",
            "cera",
            "higiene", "higienização", "higienizacao",
            "descartável", "descartaveis", "descartáveis",
            "copa e cozinha",
            "inseticida",
        },
        keywords_a={
            "material de limpeza", "materiais de limpeza",
            "produto de limpeza", "produtos de limpeza",
            "detergente", "detergentes",
            "desinfetante", "desinfetantes",
            "alvejante", "alvejantes",
            "água sanitária", "agua sanitaria",
            "saneante", "saneantes",
            "papel higienico", "papel higiênico",
            "papel toalha",
            "saco de lixo", "sacos de lixo",
            "luva de limpeza", "luvas de limpeza",
            "desengordurante", "limpa vidro",
            "material de higienização", "material de higienizacao",
            "serviço de limpeza", "servico de limpeza",
            "limpeza e conservação", "limpeza e conservacao",
            "limpeza predial",
            "pano de chão", "pano de chao",
            "cloro",
        },
        keywords_b={
            "vassoura", "vassouras",
            "rodo", "rodos",
            "esponja", "esponjas",
            "sabão", "sabao", "sabonete",
            "copa e cozinha",
        },
        keywords_c={
            "limpeza",
            "higiene", "higienização", "higienizacao",
            "descartável", "descartaveis", "descartáveis",
            "cera",
            "balde", "baldes",
            "inseticida",
        },
        exclusions={
            "limpeza de dados",
            "limpeza de terreno", "limpeza de terrenos",
            "limpeza de fossa", "limpeza de fossas",
            "limpeza de código", "limpeza de codigo",
            # "limpeza" in environmental/infrastructure context
            "limpeza de rio", "limpeza de lagoa", "limpeza de canal",
            "limpeza de córrego", "limpeza de corrego",
            "limpeza de bueiro", "limpeza de bueiros",
            "limpeza de galeria", "limpeza de galerias",
            "desassoreamento",
            "escavadeira",
            # "limpeza" in automotive context
            "limpeza pesada para veículos", "limpeza pesada para veiculos",
            "limpeza automotiva",
            # "inseticida" in pest control services (not cleaning product)
            "nebulização", "nebulizacao",
            "desinsetização", "desinsetizacao",
            "controle de pragas",
            "controle de vetores",
            # "cera" in non-cleaning context
            "cera perdida",  # lost-wax casting
            "cera ortodôntica", "cera ortodontica",
            # "higiene" in non-product context
            "higiene ocupacional",
            "higiene do trabalho",
            # "limpeza" in urban/public services context (not cleaning products)
            "limpeza urbana",
            "limpeza publica", "limpeza pública",
            "limpeza de via", "limpeza de vias",
            "limpeza de estrada", "limpeza de estradas",
            "limpeza de logradouro", "limpeza de logradouros",
            "servico de limpeza urbana", "serviço de limpeza urbana",
            # "descartavel" in medical/surgical context (not cleaning supplies)
            "descartavel cirurgico", "descartável cirúrgico",
            "descartavel hospitalar", "descartável hospitalar",
            "campo cirurgico descartavel", "campo cirúrgico descartável",
            "kit cirurgico descartavel", "kit cirúrgico descartável",
            "avental descartavel", "avental descartável",
            "lencol descartavel", "lençol descartável",
        },
    ),
    "mobiliario": SectorConfig(
        id="mobiliario",
        name="Mobiliário",
        description="Mesas, cadeiras, armários, estantes, móveis de escritório",
        keywords={
            "mobiliário", "mobiliario", "mobília", "mobilia",
            "móvel", "movel", "móveis", "moveis",
            "cadeira", "cadeiras",
            "armário", "armario", "armários", "armarios",
            "estante", "estantes",
            "gaveteiro", "gaveteiros",
            "escrivaninha", "escrivaninhas",
            "sofá", "sofa", "sofás", "sofas",
            "poltrona", "poltronas",
            "prateleira", "prateleiras",
            "birô", "biro",
            "mesa de reunião", "mesa de reuniao",
            "mesa de escritório", "mesa de escritorio",
            "mobiliário escolar", "mobiliario escolar",
            "carteira escolar", "carteiras escolares",
            "móvel planejado", "móveis planejados",
            "movel planejado", "moveis planejados",
            # Restored standalone terms (guarded by exclusions)
            "mesa", "mesas",
            "banco", "bancos",
            "balcão", "balcao",
            "arquivo", "arquivos",
            "rack", "racks",
            "quadro branco", "lousa",
        },
        exclusions={
            "mesa de negociação", "mesa de negociacao",
            "mesa redonda",
            "mesa de cirurgia",
            "mesa de bilhar",
            # "mesa" in non-furniture context (bed/bath linen)
            "roupa de cama mesa e banho",
            "cama mesa e banho",
            "roupa de mesa",
            # "móveis/móvel" in non-furniture context (portable/mobile)
            "equipamentos móveis", "equipamentos moveis",
            "equipamento móvel", "equipamento movel",
            "unidade móvel", "unidade movel",
            "telefonia móvel", "telefonia movel",
            # "banco" in non-furniture context
            "banco de dados",
            "banco central",
            "banco do brasil",
            "banco de sangue",
            "banco de leite",
            "banco de horas",
            "banco de talentos",
            "estabelecimento bancário", "estabelecimento bancario",
            "instituição bancária", "instituicao bancaria",
            # "arquivo" in non-furniture context
            "arquivo morto",
            "arquivo digital",
            "arquivo pdf",
            "arquivo de dados",
            # "rack" in non-furniture context
            "rack de servidor", "rack de servidores",
            "rack de rede",
            # "rack" in IT context (complement existing)
            "rack 19 polegadas",
            "rack de telecomunicacao", "rack de telecomunicação",
            "rack para equipamentos de informatica", "rack para equipamentos de informática",
            # "banco" in financial context (complement existing)
            "servicos bancarios", "serviços bancários",
            "servico bancario", "serviço bancário",
            "arrecadacao bancaria", "arrecadação bancária",
            "taxa bancaria", "taxa bancária",
        },
    ),
    "papelaria": SectorConfig(
        id="papelaria",
        name="Papelaria e Material de Escritório",
        description="Papel, canetas, material de escritório, suprimentos administrativos",
        keywords={
            "papelaria", "material de escritório", "material de escritorio",
            "papel a4", "papel sulfite",
            "caneta", "canetas",
            "lápis", "lapis",
            "grampeador", "grampeadores",
            "clipe", "clipes",
            "envelope", "envelopes",
            "fichário", "fichario",
            "caderno", "cadernos",
            "bloco de notas",
            "fita adesiva", "fita crepe",
            "marca texto", "marca-texto",
            "pincel atômico", "pincel atomico",
            "etiqueta", "etiquetas",
            "calculadora", "calculadoras",
            "material escolar",
            "kit escolar",
            "material de expediente",
            # Restored standalone terms (guarded by exclusions)
            "papel", "papéis", "papeis",
            "borracha", "borrachas",
            "cola", "colas",
            "tesoura", "tesouras",
            "grampo", "grampos",
            "pasta", "pastas",
            "agenda", "agendas",
            "expediente",
        },
        exclusions={
            "papel de parede",
            "papel moeda",
            "papel higiênico", "papel higienico",  # cleaning sector
            "papel toalha",  # cleaning sector
            # "borracha" in non-stationery context
            "borracha natural",
            "borracha de vedação", "borracha de vedacao",
            "pneu",
            # "clipe" in non-stationery context (medical)
            "clipe de aneurisma", "clipes de aneurisma",
            "clipes de aneurismas",
            "opme",  # Órteses, Próteses e Materiais Especiais
            # "cola" in non-stationery context
            "coca cola",
            "cola cirúrgica", "cola cirurgica",
            # "pasta" in non-stationery context
            "pasta de dente", "pasta dental",
            "pasta de solda",
            # "grampo" in non-stationery context
            "grampo cirúrgico", "grampo cirurgico",
            "grampo de cabelo",
            # "agenda" in non-product context
            "agenda de reunião", "agenda de reuniao",
            "agenda legislativa",
            # "expediente" in non-product context
            "horário de expediente", "horario de expediente",
            "fora de expediente",
        },
    ),
    "saude": SectorConfig(
        id="saude",
        name="Saúde e Medicamentos",
        description="Medicamentos, insumos hospitalares, materiais de enfermagem, EPIs hospitalares",
        keywords={
            # Medicamentos - termos compostos (alta precisao)
            "medicamento", "medicamentos",
            "remedio", "remedios", "remédio", "remédios",
            "farmaco", "fármaco", "farmaceutico", "farmacêutico",
            "medicamento generico", "medicamento genérico",
            "medicamento similar", "medicamento de referencia", "medicamento de referência",
            "insumo hospitalar", "insumos hospitalares",
            "material hospitalar", "materiais hospitalares",
            # Formas farmaceuticas
            "comprimido", "comprimidos", "capsula", "capsulas", "cápsula", "cápsulas",
            "ampola", "ampolas", "frasco-ampola",
            "pomada", "pomadas", "creme dermatologico", "creme dermatológico",
            "solucao injetavel", "solução injetável",
            "xarope", "xaropes", "suspensao oral", "suspensão oral",
            # Materiais de enfermagem/curativo
            "seringa", "seringas", "agulha", "agulhas",
            "luva cirurgica", "luva cirúrgica", "luva de procedimento",
            "gaze", "atadura", "ataduras",
            "soro", "soro fisiologico", "soro fisiológico",
            "curativo", "curativos", "material de curativo",
            "cateter", "cateteres", "sonda", "sondas",
            "bisturi", "fio de sutura", "sutura",
            "equipo", "equipos",
            # Categorias terapeuticas
            "anestesico", "anestésico", "antibiotico", "antibiótico",
            "anti-inflamatorio", "anti-inflamatório",
            "analgesico", "analgésico", "antipiretico", "antipirético",
            "vacina", "vacinas", "imunobiologico", "imunobiológico",
            "hemoderivado", "hemoderivados",
            "insulina", "hipoglicemiante",
            # Diagnostico
            "reagente laboratorial", "reagente", "reagentes",
            "kit diagnostico", "kit diagnóstico",
            "teste rapido", "teste rápido", "tira reagente",
            "contraste radiologico", "contraste radiológico",
            # EPIs hospitalares
            "mascara cirurgica", "máscara cirúrgica",
            "avental hospitalar", "avental cirurgico", "avental cirúrgico",
            "touca cirurgica", "touca cirúrgica",
            "propé", "prope",
            # Termos gerais (guardados por exclusions)
            "material de enfermagem",
            "produto farmaceutico", "produto farmacêutico",
            "produto para saude", "produto para saúde",
            "dispositivo medico", "dispositivo médico",
        },
        exclusions={
            # Saude em contexto nao-produto
            "saude financeira", "saúde financeira",
            "saude do solo", "saúde do solo",
            "saude animal", "saúde animal",
            "medicamento veterinario", "medicamento veterinário",
            "uso veterinario", "uso veterinário",
            # Regulatorio (nao e produto)
            "vigilancia sanitaria", "vigilância sanitária",
            "anvisa",
            "registro de medicamento",
            "farmacovigilancia", "farmacovigilância",
            # "soro" em contexto nao-medico
            "soro de leite",
            # "reagente" em contexto quimico industrial
            "reagente quimico industrial",
            # "sonda" em contexto nao-medico
            "sonda de perfuracao", "sonda de perfuração",
            "sonda espacial",
        },
    ),
    "veiculos": SectorConfig(
        id="veiculos",
        name="Veículos, Peças e Combustíveis",
        description="Veículos, peças automotivas, combustíveis, manutenção de frota",
        keywords={
            # Veiculos - termos compostos
            "veiculo", "veiculos", "veículo", "veículos",
            "automovel", "automoveis", "automóvel", "automóveis",
            "caminhao", "caminhoes", "caminhão", "caminhões",
            "onibus", "ônibus",
            "motocicleta", "motocicletas", "moto", "motos",
            "ambulancia", "ambulancias", "ambulância", "ambulâncias",
            "viatura", "viaturas",
            "caminhonete", "caminhonetes", "camionete",
            "van", "vans", "micro-onibus", "micro-ônibus",
            "utilitario", "utilitário",
            # Combustiveis
            "combustivel", "combustiveis", "combustível", "combustíveis",
            "gasolina", "diesel", "oleo diesel", "óleo diesel",
            "etanol", "gnv", "gas natural veicular", "gás natural veicular",
            "abastecimento", "posto de combustivel", "posto de combustível",
            # Pecas e manutencao veicular
            "peca automotiva", "pecas automotivas", "peça automotiva", "peças automotivas",
            "peca de reposicao", "pecas de reposicao", "peça de reposição", "peças de reposição",
            "pneu", "pneus",
            "bateria automotiva", "baterias automotivas",
            "filtro de oleo", "filtro de óleo",
            "filtro de ar", "filtro de combustivel", "filtro de combustível",
            "pastilha de freio", "disco de freio",
            "amortecedor", "amortecedores",
            "lubrificante", "lubrificantes", "oleo lubrificante", "óleo lubrificante",
            # Servicos veiculares
            "retifica", "funilaria", "lanternagem",
            "manutencao veicular", "manutenção veicular",
            "manutencao de frota", "manutenção de frota",
            "locacao de veiculo", "locação de veículo",
            "locacao de veiculos", "locação de veículos",
            "seguro veicular", "seguro de veiculo", "seguro de veículo",
            "rastreamento veicular", "rastreador veicular",
            "lavagem de veiculo", "lavagem de veículo",
            "lavagem de frota",
            "revisao veicular", "revisão veicular",
        },
        exclusions={
            # "veiculo" em contexto nao-automotivo
            "veiculo de comunicacao", "veículo de comunicação",
            "veiculo de imprensa", "veículo de imprensa",
            "veiculo de informacao", "veículo de informação",
            # "pecas" em contexto nao-automotivo
            "pecas de roupa", "peças de roupa",
            "pecas processuais", "peças processuais",
            "pecas juridicas", "peças jurídicas",
            "pecas teatrais", "peças teatrais",
            # "bateria" em contexto nao-automotivo
            "bateria musical", "bateria de cozinha",
            "bateria de testes",
            # "filtro" em contexto nao-automotivo
            "filtro de agua", "filtro de água",
            "filtro de linha",
            "filtro solar",
            # "abastecimento" em contexto nao-combustivel
            "abastecimento de agua", "abastecimento de água",
            "abastecimento hidrico", "abastecimento hídrico",
            # "abastecimento" in public water supply context
            "abastecimento publico", "abastecimento público",
            "sistema de abastecimento de agua", "sistema de abastecimento de água",
        },
    ),
    "engenharia": SectorConfig(
        id="engenharia",
        name="Engenharia e Construção",
        description="Obras, reformas, construção civil, pavimentação, infraestrutura",
        keywords={
            "construção civil", "construcao civil",
            "pavimentação", "pavimentacao",
            "recapeamento", "recapeamento asfaltico", "recapeamento asfáltico",
            "manutenção predial", "manutencao predial",
            "impermeabilização", "impermeabilizacao",
            "pintura predial", "pintura de fachada",
            "instalação elétrica", "instalacao eletrica",
            "instalação hidráulica", "instalacao hidraulica",
            "ar condicionado",
            "climatização", "climatizacao",
            "saneamento básico", "saneamento basico",
            "terraplanagem",
            "projeto arquitetônico", "projeto arquitetonico",
            "laudo técnico", "laudo tecnico",
            "obra de engenharia",
            "serviço de engenharia", "servico de engenharia",
            "alvenaria",
            "concreto armado", "concreto",
            "asfalto", "asfaltamento",
            "drenagem",
            "obra", "obras",
            "reforma", "reformas",
            "engenharia",
            "construção", "construcao",
            "edificação", "edificacao",
            "ampliação", "ampliacao",
            "restauração", "restauracao",
            "demolição", "demolicao",
            "infraestrutura",
            "cimento", "aço", "aco", "ferro",
            "madeira", "tijolo", "tijolos",
            "areia", "brita", "cascalho",
            "telhado", "cobertura",
            "piso", "revestimento",
            "elevador", "elevadores",
        },
        keywords_a={
            "construção civil", "construcao civil",
            "pavimentação", "pavimentacao",
            "recapeamento", "recapeamento asfaltico", "recapeamento asfáltico",
            "alvenaria", "terraplanagem",
            "concreto armado", "concreto",
            "manutenção predial", "manutencao predial",
            "impermeabilização", "impermeabilizacao",
            "pintura predial", "pintura de fachada",
            "instalação elétrica", "instalacao eletrica",
            "instalação hidráulica", "instalacao hidraulica",
            "saneamento básico", "saneamento basico",
            "projeto arquitetônico", "projeto arquitetonico",
            "laudo técnico", "laudo tecnico",
            "obra de engenharia",
            "serviço de engenharia", "servico de engenharia",
            "engenharia",
            "construção", "construcao",
            "edificação", "edificacao",
            "demolição", "demolicao",
            "cimento",
            "elevador", "elevadores",
        },
        keywords_b={
            "obra", "obras",
            "reforma", "reformas",
            "asfalto", "asfaltamento",
            "drenagem",
            "ampliação", "ampliacao",
            "restauração", "restauracao",
            "ar condicionado",
            "climatização", "climatizacao",
            "aço", "aco",
            "tijolo", "tijolos",
            "brita", "cascalho",
            "telhado",
        },
        keywords_c={
            "infraestrutura",
            "cobertura",
            "piso", "revestimento",
            "ferro",
            "madeira",
            "areia",
        },
        exclusions={
            "engenharia de software",
            "engenharia de dados",
            "engenharia social",
            # "reforma" in non-construction context
            "reforma administrativa",
            "reforma tributária", "reforma tributaria",
            "reforma curricular",
            "reforma política", "reforma politica",
            # "restauração" in non-construction context
            "restauração de dados",
            "restauração de arquivo",
            "restauração de backup",
            # "infraestrutura" in IT/telecom context
            "infraestrutura de ti",
            "infraestrutura de rede",
            "infraestrutura de dados",
            "infraestrutura como serviço", "infraestrutura como servico",
            "infraestrutura de comunicação", "infraestrutura de comunicacao",
            "infraestrutura de telecomunicação", "infraestrutura de telecomunicacao",
            "infraestrutura de telefonia",
            # "infraestrutura" in events/temporary context
            "infraestrutura temporária", "infraestrutura temporaria",
            "infraestrutura para evento", "infraestrutura para eventos",
            # "infraestrutura" as department name (not construction)
            "secretaria de infraestrutura",
            "secretaria da infraestrutura",
            "secretaria municipal de infraestrutura",
            "secretaria municipal da infraestrutura",
            "diretoria de infraestrutura",
            # "obra" in non-construction context (keep specific, avoid blocking legit civil works)
            # NOTE: "mão de obra" removed — too aggressive, blocks legit civil works
            # like "fornecimento de material e mão de obra para reforma"
            # "construção" in non-civil context
            "construção de cenário", "construcao de cenario",
            "construção de cenários", "construcao de cenarios",
            "cenários cenográficos", "cenarios cenograficos",
            # "madeira" in non-construction context
            "carroceria de madeira",
            # "cobertura" in non-construction context
            "cobertura de seguro",
            "cobertura jornalística", "cobertura jornalistica",
            "cobertura vacinal",
            # "ferro" in non-construction context
            "ferro de passar",
            # Automotive services that mention "infraestrutura"
            "serviços de borracharia", "servicos de borracharia",
            # Sports context matching "areia" (sand courts)
            "arbitragem",
            # "infraestrutura" in connectivity/logistics context (not civil works)
            "infraestrutura de conectividade",
            "infraestrutura de fibra", "infraestrutura de fibra optica", "infraestrutura de fibra óptica",
            "infraestrutura produtiva",
            "infraestrutura logistica", "infraestrutura logística",
            # "cobertura" in insurance/aviation/health context (not roofing)
            "cobertura total",
            "cobertura ambulatorial",
            "cobertura veicular",
            "cobertura aerea", "cobertura aérea",
            "cobertura aeronautica", "cobertura aeronáutica",
            "cobertura de casco",
            "cobertura hospitalar",
            "cobertura obstetra", "cobertura obstétrica",
        },
    ),
    "hospitalar": SectorConfig(
        id="hospitalar",
        name="Equipamentos e Material Hospitalar",
        description="Equipamentos médicos, laboratoriais, odontológicos, mobiliário hospitalar",
        keywords={
            # Equipamentos medicos gerais
            "equipamento medico", "equipamento médico",
            "equipamento hospitalar", "equipamentos hospitalares",
            "aparelho medico", "aparelho médico",
            # Diagnostico por imagem
            "raio-x", "raio x", "aparelho de raio-x",
            "ultrassom", "ultrassonografia",
            "tomografo", "tomógrafo", "tomografia",
            "ressonancia magnetica", "ressonância magnética",
            # Monitoramento e suporte a vida
            "desfibrilador", "desfibriladores",
            "monitor multiparametro", "monitor multiparâmetro",
            "monitor cardiaco", "monitor cardíaco",
            "ventilador pulmonar", "respirador mecanico", "respirador mecânico",
            "bomba de infusao", "bomba de infusão",
            "incubadora neonatal", "incubadora",
            "aparelho de anestesia",
            # Esterilizacao
            "autoclave", "autoclaves",
            "estufa hospitalar", "estufa de esterilizacao", "estufa de esterilização",
            # Laboratorio
            "microscopio", "microscópio",
            "centrifuga laboratorial", "centrífuga laboratorial", "centrifuga", "centrífuga",
            "eletrocardiografo", "eletrocardiógrafo", "ECG",
            "eletroencefalografo", "eletroencefalógrafo",
            # Instrumentos de medicao
            "oximetro", "oxímetro",
            "esfigmomanometro", "esfigmomanômetro",
            "estetoscopio", "estetoscópio",
            # Mobilidade e acessibilidade hospitalar
            "cama hospitalar", "camas hospitalares",
            "maca", "maca hospitalar",
            "cadeira de rodas", "cadeiras de rodas",
            "muleta", "muletas", "andador", "andadores",
            # Orteses, proteses e materiais especiais
            "ortese", "órtese", "orteses", "órteses",
            "protese", "prótese", "proteses", "próteses",
            "OPME",
            # Centro cirurgico
            "mesa cirurgica", "mesa cirúrgica",
            "foco cirurgico", "foco cirúrgico",
            "foco de luz cirurgico", "foco de luz cirúrgico",
            # Odontologia
            "cadeira odontologica", "cadeira odontológica",
            "compressor odontologico", "compressor odontológico",
            "fotopolimerizador",
            "equipo odontologico", "equipo odontológico",
        },
        exclusions={
            # Informatica (evitar confusao com "monitor")
            "equipamento de informatica", "equipamento de informática",
            "equipamento de escritorio", "equipamento de escritório",
            "monitor de video", "monitor de vídeo",
            "monitor LCD", "monitor LED",
            # Mobiliario (evitar confusao com "mesa", "cadeira")
            "mesa de escritorio", "mesa de escritório",
            "mesa de reuniao", "mesa de reunião",
            "cadeira de escritorio", "cadeira de escritório",
            "cadeira giratoria", "cadeira giratória",
            # Respirador como EPI generico
            "respirador de EPI", "respirador descartavel", "respirador descartável",
            # Centrifuga industrial
            "centrifuga industrial", "centrífuga industrial",
            "centrifuga de acucar", "centrífuga de açúcar",
        },
    ),
    "servicos_gerais": SectorConfig(
        id="servicos_gerais",
        name="Serviços Gerais e Manutenção",
        description="Manutenção predial, facilities, jardinagem, controle de pragas, portaria, zeladoria",
        keywords={
            # Termos gerais
            "servicos gerais", "serviços gerais",
            "servico terceirizado", "serviço terceirizado",
            "terceirizacao", "terceirização",
            "facilities", "facility management",
            # Manutencao predial (HVAC, elevadores)
            "manutencao de ar condicionado", "manutenção de ar condicionado",
            "manutencao de climatizacao", "manutenção de climatização",
            "manutencao de elevador", "manutenção de elevador",
            "manutencao de elevadores", "manutenção de elevadores",
            # Jardinagem e paisagismo
            "jardinagem", "paisagismo",
            "poda de arvore", "poda de árvore", "poda de arvores", "poda de árvores",
            "rocagem", "roçagem", "rocada", "roçada",
            # Controle de pragas
            "controle de pragas", "dedetizacao", "dedetização",
            "desinsetizacao", "desinsetização",
            "desratizacao", "desratização",
            # Portaria e recepcao
            "servico de portaria", "serviço de portaria",
            "porteiro", "porteiros",
            "recepcao", "recepção", "recepcionista",
            "servico de recepcao", "serviço de recepção",
            # Copa e copeiragem
            "copeiragem", "copeiro", "copeira",
            # Lavanderia
            "lavanderia hospitalar", "lavanderia industrial",
            # Zeladoria
            "zeladoria", "zelador",
            # Prevencao e combate a incendio
            "brigada de incendio", "brigada de incêndio",
            "AVCB", "PPCI",
            "recarga de extintor", "extintor de incendio", "extintor de incêndio",
            # Manutencao de sistemas prediais
            "manutencao de grupo gerador", "manutenção de grupo gerador",
            "grupo gerador",
            "manutencao eletrica", "manutenção elétrica",
            "manutencao hidraulica", "manutenção hidráulica",
            "manutencao de subestacao", "manutenção de subestação",
            "manutencao preventiva predial", "manutenção preventiva predial",
            # Servicos especificos
            "limpeza de caixa d'agua", "limpeza de caixa d'água",
            "manutencao de piscina", "manutenção de piscina",
            "tratamento de piscina",
        },
        exclusions={
            # Manutencao em contexto de TI
            "manutencao de software", "manutenção de software",
            "manutencao de sistema", "manutenção de sistema",
            "manutencao de rede", "manutenção de rede",
            "manutencao de computador", "manutenção de computador",
            # Manutencao veicular (setor veiculos)
            "manutencao de veiculo", "manutenção de veículo",
            "manutencao de frota", "manutenção de frota",
            "manutencao veicular", "manutenção veicular",
            "manutencao automotiva", "manutenção automotiva",
            # Manutencao de equipamento medico (setor hospitalar)
            "manutencao de equipamento medico", "manutenção de equipamento médico",
            "manutencao de equipamento hospitalar", "manutenção de equipamento hospitalar",
            # Manutencao de infraestrutura viaria (setor engenharia)
            "manutencao de estrada", "manutenção de estrada",
            "manutencao de rodovia", "manutenção de rodovia",
            "manutencao de ponte", "manutenção de ponte",
            "manutencao de pavimento", "manutenção de pavimento",
            # Servicos intelectuais/profissionais (nao sao servicos gerais)
            "servico de consultoria", "serviço de consultoria",
            "servico de auditoria", "serviço de auditoria",
            "servico de contabilidade", "serviço de contabilidade",
            "servico juridico", "serviço jurídico",
            # "terceirizacao" em contexto generico/politico
            "lei de terceirizacao", "lei de terceirização",
            "reforma trabalhista",
        },
    ),
    "seguranca": SectorConfig(
        id="seguranca",
        name="Segurança e Vigilância",
        description="Vigilância patrimonial, monitoramento eletrônico, controle de acesso, CFTV",
        keywords={
            # Vigilancia
            "vigilancia", "vigilância",
            "vigilancia patrimonial", "vigilância patrimonial",
            "vigilancia armada", "vigilância armada",
            "vigilancia desarmada", "vigilância desarmada",
            "vigilante", "vigilantes",
            # Seguranca patrimonial (termos compostos - alta precisao)
            "seguranca patrimonial", "segurança patrimonial",
            "seguranca armada", "segurança armada",
            "seguranca desarmada", "segurança desarmada",
            # Monitoramento eletronico
            "monitoramento eletronico", "monitoramento eletrônico",
            "monitoramento de alarme", "monitoramento de alarmes",
            "camera de seguranca", "câmera de segurança",
            "camera de monitoramento", "câmera de monitoramento",
            "CFTV", "circuito fechado de televisao", "circuito fechado de televisão",
            "circuito fechado",
            "DVR", "NVR", "camera IP", "câmera IP", "camera dome", "câmera dome",
            # Alarmes
            "alarme", "alarme monitorado", "central de alarme",
            # Barreiras fisicas
            "cerca eletrica", "cerca elétrica",
            "cerca concertina", "concertina",
            # Controle de acesso
            "controle de acesso",
            "catraca", "catracas",
            "cancela", "cancelas",
            "torniquete",
            "portaria eletronica", "portaria eletrônica",
            "portaria remota",
            "guarita",
            # Biometria
            "biometria", "leitor biometrico", "leitor biométrico",
            # Ronda e escolta
            "ronda", "ronda motorizada", "ronda noturna",
            "escolta", "escolta armada",
            # Deteccao
            "detector de metais", "detector de metal",
            "raio-x de bagagem",
        },
        exclusions={
            # Seguranca do trabalho / ocupacional
            "seguranca do trabalho", "segurança do trabalho",
            "seguranca ocupacional", "segurança ocupacional",
            "seguranca e saude do trabalho", "segurança e saúde do trabalho",
            "SESMT", "CIPA",
            # Seguranca alimentar
            "seguranca alimentar", "segurança alimentar",
            "seguranca nutricional", "segurança nutricional",
            # Seguranca da informacao / cyber
            "seguranca da informacao", "segurança da informação",
            "seguranca cibernetica", "segurança cibernética",
            "cybersecurity", "ciberseguranca", "cibersegurança",
            # Seguranca publica (policia, nao terceirizado)
            "seguranca publica", "segurança pública",
            "defesa nacional",
            # Outros contextos de "seguranca"
            "seguranca viaria", "segurança viária",
            "seguranca no transito", "segurança no trânsito",
            "seguranca sanitaria", "segurança sanitária",
            "seguranca juridica", "segurança jurídica",
            "seguranca hidrica", "segurança hídrica",
            # Vigilancia em contexto nao-patrimonial
            "vigilancia sanitaria", "vigilância sanitária",
            "vigilancia epidemiologica", "vigilância epidemiológica",
            "vigilancia em saude", "vigilância em saúde",
            # Orgaos/conselhos (nao sao servicos)
            "conselho de seguranca", "conselho de segurança",
            "secretaria de seguranca", "secretaria de segurança",
            # "alarme" em contexto nao-seguranca
            "alarme falso",
            "falso alarme",
            # "vigilancia" in public health/environmental context
            "vigilancia de vetores", "vigilância de vetores",
            "vigilancia de zoonoses", "vigilância de zoonoses",
            "vigilancia ambiental", "vigilância ambiental",
        },
    ),
}


def get_sector(sector_id: str) -> SectorConfig:
    """
    Get sector configuration by ID.

    Args:
        sector_id: Sector identifier (e.g., "vestuario", "alimentos")

    Returns:
        SectorConfig for the requested sector

    Raises:
        KeyError: If sector_id not found
    """
    if sector_id not in SECTORS:
        raise KeyError(
            f"Setor '{sector_id}' não encontrado. "
            f"Setores disponíveis: {list(SECTORS.keys())}"
        )
    return SECTORS[sector_id]


def list_sectors() -> List[dict]:
    """
    List all available sectors for frontend consumption.

    Returns:
        List of dicts with id, name, description for each sector.
    """
    return [
        {"id": s.id, "name": s.name, "description": s.description}
        for s in SECTORS.values()
    ]
