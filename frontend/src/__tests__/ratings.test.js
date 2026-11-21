import { describe, it, expect, vi, beforeEach } from 'vitest';

const summaries = vi.fn();
vi.mock('../api', () => ({ reviews: { summaries: (...a) => summaries(...a) } }));

const { requestRating, formatAverage, setRating, __test } = await import('../ratings');

describe('notes des cartes', () => {
  beforeEach(() => { summaries.mockReset(); __test.cache.clear(); });

  it('regroupe les demandes en un seul appel et garde les résultats', async () => {
    summaries.mockResolvedValue({ summaries: { a: { average: 4.5, count: 2 } } });
    requestRating('a'); requestRating('b'); requestRating('a');
    await new Promise(r => setTimeout(r, 80));
    expect(summaries).toHaveBeenCalledTimes(1);
    expect(summaries.mock.calls[0][0].sort()).toEqual(['a', 'b']);
    expect(__test.cache.get('a')).toEqual({ average: 4.5, count: 2 });
    expect(__test.cache.get('b')).toBeNull();
    requestRating('a');                       // déjà connu : pas de nouvel appel
    await new Promise(r => setTimeout(r, 80));
    expect(summaries).toHaveBeenCalledTimes(1);
  });

  it('setRating met la note à jour après un avis', () => {
    setRating('c', { average: 3, count: 1 });
    expect(__test.cache.get('c')).toEqual({ average: 3, count: 1 });
    setRating('c', { average: null, count: 0 });
    expect(__test.cache.get('c')).toBeNull();
  });

  it('formatAverage', () => {
    expect(formatAverage(4.25)).toBe('4,3');
    expect(formatAverage(4)).toBe('4');
    expect(formatAverage(null)).toBe('');
  });
});
