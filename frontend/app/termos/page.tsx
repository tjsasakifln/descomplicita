import type { Metadata } from "next";
import Link from "next/link";
import { APP_VERSION } from "../../lib/version";

export const metadata: Metadata = {
  title: "Termos de Uso — DescompLicita",
  description: "Termos de uso da plataforma DescompLicita de busca de licitações e contratos públicos.",
};

export default function TermosPage() {
  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="max-w-4xl mx-auto px-4 py-4 sm:px-6">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-ink-secondary hover:text-ink transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Voltar para a busca
          </Link>
        </div>
      </header>

      <main id="main-content" className="max-w-4xl mx-auto px-4 py-8 sm:px-6 sm:py-12">
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold font-display text-ink">Termos de Uso</h1>
          <p className="text-ink-secondary mt-2 text-sm">
            Última atualização: março de 2026
          </p>
        </div>

        <div className="space-y-8 text-sm sm:text-base text-ink-secondary leading-relaxed">

          <section>
            <h2 className="text-lg font-semibold font-display text-ink mb-3">1. Finalidade da Plataforma</h2>
            <p>
              O <strong className="text-ink">DescompLicita</strong> é uma plataforma de busca e consulta de licitações e contratos
              públicos brasileiros. Nosso objetivo é facilitar o acesso a informações sobre contratações públicas disponíveis em
              fontes oficiais, tornando o processo de prospecção mais simples e eficiente para empresas, fornecedores e cidadãos.
            </p>
            <p className="mt-3">
              A plataforma agrega e apresenta dados de editais, atas de registro de preços e contratos públicos provenientes de
              portais governamentais, sem qualquer envolvimento direto nos processos licitatórios.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold font-display text-ink mb-3">2. Fontes de Dados</h2>
            <p>
              As informações exibidas no DescompLicita são obtidas de fontes públicas oficiais do governo brasileiro, incluindo:
            </p>
            <ul className="list-disc pl-6 mt-3 space-y-1">
              <li>
                <strong className="text-ink">PNCP</strong> — Portal Nacional de Contratações Públicas
                (<a href="https://pncp.gov.br" className="text-brand-blue hover:underline" target="_blank" rel="noopener noreferrer">pncp.gov.br</a>),
                mantido pelo Ministério da Gestão e da Inovação em Serviços Públicos.
              </li>
              <li>
                <strong className="text-ink">Compras.gov.br</strong> — Sistema integrado de administração de serviços gerais
                do Governo Federal.
              </li>
            </ul>
            <p className="mt-3">
              Todos os dados são de domínio público e estão disponíveis nas APIs oficiais dos respectivos portais governamentais.
              O DescompLicita não modifica o conteúdo original dos editais e contratos.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold font-display text-ink mb-3">3. Uso Permitido</h2>
            <p>
              A plataforma é disponibilizada para uso legítimo de consulta e pesquisa. Ao utilizar o DescompLicita, você concorda em:
            </p>
            <ul className="list-disc pl-6 mt-3 space-y-1">
              <li>Utilizar a plataforma apenas para fins lícitos e de boa-fé.</li>
              <li>Não realizar scraping automatizado ou acesso em massa sem autorização prévia.</li>
              <li>Não tentar burlar mecanismos de segurança ou limites de uso da plataforma.</li>
              <li>Não reproduzir ou redistribuir o conteúdo da plataforma de forma que viole direitos autorais ou regulamentos aplicáveis.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold font-display text-ink mb-3">4. Limitações de Uso</h2>
            <p>
              Para garantir a disponibilidade do serviço a todos os usuários, podem ser aplicados limites de requisições por
              período. O uso excessivo que impacte a disponibilidade para outros usuários poderá resultar em suspensão temporária
              do acesso.
            </p>
            <p className="mt-3">
              Os downloads de resultados em formato Excel estão limitados a 10.000 itens por exportação. Para volumes maiores,
              utilize o formato CSV disponível na plataforma.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold font-display text-ink mb-3">5. Isenção de Responsabilidade</h2>
            <p>
              O DescompLicita atua exclusivamente como um agregador de informações públicas. Não nos responsabilizamos por:
            </p>
            <ul className="list-disc pl-6 mt-3 space-y-2">
              <li>
                <strong className="text-ink">Precisão dos dados:</strong> As informações são obtidas diretamente de APIs
                governamentais e podem conter erros, desatualizações ou inconsistências presentes nas fontes originais.
              </li>
              <li>
                <strong className="text-ink">Disponibilidade:</strong> A disponibilidade do serviço depende da estabilidade
                das APIs governamentais, que podem apresentar instabilidades ou alterações sem aviso prévio.
              </li>
              <li>
                <strong className="text-ink">Decisões de negócio:</strong> Qualquer decisão tomada com base nas informações
                exibidas na plataforma é de exclusiva responsabilidade do usuário. Recomendamos sempre verificar os dados
                diretamente nas fontes oficiais antes de participar de processos licitatórios.
              </li>
              <li>
                <strong className="text-ink">Perda de oportunidades:</strong> Não garantimos a completude dos resultados.
                Licitações podem não aparecer nos resultados por limitações técnicas das APIs de origem ou do sistema de busca.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold font-display text-ink mb-3">6. Propriedade Intelectual</h2>
            <p>
              O código-fonte, design, marca e demais elementos da plataforma DescompLicita são protegidos por direitos de
              propriedade intelectual. Os dados exibidos são de domínio público conforme as licenças de abertura dos portais
              governamentais de origem.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold font-display text-ink mb-3">7. Privacidade</h2>
            <p>
              Para utilizar funcionalidades como salvar buscas, coletamos dados mínimos necessários (endereço de e-mail e
              preferências de busca). Não vendemos, alugamos ou compartilhamos seus dados pessoais com terceiros, exceto
              quando exigido por lei. As buscas são registradas para fins de melhoria do serviço e de forma agregada e
              anonimizada para análise de uso.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold font-display text-ink mb-3">8. Alterações nos Termos</h2>
            <p>
              Estes termos podem ser atualizados periodicamente. Alterações significativas serão comunicadas aos usuários
              cadastrados por e-mail. O uso continuado da plataforma após a publicação de alterações implica na aceitação
              dos novos termos.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold font-display text-ink mb-3">9. Contato</h2>
            <p>
              Dúvidas, sugestões ou solicitações relacionadas a estes Termos de Uso ou ao funcionamento da plataforma podem
              ser enviadas para:
            </p>
            <p className="mt-3">
              <a
                href="mailto:contato@descomplicita.com.br"
                className="text-brand-blue hover:underline font-medium"
              >
                contato@descomplicita.com.br
              </a>
            </p>
          </section>

        </div>
      </main>

      <footer className="border-t mt-12 py-6 text-xs text-ink-muted">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>DescompLicita &mdash; Licitações e Contratos de Forma Descomplicada</span>
          <nav aria-label="Links do rodapé" className="flex items-center gap-4">
            <a href="mailto:contato@descomplicita.com.br" className="hover:text-ink transition-colors">Contato</a>
            <a href="/termos" className="hover:text-ink transition-colors" aria-current="page">Termos de Uso</a>
            <span className="tabular-nums font-data">{APP_VERSION}</span>
          </nav>
        </div>
      </footer>
    </div>
  );
}
