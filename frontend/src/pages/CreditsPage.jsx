/**
 * CreditsPage.jsx — Crédits des photos de recettes
 *
 * Les photos viennent de Wikimedia Commons et d'Openverse, sous licences
 * Creative Commons. Ces licences imposent de citer l'auteur, la licence et
 * la source : cette page est cette citation, et elle doit rester accessible.
 *
 * Les données sont lues au vol dans /images/recipes/_credits.json, le fichier
 * que le script scripts/fetch_recipe_images_free.py tient à jour. Rien à
 * regénérer à la main quand des photos changent.
 */

import { useEffect, useMemo, useState } from 'react';
import { navigate } from '../Router';

const CREDITS_URL = '/images/recipes/_credits.json';

// ── Licences ──────────────────────────────────────────────────────────────────

/** Lien vers le texte de la licence, pour que le lecteur puisse la vérifier. */
function licenseUrl(license) {
  const l = (license || '').trim().toLowerCase();
  if (!l) return null;
  if (l.startsWith('cc0')) return 'https://creativecommons.org/publicdomain/zero/1.0/';
  if (l.includes('public domain') || l.startsWith('cc pdm')) {
    return 'https://creativecommons.org/publicdomain/mark/1.0/';
  }
  const m = l.match(/^cc\s+(by(?:-sa|-nc|-nd)*)\s+([\d.]+)/);
  return m ? `https://creativecommons.org/licenses/${m[1]}/${m[2]}/` : null;
}

/** Couleur du badge : domaine public en bleu, partage à l'identique en ambre. */
function licenseTone(license) {
  const l = (license || '').toLowerCase();
  if (l.startsWith('cc0') || l.includes('public domain') || l.startsWith('cc pdm')) return 'pd';
  if (l.includes('-sa')) return 'sa';
  return 'by';
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CreditsPage() {
  const [credits, setCredits] = useState(null);
  const [error, setError]     = useState(null);
  const [query, setQuery]     = useState('');

  useEffect(() => {
    let annule = false;
    fetch(CREDITS_URL)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => { if (!annule) setCredits(data); })
      .catch(e => { if (!annule) setError(e.message); });
    return () => { annule = true; };
  }, []);

  const entries = useMemo(() => {
    if (!credits) return [];
    return Object.entries(credits)
      .map(([slug, c]) => ({ slug, ...c }))
      .sort((a, b) => (a.recipe || a.slug).localeCompare(b.recipe || b.slug, 'fr'));
  }, [credits]);

  const q = query.toLowerCase().trim();
  const filtered = useMemo(() => {
    if (!q) return entries;
    return entries.filter(e =>
      (e.recipe || '').toLowerCase().includes(q)
      || (e.author || '').toLowerCase().includes(q)
      || (e.license || '').toLowerCase().includes(q)
      || (e.source || '').toLowerCase().includes(q)
    );
  }, [entries, q]);

  const licences = useMemo(() => {
    const n = {};
    for (const e of entries) n[e.license] = (n[e.license] || 0) + 1;
    return Object.entries(n).sort((a, b) => b[1] - a[1]);
  }, [entries]);

  return (
    <div className="credits-page">

      <div className="credits-hero">
        <div className="credits-hero-inner">
          <div className="credits-hero-badge">📷 Crédits</div>
          <h1 className="credits-hero-title">Crédits photos</h1>
          <p className="credits-hero-sub">
            Les photos de recettes d'ALIM proviennent de Wikimedia Commons et d'Openverse,
            sous licences Creative Commons. Chaque auteur est cité ci-dessous, avec sa
            licence et la page d'origine de la photo.
          </p>

          <div className="credits-search-wrap">
            <span className="credits-search-icon" aria-hidden="true">🔍</span>
            <input
              type="search"
              className="credits-search"
              placeholder="Rechercher une recette, un auteur, une licence…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              aria-label="Rechercher dans les crédits photos"
            />
            {query && (
              <button
                className="credits-search-clear"
                onClick={() => setQuery('')}
                aria-label="Effacer la recherche"
              >✕</button>
            )}
          </div>

          {entries.length > 0 && (
            <p className="credits-search-count">
              {q
                ? `${filtered.length} résultat${filtered.length > 1 ? 's' : ''} sur ${entries.length}`
                : `${entries.length} photos créditées`}
            </p>
          )}
        </div>
      </div>

      <div className="credits-body">

        {/* Ce que les licences imposent, dit simplement */}
        <section className="credits-note">
          <h2 className="credits-note-title">Réutiliser ces photos</h2>
          <p>
            Les licences Creative Commons autorisent la réutilisation, y compris
            commerciale, à condition de citer l'auteur, d'indiquer la licence et de
            renvoyer vers la source. Les licences marquées <strong>BY-SA</strong> ajoutent
            une obligation : une œuvre dérivée doit être partagée sous la même licence.
          </p>
          <p>
            Les photos du domaine public (<strong>CC0</strong>, <strong>Public domain</strong>)
            n'imposent rien, mais leurs auteurs sont cités ici aussi.
          </p>
          <p className="credits-note-other">
            Les recettes dont la photo n'apparaît pas dans cette liste utilisent des images
            Unsplash, dont la licence ne demande pas d'attribution, ou n'ont pas de photo :
            le site affiche alors un dégradé coloré à la place.
          </p>
        </section>

        {licences.length > 0 && (
          <section className="credits-stats" aria-label="Répartition par licence">
            {licences.map(([lic, n]) => (
              <span key={lic} className={`credits-badge credits-badge--${licenseTone(lic)}`}>
                {lic} <span className="credits-badge-n">{n}</span>
              </span>
            ))}
          </section>
        )}

        {error && (
          <div className="credits-empty">
            <span className="credits-empty-icon">⚠️</span>
            <p className="credits-empty-title">Crédits indisponibles</p>
            <p className="credits-empty-sub">
              Le fichier des crédits n'a pas pu être chargé ({error}).
            </p>
          </div>
        )}

        {!error && credits === null && (
          <p className="credits-loading">Chargement des crédits…</p>
        )}

        {!error && credits !== null && filtered.length === 0 && (
          <div className="credits-empty">
            <span className="credits-empty-icon">🔍</span>
            <p className="credits-empty-title">
              {q ? `Aucun résultat pour « ${query} »` : 'Aucune photo créditée'}
            </p>
            {q && (
              <button className="credits-empty-reset" onClick={() => setQuery('')}>
                Réinitialiser la recherche
              </button>
            )}
          </div>
        )}

        {filtered.length > 0 && (
          <ul className="credits-list">
            {filtered.map(e => {
              const url = licenseUrl(e.license);
              return (
                <li key={e.slug} className="credits-item">
                  <img
                    className="credits-thumb"
                    src={`/images/recipes/${e.slug}.jpg`}
                    alt=""
                    loading="lazy"
                    width="64"
                    height="48"
                  />
                  <div className="credits-item-main">
                    <p className="credits-item-recipe">{e.recipe || e.slug}</p>
                    <p className="credits-item-meta">
                      <span className="credits-item-author">{e.author || 'auteur inconnu'}</span>
                      {e.source && <> · {e.source}</>}
                    </p>
                  </div>
                  <div className="credits-item-right">
                    {url ? (
                      <a
                        className={`credits-badge credits-badge--${licenseTone(e.license)}`}
                        href={url}
                        target="_blank"
                        rel="noreferrer license"
                      >{e.license}</a>
                    ) : (
                      <span className={`credits-badge credits-badge--${licenseTone(e.license)}`}>
                        {e.license || 'licence inconnue'}
                      </span>
                    )}
                    {e.page && (
                      <a
                        className="credits-item-src"
                        href={e.page}
                        target="_blank"
                        rel="noreferrer"
                      >Voir la photo d'origine ↗</a>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        <div className="credits-back">
          <button className="credits-back-btn" onClick={() => navigate('/')}>
            ← Retour aux recettes
          </button>
        </div>
      </div>
    </div>
  );
}
