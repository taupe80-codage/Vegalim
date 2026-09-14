/**
 * PlanningPage.jsx — Plan de repas hebdomadaire + Liste de courses
 *
 * Architecture :
 *  • Sidebar       : filtres globaux prédominants (mois, régime, restrictions,
 *                    allergènes, santé, difficulté, origine, temps max)
 *  • Grille        : chaque slot = types de plat + convives + 3 boutons de filtre
 *                    🌿 régime/restrictions/allergènes  💪 santé  🌍 origine
 *  • Les filtres du slot sont des ajustements au cas par cas (invité, régime spécial)
 *  • Les filtres globaux sont prédominants et s'appliquent à toute la génération
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useToast } from '../ToastContext';
import { createPortal } from 'react-dom';
import { planning as planningApi, recipes as recipesApi } from '../api';
import { navigate } from '../Router';
import PriceEditInline from '../components/PriceEditInline';
import {
  FilterSection,
  HealthAccordion,
  OriginAccordion,
  useFilterState,
  DIET_OPTIONS,
  DIET_EXTRA_OPTIONS,
  ALLERGEN_OPTIONS,
  HEALTH_GROUPS,
  ORIGIN_GROUPS,
  DIFFICULTY_OPTIONS,
} from '../components/RecipeFiltersShared';

// ── Constantes ────────────────────────────────────────────────────────────────

const PLAN_KEY              = 'alim_plan_weekly';
const CHECKED_KEY           = 'alim_shopping_checked';
const FRIGO_QTYS_KEY        = 'alim_shopping_frigo_qtys';
const FRIGO_SUFFICIENT_KEY  = 'alim_shopping_frigo_sufficient';
const PLAN_FILTERS_KEY      = 'alim_plan_filters';
const PLAN_MEALS_KEY        = 'alim_plan_meals';

const DAYS_FR  = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'];
const DAYS_KEY = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche'];

const MEAL_INFO = {
  breakfast : { label: 'Petit-déjeuner', icon: '🌅' },
  lunch     : { label: 'Déjeuner',       icon: '☀️' },
  dinner    : { label: 'Dîner',          icon: '🌙' },
};
const MEAL_ORDER = ['breakfast','lunch','dinner'];

const MEAL_DISH_TYPES = {
  breakfast : [
    { value: 'breakfast', label: '🌅 Petit-déj' },
    { value: 'snack',     label: '⚡ Brunch'    },
  ],
  lunch : [
    { value: 'starter', label: '🥣 Entrée'  },
    { value: 'soup',    label: '🍲 Soupe'   },
    { value: 'main',    label: '🍽️ Plat'   },
    { value: 'side',    label: '🫕 Accomp.' },
    { value: 'dessert', label: '🍰 Dessert' },
  ],
  dinner : [
    { value: 'starter', label: '🥣 Entrée'  },
    { value: 'soup',    label: '🍲 Soupe'   },
    { value: 'main',    label: '🍽️ Plat'   },
    { value: 'side',    label: '🫕 Accomp.' },
    { value: 'dessert', label: '🍰 Dessert' },
  ],
};

const DISH_TYPE_LABELS = {
  breakfast:'Petit-déj', snack:'Brunch', starter:'Entrée',
  soup:'Soupe', main:'Plat', side:'Accomp.', dessert:'Dessert',
};

const DAY_GRADIENTS = [
  ['#1a2440','#2e4db0'],['#1a3428','#2e7a50'],['#38182a','#7a2e50'],
  ['#28260e','#6a6420'],['#0e2634','#1a6080'],['#342010','#806020'],
  ['#22103a','#602080'],
];

const TITLE_EMOJI_RULES = [
  [['soupe','soup','bouillon','potage','velouté'],'🍲'],
  [['salade','salad'],'🥗'],[['tarte','quiche','pie'],'🥧'],
  [['cake','gâteau','brownie','cookie'],'🎂'],
  [['risotto','riz','rice','pilaf','biryani'],'🍚'],
  [['pâtes','pasta','spaghetti','tagliatelle'],'🍝'],[['pizza'],'🍕'],
  [['burger','sandwich'],'🥪'],[['curry','massaman','tikka','korma'],'🍛'],
  [['tofu','tempeh'],'🌿'],[['lentil','lentille','dal'],'🫘'],
  [['wok','poêlée','stir'],'🥡'],[['pancake','crêpe','waffle'],'🥞'],
  [['pain','bread','naan'],'🍞'],[['chocolat','chocolate'],'🍫'],
  [['avocat','avocado','guacamole'],'🥑'],[['hummus','houmous'],'🧆'],
  [['granola','muesli','bowl','porridge'],'🥣'],
];
function getMealEmoji(t='') {
  const s = t.toLowerCase();
  for (const [keys,e] of TITLE_EMOJI_RULES) if (keys.some(k=>s.includes(k))) return e;
  return '🍽️';
}

const MONTHS_FR = ['Jan','Fév','Mar','Avr','Mai','Juin','Juil','Aoû','Sep','Oct','Nov','Déc'];

const CAT_ICONS = {
  'légumes':'🥦','légumineuses':'🫘','protéines':'🥩','viandes':'🥩','volaille':'🍗',
  'poissons':'🐟','poissons & fruits de mer':'🦐','produits laitiers':'🧀','œufs':'🥚',
  'fruits':'🍎','céréales & féculents':'🌾','noix & graines':'🥜',
  'condiments & sauces':'🫙','épices & aromates':'🌶️','herbes fraîches':'🌿',
  'huiles & matières grasses':'🫒','sucres & édulcorants':'🍯','boissons':'🥤',
  'pâtisserie':'🧁','conserves':'🥫','surgelés':'🧊','autre':'📦',
};

const MEAL_DEFAULTS = {
  breakfast : { dishTypes:['breakfast'], servings:2 },
  lunch     : { dishTypes:['main'],      servings:4 },
  dinner    : { dishTypes:['main'],      servings:4 },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function _loadPlanFilters() {
  try { const r = localStorage.getItem(PLAN_FILTERS_KEY); if (r) return JSON.parse(r); } catch { /* localStorage indisponible ou JSON corrompu */ }
  return {};
}

function _loadPlanMeals() {
  try { const r = localStorage.getItem(PLAN_MEALS_KEY); if (r) return JSON.parse(r); } catch { /* localStorage indisponible ou JSON corrompu */ }
  return { breakfast: false, lunch: true, dinner: true };
}

function _findOriginLabel(val) {
  for (const group of ORIGIN_GROUPS) {
    for (const child of group.children) {
      if (child.value === val) return child.label;
      if (child.children) for (const sub of child.children) if (sub.value === val) return sub.label;
    }
  }
  return val;
}

function _slugify(t='') {
  return String(t).normalize('NFD').replace(/[̀-ͯ]/g,'')
    .toLowerCase().trim()
    .replace(/[\s_/\\]+/g,'-').replace(/[^a-z0-9-]/g,'')
    .replace(/-+/g,'-').replace(/^-|-$/g,'');
}

function getPlanningImgUrl(recipe) {
  const n = recipe?.titles?.fr || recipe?.title_fr || '';
  return n ? `/images/recipes/${_slugify(n)}.jpg` : null;
}

function createDefaultPlan() {
  const p = { meta:{} };
  for (const dk of DAYS_KEY) {
    p[dk] = {};
    for (const [m,d] of Object.entries(MEAL_DEFAULTS))
      p[dk][m] = { dishTypes:[...d.dishTypes], servings:d.servings, skip:false, recipes:[] };
  }
  return p;
}

function hasAnyRecipes(plan) {
  if (!plan) return false;
  return DAYS_KEY.some(dk => MEAL_ORDER.some(m => (plan[dk]?.[m]?.recipes?.length||0) > 0));
}

function planToShoppingFormat(plan) {
  const out = {};
  for (const dk of DAYS_KEY) {
    out[dk] = {};
    let i = 0;
    for (const m of MEAL_ORDER) {
      const slot = plan[dk]?.[m];
      if (!slot || slot.skip) continue;
      for (const r of (slot.recipes||[])) {
        if (r?.id) out[dk][`${m}_${i++}`] = { id:r.id, title:r.title_fr||r.title||'' };
      }
    }
  }
  return out;
}

function getAllUsedIds(plan) {
  const ids = [];
  for (const dk of DAYS_KEY)
    for (const m of MEAL_ORDER)
      for (const r of (plan[dk]?.[m]?.recipes||[]))
        if (r?.id) ids.push(r.id);
  return ids;
}

function fridgeMatchesIng(fid, rid) {
  const f=fid.toLowerCase(), r=rid.toLowerCase();
  if (f===r) return true;
  if (r.startsWith(f+'/')||r.startsWith(f+'_')) return true;
  if (r.endsWith('_'+f)) return true;
  const parts=r.split('/');
  if(parts.length>1){const l=parts[parts.length-1];if(l===f||l.startsWith(f+'_'))return true;}
  return false;
}

// ── SlotPickerPortal ──────────────────────────────────────────────────────────

function SlotPickerPortal({ pos, onClose, children }) {
  return createPortal(
    <>
      <div style={{position:'fixed',inset:0,zIndex:998}} onClick={onClose} />
      <div className="pslot-picker" style={{position:'fixed', top:pos.top, left:pos.left, zIndex:999}}>
        {children}
      </div>
    </>,
    document.body
  );
}

// ── RecipeSearchModal ─────────────────────────────────────────────────────────

function RecipeSearchModal({ onSelect, onClose }) {
  const toast = useToast();
  const [query,     setQuery]     = useState('');
  const [results,   setResults]   = useState([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (!query.trim()) { setResults([]); return; }
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const data = await recipesApi.search({ query: query.trim(), limit: 12 });
        const list = Array.isArray(data) ? data : (data?.results || data?.recipes || []);
        setResults(list);
      } catch (err) {
        toast(`Recherche impossible : ${err.message || 'erreur réseau'}`, 'error');
      }
      finally { setSearching(false); }
    }, 300);
    return () => clearTimeout(t);
  }, [query, toast]);

  return (
    <div className="rsm-overlay" onClick={e=>e.target===e.currentTarget&&onClose()}>
      <div className="rsm-modal">
        <div className="rsm-header">
          <span>🔍 Rechercher une recette</span>
          <button className="rsm-close" onClick={onClose} aria-label="Fermer">✕</button>
        </div>
        <input className="rsm-input" autoFocus placeholder="Nom de la recette…"
          value={query} onChange={e=>setQuery(e.target.value)} />
        <div className="rsm-results">
          {searching && <div className="rsm-loading">Recherche…</div>}
          {!searching && results.map(r=>(
            <button key={r.id} className="rsm-result-item" onClick={()=>onSelect(r)}>
              <span className="rsm-result-emoji">{getMealEmoji(r.titles?.fr||r.title_fr||r.title||'')}</span>
              <span className="rsm-result-title">{r.titles?.fr||r.title_fr||r.title||r.id}</span>
            </button>
          ))}
          {!searching && query.trim() && results.length===0 && (
            <div className="rsm-empty">Aucune recette trouvée</div>
          )}
          {!searching && !query.trim() && (
            <div className="rsm-empty rsm-empty--hint">Tapez un nom de recette pour commencer…</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── PlanningRecipeCard ────────────────────────────────────────────────────────

function PlanningRecipeCard({recipe, onReplace, onSearch, onDelete, isReplacing}) {
  const [imgFailed, setImgFailed] = useState(false);
  const emoji  = getMealEmoji(recipe.title_fr||recipe.title||'');
  const title  = recipe.title_fr||recipe.title||'—';
  const dtype  = recipe._dish_type;
  const imgUrl = getPlanningImgUrl(recipe);

  if (isReplacing)
    return <div className="prcard prcard--loading"><span className="prcard-spinner">↻</span></div>;

  return (
    <div className="prcard" role="button" tabIndex={0}
      onClick={e => { if(!e.target.closest('.prcard-actions')&&recipe.id) navigate(`/recette/${recipe.id}`); }}
      onKeyDown={e => e.key==='Enter'&&recipe.id&&navigate(`/recette/${recipe.id}`)}>
      <div className="prcard-visual">
        {imgUrl && !imgFailed
          ? <img src={imgUrl} alt={title} className="prcard-img" onError={()=>setImgFailed(true)} />
          : <span className="prcard-emoji">{emoji}</span>
        }
      </div>
      <div className="prcard-info">
        {dtype && <span className="prcard-type-badge">{DISH_TYPE_LABELS[dtype]||dtype}</span>}
        <span className="prcard-title">{title}</span>
      </div>
      <div className="prcard-actions">
        <button className="prcard-search"  onClick={e=>{e.stopPropagation();onSearch&&onSearch();}} title="Chercher">🔍</button>
        <button className="prcard-refresh" onClick={e=>{e.stopPropagation();onReplace();}}          title="Changer">↻</button>
        <button className="prcard-delete"  onClick={e=>{e.stopPropagation();onDelete&&onDelete();}} title="Supprimer">✕</button>
      </div>
    </div>
  );
}

// ── PlanningSlot ──────────────────────────────────────────────────────────────

function PlanningSlot({dayKey, mealType, slotData, enabled, replacing, onUpdate, onSkip, onReplace, onSearch, onDelete}) {
  // ── Les hooks doivent être avant tout return conditionnel ──
  const [dietOpen,   setDietOpen]   = useState(false);
  const [healthOpen, setHealthOpen] = useState(false);
  const [originOpen, setOriginOpen] = useState(false);
  const [dietPos,    setDietPos]    = useState({ top:0, left:0 });
  const [healthPos,  setHealthPos]  = useState({ top:0, left:0 });
  const [originPos,  setOriginPos]  = useState({ top:0, left:0 });
  const dietBtnRef   = useRef(null);
  const healthBtnRef = useRef(null);
  const originBtnRef = useRef(null);

  if (!enabled) return null;

  const info   = MEAL_INFO[mealType];
  const dtList = MEAL_DISH_TYPES[mealType];

  // Données du slot avec defaults rétrocompatibles
  const {
    dishTypes, servings, skip, recipes,
    diet:          slotDiet          = null,
    dietExtras:    slotDietExtras    = [],
    allergens:     slotAllergens     = [],
    healthFilters: slotHealthFilters = [],
    origins:       slotOrigins       = [],
  } = slotData;

  const hasDietActive   = !!(slotDiet || slotDietExtras.length || slotAllergens.length);
  const hasHealthActive = slotHealthFilters.length > 0;
  const hasOriginActive = slotOrigins.length > 0;
  const hasRec          = recipes && recipes.length > 0;

  // Ouvrir / fermer les pickers (mutuellement exclusifs)
  const openDietPicker = () => {
    const willOpen = !dietOpen;
    setDietOpen(willOpen); setHealthOpen(false); setOriginOpen(false);
    if (willOpen && dietBtnRef.current) {
      const r = dietBtnRef.current.getBoundingClientRect();
      setDietPos({ top: r.bottom + 4, left: Math.min(r.left, window.innerWidth - 270) });
    }
  };
  const openHealthPicker = () => {
    const willOpen = !healthOpen;
    setHealthOpen(willOpen); setDietOpen(false); setOriginOpen(false);
    if (willOpen && healthBtnRef.current) {
      const r = healthBtnRef.current.getBoundingClientRect();
      setHealthPos({ top: r.bottom + 4, left: Math.min(r.left, window.innerWidth - 220) });
    }
  };
  const openOriginPicker = () => {
    const willOpen = !originOpen;
    setOriginOpen(willOpen); setDietOpen(false); setHealthOpen(false);
    if (willOpen && originBtnRef.current) {
      const r = originBtnRef.current.getBoundingClientRect();
      setOriginPos({ top: r.bottom + 4, left: Math.min(r.left, window.innerWidth - 220) });
    }
  };

  const toggleDT = (val) => {
    const next = dishTypes.includes(val) ? dishTypes.filter(t=>t!==val) : [...dishTypes,val];
    if (next.length > 0) onUpdate({ dishTypes:next });
  };

  // Toggles pour filtres par slot
  const toggleSlotDietExtra = v => {
    const cur = slotDietExtras || [];
    onUpdate({ dietExtras: cur.includes(v) ? cur.filter(x=>x!==v) : [...cur, v] });
  };
  const toggleSlotAllergen = v => {
    const cur = slotAllergens || [];
    onUpdate({ allergens: cur.includes(v) ? cur.filter(x=>x!==v) : [...cur, v] });
  };
  const toggleSlotHealth = v => {
    const cur = slotHealthFilters || [];
    onUpdate({ healthFilters: cur.includes(v) ? cur.filter(x=>x!==v) : [...cur, v] });
  };
  const toggleSlotOrigin = v => {
    const cur = slotOrigins || [];
    onUpdate({ origins: cur.includes(v) ? cur.filter(x=>x!==v) : [...cur, v] });
  };

  return (
    <div className={`pslot${skip?' pslot--skip':''}`}>

      {/* ── En-tête : repas + boutons filtres + skip ── */}
      <div className="pslot-header">
        <span className="pslot-label">{info.icon} {info.label}</span>
        <div className="pslot-header-actions">

          {/* 🌿 Régime / Restrictions / Allergènes */}
          <button
            ref={dietBtnRef}
            className={`pslot-filter-btn${hasDietActive?' pslot-filter-btn--active':''}`}
            onClick={openDietPicker}
            title="Régime, restrictions, allergènes"
          >
            🌿{hasDietActive && <span className="pslot-filter-dot"/>}
          </button>

          {/* 💪 Santé */}
          <button
            ref={healthBtnRef}
            className={`pslot-filter-btn${hasHealthActive?' pslot-filter-btn--active':''}`}
            onClick={openHealthPicker}
            title="Filtres santé"
          >
            💪{hasHealthActive && <span className="pslot-filter-dot"/>}
          </button>

          {/* 🌍 Origine */}
          <button
            ref={originBtnRef}
            className={`pslot-filter-btn${hasOriginActive?' pslot-filter-btn--active':''}`}
            onClick={openOriginPicker}
            title="Cuisine / Origine"
          >
            🌍{hasOriginActive && <span className="pslot-filter-dot"/>}
          </button>

          {/* ⊘ Skip */}
          <button
            className={`pslot-skip-btn${skip?' pslot-skip-btn--skipped':''}`}
            onClick={onSkip}
            title={skip?'Reprendre ce repas':'Sauter (jeûne)'}
          >{skip?'↺':'⊘'}</button>
        </div>
      </div>

      {/* ── Chips des filtres actifs sur ce slot ── */}
      {(hasDietActive || hasHealthActive || hasOriginActive) && !skip && (
        <div className="pslot-active-filters">
          {slotDiet && (
            <button className="pslot-filter-badge" onClick={()=>onUpdate({diet:null})}>
              {DIET_OPTIONS.find(o=>o.value===slotDiet)?.label || slotDiet} ×
            </button>
          )}
          {slotDietExtras.map(v => (
            <button key={v} className="pslot-filter-badge" onClick={()=>toggleSlotDietExtra(v)}>
              {DIET_EXTRA_OPTIONS.find(o=>o.value===v)?.label || v} ×
            </button>
          ))}
          {slotAllergens.map(v => (
            <button key={v} className="pslot-filter-badge" onClick={()=>toggleSlotAllergen(v)}>
              {ALLERGEN_OPTIONS.find(o=>o.value===v)?.label || v} ×
            </button>
          ))}
          {slotHealthFilters.map(v => (
            <button key={v} className="pslot-filter-badge pslot-filter-badge--health" onClick={()=>toggleSlotHealth(v)}>
              {HEALTH_GROUPS.find(g=>g.value===v)?.label || v} ×
            </button>
          ))}
          {slotOrigins.map(v => (
            <button key={v} className="pslot-filter-badge pslot-filter-badge--origin" onClick={()=>toggleSlotOrigin(v)}>
              {_findOriginLabel(v)} ×
            </button>
          ))}
        </div>
      )}

      {/* ── Picker : 🌿 Régime / Restrictions / Allergènes ── */}
      {dietOpen && (
        <SlotPickerPortal pos={dietPos} onClose={()=>setDietOpen(false)}>
          <div className="pslot-picker-section">
            <div className="pslot-picker-label">Régime</div>
            <button className={`pslot-diet-opt${!slotDiet?' pslot-diet-opt--on':''}`}
              onClick={()=>onUpdate({diet:null})}>— Aucun —</button>
            {DIET_OPTIONS.map(o=>(
              <button key={o.value}
                className={`pslot-diet-opt${slotDiet===o.value?' pslot-diet-opt--on':''}`}
                onClick={()=>onUpdate({diet:o.value})}>{o.label}</button>
            ))}
          </div>
          <div className="pslot-picker-sep"/>
          <div className="pslot-picker-section">
            <div className="pslot-picker-label">Restrictions</div>
            {DIET_EXTRA_OPTIONS.map(o=>(
              <button key={o.value}
                className={`pslot-diet-opt${slotDietExtras.includes(o.value)?' pslot-diet-opt--on':''}`}
                onClick={()=>toggleSlotDietExtra(o.value)}>{o.label}</button>
            ))}
          </div>
          <div className="pslot-picker-sep"/>
          <div className="pslot-picker-section">
            <div className="pslot-picker-label">Allergènes</div>
            {ALLERGEN_OPTIONS.map(o=>(
              <button key={o.value}
                className={`pslot-diet-opt${slotAllergens.includes(o.value)?' pslot-diet-opt--on':''}`}
                onClick={()=>toggleSlotAllergen(o.value)}>{o.label}</button>
            ))}
          </div>
        </SlotPickerPortal>
      )}

      {/* ── Picker : 💪 Santé ── */}
      {healthOpen && (
        <SlotPickerPortal pos={healthPos} onClose={()=>setHealthOpen(false)}>
          <div className="pslot-picker-label">Santé — ce repas</div>
          {HEALTH_GROUPS.map(g=>(
            <button key={g.value}
              className={`pslot-diet-opt${slotHealthFilters.includes(g.value)?' pslot-diet-opt--on':''}`}
              onClick={()=>toggleSlotHealth(g.value)}>{g.label}</button>
          ))}
        </SlotPickerPortal>
      )}

      {/* ── Picker : 🌍 Origine ── */}
      {originOpen && (
        <SlotPickerPortal pos={originPos} onClose={()=>setOriginOpen(false)}>
          {ORIGIN_GROUPS.map(group=>(
            <div key={group.id} className="pslot-picker-section">
              <div className="pslot-picker-label">{group.label}</div>
              {group.children.map(c=>(
                <button key={c.value}
                  className={`pslot-diet-opt${slotOrigins.includes(c.value)?' pslot-diet-opt--on':''}`}
                  onClick={()=>toggleSlotOrigin(c.value)}>{c.label}</button>
              ))}
            </div>
          ))}
        </SlotPickerPortal>
      )}

      {skip ? (
        <div className="pslot-fasting">🌿 Jeûne</div>
      ) : (
        <>
          {/* Types de plat + convives */}
          <div className="pslot-config">
            <div className="pslot-dtype-chips">
              {dtList.map(dt => (
                <button key={dt.value}
                  className={`pslot-dtype-chip${dishTypes.includes(dt.value)?' pslot-dtype-chip--on':''}`}
                  onClick={()=>toggleDT(dt.value)}>{dt.label}</button>
              ))}
            </div>
            <div className="pslot-srv-row">
              <span className="pslot-srv-lbl">🧑‍🍳</span>
              <div className="servings-counter">
                <button className="servings-btn" onClick={()=>servings>1&&onUpdate({servings:servings-1})}>−</button>
                <span className="servings-val">{servings}</span>
                <button className="servings-btn" onClick={()=>onUpdate({servings:servings+1})}>+</button>
              </div>
            </div>
          </div>

          {/* Recettes */}
          {hasRec && (
            <div className="pslot-recipes">
              {recipes.map((recipe,i) => {
                const isRep = replacing?.day===dayKey && replacing?.meal===mealType && replacing?.idx===i;
                return (
                  <PlanningRecipeCard
                    key={recipe.id||i}
                    recipe={recipe}
                    onReplace={()=>onReplace(i)}
                    onSearch={()=>onSearch&&onSearch(i)}
                    onDelete={()=>onDelete&&onDelete(i)}
                    isReplacing={isRep}
                  />
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── PlanningDayCol ────────────────────────────────────────────────────────────

function PlanningDayCol({dayKey, dayIndex, dayData, enabledMeals, replacing, loading, onUpdate, onSkip, onReplace, onSearch, onDelete}) {
  const [c1,c2] = DAY_GRADIENTS[dayIndex%7];
  return (
    <div className="pday-col">
      <div className="pday-header" style={{background:`linear-gradient(135deg,${c1} 0%,${c2} 100%)`}}>
        {DAYS_FR[dayIndex]}
      </div>
      {MEAL_ORDER.map(m => {
        if (!enabledMeals[m]) return null;
        const slot = dayData?.[m] || { dishTypes:MEAL_DEFAULTS[m].dishTypes, servings:MEAL_DEFAULTS[m].servings, skip:false, recipes:[] };
        return (
          <PlanningSlot
            key={m}
            dayKey={dayKey}
            mealType={m}
            slotData={slot}
            enabled={true}
            replacing={replacing?.day===dayKey ? replacing : null}
            onUpdate={upd => onUpdate(dayKey,m,upd)}
            onSkip={()=>onSkip(dayKey,m)}
            onReplace={idx=>onReplace(dayKey,m,idx)}
            onSearch={idx=>onSearch&&onSearch(dayKey,m,idx)}
            onDelete={idx=>onDelete&&onDelete(dayKey,m,idx)}
          />
        );
      })}
      {loading && (
        <div className="pday-loading">
          <span className="prcard-spinner" style={{fontSize:20}}>↻</span>
        </div>
      )}
    </div>
  );
}

// ── Helpers liste de courses ──────────────────────────────────────────────────

function _fmtNet(value, unit) {
  if (value == null) return null;
  const v = value === Math.round(value) ? Math.round(value) : Math.round(value * 10) / 10;
  const label = { g:'g', ml:'ml', kg:'kg', piece:'pièce', pieces:'pièces',
    pinch:'pincée', leaf:'feuille', tbsp:'c. à s.', tsp:'c. à c.' };
  return `${v}\u202f${label[unit]||unit}`;   // espace fine insécable
}

// ── ShoppingView ──────────────────────────────────────────────────────────────

function ShoppingView({shopping, checked, fridgeIds, fridgeQtys, fridgeSufficient, onFridgeQtyChange, onFridgeSufficient, onToggle, onClearAll, onItemPriceUpdate}) {
  const {by_category, estimated_cost, n_recipes} = shopping;
  const allItems   = shopping.items||[];
  const nUnknown   = shopping.n_unknown_price || 0;
  const total      = allItems.length;
  const nChecked   = allItems.filter(i=>checked.has(i.ingredient)).length;
  const nFridge    = allItems.filter(i=>[...fridgeIds].some(f=>fridgeMatchesIng(f,i.ingredient))).length;
  const done       = nChecked+nFridge;
  const [copyDone, setCopyDone]       = useState(false);
  const [pantryOpen, setPantryOpen]   = useState(true);

  // Éléments nets (quantité à acheter après déduction frigo, hors cochés)
  const netItems = allItems.map(item => {
    const id         = item.ingredient;
    const inFrigo    = [...fridgeIds].some(f => fridgeMatchesIng(f, id));
    const sufficient = inFrigo && fridgeSufficient.has(id);
    const fQty       = inFrigo && !sufficient ? (fridgeQtys[id] || 0) : 0;
    const netValue   = sufficient ? 0 : (item.qty_value != null ? Math.max(0, item.qty_value - fQty) : item.qty_value);
    return { ...item, netValue, netQtyStr: netValue != null ? _fmtNet(netValue, item.qty_unit) : item.qty_str };
  }).filter(i => !checked.has(i.ingredient) && i.netValue !== 0);

  // Regrouper par catégorie (print + partage)
  const netByCat = {};
  for (const item of netItems) {
    const cat = Object.entries(by_category).find(([,its]) => its.some(x=>x.ingredient===item.ingredient))?.[0] || 'Autre';
    if (!netByCat[cat]) netByCat[cat] = [];
    netByCat[cat].push(item);
  }

  // Texte formaté pour le partage
  function buildShareText() {
    const lines = [`🛒 Liste de courses — ${n_recipes} recette${n_recipes>1?'s':''}\n`];
    // Items placard non couverts
    const pantryToBuy = pantryItems.filter(i => !checked.has(i.ingredient) && !fridgeSufficient.has(i.ingredient) && !(i.qty_value != null && (fridgeQtys[i.ingredient]||0) >= i.qty_value));
    if (pantryToBuy.length > 0) {
      lines.push('\n🗄️ Placard (à vérifier)');
      for (const item of pantryToBuy) {
        const qty = item.qty_str || '';
        const price = !item.price_unknown && item.package_label ? ` [${item.package_label} · ${item.price_eur?.toFixed(2)} €]` : '';
        lines.push(`  ☐ ${item.name_fr||item.ingredient.replace(/_/g,' ')}${qty?' — '+qty:''}${price}`);
      }
    }
    for (const [cat, catItems] of Object.entries(netByCat)) {
      lines.push(`\n${CAT_ICONS[cat.toLowerCase()]||'📦'} ${cat}`);
      for (const item of catItems) {
        const qty   = item.netQtyStr || (item.occurrences>1?`×${item.occurrences}`:'');
        const price = !item.price_unknown && item.package_label ? ` [${item.package_label} · ${item.price_eur?.toFixed(2)} €]` : '';
        lines.push(`  ☐ ${item.name_fr||item.ingredient.replace(/_/g,' ')}${qty?' — '+qty:''}${price}`);
      }
    }
    const total_cost = netItems.reduce((s,i) => s + (i.price_eur||0), 0) + pantryToBuy.reduce((s,i) => s + (i.price_eur||0), 0);
    if (total_cost > 0) lines.push(`\n💶 Total estimé : ~${total_cost.toFixed(2)} €`);
    if (nFridge>0) lines.push('◈ Quantités du frigo déjà déduites.');
    return lines.join('\n');
  }

  const handleShare = async () => {
    const text = buildShareText();
    if (navigator.share) {
      try {
        await navigator.share({ title: '🛒 Liste de courses', text });
      } catch { /* partage annulé par l'utilisateur */ }
    } else {
      // Fallback : copie dans le presse-papier
      try {
        await navigator.clipboard.writeText(text);
        setCopyDone(true);
        setTimeout(() => setCopyDone(false), 2500);
      } catch { /* presse-papier refusé par le navigateur */ }
    }
  };

  // Séparer items frigo / placard / normal pour l'affichage
  const pantryItems = allItems.filter(i => i.pantry && ![...fridgeIds].some(f=>fridgeMatchesIng(f,i.ingredient)));

  return (
    <div className="shopping-view">
      <div className="shopping-header no-print">
        <div className="shopping-stats">
          <div className="shopping-stat"><span className="shopping-stat-val">{n_recipes}</span><span className="shopping-stat-lbl">recette{n_recipes>1?'s':''}</span></div>
          <div className="shopping-stat"><span className="shopping-stat-val">{total}</span><span className="shopping-stat-lbl">articles</span></div>
          <div className="shopping-stat shopping-stat--done"><span className="shopping-stat-val">{done}/{total}</span><span className="shopping-stat-lbl">obtenus</span></div>
          {nFridge>0&&<div className="shopping-stat shopping-stat--frigo"><span className="shopping-stat-val">{nFridge}</span><span className="shopping-stat-lbl">◈ frigo</span></div>}
          {estimated_cost>0&&<div className="shopping-stat shopping-stat--cost"><span className="shopping-stat-val">~{estimated_cost.toFixed(2)} €</span><span className="shopping-stat-lbl">estimé</span></div>}
          {nUnknown>0&&<div className="shopping-stat shopping-stat--warn" title={`${nUnknown} ingrédient(s) sans prix dans le catalogue`}><span className="shopping-stat-val">⚠ {nUnknown}</span><span className="shopping-stat-lbl">prix inconnus</span></div>}
        </div>
        <div className="shopping-progress-wrap">
          <div className="shopping-progress-bar" style={{width:total>0?`${Math.round((done/total)*100)}%`:'0%'}}/>
        </div>
        <div className="shopping-header-actions">
          {nChecked>0&&<button className="shopping-clear-btn" onClick={onClearAll}>Tout décocher</button>}
          <button className="shopping-share-btn" onClick={handleShare} title={navigator.share?'Partager':'Copier dans le presse-papier'}>
            {copyDone ? '✓ Copié !' : navigator.share ? '↗ Partager' : '⎘ Copier'}
          </button>
          <button className="shopping-print-btn" onClick={()=>window.print()}>🖨️ Imprimer</button>
        </div>
      </div>

      {/* Section Placard */}
      {pantryItems.length > 0 && (
        <div className="shopping-pantry-section no-print">
          <button className="shopping-pantry-toggle" onClick={()=>setPantryOpen(o=>!o)}>
            <span>🗄️ Placard <span className="shopping-pantry-count">{pantryItems.length} article{pantryItems.length>1?'s':''}</span></span>
            <span className="shopping-pantry-chevron">{pantryOpen?'▾':'▸'}</span>
          </button>
          {pantryOpen && (
            <div className="shopping-pantry-list">
              {pantryItems.map(item => {
                const id        = item.ingredient;
                const sufficient = fridgeSufficient.has(id);
                const fQty      = !sufficient ? (fridgeQtys[id] || 0) : 0;
                const fullyCovered = sufficient || (item.qty_value != null && fQty >= item.qty_value);
                const isDone    = checked.has(id) || fullyCovered;
                return (
                  <div key={id} className={`shopping-pantry-item${isDone?' shopping-pantry-item--done':''}`}>
                    <div className="shopping-item-label">
                      <input type="checkbox" className="shopping-item-check" checked={isDone}
                        onChange={()=>!fullyCovered&&onToggle(id)} disabled={fullyCovered}/>
                      <span className="shopping-item-name">{item.name_fr||id.replace(/_/g,' ')}</span>
                      <span className="shopping-item-qty-wrap">
                        {sufficient
                          ? <span className="shopping-item-qty shopping-item-qty--net">✓ suffisant</span>
                          : item.qty_str && <span className="shopping-item-qty">{item.qty_str}</span>
                        }
                        {item.price_unknown
                          ? <span className="shopping-price-unknown">⚠ prix inconnu</span>
                          : !isDone && <PriceEditInline item={item} onSaved={updated => onItemPriceUpdate?.(updated)} />
                        }
                      </span>
                    </div>
                    <div className="shopping-frigo-row">
                      <label className="shopping-frigo-sufficient">
                        <input type="checkbox" checked={sufficient} onChange={()=>onFridgeSufficient(id)}/>
                        En stock ✓
                      </label>
                      {!sufficient && <>
                        <span className="shopping-frigo-sep">ou</span>
                        <span className="shopping-frigo-label">quantité :</span>
                        <input type="number" min="0" step="any" className="shopping-frigo-input" placeholder="0"
                          value={fridgeQtys[id]!=null?fridgeQtys[id]:''}
                          onChange={e=>onFridgeQtyChange(id,e.target.value===''?0:parseFloat(e.target.value)||0)}/>
                        {item.qty_unit&&<span className="shopping-frigo-unit">{item.qty_unit}</span>}
                      </>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Liste interactive principale (écran) */}
      <div className="shopping-categories no-print">
        {Object.entries(by_category).map(([cat,catItems])=>(
          <ShoppingCategory key={cat} cat={cat} items={catItems} checked={checked}
            fridgeIds={fridgeIds} fridgeQtys={fridgeQtys} fridgeSufficient={fridgeSufficient}
            onFridgeQtyChange={onFridgeQtyChange} onFridgeSufficient={onFridgeSufficient}
            onToggle={onToggle} onItemPriceUpdate={onItemPriceUpdate}/>
        ))}
      </div>

      {/* Vue impression — masquée à l'écran, visible à l'impression */}
      <div className="shopping-print-view print-only">
        <h2 className="shopping-print-title">🛒 Liste de courses</h2>
        <p className="shopping-print-sub">{n_recipes} recette{n_recipes>1?'s':''} · {netItems.length} article{netItems.length>1?'s':''} à acheter</p>
        {Object.entries(netByCat).map(([cat, catItems]) => (
          <div key={cat} className="shopping-print-cat">
            <div className="shopping-print-cat-label">{CAT_ICONS[cat.toLowerCase()]||'📦'} {cat}</div>
            <ul className="shopping-print-items">
              {catItems.map(item => (
                <li key={item.ingredient} className="shopping-print-item">
                  <span className="shopping-print-item-check">☐</span>
                  <span className="shopping-print-item-name">{item.name_fr||item.ingredient.replace(/_/g,' ')}</span>
                  <span className="shopping-print-item-qty">{item.netQtyStr || (item.occurrences>1?`×${item.occurrences}`:'')}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {nFridge>0&&<p className="shopping-print-frigo-note">◈ Quantités déjà disponibles dans votre frigo déduites.</p>}
      </div>
    </div>
  );
}

function ShoppingCategory({cat, items, checked, fridgeIds, fridgeQtys, fridgeSufficient, onFridgeQtyChange, onFridgeSufficient, onToggle, onItemPriceUpdate}) {
  const icon      = CAT_ICONS[cat.toLowerCase()]||'📦';
  const doneCount = items.filter(i=>{
    const inFrigo = [...fridgeIds].some(f=>fridgeMatchesIng(f,i.ingredient));
    if (!inFrigo) return checked.has(i.ingredient);
    if (fridgeSufficient.has(i.ingredient)) return true;
    const fQty = fridgeQtys[i.ingredient] || 0;
    return i.qty_value != null ? fQty >= i.qty_value : false;
  }).length;

  return (
    <div className={`shopping-category${doneCount===items.length?' shopping-category--done':''}`}>
      <div className="shopping-cat-header">
        <span className="shopping-cat-icon">{icon}</span>
        <span className="shopping-cat-label">{cat}</span>
        <span className="shopping-cat-count">{doneCount}/{items.length}</span>
      </div>
      <ul className="shopping-items">
        {items.map(item=>{
          const id        = item.ingredient;
          const inFrigo   = [...fridgeIds].some(f=>fridgeMatchesIng(f,id));
          const sufficient = inFrigo && fridgeSufficient.has(id);
          const fQty      = inFrigo && !sufficient ? (fridgeQtys[id] || 0) : 0;

          const netValue     = sufficient ? 0 : (item.qty_value != null ? Math.max(0, item.qty_value - fQty) : item.qty_value);
          const fullyCovered = sufficient || (inFrigo && item.qty_value != null && fQty >= item.qty_value);
          const isDone       = checked.has(id) || fullyCovered;

          const netStr = !sufficient && netValue != null && inFrigo && fQty > 0
            ? _fmtNet(netValue, item.qty_unit)
            : null;

          return (
            <li key={id} className={`shopping-item${isDone?' shopping-item--checked':''}${inFrigo?' shopping-item--frigo':''}`}>
              <div className="shopping-item-label">
                <input type="checkbox" className="shopping-item-check" checked={isDone}
                  onChange={()=>!fullyCovered&&onToggle(id)} disabled={fullyCovered}/>
                <span className="shopping-item-name">{item.name_fr||id.replace(/_/g,' ')}</span>
                <span className="shopping-item-qty-wrap">
                  {sufficient
                    ? <span className="shopping-item-qty shopping-item-qty--net">✓ suffisant</span>
                    : netStr
                      ? <><span className="shopping-item-qty shopping-item-qty--net">à acheter : {netStr}</span><span className="shopping-item-qty shopping-item-qty--orig">{item.qty_str}</span></>
                      : item.qty_str
                        ? <span className="shopping-item-qty">{item.qty_str}</span>
                        : item.occurrences>1&&<span className="shopping-item-qty">×{item.occurrences}</span>
                  }
                  {!isDone && (item.price_unknown
                    ? <span className="shopping-price-unknown">⚠ prix inconnu</span>
                    : <PriceEditInline item={item} onSaved={updated => onItemPriceUpdate?.(updated)} />
                  )}
                </span>
              </div>
              {inFrigo && (
                <div className="shopping-frigo-row">
                  <label className="shopping-frigo-sufficient">
                    <input type="checkbox" checked={sufficient}
                      onChange={()=>onFridgeSufficient(id)}/>
                    En stock ✓
                  </label>
                  {!sufficient && <>
                    <span className="shopping-frigo-sep">ou</span>
                    <span className="shopping-frigo-label">quantité :</span>
                    <input
                      type="number" min="0" step="any"
                      className="shopping-frigo-input"
                      placeholder="0"
                      value={fridgeQtys[id] != null ? fridgeQtys[id] : ''}
                      onChange={e => onFridgeQtyChange(id, e.target.value === '' ? 0 : parseFloat(e.target.value) || 0)}
                    />
                    {item.qty_unit && <span className="shopping-frigo-unit">{item.qty_unit}</span>}
                    {fullyCovered && !sufficient && <span className="shopping-frigo-ok">✓ couvert</span>}
                  </>}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function PlanningPage() {
  // ── UI ────────────────────────────────────────────────────────────────────
  const [view,        setView]        = useState('plan');
  const [loading,     setLoading]     = useState(false);
  const [shopLoad,    setShopLoad]    = useState(false);
  const [error,       setError]       = useState(null);
  const [replacing,   setReplacing]   = useState(null);
  const [searchModal, setSearchModal] = useState(null);

  // ── Filtres globaux (persistants via useFilterState) ──────────────────────
  const _sf = _loadPlanFilters();
  const fs = useFilterState({
    diet:          _sf.diet          || '',
    dietExtras:    _sf.dietExtras    || [],
    difficulty:    _sf.difficulty    || '',
    allergens:     _sf.allergens     || [],
    healthFilters: _sf.healthFilters || [],
    subFilters:    _sf.subFilters    || [],
    origins:       _sf.origins       || [],
    maxTime:       _sf.maxTime       || '',
    season:        '',   // non utilisé (remplacé par mois)
    dishFilters:   [],   // non utilisé en planning
  });

  const [month,     setMonth]     = useState(() => new Date().getMonth() + 1);
  const [diversity, setDiversity] = useState(() => {
    try { const v = localStorage.getItem('alim_plan_diversity'); return v !== null ? parseFloat(v) : 0.5; } catch { return 0.5; }
  });
  const [openSects, setOpenSects] = useState(new Set(['saison','regime']));

  // ── Repas actifs (persistants) ────────────────────────────────────────────
  const [enabledMeals, setEnabledMeals] = useState(_loadPlanMeals);

  // ── Plan ──────────────────────────────────────────────────────────────────
  const [plan, setPlan] = useState(()=>{
    try {
      const raw = localStorage.getItem(PLAN_KEY);
      if (raw) { const saved = JSON.parse(raw); if (saved && saved.lundi) return saved; }
    } catch { /* localStorage indisponible ou JSON corrompu */ }
    return createDefaultPlan();
  });

  const [shopping, setShopping] = useState(null);
  const [checked,  setChecked]  = useState(()=>{
    try{const r=localStorage.getItem(CHECKED_KEY);return r?new Set(JSON.parse(r)):new Set();}
    catch{return new Set();}
  });
  // Fix: alim_frigo_selected est un tableau de strings (Set sérialisé depuis FrigoPage)
  const [fridgeIds] = useState(()=>{
    try{const r=localStorage.getItem('alim_frigo_selected');return r?new Set(JSON.parse(r)):new Set();}
    catch{return new Set();}
  });
  const [fridgeQtys, setFridgeQtys] = useState(()=>{
    try{const r=localStorage.getItem(FRIGO_QTYS_KEY);return r?JSON.parse(r):{};}
    catch{return {};}
  });
  const [fridgeSufficient, setFridgeSufficient] = useState(()=>{
    try{const r=localStorage.getItem(FRIGO_SUFFICIENT_KEY);return r?new Set(JSON.parse(r)):new Set();}
    catch{return new Set();}
  });

  // ── Persistance ───────────────────────────────────────────────────────────
  useEffect(()=>{
    try{if(plan)localStorage.setItem(PLAN_KEY,JSON.stringify(plan));else localStorage.removeItem(PLAN_KEY);}catch{ /* localStorage indisponible */ }
  },[plan]);

  useEffect(()=>{
    try{localStorage.setItem(CHECKED_KEY,JSON.stringify([...checked]));}catch{ /* localStorage indisponible */ }
  },[checked]);

  useEffect(()=>{
    try{localStorage.setItem(FRIGO_QTYS_KEY,JSON.stringify(fridgeQtys));}catch{ /* localStorage indisponible */ }
  },[fridgeQtys]);

  useEffect(()=>{
    try{localStorage.setItem(FRIGO_SUFFICIENT_KEY,JSON.stringify([...fridgeSufficient]));}catch{ /* localStorage indisponible */ }
  },[fridgeSufficient]);

  useEffect(()=>{
    try{
      localStorage.setItem(PLAN_FILTERS_KEY, JSON.stringify({
        diet:          fs.diet,
        dietExtras:    [...fs.dietExtras],
        difficulty:    fs.difficulty,
        allergens:     [...fs.allergens],
        healthFilters: [...fs.healthFilters],
        subFilters:    [...fs.subFilters],
        origins:       [...fs.origins],
        maxTime:       fs.maxTime,
      }));
    }catch{ /* localStorage indisponible */ }
  },[fs.diet, fs.dietExtras, fs.difficulty, fs.allergens, fs.healthFilters, fs.subFilters, fs.origins, fs.maxTime]);

  useEffect(()=>{
    try{localStorage.setItem(PLAN_MEALS_KEY, JSON.stringify(enabledMeals));}catch{ /* localStorage indisponible */ }
  },[enabledMeals]);

  useEffect(()=>{
    try{localStorage.setItem('alim_plan_diversity', String(diversity));}catch{ /* localStorage indisponible */ }
  },[diversity]);

  // ── Helpers UI ────────────────────────────────────────────────────────────
  const toggleSect    = id => setOpenSects(p=>{const n=new Set(p);n.has(id)?n.delete(id):n.add(id);return n;});
  const toggleChecked      = useCallback(id=>setChecked(p=>{const n=new Set(p);n.has(id)?n.delete(id):n.add(id);return n;}),[]);
  const setFridgeQty       = useCallback((ing, val)=>setFridgeQtys(p=>({...p,[ing]:val})),[]);
  const toggleFridgeSuf    = useCallback(id=>setFridgeSufficient(p=>{const n=new Set(p);n.has(id)?n.delete(id):n.add(id);return n;}),[]);
  const handleItemPriceUpdate = useCallback(updated => setShopping(prev => {
    if (!prev) return prev;
    const patch    = items => items.map(i => i.ingredient === updated.ingredient ? {...i, ...updated} : i);
    const patchCat = by_cat => Object.fromEntries(Object.entries(by_cat).map(([cat, its]) => [cat, patch(its)]));
    return { ...prev, items: patch(prev.items||[]), by_category: patchCat(prev.by_category||{}) };
  }), []);

  const resetFilters = () => fs.clearAll();

  // ── Plan helpers ──────────────────────────────────────────────────────────
  const updateSlot = useCallback((dayKey,mealType,upd)=>{
    setPlan(p=>{ const n=JSON.parse(JSON.stringify(p)); Object.assign(n[dayKey][mealType],upd); return n; });
    setShopping(null);
  },[]);

  const toggleSkip = useCallback((dayKey,mealType)=>{
    setPlan(p=>{
      const n=JSON.parse(JSON.stringify(p));
      if(n[dayKey]?.[mealType]) n[dayKey][mealType].skip=!n[dayKey][mealType].skip;
      return n;
    });
    setShopping(null);
  },[]);

  // ── Génération ────────────────────────────────────────────────────────────
  const generatePlan = async ()=>{
    const active = MEAL_ORDER.filter(m=>enabledMeals[m]);
    if(!active.length){setError('Activez au moins un repas.');return;}

    setLoading(true); setError(null); setShopping(null);

    try {
      // Allergens : envoyés comme flags boolean (identique à HomePage → apply_filters côté backend)
      const apiParams = {
        month,
        diet:         fs.diet || undefined,
        max_time:     fs.maxTime ? parseInt(fs.maxTime) : undefined,
        // Flags allergens — même format que /recettes/recherche (apply_filters)
        gluten_free:  fs.allergens.has('gluten_free')  || undefined,
        lactose_free: fs.allergens.has('lactose_free') || undefined,
        nut_free:     fs.allergens.has('nut_free')     || undefined,
        egg_free:     fs.allergens.has('egg_free')     || undefined,
        dairy_free:   fs.allergens.has('dairy_free')   || undefined,
        soy_free:     fs.allergens.has('soy_free')     || undefined,
        difficulty:   fs.difficulty || undefined,
        health:       fs.healthFilters.size > 0 ? [...fs.healthFilters] : undefined,
        cuisine:      fs.origins.size === 1 ? [...fs.origins][0] : undefined,
        diversity,
      };

      const neededDTs = new Set();
      for(const dk of DAYS_KEY)
        for(const m of active){
          const slot=plan[dk]?.[m];
          if(!slot?.skip)(slot?.dishTypes||MEAL_DEFAULTS[m].dishTypes).forEach(dt=>neededDTs.add(dt));
        }

      const uniqueDTs = [...neededDTs];
      const results   = await Promise.all(
        uniqueDTs.map(dt=>planningApi.mealplan({...apiParams, dish_type:dt}))
      );
      const byDT = Object.fromEntries(uniqueDTs.map((dt,i)=>[dt,results[i]]));

      const dtDayUsed = {};
      const newPlan   = JSON.parse(JSON.stringify(plan));
      newPlan.meta    = { generated_at: new Date().toISOString() };

      for(const dk of DAYS_KEY){
        for(const m of MEAL_ORDER){
          if(!enabledMeals[m]) continue;
          const slot = newPlan[dk][m];
          if(slot.skip){ slot.recipes=[]; continue; }
          slot.recipes=[];
          for(const dt of slot.dishTypes){
            const res=byDT[dt];
            if(!res) continue;
            const dayData=res[dk]||{};
            const key=`${dt}:${dk}`;
            const useIdx=dtDayUsed[key]||0;
            const recipe=useIdx===0?(dayData.lunch||dayData.dinner):(dayData.dinner||dayData.lunch);
            dtDayUsed[key]=useIdx+1;
            if(recipe) slot.recipes.push({...recipe,_dish_type:dt});
          }
        }
      }

      setPlan(newPlan);
      setView('plan');
    } catch(err){
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Suppression ───────────────────────────────────────────────────────────
  const deleteRecipe = useCallback((dayKey,mealType,idx)=>{
    setPlan(p=>{ const n=JSON.parse(JSON.stringify(p)); n[dayKey]?.[mealType]?.recipes?.splice(idx,1); return n; });
    setShopping(null);
  },[]);

  // ── Remplacement ──────────────────────────────────────────────────────────
  const replaceRecipe = useCallback(async(dayKey,mealType,idx)=>{
    if(!plan) return;
    const slot   = plan[dayKey]?.[mealType];
    const recipe = slot?.recipes?.[idx];
    const dt     = recipe?._dish_type||'main';
    const usedIds= getAllUsedIds(plan).filter(id=>id!==recipe?.id);
    // Le diet du slot est prioritaire sur le global
    const effectiveDiet = slot?.diet || fs.diet || undefined;

    // Merge global allergens + slot allergens for the replace call
    const effectiveAllergens = new Set([...fs.allergens, ...(slot?.allergens || [])]);

    setReplacing({day:dayKey,meal:mealType,idx});
    try{
      const result=await planningApi.mealplan({
        month,
        diet:         effectiveDiet,
        difficulty:   fs.difficulty || undefined,
        dish_type:    dt,
        exclude_ids:  usedIds.length?usedIds:undefined,
        gluten_free:  effectiveAllergens.has('gluten_free')  || undefined,
        lactose_free: effectiveAllergens.has('lactose_free') || undefined,
        nut_free:     effectiveAllergens.has('nut_free')     || undefined,
        egg_free:     effectiveAllergens.has('egg_free')     || undefined,
        dairy_free:   effectiveAllergens.has('dairy_free')   || undefined,
        soy_free:     effectiveAllergens.has('soy_free')     || undefined,
      });
      const dd=result[dayKey]||{};
      const newR=dd.lunch||dd.dinner;
      if(newR){
        setPlan(p=>{
          const n=JSON.parse(JSON.stringify(p));
          if(n[dayKey]?.[mealType]?.recipes?.[idx]!==undefined)
            n[dayKey][mealType].recipes[idx]={...newR,_dish_type:dt};
          return n;
        });
        setShopping(null);
      }
    }catch(err){console.error('replace:',err.message);}
    finally{setReplacing(null);}
  },[plan, month, fs.diet, fs.difficulty, fs.allergens]);

  // ── Recherche manuelle ────────────────────────────────────────────────────
  const handleSearchSelect = useCallback((recipe)=>{
    if (!searchModal) return;
    const { dayKey, mealType, idx } = searchModal;
    setPlan(p => {
      const n    = JSON.parse(JSON.stringify(p));
      const slot = n[dayKey]?.[mealType];
      if (!slot) return p;
      const dt   = slot.recipes?.[idx]?._dish_type || slot.dishTypes?.[0] || 'main';
      const entry = {
        id:        recipe.id,
        title_fr:  recipe.titles?.fr || recipe.title_fr || recipe.title || '',
        title:     recipe.title || recipe.titles?.original || '',
        _dish_type:dt,
      };
      if (idx !== undefined && slot.recipes?.[idx] !== undefined) {
        slot.recipes[idx] = entry;
      } else {
        if (!slot.recipes) slot.recipes = [];
        slot.recipes.push(entry);
      }
      return n;
    });
    setShopping(null);
    setSearchModal(null);
  }, [searchModal]);

  // ── Shopping ──────────────────────────────────────────────────────────────
  const generateShopping = async()=>{
    if(!plan) return;
    setShopLoad(true); setError(null);
    try{
      const data=await planningApi.shoppingList({plan:planToShoppingFormat(plan)});
      setShopping(data);
    }catch(err){setError(err.message);}
    finally{setShopLoad(false);}
  };

  const planHasRecipes = hasAnyRecipes(plan);

  // ── Rendu ─────────────────────────────────────────────────────────────────
  return (
    <div className="page-planning">
      <div className="page-header">
        <h1 className="page-title"><span className="page-icon">▦</span> Planning</h1>
        <p className="page-sub">Plan de repas hebdomadaire personnalisé + liste de courses.</p>
      </div>

      <div className="planning-layout">

        {/* ── SIDEBAR ─────────────────────────────────────────────────────── */}
        <aside className="planning-sidebar">

          <div className="planning-filter-panel">
            <div className="planning-filter-header">
              <span className="planning-filter-title">Filtres globaux</span>
              {fs.hasActiveFilters && (
                <button className="planning-filter-reset" onClick={resetFilters}>Réinitialiser</button>
              )}
            </div>

            {/* ── Saison / Mois — grille mois personnalisée ── */}
            <FilterSection id="saison" label="🗓 Saison / Mois"
              isOpen={openSects.has('saison')} onToggle={toggleSect} hasActive={!!month}>
              <div className="plan-months-grid">
                <button
                  className={`plan-month-chip plan-month-chip--all${!month?' plan-month-chip--active':''}`}
                  onClick={()=>setMonth(null)}>Toutes</button>
                {MONTHS_FR.map((m,i)=>(
                  <button key={i}
                    className={`plan-month-chip${month===i+1?' plan-month-chip--active':''}`}
                    onClick={()=>setMonth(p=>p===i+1?null:i+1)}>{m}</button>
                ))}
              </div>
            </FilterSection>

            {/* ── Régime ── */}
            <FilterSection id="regime" label="Régime"
              isOpen={openSects.has('regime')} onToggle={toggleSect} hasActive={!!fs.diet}>
              <div className="plan-filter-chips">
                {DIET_OPTIONS.map(o=>(
                  <button key={o.value}
                    className={`plan-filter-chip${fs.diet===o.value?' plan-filter-chip--active':''}`}
                    onClick={()=>fs.setDiet(p=>p===o.value?'':o.value)}>{o.label}</button>
                ))}
              </div>
            </FilterSection>

            {/* ── Restrictions ── */}
            <FilterSection id="restrictions" label="Restrictions"
              isOpen={openSects.has('restrictions')} onToggle={toggleSect} hasActive={fs.dietExtras.size>0}>
              <div className="plan-filter-chips">
                {DIET_EXTRA_OPTIONS.map(o=>(
                  <button key={o.value}
                    className={`plan-filter-chip${fs.dietExtras.has(o.value)?' plan-filter-chip--active':''}`}
                    onClick={()=>fs.toggleDietExtra(o.value)}>{o.label}</button>
                ))}
              </div>
            </FilterSection>

            {/* ── Allergènes ── */}
            <FilterSection id="allergenes" label="Allergènes"
              isOpen={openSects.has('allergenes')} onToggle={toggleSect} hasActive={fs.allergens.size>0}>
              <div className="plan-filter-chips">
                {ALLERGEN_OPTIONS.map(o=>(
                  <button key={o.value}
                    className={`plan-filter-chip${fs.allergens.has(o.value)?' plan-filter-chip--active':''}`}
                    onClick={()=>fs.toggleAllergen(o.value)}>{o.label}</button>
                ))}
              </div>
            </FilterSection>

            {/* ── Santé ── */}
            <FilterSection id="sante" label="💪 Santé"
              isOpen={openSects.has('sante')} onToggle={toggleSect}
              hasActive={fs.healthFilters.size>0||fs.subFilters.size>0}>
              <HealthAccordion
                groups={HEALTH_GROUPS}
                selected={fs.healthFilters}
                subSelected={fs.subFilters}
                onToggle={fs.toggleHealth}
                onSubToggle={fs.toggleSub}
              />
            </FilterSection>

            {/* ── Difficulté (uniquement global) ── */}
            <FilterSection id="difficulte" label="Difficulté"
              isOpen={openSects.has('difficulte')} onToggle={toggleSect} hasActive={!!fs.difficulty}>
              <div className="plan-filter-chips">
                {DIFFICULTY_OPTIONS.map(o=>(
                  <button key={o.value}
                    className={`plan-filter-chip${fs.difficulty===o.value?' plan-filter-chip--active':''}`}
                    onClick={()=>fs.setDifficulty(p=>p===o.value?'':o.value)}>{o.label}</button>
                ))}
              </div>
            </FilterSection>

            {/* ── Origine ── */}
            <FilterSection id="origine" label="🌍 Origine"
              isOpen={openSects.has('origine')} onToggle={toggleSect} hasActive={fs.origins.size>0}>
              <OriginAccordion
                groups={ORIGIN_GROUPS}
                selected={fs.origins}
                onToggle={fs.toggleOrigin}
                onBulkToggle={fs.bulkToggleOrigins}
              />
            </FilterSection>

            {/* ── Temps max ── */}
            <FilterSection id="temps" label="Temps max"
              isOpen={openSects.has('temps')} onToggle={toggleSect} hasActive={!!fs.maxTime}>
              <div className="frigo-slider-row" style={{padding:'4px 0'}}>
                <input type="range" min={0} max={120} step={15}
                  value={fs.maxTime ? parseInt(fs.maxTime) : 0}
                  onChange={e=>fs.setMaxTime(e.target.value==='0'?'':e.target.value)}
                  className="frigo-slider"/>
                <span className="frigo-slider-val" style={{minWidth:56}}>
                  {fs.maxTime?`${fs.maxTime} min`:'Illimité'}
                </span>
              </div>
            </FilterSection>
          </div>

          {/* ── Repas actifs ── */}
          <div className="meal-toggles-panel">
            <span className="meal-toggles-title">Repas actifs</span>
            <div className="meal-toggles-row">
              {MEAL_ORDER.map(m=>(
                <button key={m}
                  className={`meal-toggle-btn${enabledMeals[m]?' meal-toggle-btn--on':''}`}
                  onClick={()=>setEnabledMeals(p=>({...p,[m]:!p[m]}))}
                  title={MEAL_INFO[m].label}>
                  {MEAL_INFO[m].icon}
                  <span>{m==='breakfast'?'Petit-déj':m==='lunch'?'Déjeuner':'Dîner'}</span>
                </button>
              ))}
            </div>
          </div>

          {/* ── Diversité / Variété ── */}
          <div className="plan-diversity-wrap">
            <div className="plan-diversity-header">
              <span className="plan-diversity-label">Variété</span>
              <span className="plan-diversity-val">
                {diversity <= 0.15 ? '🎯 Optimal' : diversity <= 0.45 ? '⚖️ Équilibré' : diversity <= 0.75 ? '🎲 Varié' : '🌀 Aléatoire'}
              </span>
            </div>
            <input type="range" min={0} max={1} step={0.05}
              value={diversity}
              onChange={e => setDiversity(parseFloat(e.target.value))}
              className="frigo-slider plan-diversity-slider"
            />
            <p className="plan-diversity-hint">
              {diversity <= 0.15
                ? 'Toujours les recettes les mieux notées.'
                : diversity <= 0.45
                ? 'Favorise les meilleures recettes avec un peu de surprise.'
                : diversity <= 0.75
                ? 'Bonne surprise à chaque génération.'
                : 'Sélection très aléatoire parmi les candidats.'}
            </p>
          </div>

          {/* ── Bouton générer ── */}
          <button className="frigo-search-btn" onClick={generatePlan} disabled={loading}
            style={{width:'100%',marginTop:8}}>
            {loading?'⏳ Génération…':planHasRecipes?'↻ Régénérer':'✦ Générer mon planning'}
          </button>

          {planHasRecipes&&(
            <button className="plan-reset-btn"
              onClick={()=>{setPlan(createDefaultPlan());setShopping(null);setView('plan');}}>
              ✕ Réinitialiser le planning
            </button>
          )}
        </aside>

        {/* ── CONTENU PRINCIPAL ────────────────────────────────────────────── */}
        <main className="planning-main">

          {error&&(
            <div className="state-msg state-msg--error"
              style={{marginBottom:16,padding:'12px 16px',textAlign:'left',border:'1px solid var(--red)',borderRadius:8}}>
              {error}
            </div>
          )}

          {planHasRecipes&&(
            <div className="planning-tabs">
              <button className={`plan-tab-btn${view==='plan'?' plan-tab-btn--active':''}`}
                onClick={()=>setView('plan')}>▦ Planning</button>
              <button className={`plan-tab-btn${view==='shopping'?' plan-tab-btn--active':''}`}
                onClick={()=>setView('shopping')}>
                🛒 {shopping?`Courses (${(shopping.items||[]).length})` : 'Liste de courses'}
              </button>
            </div>
          )}

          {view==='plan'&&(
            <div className="pday-grid">
              {DAYS_KEY.map((dk,di)=>(
                <PlanningDayCol
                  key={dk}
                  dayKey={dk}
                  dayIndex={di}
                  dayData={plan[dk]}
                  enabledMeals={enabledMeals}
                  replacing={replacing}
                  loading={false}
                  onUpdate={updateSlot}
                  onSkip={toggleSkip}
                  onReplace={replaceRecipe}
                  onSearch={(dayKey,m,idx)=>setSearchModal({dayKey,mealType:m,idx})}
                  onDelete={(dayKey,m,idx)=>deleteRecipe(dayKey,m,idx)}
                />
              ))}
            </div>
          )}

          {!MEAL_ORDER.some(m=>enabledMeals[m])&&view==='plan'&&(
            <p className="planning-hint" style={{marginTop:16}}>
              Activez au moins un repas dans la sidebar pour configurer votre planning.
            </p>
          )}

          {view==='shopping'&&(
            <>
              {!shopping&&!shopLoad&&(
                <div className="shopping-cta">
                  <p className="shopping-cta-text">Votre planning est prêt. Cliquez pour générer la liste de courses complète.</p>
                  <button className="frigo-search-btn" onClick={generateShopping} style={{maxWidth:340}}>
                    🛒 Générer la liste de courses
                  </button>
                </div>
              )}
              {shopLoad&&<div className="state-msg">Génération de la liste…</div>}
              {shopping&&(
                <ShoppingView shopping={shopping} checked={checked} fridgeIds={fridgeIds}
                  fridgeQtys={fridgeQtys} fridgeSufficient={fridgeSufficient}
                  onFridgeQtyChange={setFridgeQty} onFridgeSufficient={toggleFridgeSuf}
                  onToggle={toggleChecked} onClearAll={()=>setChecked(new Set())}
                  onItemPriceUpdate={handleItemPriceUpdate}/>
              )}
            </>
          )}
        </main>
      </div>

      {searchModal && (
        <RecipeSearchModal
          onSelect={handleSearchSelect}
          onClose={()=>setSearchModal(null)}
        />
      )}
    </div>
  );
}
