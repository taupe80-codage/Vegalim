/**
 * IngredientPage.jsx — Fiche d'un ingrédient (#/ingredient/:id).
 *
 * Tableaux pour 100 g (% des valeurs nutritionnelles de référence), part dans
 * la recette d'où l'on vient (?q=400&u=g&p=4&r=…), saison, prix, empreinte
 * carbone, allergènes, régimes, remplacements, recettes qui l'utilisent,
 * source avec lien et corrections acceptées. GET /ingredients/:id/fiche.
 */
import { useEffect, useState } from 'react';
import { useRouter, Link, navigate } from '../Router';
import { ingredients as ingredientsApi } from '../api';
import { MONTHS_FR, MONTHS_SHORT, fmt, portionRows, readRecipeQty } from '../ingredientSheet';
import IngredientCorrection from '../components/IngredientCorrection';

function NutritionTable({ group }) {
  return (
    <div className="ig-table-wrap">
      <table className="ig-table">
        <caption>{group.title}</caption>
        <thead>
          <tr><th scope="col">Pour 100 g</th><th scope="col" className="ig-num">Quantité</th><th scope="col" className="ig-num">% VNR</th></tr>
        </thead>
        <tbody>
          {group.rows.map(r => (
            <tr key={r.key} className={r.label.startsWith('dont ') ? 'ig-sub' : ''}>
              <th scope="row">
                {r.label}
                {r.corrected && <span className="ig-corrected" title="Valeur corrigée (voir les corrections plus bas)"> ✎</span>}
              </th>
              <td className="ig-num">{r.value == null ? '—' : `${fmt(r.value)} ${r.unit}`}</td>
              <td className="ig-num">
                {r.pct == null ? '' : (
                  <span className="ig-pct">
                    <span className="ig-bar" aria-hidden="true"><span style={{ width: `${Math.min(100, r.pct)}%` }} /></span>
                    {r.pct} %
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function IngredientPage({ onAuthClick }) {
  const { params, search } = useRouter();
  // réponse liée à l'ingrédient demandé : en passant d'une fiche à l'autre
  // (remplacements), l'ancienne ne s'affiche pas sous le nouveau nom
  const [loaded, setLoaded] = useState({ id: null, data: null, error: null });
  const [reporting, setReporting] = useState(false);
  const id = params.id;
  const data = loaded.id === id ? loaded.data : null;
  const error = loaded.id === id ? loaded.error : null;

  useEffect(() => {
    if (!id) return undefined;
    let alive = true;
    ingredientsApi.sheet(id)
      .then(d => { if (alive) setLoaded({ id, data: d, error: null }); })
      .catch(e => { if (alive) setLoaded({ id, data: null, error: e.message || 'Ingrédient introuvable' }); });
    return () => { alive = false; };
  }, [id]);

  useEffect(() => {
    if (data?.name_fr) document.title = `${data.name_fr} : valeurs nutritionnelles, saison, recettes — ALIM`;
    return () => { document.title = 'ALIM'; };
  }, [data?.name_fr]);

  if (error) return (
    <div className="state-msg state-msg--error">
      Ingrédient introuvable.<br />
      <button className="back-button" onClick={() => navigate('/')}>← Retour</button>
    </div>
  );
  if (!data) return (
    <div className="detail-loading">
      <div className="skeleton skeleton-line" style={{ width: '40%', height: 36, marginBottom: 16 }} />
      <div className="skeleton skeleton-line" style={{ width: '80%', marginBottom: 8 }} />
      <div className="skeleton skeleton-img" style={{ height: 240, borderRadius: 16 }} />
    </div>
  );

  const inRecipe = readRecipeQty(search);
  const recipeId = search?.get('r');
  const recipeTitle = recipeId && data.recipes.find(r => r.id === recipeId)?.title;
  const per100 = data.nutrition_per_100g || {};
  const now = new Date().getMonth() + 1;
  const src = data.source || {};

  return (
    <div className="ig-page">
      <button className="back-button" onClick={() => (window.history.length > 1 ? window.history.back() : navigate('/'))}>
        ← Retour
      </button>

      <header className="ig-head">
        <h1 className="detail-title">{data.name_fr}</h1>
        <p className="ig-sub">
          Valeurs nutritionnelles pour 100 g, saison, prix et recettes végétariennes.
          {data.name_en && <> <span lang="en">({data.name_en})</span></>}
        </p>
        <div className="ig-chips">
          {data.season?.in_season && <span className="badge ig-chip-season">🌱 De saison</span>}
          <span className="badge">{data.aisle}</span>
          {data.nova_group && <span className="badge" title="Classification NOVA : 1 = brut ou peu transformé, 4 = ultra-transformé">NOVA {data.nova_group}</span>}
          {data.diets.includes('Vegan') && <span className="badge">🌿 Vegan</span>}
        </div>
      </header>

      <div className="ig-facts">
        <div className="stat-box"><span className="stat-label">Énergie</span>
          <span className="stat-value">{data.kcal_100g ?? '—'} kcal</span><span className="ig-fact-sub">pour 100 g</span></div>
        <div className="stat-box"><span className="stat-label">Protéines</span>
          <span className="stat-value">{fmt(per100.protein_g)} g</span><span className="ig-fact-sub">pour 100 g</span></div>
        {data.price && (
          <div className="stat-box" title={data.price.package || ''}><span className="stat-label">Prix</span>
            <span className="stat-value">{data.price.estimated ? '≈ ' : ''}{fmt(data.price.per_kg_eur)} €/kg</span>
            <span className="ig-fact-sub">{data.price.package || 'prix relevé'}</span></div>
        )}
        {data.carbon && (
          <div className="stat-box"><span className="stat-label">Empreinte carbone</span>
            <span className="stat-value">{fmt(data.carbon.kg_co2_per_kg)} kg CO₂e/kg</span>
            <span className="ig-fact-sub">{data.carbon.label}</span></div>
        )}
      </div>

      {inRecipe && (
        <section className="ig-card" aria-labelledby="ig-recipe">
          <h2 id="ig-recipe" className="ig-h2">
            Dans {recipeTitle ? <Link to={`/recette/${recipeId}`}>{recipeTitle}</Link> : 'la recette'}
          </h2>
          <p className="ig-muted">
            {fmt(inRecipe.quantity)} {inRecipe.unit} pour {inRecipe.portions} portion{inRecipe.portions > 1 ? 's' : ''},
            soit {fmt(inRecipe.quantity / inRecipe.portions)} {inRecipe.unit} par portion
            {inRecipe.unit === 'ml' ? ' (1 ml compté comme 1 g)' : ''}.
          </p>
          <div className="ig-table-wrap">
            <table className="ig-table">
              <thead><tr><th scope="col">Par portion</th><th scope="col" className="ig-num">Apport</th></tr></thead>
              <tbody>
                {portionRows(per100, inRecipe).map(r => (
                  <tr key={r.key}><th scope="row">{r.label}</th><td className="ig-num">{fmt(r.value)} {r.unit}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="ig-card" aria-labelledby="ig-nutri">
        <div className="ig-card-head">
          <h2 id="ig-nutri" className="ig-h2">Valeurs nutritionnelles pour 100 g</h2>
          <button type="button" className="ct-btn ct-btn--sm" onClick={() => setReporting(true)}>
            ✎ Signaler une erreur
          </button>
        </div>
        <p className="ig-muted">
          Produit cru ou tel qu'acheté. % VNR : part des valeurs nutritionnelles de référence
          d'un adulte (règlement UE 1169/2011 ; fibres : repère ANSES de 30 g).
        </p>
        <div className="ig-tables">
          {data.nutrition.map(g => <NutritionTable key={g.title} group={g} />)}
        </div>
        <p className="ig-source">
          Source : {src.url
            ? <a href={src.url} target="_blank" rel="noopener noreferrer">{src.name}{src.id ? `, code ${src.id}` : ''} ↗</a>
            : src.name}
          {src.label && <> — « {src.label} »</>}
        </p>
      </section>

      {data.corrections?.length > 0 && (
        <section className="ig-card" aria-labelledby="ig-corr">
          <h2 id="ig-corr" className="ig-h2">Corrections apportées</h2>
          <ul className="ig-list">
            {data.corrections.map(c => (
              <li key={c.field}>
                <strong>{c.label}</strong> : {fmt(c.previous)} → {fmt(c.value)} {c.unit}
                {c.date && <> (le {new Date(c.date).toLocaleDateString('fr-FR')})</>}. Source :{' '}
                {c.url ? <a href={c.url} target="_blank" rel="noopener noreferrer">{c.source} ↗</a> : c.source}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="ig-grid">
        <section className="ig-card" aria-labelledby="ig-season">
          <h2 id="ig-season" className="ig-h2">Saison</h2>
          {data.season ? (
            <>
              <ol className="ig-months" aria-label={`De saison en ${data.season.label}`}>
                {MONTHS_SHORT.map((m, i) => (
                  <li key={i} className={`${data.season.months.includes(i + 1) ? 'is-on' : ''}${i + 1 === now ? ' is-now' : ''}`}
                    title={MONTHS_FR[i]}>{m}</li>
                ))}
              </ol>
              <p className="ig-muted">De saison en {data.season.label}.</p>
            </>
          ) : <p className="ig-muted">Disponible toute l'année (produit sec, d'épicerie ou importé).</p>}
          {data.carbon?.in_season_kg != null && (
            <p className="ig-muted">
              Empreinte : {fmt(data.carbon.in_season_kg)} kg CO₂e/kg de saison, {fmt(data.carbon.off_season_kg)} hors saison (serre ou avion).
            </p>
          )}
        </section>

        <section className="ig-card" aria-labelledby="ig-allerg">
          <h2 id="ig-allerg" className="ig-h2">Allergènes et régimes</h2>
          <table className="ig-table ig-table--plain">
            <tbody>
              <tr><th scope="row">Allergènes (UE)</th><td>{data.allergens.length ? data.allergens.join(', ') : 'aucun des 14 allergènes réglementaires'}</td></tr>
              <tr><th scope="row">Convient à</th><td>{data.diets.join(', ') || '—'}</td></tr>
              <tr><th scope="row">Rayon</th><td>{data.aisle}</td></tr>
              {data.available_in_france === false && <tr><th scope="row">En France</th><td>Difficile à trouver</td></tr>}
            </tbody>
          </table>
        </section>
      </div>

      {data.replacements?.length > 0 && (
        <section className="ig-card" aria-labelledby="ig-repl">
          <h2 id="ig-repl" className="ig-h2">Peut se remplacer par</h2>
          <div className="re-suggest">
            {data.replacements.map(r => (
              <Link key={r.id} to={`/ingredient/${r.id}`} className="re-chip">{r.name_fr}{r.reason === 'version vegan' ? ' 🌿' : ''}</Link>
            ))}
          </div>
          <p className="ig-muted">Même usage en cuisine et valeurs proches. Sur une fiche recette, « Modifier les ingrédients » fait le remplacement et recalcule tout.</p>
        </section>
      )}

      <section className="ig-card" aria-labelledby="ig-recipes">
        <h2 id="ig-recipes" className="ig-h2">
          Recettes avec {data.name_fr.toLowerCase()} <span className="ig-count">({data.recipes_count})</span>
        </h2>
        {data.recipes.length ? (
          <ul className="ig-recipes">
            {data.recipes.map(r => (
              <li key={r.id}><Link to={`/recette/${r.id}`}>{r.title}</Link>{r.vegan && <span className="ig-vegan" title="Vegan"> 🌿</span>}</li>
            ))}
          </ul>
        ) : <p className="ig-muted">Aucune recette du catalogue pour l'instant.</p>}
        {data.recipes_count > data.recipes.length && (
          <p className="ig-muted">Et {data.recipes_count - data.recipes.length} autres : cherchez « {data.name_fr.toLowerCase()} » dans les recettes.</p>
        )}
      </section>

      {reporting && (
        <IngredientCorrection ingredient={data} onAuthClick={onAuthClick} onClose={() => setReporting(false)} />
      )}
    </div>
  );
}
