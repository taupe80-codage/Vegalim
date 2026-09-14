import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

function stubLocalStorage(initial = {}) {
  const store = { ...initial };
  vi.stubGlobal('localStorage', {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; },
  });
  return store;
}

describe('api.js', () => {
  beforeEach(() => { vi.resetModules(); });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('envoie le jeton JWT quand il est présent', async () => {
    stubLocalStorage({ alim_token: 'abc' });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ ok: 1 }) });
    vi.stubGlobal('fetch', fetchMock);
    const { auth } = await import('../api');
    await auth.me();
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer abc');
  });

  it("remonte le « detail » de l'API en message d'erreur", async () => {
    stubLocalStorage();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 401, json: async () => ({ detail: 'Authentification requise' }),
    }));
    const { planning } = await import('../api');
    await expect(planning.updatePrice('olive_oil', '1L', 5)).rejects.toThrow('Authentification requise');
  });

  it('garde « Erreur <status> » si le corps n’est pas du JSON', async () => {
    stubLocalStorage();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 502, json: async () => { throw new SyntaxError('html'); },
    }));
    const { auth } = await import('../api');
    await expect(auth.me()).rejects.toThrow('Erreur 502');
  });

  it('setToken(null) supprime le jeton', async () => {
    const store = stubLocalStorage({ alim_token: 'abc' });
    const { setToken, getToken } = await import('../api');
    setToken(null);
    expect(getToken()).toBeNull();
    expect(store.alim_token).toBeUndefined();
  });
});
