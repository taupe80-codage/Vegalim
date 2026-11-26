/**
 * WeekCarbon.jsx — Empreinte carbone de la semaine planifiée
 * (POST /planning/week_carbon) : total, moyenne par portion comparée aux plats
 * du catalogue, repas et ingrédients qui pèsent le plus avec des alternatives,
 * produits frais hors saison.
 */
import { useEffect, useState } from 'react';
import { planning as planningApi } from '../api';
import { Link } from '../Router';
import { MONTHS_FR, fmt } from '../ingredientSheet';
import { compareText } from '../carbonText';

const DAY_FR = { lundi: 'lundi', mardi: 'mardi', mercredi: 'mercredi', jeudi: 'jeudi', vendredi: 'vendredi', samedi: 'samedi', dimanche: 'dimanche' };

export default function WeekCarbon({ plan, diet }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const key = JSON.stringify(plan || {});

  useEffect(() => {
    let alive = true;
    planningApi.weekCarbon({ plan, diet: diet === 'vegan' ? 'vegan' : null })
      .then(d => { if (alive) { setData(d); setError(null); } })
      .catch(e => { if (alive) setError(e.message || 'Empreinte indisponible'); });
    return () => { alive = false; };
  }, [key, diet]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <p className="week-note">{error}</p>;
  if (!data) return <p className="week-note">Calcul de l'empreinte carbone…</p>;
  if (!data.n_meals) return null;

  return (
    <section className="week-section wc" aria-labelledby="wc-title">
      <h4 id="wc-title">🌍 Empreinte carbone de la semaine</h4>
      <div className="wc-head">
        <div className="wc-total">
          <span className="wc-big">{fmt(data.total_kg)} kg</span>
          <span className="wc-unit">CO₂e pour {data.portions} portions</span>
        </div>
        <div className="wc-total">
          <span className="wc-big">{fmt(data.per_portion_kg)} kg</span>
          <span className="wc-unit">par portion · {compareText(data.per_portion_kg, data.catalogue_avg_kg)}</span>
        </div>
      </div>

      {data.top_meals.length > 0 && (
        <>
          <h5 className="wc-h5">Les repas qui pèsent le plus</h5>
          <ul className="wc-list">
            {data.top_meals.map(m => (
              <li key={m.id}>
                <div className="wc-line">
                  <Link to={`/recette/${m.id}`}>{m.title_fr}</Link>
                  <span className="wc-meta">{DAY_FR[m.day]} · {fmt(m.per_portion_kg)} kg/portion</span>
                </div>
                {m.alternatives.length > 0 && (
                  <p className="wc-alt">
                    Moins émetteur, dans le même esprit :{' '}
                    {m.alternatives.map((a, i) => (
                      <span key={a.id}>{i > 0 && ', '}<Link to={`/recette/${a.id}`}>{a.title_fr}</Link> ({fmt(a.per_portion_kg)} kg)</span>
                    ))}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      {data.top_ingredients.length > 0 && (
        <>
          <h5 className="wc-h5">Les ingrédients qui pèsent le plus</h5>
          <ul className="wc-list">
            {data.top_ingredients.map(x => (
              <li key={x.id}>
                <div className="wc-line">
                  <Link to={`/ingredient/${x.id}`}>{x.name_fr.charAt(0).toUpperCase() + x.name_fr.slice(1)}</Link>
                  <span className="wc-meta">{x.share_pct} % de la semaine · {fmt(x.kg)} kg</span>
                </div>
                {x.lower.length > 0 && (
                  <p className="wc-alt">
                    À la place :{' '}
                    {x.lower.map((l, i) => (
                      <span key={l.id}>{i > 0 && ', '}<Link to={`/ingredient/${l.id}`}>{l.name_fr}</Link> ({fmt(l.kg_co2_per_kg)} kg/kg)</span>
                    ))}
                    {' '}— « Modifier les ingrédients » sur la fiche fait le remplacement.
                  </p>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      {data.off_season.length > 0 && (
        <>
          <h5 className="wc-h5">Hors saison en {MONTHS_FR[data.month - 1]}</h5>
          <ul className="wc-list">
            {data.off_season.map(x => (
              <li key={x.id} className="wc-line">
                <Link to={`/ingredient/${x.id}`}>{x.name_fr.charAt(0).toUpperCase() + x.name_fr.slice(1)}</Link>
                <span className="wc-meta">de saison en {x.months} : {x.saving_pct} % d'émissions en moins</span>
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="week-note">
        Valeurs Agribalyse (ADEME) par ingrédient, au mois en cours (serre chauffée ou avion hors saison), pour les
        portions prévues ; les versions vegan et vos versions modifiées sont comptées telles que vous les cuisinerez.
        {data.recipes_without_data?.length > 0 && ` ${data.recipes_without_data.length} recette(s) trop peu renseignées ne sont pas comptées.`}
      </p>
    </section>
  );
}
