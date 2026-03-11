import { dateDiffInDays } from '@/lib/utils';

describe('dateDiffInDays', () => {
  it('returns correct difference for 7-day range', () => {
    expect(dateDiffInDays('2026-01-01', '2026-01-08')).toBe(7);
  });

  it('returns correct difference regardless of order', () => {
    expect(dateDiffInDays('2026-01-08', '2026-01-01')).toBe(7);
  });

  it('returns 0 for same day', () => {
    expect(dateDiffInDays('2026-03-10', '2026-03-10')).toBe(0);
  });

  it('handles month boundaries', () => {
    expect(dateDiffInDays('2026-01-30', '2026-02-01')).toBe(2);
  });

  it('handles leap year', () => {
    expect(dateDiffInDays('2024-02-28', '2024-03-01')).toBe(2);
  });

  it('handles large ranges', () => {
    expect(dateDiffInDays('2025-01-01', '2026-01-01')).toBe(365);
  });
});
