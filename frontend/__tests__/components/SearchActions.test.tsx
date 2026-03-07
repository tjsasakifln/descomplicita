import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchActions } from '@/app/components/SearchActions';
import type { BuscaResult } from '@/app/types';

const mockResult: BuscaResult = {
  resumo: {
    resumo_executivo: 'Test',
    total_oportunidades: 15,
    valor_total: 450000,
    destaques: [],
    distribuicao_uf: {},
    alerta_urgencia: null,
  },
  download_id: 'dl-1',
  total_raw: 200,
  total_filtrado: 15,
  total_atas: 0,
  total_licitacoes: 15,
  filter_stats: null,
  sources_used: [],
  source_stats: {},
  dedup_removed: 0,
  truncated_combos: 0,
};

describe('SearchActions', () => {
  const defaultProps = {
    result: mockResult,
    rawCount: 200,
    sectorName: 'Vestuário e Uniformes',
    downloadLoading: false,
    downloadError: null,
    isMaxCapacity: false,
    onDownload: jest.fn(),
    onSaveSearch: jest.fn(),
  };

  it('should render download button', () => {
    render(<SearchActions {...defaultProps} />);
    expect(screen.getByRole('button', { name: /Baixar Excel/i })).toBeInTheDocument();
  });

  it('should display opportunity count in download button', () => {
    render(<SearchActions {...defaultProps} />);
    expect(screen.getByText(/15 licitações/)).toBeInTheDocument();
  });

  it('should call onDownload when download clicked', () => {
    render(<SearchActions {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /Baixar Excel/i }));
    expect(defaultProps.onDownload).toHaveBeenCalled();
  });

  it('should show loading state when downloading', () => {
    render(<SearchActions {...defaultProps} downloadLoading={true} />);
    expect(screen.getByText('Preparando download...')).toBeInTheDocument();
  });

  it('should render save search button', () => {
    render(<SearchActions {...defaultProps} />);
    expect(screen.getByText('Salvar Busca')).toBeInTheDocument();
  });

  it('should call onSaveSearch when save clicked', () => {
    render(<SearchActions {...defaultProps} />);
    fireEvent.click(screen.getByText('Salvar Busca'));
    expect(defaultProps.onSaveSearch).toHaveBeenCalled();
  });

  it('should disable save button when at max capacity', () => {
    render(<SearchActions {...defaultProps} isMaxCapacity={true} />);
    expect(screen.getByText('Limite de buscas atingido')).toBeInTheDocument();
  });

  it('should display download error', () => {
    render(<SearchActions {...defaultProps} downloadError="Arquivo expirado" />);
    expect(screen.getByText('Arquivo expirado')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('should display stats when rawCount > 0', () => {
    render(<SearchActions {...defaultProps} />);
    expect(screen.getByText(/Encontradas 15 de 200/)).toBeInTheDocument();
  });

  it('should not display stats when rawCount is 0', () => {
    render(<SearchActions {...defaultProps} rawCount={0} />);
    expect(screen.queryByText(/Encontradas/)).not.toBeInTheDocument();
  });
});
