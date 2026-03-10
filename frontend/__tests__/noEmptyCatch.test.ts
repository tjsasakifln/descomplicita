import * as fs from 'fs';
import * as path from 'path';

function getAllTsFiles(dir: string): string[] {
  const results: string[] = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === '.next' || entry.name === 'coverage') continue;
      results.push(...getAllTsFiles(fullPath));
    } else if (/\.(ts|tsx)$/.test(entry.name)) {
      results.push(fullPath);
    }
  }
  return results;
}

describe('RT5: No empty catch blocks in frontend', () => {
  const frontendDir = path.resolve(__dirname, '..');
  const files = getAllTsFiles(frontendDir);

  it('should have found TypeScript files to scan', () => {
    expect(files.length).toBeGreaterThan(0);
  });

  it('no TypeScript files contain empty catch blocks', () => {
    // Matches catch blocks that contain only whitespace or single-line comments
    // Pattern: catch (optional binding) { optional-whitespace-and-comments }
    const emptyCatchPattern = /catch\s*(?:\([^)]*\))?\s*\{\s*(?:\/\/[^\n]*)?\s*\}/g;

    const violations: string[] = [];

    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      const matches = content.match(emptyCatchPattern);
      if (matches) {
        // Filter out false positives: if the catch block has actual code statements (not just comments)
        for (const match of matches) {
          // Extract content between { and }
          const inner = match.replace(/^catch\s*(?:\([^)]*\))?\s*\{/, '').replace(/\}$/, '').trim();
          // If inner is empty or only a single-line comment, it's a violation
          if (!inner || /^\/\/.*$/.test(inner)) {
            const relativePath = path.relative(frontendDir, file);
            violations.push(`${relativePath}: ${match.trim()}`);
          }
        }
      }
    }

    expect(violations).toEqual([]);
  });
});
