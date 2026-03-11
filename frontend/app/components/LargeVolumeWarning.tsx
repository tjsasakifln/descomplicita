"use client";

interface LargeVolumeWarningProps {
  ufCount: number;
  dateRangeDays: number;
}

function estimateMinutes(ufCount: number, days: number): number {
  // Backend formula: 300 + max(0, ufCount - 5) * 15 seconds base
  // Add ~30% for filtering large volumes
  const baseSec = 300 + Math.max(0, ufCount - 5) * 15;
  const filterMultiplier = days > 30 ? 1.3 : 1;
  return Math.ceil((baseSec * filterMultiplier) / 60);
}

export function LargeVolumeWarning({ ufCount, dateRangeDays }: LargeVolumeWarningProps) {
  const showUfWarning = ufCount > 10;
  const showDateWarning = dateRangeDays > 30;

  if (!showUfWarning && !showDateWarning) return null;

  const estimatedMin = estimateMinutes(ufCount, dateRangeDays);
  const combinations = ufCount * 5; // ~5 modalidades per UF

  return (
    <div
      role="status"
      aria-live="polite"
      className="mb-4 p-4 rounded-card border animate-fade-in-up"
      style={{
        backgroundColor: "var(--status-warning-bg)",
        borderColor: "var(--status-warning-border)",
        color: "var(--status-warning-text)",
      }}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg flex-shrink-0 mt-0.5" aria-hidden="true">⏱</span>
        <div className="text-sm space-y-1">
          <p className="font-semibold">
            Busca de grande volume detectada
          </p>
          <ul className="list-disc list-inside space-y-0.5">
            {showUfWarning && (
              <li>{ufCount} estados selecionados ({combinations} combinações UF × modalidade)</li>
            )}
            {showDateWarning && (
              <li>Período de {dateRangeDays} dias selecionado</li>
            )}
            <li>Tempo estimado: ~{estimatedMin} minutos</li>
          </ul>
          <p className="mt-2 opacity-80">
            Considere selecionar menos estados ou um período menor para resultados mais rápidos.
          </p>
        </div>
      </div>
    </div>
  );
}
