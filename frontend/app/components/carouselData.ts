// Pure data module — no "use client", no React hooks.

export type CuriosidadeCategoria = "legislacao" | "estrategia" | "insight" | "dica";

export interface Curiosidade {
  texto: string;
  fonte: string;
  categoria: CuriosidadeCategoria;
  setores?: string[];
}

export const CATEGORIA_CONFIG: Record<
  CuriosidadeCategoria,
  { label: string; header: string; icon: string; bgClass: string; iconBgClass: string; iconTextClass: string }
> = {
  legislacao: {
    label: "Legislação",
    header: "Você sabia?",
    icon: "⚖️",
    bgClass: "bg-blue-50 dark:bg-blue-950/30",
    iconBgClass: "bg-blue-100 dark:bg-blue-900/50",
    iconTextClass: "text-blue-600 dark:text-blue-400",
  },
  estrategia: {
    label: "Estratégia",
    header: "Estratégia",
    icon: "🎯",
    bgClass: "bg-green-50 dark:bg-green-950/30",
    iconBgClass: "bg-green-100 dark:bg-green-900/50",
    iconTextClass: "text-green-600 dark:text-green-400",
  },
  insight: {
    label: "Insight de Mercado",
    header: "Insight de Mercado",
    icon: "📊",
    bgClass: "bg-purple-50 dark:bg-purple-950/30",
    iconBgClass: "bg-purple-100 dark:bg-purple-900/50",
    iconTextClass: "text-purple-600 dark:text-purple-400",
  },
  dica: {
    label: "Dica Descomplicita",
    header: "Dica",
    icon: "💡",
    bgClass: "bg-amber-50 dark:bg-amber-950/30",
    iconBgClass: "bg-amber-100 dark:bg-amber-900/50",
    iconTextClass: "text-amber-600 dark:text-amber-400",
  },
};

export const CURIOSIDADES: Curiosidade[] = [
  // ═══════════════════════════════════════════
  // LEGISLAÇÃO (13 items)
  // ═══════════════════════════════════════════
  {
    texto: "A margem de preferência para produtos nacionais pode chegar a 20% sobre o preço de produtos importados em licitações.",
    fonte: "Lei 14.133/2021, Art. 26",
    categoria: "legislacao",
  },
  {
    texto: "O prazo para impugnação do edital é de até 3 dias úteis antes da abertura para pregão.",
    fonte: "Lei 14.133/2021, Art. 164",
    categoria: "legislacao",
  },
  {
    texto: "A Nova Lei permite que o preço estimado da contratação não conste do edital, sendo sigiloso.",
    fonte: "Lei 14.133/2021, Art. 24",
    categoria: "legislacao",
  },
  {
    texto: "Contratos de serviços continuados podem ser prorrogados por até 10 anos, criando receita recorrente.",
    fonte: "Lei 14.133/2021, Art. 107",
    categoria: "legislacao",
  },
  {
    texto: "A Lei 14.133/2021 substituiu a Lei 8.666/93 após 28 anos de vigência, modernizando as contratações públicas.",
    fonte: "Nova Lei de Licitações",
    categoria: "legislacao",
  },
  {
    texto: "A Nova Lei de Licitações trouxe o diálogo competitivo como nova modalidade de contratação.",
    fonte: "Lei 14.133/2021, Art. 32",
    categoria: "legislacao",
  },
  {
    texto: "A fase de habilitação agora pode ocorrer após o julgamento das propostas na Nova Lei.",
    fonte: "Lei 14.133/2021, Art. 17",
    categoria: "legislacao",
  },
  {
    texto: "A garantia contratual pode ser exigida em até 5% do valor do contrato, ou 10% para obras de grande vulto.",
    fonte: "Lei 14.133/2021, Art. 96",
    categoria: "legislacao",
  },
  {
    texto: "A Nova Lei permite o uso de seguro-garantia com cláusula de retomada, protegendo a Administração em obras.",
    fonte: "Lei 14.133/2021, Art. 102",
    categoria: "legislacao",
  },
  {
    texto: "O critério de julgamento por maior desconto substitui o antigo menor preço global em muitos casos.",
    fonte: "Lei 14.133/2021, Art. 33",
    categoria: "legislacao",
  },
  {
    texto: "A Lei 14.133 exige que todo processo licitatório tenha um agente de contratação designado.",
    fonte: "Lei 14.133/2021, Art. 8",
    categoria: "legislacao",
  },
  {
    texto: "A Lei 14.133 prevê sanções como multa, impedimento e declaração de inidoneidade para licitantes.",
    fonte: "Lei 14.133/2021, Art. 155",
    categoria: "legislacao",
  },
  {
    texto: "Microempresas e EPPs têm tratamento diferenciado com preferência em licitações até R$ 80 mil.",
    fonte: "LC 123/2006, Art. 47-49",
    categoria: "legislacao",
  },

  // ═══════════════════════════════════════════
  // ESTRATÉGIA (13 items)
  // ═══════════════════════════════════════════
  {
    texto: "Analise o histórico de preços de licitações similares antes de montar sua proposta — isso evita precificar acima do mercado.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Forme consórcio com outras empresas para participar de licitações maiores que seu porte individual não atenderia.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Mantenha todas as certidões (FGTS, Receita Federal, Trabalhista) sempre atualizadas para não perder prazos curtos.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Cadastre-se no SICAF e mantenha seu registro atualizado — muitos órgãos federais exigem cadastro prévio.",
    fonte: "Portal de Compras do Governo",
    categoria: "estrategia",
  },
  {
    texto: "Priorize licitações com menos concorrentes: municípios menores e modalidades como tomada de preços costumam ter menos participantes.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Empresas que monitoram licitações diariamente encontram 3x mais oportunidades que as que buscam semanalmente.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Preparar a documentação de habilitação com antecedência e mantê-la atualizada reduz em 70% o risco de desclassificação.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Especialize-se em um nicho de mercado — empresas focadas em segmentos específicos vencem até 40% mais licitações que generalistas.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Leia o edital inteiro com atenção, incluindo anexos e termos de referência — detalhes ignorados são a principal causa de desclassificação.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Monte uma planilha de custos detalhada para cada licitação — propostas com composição de preços clara transmitem mais confiança ao pregoeiro.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Acompanhe as atas de registro de preços vigentes — aderir a uma ARP existente pode garantir contratos sem nova licitação.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Invista em atestados de capacidade técnica — eles são decisivos na fase de habilitação e demonstram experiência prévia comprovada.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },
  {
    texto: "Participe de sessões públicas de licitação mesmo quando não for competir — observar o processo ajuda a entender a dinâmica e se preparar melhor.",
    fonte: "Melhores Práticas de Mercado",
    categoria: "estrategia",
  },

  // ═══════════════════════════════════════════
  // INSIGHT (13 items)
  // ═══════════════════════════════════════════
  {
    texto: "Compras públicas movimentam aproximadamente 12% do PIB brasileiro — mais de R$ 1 trilhão por ano.",
    fonte: "OCDE / Governo Federal",
    categoria: "insight",
  },
  {
    texto: "O pregão eletrônico representa cerca de 80% de todas as modalidades de licitação no Brasil.",
    fonte: "Portais Oficiais de Contratações",
    categoria: "insight",
  },
  {
    texto: "Uniformes escolares têm pico de licitações entre outubro e fevereiro, antes do início do ano letivo.",
    fonte: "Estimativa de Mercado",
    categoria: "insight",
    setores: ["vestuario"],
  },
  {
    texto: "Municípios com menos de 50 mil habitantes concentram grande volume de licitações com menor concorrência.",
    fonte: "IBGE / Governo Federal",
    categoria: "insight",
  },
  {
    texto: "O setor de saúde lidera em volume de licitações, seguido por educação e infraestrutura.",
    fonte: "Portal de Compras do Governo",
    categoria: "insight",
  },
  {
    texto: "O Brasil realiza mais de 40 mil licitações por mês, movimentando bilhões em contratações públicas.",
    fonte: "Portal de Compras do Governo",
    categoria: "insight",
  },
  {
    texto: "Uniformes escolares movimentam cerca de R$ 2 bilhões por ano em licitações públicas.",
    fonte: "Estimativa de Mercado",
    categoria: "insight",
    setores: ["vestuario"],
  },
  {
    texto: "Janeiro e fevereiro concentram 35% das licitações de uniformes escolares — planeje-se com antecedência.",
    fonte: "Estimativa de Mercado",
    categoria: "insight",
    setores: ["vestuario"],
  },
  {
    texto: "O último trimestre do ano fiscal concentra até 30% do orçamento de compras de muitos órgãos públicos, gerando um pico de licitações.",
    fonte: "Portal de Compras do Governo",
    categoria: "insight",
  },
  {
    texto: "Licitações de tecnologia da informação cresceram mais de 25% nos últimos 3 anos, impulsionadas pela transformação digital do setor público.",
    fonte: "Governo Digital / Ministério da Gestão",
    categoria: "insight",
    setores: ["informatica"],
  },
  {
    texto: "Mais de 5.500 municípios brasileiros publicam licitações regularmente — a maioria das oportunidades está fora das capitais.",
    fonte: "IBGE / Governo Federal",
    categoria: "insight",
  },
  {
    texto: "Licitações de alimentação escolar movimentam mais de R$ 4 bilhões por ano pelo PNAE, com preferência para produtores locais.",
    fonte: "FNDE / Governo Federal",
    categoria: "insight",
    setores: ["alimentos"],
  },
  {
    texto: "Cerca de 30% das licitações de pregão eletrônico terminam com desconto superior a 20% sobre o valor estimado.",
    fonte: "Portais Oficiais de Contratações",
    categoria: "insight",
  },

  // ═══════════════════════════════════════════
  // DICA (13 items)
  // ═══════════════════════════════════════════
  {
    texto: "Use a busca por termos específicos para encontrar nichos que o filtro por setor pode não cobrir.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Selecione estados onde você tem capacidade logística — licitar para locais que você não atende desperdiça recursos.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Salve suas buscas favoritas para acompanhar novas oportunidades sem refazer a pesquisa toda vez.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Amplie o período de busca para 30 dias quando quiser uma visão mais completa do mercado.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Exporte o Excel e organize por valor estimado para priorizar as melhores oportunidades primeiro.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Busque em múltiplos setores — muitas licitações de uniformes aparecem junto com material de EPI.",
    fonte: "Descomplicita",
    categoria: "dica",
    setores: ["vestuario"],
  },
  {
    texto: "Combine palavras-chave com filtros de estado para encontrar oportunidades regionais mais relevantes para o seu negócio.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Verifique o prazo de abertura das licitações encontradas — oportunidades com prazo curto exigem documentação já preparada.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Use sinônimos na busca: 'camisa polo', 'camiseta', 'uniforme' podem retornar resultados diferentes e complementares.",
    fonte: "Descomplicita",
    categoria: "dica",
    setores: ["vestuario"],
  },
  {
    texto: "Filtre por modalidade de licitação para focar em pregões eletrônicos, que oferecem maior agilidade e transparência.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Consulte o órgão licitante antes de participar — entender o histórico de compras dele ajuda a calibrar sua proposta.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Acompanhe os resultados das licitações que você não venceu — entender o preço vencedor melhora suas futuras propostas.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
  {
    texto: "Configure alertas para receber notificações quando novas licitações do seu interesse forem publicadas.",
    fonte: "Descomplicita",
    categoria: "dica",
  },
];

export function shuffleBalanced(items: Curiosidade[]): Curiosidade[] {
  // Group by category
  const groups: Record<string, Curiosidade[]> = {};
  for (const item of items) {
    if (!groups[item.categoria]) groups[item.categoria] = [];
    groups[item.categoria].push(item);
  }

  // Shuffle each group (Fisher-Yates)
  for (const key of Object.keys(groups)) {
    const arr = groups[key];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
  }

  // Interleave: round-robin from each category
  const result: Curiosidade[] = [];
  const iterators = Object.values(groups);
  const indices = iterators.map(() => 0);
  let added = true;
  while (added) {
    added = false;
    for (let g = 0; g < iterators.length; g++) {
      if (indices[g] < iterators[g].length) {
        result.push(iterators[g][indices[g]]);
        indices[g]++;
        added = true;
      }
    }
  }
  return result;
}
