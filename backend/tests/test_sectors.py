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
        assert ids == {"vestuario", "alimentos", "informatica", "limpeza", "mobiliario", "papelaria", "engenharia", "saude"}

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
