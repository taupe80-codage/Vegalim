/**
 * ratings.js — Notes moyennes des recettes pour les cartes.
 *
 * Les cartes demandent leur note une par une ; les demandes d'un même rendu
 * sont regroupées en un seul appel POST /avis/resume (fenêtre de 40 ms) et
 * gardées en mémoire. setRating() met à jour une note après un avis donné.
 */
import { useEffect, useState } from 'react';
import { reviews } from './api';

const cache = new Map();          // id → {average, count} | null (aucune note)
const listeners = new Map();      // id → Set(callback)
let queue = new Set();
let timer = null;

function notify(id) {
  (listeners.get(id) || []).forEach(cb => cb(cache.get(id)));
}

async function flush() {
  const ids = [...queue];
  queue = new Set();
  timer = null;
  for (let i = 0; i < ids.length; i += 300) {
    const batch = ids.slice(i, i + 300);
    try {
      const { summaries } = await reviews.summaries(batch);
      batch.forEach(id => { cache.set(id, summaries?.[id] || null); notify(id); });
    } catch {
      batch.forEach(id => { if (!cache.has(id)) cache.set(id, null); });
    }
  }
}

export function requestRating(id) {
  if (!id || cache.has(id) || queue.has(id)) return;
  queue.add(id);
  if (!timer) timer = setTimeout(flush, 40);
}

export function setRating(id, summary) {
  cache.set(id, summary && summary.count ? { average: summary.average, count: summary.count } : null);
  notify(id);
}

/** Note moyenne d'une recette ({average, count}) ou null. */
export function useRating(id) {
  const [value, setValue] = useState(() => cache.get(id) ?? null);
  useEffect(() => {
    if (!id) return undefined;
    const cb = (v) => setValue(v ?? null);
    if (!listeners.has(id)) listeners.set(id, new Set());
    listeners.get(id).add(cb);
    if (cache.has(id)) cb(cache.get(id));
    else requestRating(id);
    return () => listeners.get(id)?.delete(cb);
  }, [id]);
  return value;
}

/** « 4,5 » */
export function formatAverage(avg) {
  return avg == null ? '' : String(Math.round(avg * 10) / 10).replace('.', ',');
}

export const __test = { cache, flush };
