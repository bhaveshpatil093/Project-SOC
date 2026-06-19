import { describe, it, expect } from 'vitest';
import { formatTimestamp, formatThreatScore, formatThreatLevel, formatEntityKey, formatMitreId, formatBytes, truncate } from '../utils/formatters';

describe('formatters utility', () => {
  it('formats timestamp gracefully handling nulls', () => {
    expect(formatTimestamp("2026-06-19T14:32:05Z")).toContain("2026");
    expect(formatTimestamp(null)).toBe("—");
  });

  it('formats decimal threat scores securely', () => {
    expect(formatThreatScore(87.345)).toBe("87.3");
    expect(formatThreatScore(0)).toBe("0.0");
    expect(formatThreatScore(null)).toBe("—");
  });

  it('uppercases threat levels safely', () => {
    expect(formatThreatLevel("critical")).toBe("CRITICAL");
    expect(formatThreatLevel(null)).toBe("UNKNOWN");
  });

  it('splits entity keys into slash notation', () => {
    expect(formatEntityKey("host-123|admin")).toBe("host-123 / admin");
    expect(formatEntityKey(null)).toBe("—");
  });

  it('formats bytes algorithmically', () => {
    expect(formatBytes(1024 * 1024)).toBe("1 MB");
    expect(formatBytes(0)).toBe("0 Bytes");
    expect(formatBytes(null)).toBe("—");
  });
  
  it('truncates strings adding ellipses', () => {
    expect(truncate("Hello World", 5)).toBe("Hello...");
    expect(truncate("Short", 10)).toBe("Short");
  });
});
