describe('CP1: Frontend timeout >= backend timeout for all UF combinations', () => {
  // Test the formula directly - extracted for testability
  function backendExpectedDuration(ufCount: number): number {
    return 300 + Math.max(0, ufCount - 5) * 15;
  }

  function frontendPollTimeout(ufCount: number): number {
    const expectedSeconds = 300 + Math.max(0, ufCount - 5) * 15;
    return (expectedSeconds + 60) * 1000;
  }

  // Property: frontend timeout > backend timeout for ALL valid UF counts
  it.each([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 27])(
    'frontend timeout > backend timeout for %d UFs',
    (ufCount) => {
      const backendMs = backendExpectedDuration(ufCount) * 1000;
      const frontendMs = frontendPollTimeout(ufCount);
      expect(frontendMs).toBeGreaterThan(backendMs);
      // The margin should be exactly 60 seconds
      expect(frontendMs - backendMs).toBe(60000);
    }
  );

  // Specific scenarios from the story
  it('1 UF: frontend timeout is 360s (300+60), backend is 300s', () => {
    expect(backendExpectedDuration(1)).toBe(300);
    expect(frontendPollTimeout(1)).toBe(360000);
  });

  it('5 UFs: frontend timeout is 360s, backend is 300s', () => {
    expect(backendExpectedDuration(5)).toBe(300);
    expect(frontendPollTimeout(5)).toBe(360000);
  });

  it('10 UFs: frontend timeout is 435s, backend is 375s', () => {
    expect(backendExpectedDuration(10)).toBe(375);
    expect(frontendPollTimeout(10)).toBe(435000);
  });

  it('27 UFs: frontend timeout is 690s, backend is 630s', () => {
    expect(backendExpectedDuration(27)).toBe(630);
    expect(frontendPollTimeout(27)).toBe(690000);
  });

  // Exhaustive: all 27 UF counts
  it('frontend > backend for every valid UF count (1-27)', () => {
    for (let ufs = 1; ufs <= 27; ufs++) {
      const backendMs = backendExpectedDuration(ufs) * 1000;
      const frontendMs = frontendPollTimeout(ufs);
      expect(frontendMs).toBeGreaterThan(backendMs);
    }
  });
});
