"""
Tests for multi-sector keyword filtering — based on real PNCP audit (2026-01-29).

Each test case was derived from actual procurement descriptions found in PNCP data.
"""

from filter import match_keywords
from sectors import SECTORS, get_sector, list_sectors


class TestSectorConfig:
    """Tests for sector configuration basics."""

    def test_all_sectors_exist(self):
        sectors = list_sectors()
        ids = {s["id"] for s in sectors}
        assert ids == {"vestuario", "alimentos", "informatica", "limpeza", "mobiliario", "papelaria", "engenharia", "saude", "veiculos", "hospitalar"}

    def test_get_sector_returns_config(self):
        s = get_sector("vestuario")
        assert s.id == "vestuario"
        assert len(s.keywords) > 0

    def test_get_sector_invalid_raises(self):
        import pytest
        with pytest.raises(KeyError):
            get_sector("inexistente")


class TestInformaticaSector:
    """Tests for Informática e Tecnologia sector — audit-derived."""

    def _match(self, texto):
        s = SECTORS["informatica"]
        return match_keywords(texto, s.keywords, s.exclusions)

    def test_matches_notebooks(self):
        ok, kw = self._match("Registro de Preços para aquisição de notebooks para a FIPASE")
        assert ok is True

    def test_matches_toner(self):
        ok, _ = self._match("REGISTRO DE PREÇO PARA AQUISIÇÃO DE RECARGAS DE CARTUCHOS DE TONERS")
        assert ok is True

    def test_matches_desktops_monitors(self):
        ok, _ = self._match("AQUISIÇÃO DE ESTAÇÕES DE TRABALHO (DESKTOPS) E MONITORES")
        assert ok is True

    def test_excludes_servidores_publicos(self):
        """Audit FP: 'servidores públicos' matched 'servidores' keyword."""
        ok, _ = self._match(
            "Registro de preços para aquisição de EPIs destinados à proteção dos servidores públicos"
        )
        assert ok is False

    def test_excludes_pagamento_servidores(self):
        """Audit FP: banking service for civil servants matched 'servidores'."""
        ok, _ = self._match(
            "CONTRATAÇÃO DE ESTABELECIMENTO BANCÁRIO PARA PAGAMENTOS DOS SERVIDORES ATIVOS E INATIVOS"
        )
        assert ok is False

    def test_excludes_folha_pagamento_servidores(self):
        ok, _ = self._match(
            "Contratação de instituição bancária para folha de pagamento dos servidores da Prefeitura"
        )
        assert ok is False


class TestLimpezaSector:
    """Tests for Produtos de Limpeza sector — audit-derived."""

    def _match(self, texto):
        s = SECTORS["limpeza"]
        return match_keywords(texto, s.keywords, s.exclusions)

    def test_matches_material_limpeza(self):
        ok, _ = self._match("AQUISIÇÃO FUTURA DE DIVERSOS MATERIAIS DE LIMPEZA")
        assert ok is True

    def test_matches_saco_de_lixo(self):
        ok, _ = self._match("AQUISICAO DE SACO DE LIXO")
        assert ok is True

    def test_excludes_escavadeira_limpeza(self):
        """Audit FP: excavator for lagoon cleaning matched 'limpeza'."""
        ok, _ = self._match(
            "Aquisição de escavadeira hidráulica anfíbia destinada às atividades de limpeza e desassoreamento da lagoa"
        )
        assert ok is False

    def test_excludes_nebulizacao(self):
        """Audit FP: pest control nebulization matched 'inseticida'."""
        ok, _ = self._match(
            "Registro de preços de serviços de nebulização costal com inseticida fornecido"
        )
        assert ok is False

    def test_excludes_limpeza_veiculos(self):
        """Audit FP: automotive cleaning products matched 'limpeza'."""
        ok, _ = self._match(
            "AQUISIÇÃO DE LUBRIFICANTES E PRODUTOS DE LIMPEZA PESADA PARA VEÍCULOS"
        )
        assert ok is False


class TestMobiliarioSector:
    """Tests for Mobiliário sector — audit-derived."""

    def _match(self, texto):
        s = SECTORS["mobiliario"]
        return match_keywords(texto, s.keywords, s.exclusions)

    def test_matches_mesas_reuniao(self):
        ok, _ = self._match("Aquisição eventual de 80 mesas de reunião")
        assert ok is True

    def test_matches_armario(self):
        ok, _ = self._match("Aquisição de armário vestiário de aço")
        assert ok is True

    def test_excludes_equipamentos_moveis(self):
        """Audit FP: 'EQUIPAMENTOS MÓVEIS (NOTEBOOKS)' matched 'móveis'."""
        ok, _ = self._match("AQUISIÇÃO DE ESTAÇÕES DE TRABALHO (DESKTOPS), EQUIPAMENTOS MÓVEIS (NOTEBOOKS)")
        assert ok is False

    def test_excludes_roupa_cama_mesa_banho(self):
        """Audit FP: 'roupa de cama, mesa e banho' matched 'mesa'."""
        ok, _ = self._match("Aquisição de material de roupa de cama, mesa e banho")
        assert ok is False


class TestPapelariaSector:
    """Tests for Papelaria sector — audit-derived."""

    def _match(self, texto):
        s = SECTORS["papelaria"]
        return match_keywords(texto, s.keywords, s.exclusions)

    def test_matches_papel_sulfite(self):
        ok, _ = self._match("Abertura de Ata de Registro de Preços para aquisição de Papel Sulfite")
        assert ok is True

    def test_matches_material_escolar(self):
        ok, _ = self._match("Aquisição de kits de material escolar")
        assert ok is True

    def test_excludes_clipes_aneurisma(self):
        """Audit FP: surgical clips (OPME) matched 'clipes'."""
        ok, _ = self._match("Aquisição de Material de Consumo, OPME Clipes de Aneurismas")
        assert ok is False


class TestEngenhariaSector:
    """Tests for Engenharia e Construção sector — audit-derived."""

    def _match(self, texto):
        s = SECTORS["engenharia"]
        return match_keywords(texto, s.keywords, s.exclusions)

    def test_matches_materiais_construcao(self):
        ok, _ = self._match("AQUISIÇÃO DE MATERIAIS DE CONSTRUÇÃO DIVERSOS")
        assert ok is True

    def test_matches_concreto(self):
        ok, _ = self._match("REGISTRO DE PREÇOS para eventual aquisição de concreto")
        assert ok is True

    def test_matches_sondagem_geotecnica(self):
        ok, _ = self._match(
            "CONTRATAÇÃO DE EMPRESA PARA PRESTAÇÃO DE SERVIÇOS DE SONDAGEM GEOTÉCNICA — Secretaria de Obras"
        )
        assert ok is True

    def test_allows_mao_de_obra_civil(self):
        """'Mão de obra' should NOT be excluded — legit civil works use this term.

        Audit 2026-01-29: Removing 'mão de obra' exclusion because it blocks
        legitimate items like 'fornecimento de material e mão de obra para reforma'.
        Prefer false positives over false negatives (lost opportunities).
        """
        ok, _ = self._match(
            "CONTRATAÇÃO COM FORNECIMENTO DE MATERIAL E MÃO DE OBRA PARA REVITALIZAÇÃO DA PRAÇA"
        )
        assert ok is True

    def test_excludes_infraestrutura_telecom(self):
        """Audit FP: telecom infrastructure matched 'infraestrutura'."""
        ok, _ = self._match(
            "Contratação para modernizar e ampliar a infraestrutura de comunicação da Prefeitura"
        )
        assert ok is False

    def test_excludes_infraestrutura_temporaria(self):
        """Audit FP: temporary event infrastructure matched 'infraestrutura'."""
        ok, _ = self._match(
            "Prestação de serviços de montagem e desmontagem de infraestrutura temporária para eventos"
        )
        assert ok is False

    def test_excludes_cenarios_cenograficos(self):
        """Audit FP: stage scenography matched 'construção'."""
        ok, _ = self._match(
            "CONTRATAÇÃO PARA CONSTRUÇÃO DE CENÁRIOS CENOGRÁFICOS DESTINADOS À PAIXÃO DE CRISTO"
        )
        assert ok is False

    def test_excludes_secretaria_infraestrutura(self):
        """Audit FP: department name containing 'infraestrutura'."""
        ok, _ = self._match(
            "Contratação de postos de trabalho de auxiliar de serviços gerais — Secretaria de Infraestrutura"
        )
        assert ok is False

    def test_excludes_carroceria_madeira(self):
        """Audit FP: vehicle with wooden body matched 'madeira'."""
        ok, _ = self._match("Locação de caminhão toco com cabine suplementar e carroceria de madeira")
        assert ok is False


class TestSaudeSector:
    """Tests for Saúde e Medicamentos sector."""

    def _match(self, texto):
        s = SECTORS["saude"]
        return match_keywords(texto, s.keywords, s.exclusions)

    # --- True positives ---

    def test_matches_medicamentos(self):
        ok, _ = self._match("AQUISIÇÃO DE MEDICAMENTOS PARA A REDE MUNICIPAL DE SAÚDE")
        assert ok is True

    def test_matches_insumos_hospitalares(self):
        ok, _ = self._match("Registro de Preços para aquisição de insumos hospitalares")
        assert ok is True

    def test_matches_seringas_agulhas(self):
        ok, _ = self._match("AQUISIÇÃO DE SERINGAS E AGULHAS DESCARTÁVEIS")
        assert ok is True

    def test_matches_luva_cirurgica(self):
        ok, _ = self._match("Aquisição de luva cirúrgica estéril")
        assert ok is True

    def test_matches_soro_fisiologico(self):
        ok, _ = self._match("AQUISIÇÃO DE SORO FISIOLÓGICO 500ML")
        assert ok is True

    def test_matches_antibiotico(self):
        ok, _ = self._match("Registro de preços para aquisição de antibiótico injetável")
        assert ok is True

    def test_matches_vacinas(self):
        ok, _ = self._match("AQUISIÇÃO DE VACINAS PARA CAMPANHA DE IMUNIZAÇÃO")
        assert ok is True

    def test_matches_reagente_laboratorial(self):
        ok, _ = self._match("Aquisição de reagente laboratorial para análises clínicas")
        assert ok is True

    def test_matches_curativo(self):
        ok, _ = self._match("AQUISIÇÃO DE MATERIAL DE CURATIVO PARA UBS")
        assert ok is True

    def test_matches_cateter(self):
        ok, _ = self._match("Registro de preços para aquisição de cateteres intravenosos")
        assert ok is True

    def test_matches_kit_diagnostico(self):
        ok, _ = self._match("AQUISIÇÃO DE KIT DIAGNÓSTICO PARA TESTE RÁPIDO DE COVID")
        assert ok is True

    def test_matches_insulina(self):
        ok, _ = self._match("Aquisição de insulina NPH para a rede de saúde")
        assert ok is True

    def test_matches_comprimidos(self):
        ok, _ = self._match("REGISTRO DE PREÇOS PARA AQUISIÇÃO DE COMPRIMIDOS DIVERSOS")
        assert ok is True

    def test_matches_mascara_cirurgica(self):
        ok, _ = self._match("Aquisição de máscara cirúrgica descartável tripla camada")
        assert ok is True

    def test_matches_material_enfermagem(self):
        ok, _ = self._match("AQUISIÇÃO DE MATERIAL DE ENFERMAGEM PARA HOSPITAL MUNICIPAL")
        assert ok is True

    def test_matches_hemoderivados(self):
        ok, _ = self._match("Registro de preços para aquisição de hemoderivados")
        assert ok is True

    def test_matches_avental_hospitalar(self):
        ok, _ = self._match("Aquisição de avental hospitalar descartável")
        assert ok is True

    def test_matches_bisturi(self):
        ok, _ = self._match("AQUISIÇÃO DE BISTURI DESCARTÁVEL N. 23")
        assert ok is True

    def test_matches_fio_sutura(self):
        ok, _ = self._match("Registro de preços para aquisição de fio de sutura absorvível")
        assert ok is True

    def test_matches_equipo(self):
        ok, _ = self._match("AQUISIÇÃO DE EQUIPOS DE SORO MACROGOTAS")
        assert ok is True

    # --- True negatives (exclusions) ---

    def test_excludes_medicamento_veterinario(self):
        ok, _ = self._match("Aquisição de medicamento veterinário para controle de zoonoses")
        assert ok is False

    def test_excludes_uso_veterinario(self):
        ok, _ = self._match("REGISTRO DE PREÇOS PARA AQUISIÇÃO DE SERINGAS DE USO VETERINÁRIO")
        assert ok is False

    def test_excludes_saude_financeira(self):
        ok, _ = self._match("Consultoria para avaliação da saúde financeira do município")
        assert ok is False

    def test_excludes_saude_animal(self):
        ok, _ = self._match("Programa de saúde animal para controle de raiva")
        assert ok is False

    def test_excludes_vigilancia_sanitaria(self):
        ok, _ = self._match("Contratação de serviços de vigilância sanitária municipal")
        assert ok is False

    def test_excludes_soro_de_leite(self):
        ok, _ = self._match("Aquisição de soro de leite em pó para merenda escolar")
        assert ok is False

    def test_excludes_sonda_perfuracao(self):
        ok, _ = self._match("Contratação de sonda de perfuração para poço artesiano")
        assert ok is False

    def test_excludes_sonda_espacial(self):
        ok, _ = self._match("Projeto educacional sobre sonda espacial para escolas")
        assert ok is False

    def test_excludes_anvisa(self):
        ok, _ = self._match("Contratação de consultoria para registro na ANVISA")
        assert ok is False

    def test_excludes_farmacovigilancia(self):
        ok, _ = self._match("Sistema de farmacovigilância para notificação de eventos adversos")
        assert ok is False

    def test_excludes_reagente_quimico_industrial(self):
        ok, _ = self._match("Aquisição de reagente químico industrial para tratamento de água")
        assert ok is False

    def test_excludes_saude_do_solo(self):
        ok, _ = self._match("Análise da saúde do solo para projeto agrícola")
        assert ok is False


class TestVeiculosSector:
    """Tests for Veículos, Peças e Combustíveis sector."""

    def _match(self, texto):
        s = SECTORS["veiculos"]
        return match_keywords(texto, s.keywords, s.exclusions)

    # --- True positives: veiculos ---

    def test_matches_veiculos(self):
        ok, _ = self._match("AQUISIÇÃO DE VEÍCULOS PARA A FROTA MUNICIPAL")
        assert ok is True

    def test_matches_caminhao(self):
        ok, _ = self._match("Registro de preços para aquisição de caminhão basculante")
        assert ok is True

    def test_matches_onibus(self):
        ok, _ = self._match("AQUISIÇÃO DE ÔNIBUS ESCOLAR PARA TRANSPORTE DE ALUNOS")
        assert ok is True

    def test_matches_motocicleta(self):
        ok, _ = self._match("Aquisição de motocicletas para fiscalização de trânsito")
        assert ok is True

    def test_matches_ambulancia(self):
        ok, _ = self._match("AQUISIÇÃO DE AMBULÂNCIA TIPO D PARA O SAMU")
        assert ok is True

    def test_matches_viatura(self):
        ok, _ = self._match("Registro de preços para aquisição de viaturas para a Guarda Municipal")
        assert ok is True

    def test_matches_caminhonete(self):
        ok, _ = self._match("AQUISIÇÃO DE CAMINHONETES 4X4 PARA A SECRETARIA DE OBRAS")
        assert ok is True

    def test_matches_van(self):
        ok, _ = self._match("Aquisição de vans para transporte de pacientes")
        assert ok is True

    def test_matches_utilitario(self):
        ok, _ = self._match("REGISTRO DE PREÇOS PARA AQUISIÇÃO DE VEÍCULO UTILITÁRIO")
        assert ok is True

    # --- True positives: combustiveis ---

    def test_matches_combustivel(self):
        ok, _ = self._match("REGISTRO DE PREÇOS PARA AQUISIÇÃO DE COMBUSTÍVEL")
        assert ok is True

    def test_matches_gasolina(self):
        ok, _ = self._match("Aquisição de gasolina comum para a frota municipal")
        assert ok is True

    def test_matches_diesel(self):
        ok, _ = self._match("AQUISIÇÃO DE ÓLEO DIESEL S10 PARA FROTA")
        assert ok is True

    def test_matches_etanol(self):
        ok, _ = self._match("Registro de preços para fornecimento de etanol hidratado")
        assert ok is True

    def test_matches_abastecimento(self):
        ok, _ = self._match("CONTRATAÇÃO DE POSTO PARA ABASTECIMENTO DA FROTA MUNICIPAL")
        assert ok is True

    # --- True positives: pecas e manutencao ---

    def test_matches_pneus(self):
        ok, _ = self._match("AQUISIÇÃO DE PNEUS PARA VEÍCULOS DA PREFEITURA")
        assert ok is True

    def test_matches_bateria_automotiva(self):
        ok, _ = self._match("Registro de preços para aquisição de baterias automotivas")
        assert ok is True

    def test_matches_filtro_oleo(self):
        ok, _ = self._match("AQUISIÇÃO DE FILTRO DE ÓLEO PARA FROTA")
        assert ok is True

    def test_matches_pastilha_freio(self):
        ok, _ = self._match("Aquisição de pastilha de freio para veículos leves")
        assert ok is True

    def test_matches_amortecedor(self):
        ok, _ = self._match("REGISTRO DE PREÇOS PARA AQUISIÇÃO DE AMORTECEDORES")
        assert ok is True

    def test_matches_lubrificante(self):
        ok, _ = self._match("Aquisição de lubrificantes para manutenção da frota")
        assert ok is True

    def test_matches_pecas_reposicao(self):
        ok, _ = self._match("AQUISIÇÃO DE PEÇAS DE REPOSIÇÃO PARA VEÍCULOS PESADOS")
        assert ok is True

    # --- True positives: servicos veiculares ---

    def test_matches_manutencao_frota(self):
        ok, _ = self._match("CONTRATAÇÃO DE SERVIÇO DE MANUTENÇÃO DE FROTA")
        assert ok is True

    def test_matches_locacao_veiculos(self):
        ok, _ = self._match("Registro de preços para locação de veículos sem motorista")
        assert ok is True

    def test_matches_seguro_veicular(self):
        ok, _ = self._match("CONTRATAÇÃO DE SEGURO VEICULAR PARA A FROTA MUNICIPAL")
        assert ok is True

    def test_matches_rastreamento_veicular(self):
        ok, _ = self._match("Contratação de serviço de rastreamento veicular por GPS")
        assert ok is True

    def test_matches_funilaria(self):
        ok, _ = self._match("CONTRATAÇÃO DE SERVIÇOS DE FUNILARIA E PINTURA AUTOMOTIVA")
        assert ok is True

    def test_matches_revisao_veicular(self):
        ok, _ = self._match("Contratação de serviço de revisão veicular preventiva")
        assert ok is True

    def test_matches_lavagem_frota(self):
        ok, _ = self._match("CONTRATAÇÃO DE SERVIÇO DE LAVAGEM DE FROTA MUNICIPAL")
        assert ok is True

    # --- True negatives (exclusions) ---

    def test_excludes_veiculo_comunicacao(self):
        ok, _ = self._match("Contratação de veículo de comunicação para campanha publicitária")
        assert ok is False

    def test_excludes_veiculo_imprensa(self):
        ok, _ = self._match("Credenciamento de veículo de imprensa para cobertura de eventos")
        assert ok is False

    def test_excludes_veiculo_informacao(self):
        ok, _ = self._match("Desenvolvimento de veículo de informação institucional")
        assert ok is False

    def test_excludes_pecas_processuais(self):
        ok, _ = self._match("Elaboração de peças processuais para a Procuradoria")
        assert ok is False

    def test_excludes_pecas_teatrais(self):
        ok, _ = self._match("Produção de peças teatrais para festival cultural")
        assert ok is False

    def test_excludes_pecas_roupa(self):
        ok, _ = self._match("Aquisição de peças de roupa para abrigo municipal")
        assert ok is False

    def test_excludes_bateria_musical(self):
        ok, _ = self._match("Aquisição de bateria musical para escola de música")
        assert ok is False

    def test_excludes_bateria_cozinha(self):
        ok, _ = self._match("Aquisição de bateria de cozinha para restaurante popular")
        assert ok is False

    def test_excludes_bateria_testes(self):
        ok, _ = self._match("Aplicação de bateria de testes para concurso público")
        assert ok is False

    def test_excludes_filtro_agua(self):
        ok, _ = self._match("Aquisição de filtro de água para escolas municipais")
        assert ok is False

    def test_excludes_filtro_solar(self):
        ok, _ = self._match("Aquisição de filtro solar para agentes de saúde")
        assert ok is False

    def test_excludes_abastecimento_agua(self):
        ok, _ = self._match("Contratação de serviço de abastecimento de água por caminhão-pipa")
        assert ok is False

    def test_excludes_abastecimento_hidrico(self):
        ok, _ = self._match("Projeto de abastecimento hídrico para zona rural")
        assert ok is False

    def test_excludes_pecas_juridicas(self):
        ok, _ = self._match("Confecção de peças jurídicas para defesa do município")
        assert ok is False

    def test_excludes_filtro_linha(self):
        ok, _ = self._match("Aquisição de filtro de linha para equipamentos de informática")
        assert ok is False


class TestAlimentosSector:
    """Tests for Alimentos e Merenda sector — audit-derived."""

    def _match(self, texto):
        s = SECTORS["alimentos"]
        return match_keywords(texto, s.keywords, s.exclusions)

    def test_matches_generos_alimenticios(self):
        ok, _ = self._match("Gêneros Alimentícios Remanescentes")
        assert ok is True

    def test_matches_merenda_escolar(self):
        ok, _ = self._match(
            "REGISTRO DE PREÇOS PARA AQUISIÇÃO DE GÊNEROS ALIMENTÍCIOS PARA MERENDA ESCOLAR"
        )
        assert ok is True

    def test_matches_cafe(self):
        ok, _ = self._match("AQUISIÇÃO PARCELADA DE CAFÉ PARA O ANO DE 2026")
        assert ok is True

    def test_excludes_oleo_diesel(self):
        ok, _ = self._match("Aquisição de óleo diesel para frota municipal")
        assert ok is False

    def test_excludes_oleo_lubrificante(self):
        ok, _ = self._match("Aquisição de óleo lubrificante para máquinas")
        assert ok is False


class TestHospitalarSector:
    """Tests for Equipamentos e Material Hospitalar sector."""

    def _match(self, texto):
        s = SECTORS["hospitalar"]
        return match_keywords(texto, s.keywords, s.exclusions)

    # --- True positives: equipamentos medicos ---

    def test_matches_equipamento_medico(self):
        ok, _ = self._match("AQUISIÇÃO DE EQUIPAMENTO MÉDICO PARA HOSPITAL REGIONAL")
        assert ok is True

    def test_matches_equipamento_hospitalar(self):
        ok, _ = self._match("Registro de preços para aquisição de equipamentos hospitalares")
        assert ok is True

    def test_matches_aparelho_medico(self):
        ok, _ = self._match("AQUISIÇÃO DE APARELHO MÉDICO PARA UPA")
        assert ok is True

    # --- True positives: diagnostico por imagem ---

    def test_matches_raio_x(self):
        ok, _ = self._match("AQUISIÇÃO DE APARELHO DE RAIO-X DIGITAL PARA HOSPITAL")
        assert ok is True

    def test_matches_ultrassom(self):
        ok, _ = self._match("Registro de preços para aquisição de aparelho de ultrassom")
        assert ok is True

    def test_matches_tomografo(self):
        ok, _ = self._match("AQUISIÇÃO DE TOMÓGRAFO COMPUTADORIZADO 64 CANAIS")
        assert ok is True

    def test_matches_ressonancia_magnetica(self):
        ok, _ = self._match("Aquisição de aparelho de ressonância magnética 1.5T")
        assert ok is True

    # --- True positives: monitoramento e suporte a vida ---

    def test_matches_desfibrilador(self):
        ok, _ = self._match("AQUISIÇÃO DE DESFIBRILADOR EXTERNO AUTOMÁTICO")
        assert ok is True

    def test_matches_monitor_multiparametro(self):
        ok, _ = self._match("Registro de preços para aquisição de monitor multiparâmetro")
        assert ok is True

    def test_matches_ventilador_pulmonar(self):
        ok, _ = self._match("AQUISIÇÃO DE VENTILADOR PULMONAR PARA UTI")
        assert ok is True

    def test_matches_bomba_infusao(self):
        ok, _ = self._match("Aquisição de bomba de infusão volumétrica")
        assert ok is True

    def test_matches_incubadora_neonatal(self):
        ok, _ = self._match("AQUISIÇÃO DE INCUBADORA NEONATAL PARA MATERNIDADE")
        assert ok is True

    def test_matches_aparelho_anestesia(self):
        ok, _ = self._match("Registro de preços para aquisição de aparelho de anestesia")
        assert ok is True

    # --- True positives: esterilizacao ---

    def test_matches_autoclave(self):
        ok, _ = self._match("AQUISIÇÃO DE AUTOCLAVE HOSPITALAR 100 LITROS")
        assert ok is True

    def test_matches_estufa_esterilizacao(self):
        ok, _ = self._match("Aquisição de estufa de esterilização para CME")
        assert ok is True

    # --- True positives: laboratorio ---

    def test_matches_microscopio(self):
        ok, _ = self._match("AQUISIÇÃO DE MICROSCÓPIO BINOCULAR PARA LABORATÓRIO")
        assert ok is True

    def test_matches_centrifuga_laboratorial(self):
        ok, _ = self._match("Registro de preços para aquisição de centrífuga laboratorial")
        assert ok is True

    def test_matches_eletrocardiografo(self):
        ok, _ = self._match("AQUISIÇÃO DE ELETROCARDIÓGRAFO 12 CANAIS")
        assert ok is True

    # --- True positives: instrumentos de medicao ---

    def test_matches_oximetro(self):
        ok, _ = self._match("Aquisição de oxímetro de pulso portátil")
        assert ok is True

    def test_matches_esfigmomanometro(self):
        ok, _ = self._match("AQUISIÇÃO DE ESFIGMOMANÔMETRO ANEROIDE")
        assert ok is True

    def test_matches_estetoscopio(self):
        ok, _ = self._match("Registro de preços para aquisição de estetoscópio")
        assert ok is True

    # --- True positives: mobilidade hospitalar ---

    def test_matches_cama_hospitalar(self):
        ok, _ = self._match("AQUISIÇÃO DE CAMA HOSPITALAR ELÉTRICA COM GRADES")
        assert ok is True

    def test_matches_maca(self):
        ok, _ = self._match("Aquisição de maca hospitalar com rodízios")
        assert ok is True

    def test_matches_cadeira_de_rodas(self):
        ok, _ = self._match("AQUISIÇÃO DE CADEIRA DE RODAS DOBRÁVEL")
        assert ok is True

    def test_matches_muleta(self):
        ok, _ = self._match("Registro de preços para aquisição de muletas e andadores")
        assert ok is True

    # --- True positives: orteses e proteses ---

    def test_matches_opme(self):
        ok, _ = self._match("AQUISIÇÃO DE MATERIAIS OPME PARA CIRURGIAS ORTOPÉDICAS")
        assert ok is True

    def test_matches_protese(self):
        ok, _ = self._match("Registro de preços para aquisição de prótese de quadril")
        assert ok is True

    def test_matches_ortese(self):
        ok, _ = self._match("AQUISIÇÃO DE ÓRTESES PARA REABILITAÇÃO")
        assert ok is True

    # --- True positives: centro cirurgico ---

    def test_matches_mesa_cirurgica(self):
        ok, _ = self._match("AQUISIÇÃO DE MESA CIRÚRGICA COM ACESSÓRIOS")
        assert ok is True

    def test_matches_foco_cirurgico(self):
        ok, _ = self._match("Registro de preços para aquisição de foco cirúrgico LED")
        assert ok is True

    # --- True positives: odontologia ---

    def test_matches_cadeira_odontologica(self):
        ok, _ = self._match("AQUISIÇÃO DE CADEIRA ODONTOLÓGICA COMPLETA")
        assert ok is True

    def test_matches_compressor_odontologico(self):
        ok, _ = self._match("Registro de preços para aquisição de compressor odontológico")
        assert ok is True

    def test_matches_fotopolimerizador(self):
        ok, _ = self._match("AQUISIÇÃO DE FOTOPOLIMERIZADOR LED PARA CONSULTÓRIO")
        assert ok is True

    def test_matches_equipo_odontologico(self):
        ok, _ = self._match("Aquisição de equipo odontológico com refletor")
        assert ok is True

    # --- True negatives (exclusions) ---

    def test_excludes_equipamento_informatica(self):
        """Exclusion: 'equipamento de informática' should not match."""
        ok, _ = self._match("AQUISIÇÃO DE EQUIPAMENTO DE INFORMÁTICA PARA SECRETARIA")
        assert ok is False

    def test_excludes_monitor_video(self):
        """Exclusion: 'monitor de vídeo' should not match via 'monitor'."""
        ok, _ = self._match("Aquisição de monitor de vídeo 24 polegadas para escritório")
        assert ok is False

    def test_excludes_monitor_lcd(self):
        """Exclusion: 'monitor LCD' should not match."""
        ok, _ = self._match("AQUISIÇÃO DE MONITOR LCD PARA ESTAÇÃO DE TRABALHO")
        assert ok is False

    def test_excludes_mesa_escritorio(self):
        """Exclusion: 'mesa de escritório' should not match via 'mesa'."""
        ok, _ = self._match("Aquisição de mesa de escritório com gavetas")
        assert ok is False

    def test_excludes_mesa_reuniao(self):
        """Exclusion: 'mesa de reunião' should not match."""
        ok, _ = self._match("AQUISIÇÃO DE MESA DE REUNIÃO OVAL 12 LUGARES")
        assert ok is False

    def test_excludes_cadeira_escritorio(self):
        """Exclusion: 'cadeira de escritório' should not match via 'cadeira'."""
        ok, _ = self._match("Aquisição de cadeira de escritório ergonômica")
        assert ok is False

    def test_excludes_cadeira_giratoria(self):
        """Exclusion: 'cadeira giratória' should not match."""
        ok, _ = self._match("AQUISIÇÃO DE CADEIRA GIRATÓRIA COM BRAÇO")
        assert ok is False

    def test_excludes_respirador_epi(self):
        """Exclusion: generic EPI respirator should not match."""
        ok, _ = self._match("Aquisição de respirador descartável PFF2 para uso geral")
        assert ok is False

    def test_excludes_centrifuga_industrial(self):
        """Exclusion: industrial centrifuge should not match."""
        ok, _ = self._match("AQUISIÇÃO DE CENTRÍFUGA INDUSTRIAL PARA USINA")
        assert ok is False

    def test_excludes_centrifuga_acucar(self):
        """Exclusion: sugar centrifuge should not match."""
        ok, _ = self._match("Aquisição de centrífuga de açúcar para indústria alimentícia")
        assert ok is False

    def test_excludes_equipamento_escritorio(self):
        """Exclusion: office equipment should not match."""
        ok, _ = self._match("AQUISIÇÃO DE EQUIPAMENTO DE ESCRITÓRIO PARA ADMINISTRAÇÃO")
        assert ok is False

    # --- Cross-sector overlap: hospitalar vs saude ---

    def test_no_false_match_medicamentos(self):
        """Should NOT match pure medication procurement (saude sector)."""
        ok, _ = self._match("AQUISIÇÃO DE MEDICAMENTOS PARA A REDE MUNICIPAL DE SAÚDE")
        assert ok is False

    def test_no_false_match_seringas(self):
        """Should NOT match consumable supplies (saude sector)."""
        ok, _ = self._match("AQUISIÇÃO DE SERINGAS E AGULHAS DESCARTÁVEIS")
        assert ok is False

    def test_no_false_match_soro(self):
        """Should NOT match IV fluids (saude sector)."""
        ok, _ = self._match("AQUISIÇÃO DE SORO FISIOLÓGICO 500ML")
        assert ok is False
