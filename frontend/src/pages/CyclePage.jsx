import { useState, useEffect } from 'react';
import { cycle as cycleApi, recipes as recipesApi } from '../api';
import RecipeCard, { computeAlimScore } from '../components/RecipeCard';
import { useFilterState, FiltersBlock, localFilterRecipes } from '../components/RecipeFiltersShared';
import translations from '../translations.json';

const CYCLE_KEY = 'alim_cycle_phase';

// ── Données ───────────────────────────────────────────────────────────────────
const CYCLE_PHASES = [
  {
    id: 'menstrual', label: 'Menstruelle', range: 'J1 – J5', moon: '🌑', moonName: 'Nouvelle lune',
    title: 'Recharge en fer & réconfort',
    desc: 'Le corps perd du sang et du fer. Fatigue, crampes, inflammation sont fréquentes. Compensez les pertes en fer, réduisez l\'inflammation avec des oméga-3, soutenez le système nerveux avec du magnésium.',
    longDesc: [
      'La phase menstruelle marque le début du cycle. La chute brutale de progestérone et d\'œstrogènes déclenche la desquamation de l\'endomètre — c\'est la perte de sang. Le corps mobilise beaucoup d\'énergie : il évacue, contracte, régénère.',
      'Sur 5 jours, vous perdez en moyenne 30 à 80 ml de sang, soit 15 à 40 mg de fer. C\'est l\'équivalent d\'un apport quotidien complet. Sans recharge, c\'est la voie ouverte à l\'anémie ferriprive, surtout en alimentation végétale où le fer non-héminique est moins biodisponible.',
      'Privilégiez l\'écoute, le repos, la chaleur. C\'est aussi un moment d\'introspection — l\'énergie mentale est différente. Utilisez-la pour la réflexion, pas pour des décisions sociales lourdes.',
    ],
    symptoms: [
      { icon: '😴', label: 'Fatigue', detail: 'Énergie basse, besoin de sommeil accru' },
      { icon: '🌡', label: 'Crampes', detail: 'Contractions utérines, douleurs lombaires' },
      { icon: '🧠', label: 'Brouillard mental', detail: 'Concentration et mémoire diminuées' },
      { icon: '💧', label: 'Rétention d\'eau', detail: 'Légère prise de poids, ballonnements' },
      { icon: '🌿', label: 'Sensibilité accrue', detail: 'Émotions amplifiées, besoin de calme' },
      { icon: '🔥', label: 'Inflammation', detail: 'Prostaglandines élevées, sensibilité' },
    ],
    avoid: ['Café excessif (vasoconstricteur)', 'Sucre raffiné (inflammation)', 'Alcool (déshydratation)', 'Aliments très salés'],
    favor: ['Aliments chauds et cuits', 'Bouillons riches', 'Cacao pur, thé rouge', 'Tisanes (camomille, gingembre)'],
    activity: 'Yoga doux, marche, étirements lombaires. Évitez les efforts intenses, écoutez la fatigue.',
    needs: [
      { icon: '🩸', label: 'Fer', detail: 'Lentilles, épinards, betterave' },
      { icon: '🧲', label: 'Magnésium', detail: 'Anti-crampes — chocolat noir, noix' },
      { icon: '🐟', label: 'Oméga-3', detail: 'Anti-inflammatoire — lin, noix' },
      { icon: '🍊', label: 'Vitamine C', detail: 'Booste l\'absorption du fer' },
    ],
    ingredients: ['Lentilles corail', 'Épinards', 'Betterave', 'Chocolat noir 70%', 'Graines de lin', 'Orange', 'Persil', 'Quinoa'],
  },
  {
    id: 'follicular', label: 'Folliculaire', range: 'J6 – J14', moon: '🌒', moonName: 'Premier croissant',
    title: 'Énergie légère & hydratation',
    desc: 'Les œstrogènes remontent, l\'énergie revient. Aliments légers, protéines végétales, soutien de la croissance cellulaire et de la préparation à l\'ovulation.',
    longDesc: [
      'C\'est la phase de remontée. Les œstrogènes augmentent progressivement, stimulant la maturation d\'un follicule ovarien. La FSH (hormone folliculo-stimulante) prépare l\'ovulation.',
      'Vous récupérez de l\'énergie, du focus, de la libido. C\'est la meilleure fenêtre pour démarrer des projets, apprendre, faire du sport intense. Le corps est dans une dynamique constructive : il synthétise, il bâtit.',
      'C\'est aussi le moment où la peau est la plus éclatante grâce aux œstrogènes. Profitez de cette fenêtre productive — mais ne brûlez pas tout : gardez de l\'énergie pour le pic ovulatoire.',
    ],
    symptoms: [
      { icon: '⚡', label: 'Énergie renouvelée', detail: 'Vitalité physique et mentale' },
      { icon: '🎯', label: 'Focus accru', detail: 'Concentration et créativité élevées' },
      { icon: '💖', label: 'Humeur stable', detail: 'Sérotonine en hausse' },
      { icon: '✨', label: 'Peau éclatante', detail: 'Œstrogènes au top, peau hydratée' },
      { icon: '💪', label: 'Force physique', detail: 'Meilleure récupération musculaire' },
      { icon: '🧘', label: 'Sociabilité', detail: 'Envie d\'extérieur et d\'interactions' },
    ],
    avoid: ['Excès de gras saturés', 'Repas lourds et longs à digérer', 'Excès de sucre raffiné'],
    favor: ['Fermentés (kéfir, kombucha, miso)', 'Crudités, salades fraîches', 'Smoothies verts', 'Graines germées'],
    activity: 'HIIT, course, vélo, danse — toutes les activités intenses sont bienvenues. Phase idéale pour les records perso.',
    needs: [
      { icon: '💪', label: 'Protéines', detail: 'Quinoa, tofu, pois chiches' },
      { icon: '🥦', label: 'Vitamines B', detail: 'Brocoli, avocat, légumineuses' },
      { icon: '🌾', label: 'Fibres', detail: 'Avoine, chia' },
      { icon: '💧', label: 'Hydratation', detail: 'Concombre, courgette' },
    ],
    ingredients: ['Quinoa', 'Tofu', 'Pois chiches', 'Brocoli', 'Avocat', 'Concombre', 'Courgette', 'Avoine'],
  },
  {
    id: 'ovulatory', label: 'Ovulatoire', range: 'J15 – J17', moon: '🌕', moonName: 'Pleine lune',
    title: 'Soutien hépatique maximal',
    desc: 'Pic hormonal (œstrogènes + LH). Le foie travaille davantage pour métaboliser les hormones. Antioxydants et zinc protègent les cellules, fibres aident l\'élimination hormonale.',
    longDesc: [
      'L\'ovulation : le follicule mature libère l\'ovule. Pic d\'œstrogènes, pic de LH. Phase courte mais intense — fenêtre de fertilité maximale.',
      'Le foie est en surcharge : il doit métaboliser des taux d\'œstrogènes très élevés et les évacuer correctement via la bile, puis l\'intestin. Les crucifères (brocoli, chou-fleur, choux) contiennent du DIM qui aide spécifiquement à la détox œstrogénique.',
      'Sur le plan énergétique, vous êtes au sommet. Communication, confiance, charisme — c\'est la phase la plus solaire. Trois jours seulement : profitez-en pour les présentations, les négociations, les premières fois.',
    ],
    symptoms: [
      { icon: '🔥', label: 'Libido maximale', detail: 'Pic hormonal, sensibilité augmentée' },
      { icon: '🎤', label: 'Confiance', detail: 'Charisme et expression à leur meilleur' },
      { icon: '🌡', label: 'Légère hausse de t°', detail: 'Température basale +0.3 à +0.5°C' },
      { icon: '💧', label: 'Glaire cervicale', detail: 'Plus abondante, signe de fertilité' },
      { icon: '⚡', label: 'Énergie au sommet', detail: 'Plateau d\'énergie' },
      { icon: '🤕', label: 'Mittelschmerz', detail: 'Possible douleur ovarienne brève' },
    ],
    avoid: ['Alcool (charge hépatique)', 'Aliments transformés', 'Sucres raffinés', 'Régime trop pauvre en gras'],
    favor: ['Crucifères (brocoli, chou-fleur, kale)', 'Baies rouges et bleues', 'Citron, persil (détox)', 'Légumes verts amers'],
    activity: 'Phase haute — sports collectifs, défis physiques, danse. Évitez les longues sessions d\'endurance qui épuisent.',
    needs: [
      { icon: '🫐', label: 'Antioxydants', detail: 'Baies, tomate, grenade' },
      { icon: '🍋', label: 'Vitamine C', detail: 'Poivron, agrumes' },
      { icon: '⚡', label: 'Zinc', detail: 'Graines de courge, sésame' },
      { icon: '🥬', label: 'Crucifères', detail: 'Brocoli, chou-fleur' },
    ],
    ingredients: ['Myrtilles', 'Grenade', 'Poivron rouge', 'Citron', 'Graines de courge', 'Sésame', 'Chou-fleur', 'Brocoli'],
  },
  {
    id: 'luteal', label: 'Lutéale', range: 'J18 – J28', moon: '🌗', moonName: 'Dernier quartier',
    title: 'Glycémie stable & anti-SPM',
    desc: 'La progestérone domine, envies sucrées et irritabilité apparaissent. Glucides complexes stabilisent la glycémie, magnésium réduit le SPM, vitamine B6 régule l\'humeur.',
    longDesc: [
      'Phase post-ovulatoire. Le corps jaune (issu du follicule rompu) sécrète de la progestérone, qui prépare l\'utérus à une éventuelle nidation. Si la fécondation n\'a pas lieu, les taux chutent en fin de phase — c\'est le SPM.',
      'La progestérone augmente le métabolisme basal (+150 à +300 kcal/jour), d\'où la sensation de faim plus marquée. Elle ralentit aussi le transit, ce qui peut causer ballonnements et constipation. C\'est aussi pourquoi le sucre attire tant : la glycémie devient plus instable.',
      'Les jours 22 à 28 sont les plus délicats : irritabilité, anxiété, fringales, fatigue, douleurs aux seins. C\'est le moment de ralentir, de manger plus de glucides complexes, de pratiquer la cohérence cardiaque.',
    ],
    symptoms: [
      { icon: '🍬', label: 'Fringales sucrées', detail: 'Glycémie instable, baisse de sérotonine' },
      { icon: '😤', label: 'Irritabilité', detail: 'Chute de sérotonine en fin de phase' },
      { icon: '🤰', label: 'Ballonnements', detail: 'Ralentissement digestif' },
      { icon: '🌧', label: 'Mélancolie', detail: 'Énergie introspective' },
      { icon: '💤', label: 'Sommeil perturbé', detail: 'Insomnies, réveils nocturnes' },
      { icon: '🪞', label: 'Sensibilité corporelle', detail: 'Tensions mammaires, peau plus grasse' },
    ],
    avoid: ['Sucres rapides (fringales)', 'Alcool (aggrave le SPM)', 'Café excessif (anxiété)', 'Sel en excès (rétention)'],
    favor: ['Patate douce, riz complet', 'Chocolat noir 70%+', 'Bananes (B6, magnésium)', 'Tisanes (gattilier, mélisse)'],
    activity: 'Yoga, pilates, marche, natation douce. Diminuez progressivement l\'intensité au fil des jours.',
    needs: [
      { icon: '🧲', label: 'Magnésium', detail: 'Chocolat noir, amandes, banane' },
      { icon: '🍠', label: 'Glucides complexes', detail: 'Patate douce, riz complet' },
      { icon: '🧠', label: 'Vitamine B6', detail: 'Banane, lentilles' },
      { icon: '🌿', label: 'Fibres', detail: 'Légumineuses, graines' },
    ],
    ingredients: ['Patate douce', 'Riz complet', 'Banane', 'Amande', 'Chocolat noir', 'Avoine', 'Lentilles', 'Graines de chia'],
  },
];

// ── Composants visuels ────────────────────────────────────────────────────────

function MoonGlyph({ phase, size = 18, color = 'currentColor', bg = 'rgba(0,0,0,0.08)' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" fill={bg} stroke={color} strokeWidth="1" strokeOpacity="0.4" />
      {phase === 1 && <path d="M12 2 a10 10 0 0 1 0 20 z" fill={color} />}
      {phase === 2 && <circle cx="12" cy="12" r="10" fill={color} />}
      {phase === 3 && <path d="M12 2 a10 10 0 0 0 0 20 z" fill={color} />}
    </svg>
  );
}

function MoonOrbit({ activeIndex, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      {[0, 1, 2, 3].map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            transition: 'transform .3s, filter .3s',
            transform: i === activeIndex ? 'scale(1.35)' : 'scale(0.8)',
            opacity: i === activeIndex ? 1 : 0.4,
            filter: i === activeIndex ? `drop-shadow(0 0 8px ${color})` : 'none',
          }}>
            <MoonGlyph phase={p} size={20} color={color} bg="transparent" />
          </div>
          {i < 3 && <span style={{ width: 20, height: 1, background: color, opacity: 0.2 }} />}
        </div>
      ))}
    </div>
  );
}

function HormoneCurve({ activePhaseId }) {
  const phaseRanges = { menstrual: [0, 5], follicular: [5, 14], ovulatory: [14, 17], luteal: [17, 28] };
  const range = phaseRanges[activePhaseId];
  const estrogen = (d) => {
    if (d < 5)  return 18 + d * 1.5;
    if (d < 13) return 25 + (d - 5) * 6;
    if (d < 15) return 73 + (d - 13) * 12;
    if (d < 17) return 97 - (d - 15) * 18;
    if (d < 22) return 61 + Math.sin((d - 17) * 0.6) * 10;
    return 60 - (d - 22) * 9;
  };
  const progest = (d) => {
    if (d < 14) return 10 + d * 0.4;
    if (d < 21) return 13 + (d - 14) * 11;
    return Math.max(8, 90 - (d - 21) * 11);
  };
  const W = 600, H = 130, pL = 38, pR = 10, pT = 14, pB = 22;
  const xs = d => pL + (d / 28) * (W - pL - pR);
  const ys = v => H - pB - (v / 100) * (H - pT - pB);
  const ep = Array.from({ length: 29 }, (_, d) => `${d === 0 ? 'M' : 'L'}${xs(d)},${ys(estrogen(d))}`).join(' ');
  const pp = Array.from({ length: 29 }, (_, d) => `${d === 0 ? 'M' : 'L'}${xs(d)},${ys(progest(d))}`).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block' }}>
      <rect x={xs(range[0])} y={pT} width={xs(range[1]) - xs(range[0])} height={H - pT - pB}
        fill="var(--grn)" opacity="0.12" rx="4" />
      {[0, 7, 14, 21, 28].map(d => (
        <g key={d}>
          <line x1={xs(d)} x2={xs(d)} y1={pT} y2={H - pB} stroke="var(--brd)" strokeWidth="1" strokeDasharray="2 3" />
          <text x={xs(d)} y={H - 5} textAnchor="middle" fontSize="9" fill="var(--mut)">J{d === 0 ? 1 : d}</text>
        </g>
      ))}
      <text x={pL - 6} y={ys(50)} textAnchor="end" fontSize="9" fill="var(--mut)">moy.</text>
      <text x={pL - 6} y={ys(95)} textAnchor="end" fontSize="9" fill="var(--mut)">pic</text>
      <path d={ep} fill="none" stroke="var(--grn)" strokeWidth="2" />
      <path d={pp} fill="none" stroke="var(--mut)" strokeWidth="2" strokeDasharray="4 3" />
      <g transform={`translate(${pL},${pT - 2})`}>
        <circle cx="4" cy="4" r="3" fill="var(--grn)" />
        <text x="12" y="7" fontSize="10" fill="var(--mut)">Œstrogènes</text>
        <circle cx="82" cy="4" r="3" fill="var(--mut)" />
        <text x="90" y="7" fontSize="10" fill="var(--mut)">Progestérone</text>
      </g>
    </svg>
  );
}

// ── Vue détail d'une phase ────────────────────────────────────────────────────
function CyclePhaseDetail({ phase, phaseIndex, onBack, cycleRecipes }) {
  const phaseRanges = { menstrual: [0, 5], follicular: [5, 14], ovulatory: [14, 17], luteal: [17, 28] };
  const [start, end] = phaseRanges[phase.id];
  const previewRecipes = cycleRecipes.slice(0, 3);

  return (
    <div>
      <button onClick={onBack} style={{
        background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px 0 16px',
        fontSize: 13, color: 'var(--mut)', display: 'inline-flex', alignItems: 'center', gap: 8,
        letterSpacing: '0.04em', textTransform: 'uppercase',
      }}>
        ← Retour aux phases
      </button>

      <div style={{ position: 'relative', overflow: 'hidden', paddingBottom: 28, marginBottom: 8 }}>
        <div style={{ position: 'absolute', right: 0, top: 0, opacity: 0.07, pointerEvents: 'none' }}>
          <MoonGlyph phase={phaseIndex} size={200} color="var(--grn)" bg="transparent" />
        </div>
        <div style={{ position: 'relative' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
            <MoonGlyph phase={phaseIndex} size={26} color="var(--grn)" bg="transparent" />
            <span style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--grn)' }}>
              {phase.moonName} · {phase.range} · ~{end - start} jours
            </span>
          </div>
          <h1 style={{ margin: 0, fontSize: 'clamp(32px,5vw,52px)', fontWeight: 500, letterSpacing: '-0.03em', lineHeight: 1 }}>
            Phase <em style={{ color: 'var(--grn)', fontStyle: 'italic' }}>{phase.label.toLowerCase()}</em>
          </h1>
          <div style={{ marginTop: 8, fontSize: 17, color: 'var(--txt2)', fontStyle: 'italic' }}>{phase.title}</div>
        </div>
      </div>

      <div className="frigo-panel" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
          <h3 className="frigo-panel-title" style={{ margin: 0 }}>Quand dans le cycle ?</h3>
          <span style={{ fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--mut)' }}>
            HORMONES SUR 28 JOURS
          </span>
        </div>
        <HormoneCurve activePhaseId={phase.id} />
        <p style={{ margin: '8px 0 0', fontSize: 12, color: 'var(--mut)', lineHeight: 1.5 }}>
          Bande surlignée = phase actuelle. Le cycle moyen est de 28 jours mais varie de 24 à 35 jours selon les personnes.
        </p>
      </div>

      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 12 }}>Ce qui se passe dans le corps</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 14 }}>
          {phase.longDesc.map((p, i) => (
            <div key={i} className="frigo-panel">
              <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--grn)', marginBottom: 8, textTransform: 'uppercase' }}>
                — {String(i + 1).padStart(2, '0')}
              </div>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.7, color: 'var(--txt2)' }}>{p}</p>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 12 }}>Symptômes fréquents</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 12 }}>
          {phase.symptoms.map((s, i) => (
            <div key={i} className="frigo-panel" style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
              <span style={{ fontSize: 26, flexShrink: 0 }}>{s.icon}</span>
              <div>
                <div style={{ fontWeight: 500, marginBottom: 4 }}>{s.label}</div>
                <div style={{ fontSize: 12, color: 'var(--txt2)', lineHeight: 1.5 }}>{s.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 12 }}>Côté assiette</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div className="frigo-panel" style={{
            background: 'color-mix(in srgb, #3a7d44 8%, var(--sur))',
            border: '1px solid color-mix(in srgb, #3a7d44 25%, transparent)',
          }}>
            <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#3a7d44', marginBottom: 10, textTransform: 'uppercase' }}>
              ✓ À PRIVILÉGIER
            </div>
            <ul style={{ margin: 0, padding: '0 0 0 18px', fontSize: 14, lineHeight: 1.9, color: 'var(--txt)' }}>
              {phase.favor.map(x => <li key={x}>{x}</li>)}
            </ul>
          </div>
          <div className="frigo-panel" style={{
            background: 'color-mix(in srgb, #c87a4a 8%, var(--sur))',
            border: '1px solid color-mix(in srgb, #c87a4a 25%, transparent)',
          }}>
            <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#c87a4a', marginBottom: 10, textTransform: 'uppercase' }}>
              ⚠ À MODÉRER
            </div>
            <ul style={{ margin: 0, padding: '0 0 0 18px', fontSize: 14, lineHeight: 1.9, color: 'var(--txt)' }}>
              {phase.avoid.map(x => <li key={x}>{x}</li>)}
            </ul>
          </div>
        </div>
      </div>

      <div className="frigo-panel" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 18 }}>
        <span style={{ fontSize: 38, flexShrink: 0 }}>🏃‍♀️</span>
        <div>
          <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 6 }}>
            ACTIVITÉ PHYSIQUE RECOMMANDÉE
          </div>
          <div style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--txt)' }}>{phase.activity}</div>
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 12 }}>Nutriments clés</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 12 }}>
          {phase.needs.map((n, i) => (
            <div key={i} className="frigo-panel">
              <span style={{ fontSize: 22 }}>{n.icon}</span>
              <div style={{ fontWeight: 500, marginTop: 8, marginBottom: 4 }}>{n.label}</div>
              <div style={{ fontSize: 12, color: 'var(--txt2)', lineHeight: 1.4 }}>{n.detail}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 12 }}>Ingrédients recommandés</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {phase.ingredients.map(ing => (
            <span key={ing} style={{
              padding: '7px 14px',
              background: 'var(--grn-dim)',
              color: 'var(--grn)',
              border: '1px solid color-mix(in srgb, var(--grn) 25%, transparent)',
              borderRadius: 999, fontSize: 13,
            }}>{ing}</span>
          ))}
        </div>
      </div>

      {previewRecipes.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 12 }}>Recettes adaptées · {phase.label}</h2>
          <div className="recipe-grid">
            {previewRecipes.map(recipe => (
              <RecipeCard key={recipe.id || recipe._id} recipe={recipe} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────
const SORT_OPTIONS = [
  { value: 'score',      label: 'Score NRF ↓',   icon: '◆' },
  { value: 'alpha',      label: 'A → Z',          icon: '🔤' },
  { value: 'time_asc',   label: 'Temps ↑',        icon: '⏱' },
  { value: 'iron',       label: 'Fer',             icon: '🩸' },
  { value: 'protein',    label: 'Protéines',       icon: '💪' },
  { value: 'fiber',      label: 'Fibres',          icon: '🌾' },
  { value: 'magnesium',  label: 'Magnésium',       icon: '🧲' },
  { value: 'vitamin_c',  label: 'Vit. C',          icon: '🍊' },
  { value: 'zinc',       label: 'Zinc',            icon: '⚡' },
];


function sortRecipes(list, sortKey, maxTime) {
  let filtered = [...list];
  if (maxTime) {
    const mt = parseInt(maxTime);
    filtered = filtered.filter(r => (r.timing?.total_min || r.total_time_min || 999) <= mt);
  }
  switch (sortKey) {
    case 'score':    filtered.sort((a, b) => computeAlimScore(b) - computeAlimScore(a)); break;
    case 'alpha':    filtered.sort((a, b) => (a.titles?.fr || '').localeCompare(b.titles?.fr || '')); break;
    case 'time_asc': filtered.sort((a, b) => (a.timing?.total_min || 999) - (b.timing?.total_min || 999)); break;
    case 'iron': case 'protein': case 'fiber': case 'magnesium':
    case 'vitamin_c': case 'zinc': case 'calcium': case 'potassium':
      filtered.sort((a, b) => (b._nutrition?.[sortKey]?.pct_ajr || 0) - (a._nutrition?.[sortKey]?.pct_ajr || 0));
      break;
    default: break;
  }
  return filtered;
}

export default function CyclePage() {
  const [view, setView] = useState('overview');
  const [phase, setPhase] = useState(() => {
    const saved = localStorage.getItem(CYCLE_KEY);
    return CYCLE_PHASES.some(p => p.id === saved) ? saved : 'menstrual';
  });
  const [cycleData, setCycleData]       = useState(null);
  const [loadingCycle, setLoadingCycle] = useState(false);
  const [errorCycle, setErrorCycle]     = useState(null);
  const [cycleRecipes, setCycleRecipes] = useState([]);
  const [loadingCycleRecipes, setLoadingCycleRecipes] = useState(false);
  const [cycleVisible, setCycleVisible] = useState(20);
  const [cycleSort,    setCycleSort]    = useState('score');
  const fs = useFilterState();

  // Persist phase selection
  useEffect(() => { localStorage.setItem(CYCLE_KEY, phase); }, [phase]);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoadingCycle(true); setErrorCycle(null);
      try {
        const res = await cycleApi.getIngredients(phase);
        if (!cancelled) setCycleData(res);
      } catch (err) {
        if (!cancelled) setErrorCycle(err.message);
      } finally {
        if (!cancelled) setLoadingCycle(false);
      }
      setLoadingCycleRecipes(true);
      try {
        const data = await recipesApi.list({ cycle_phase: phase, limit: 500 });
        if (!cancelled) { setCycleRecipes(data.results || []); setCycleVisible(20); }
      } catch { /* ignore */ } finally {
        if (!cancelled) setLoadingCycleRecipes(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [phase]);

  const activePhase = CYCLE_PHASES.find(p => p.id === phase);
  const phaseIndex  = CYCLE_PHASES.findIndex(p => p.id === phase);
  const filteredCycle = localFilterRecipes(cycleRecipes, fs.filterState);
  const sortedCycle   = sortRecipes(filteredCycle, cycleSort);

  if (view === 'detail') {
    return (
      <div className="page-home" style={{ padding: '0 24px', maxWidth: 1100, margin: '0 auto' }}>
        <CyclePhaseDetail
          phase={activePhase}
          phaseIndex={phaseIndex}
          onBack={() => setView('overview')}
          cycleRecipes={cycleRecipes}
        />
      </div>
    );
  }

  return (
    <div className="page-home" style={{ padding: '0 24px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="page-header" style={{ marginBottom: 24 }}>
        <h1 className="page-title"><span className="page-icon">🌑</span> Cycle Féminin</h1>
        <p className="page-sub">Adaptez votre alimentation aux variations hormonales pour un meilleur bien-être.</p>
      </div>

      {/* Phase tabs */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', position: 'relative', marginBottom: 20 }}>
        <div style={{ position: 'absolute', right: 0, top: '50%', transform: 'translateY(-50%)', opacity: 0.8 }}>
          <MoonOrbit activeIndex={phaseIndex} color="var(--grn)" />
        </div>
        {CYCLE_PHASES.map((p, i) => {
          const isActive = phase === p.id;
          return (
            <button key={p.id} onClick={() => { setPhase(p.id); setView('overview'); }}
              style={{
                padding: '10px 16px', borderRadius: 12, fontSize: 13,
                background: isActive ? 'var(--grn)' : 'transparent',
                color: isActive ? 'var(--bg)' : 'var(--txt2)',
                border: `1px solid ${isActive ? 'var(--grn)' : 'var(--brd)'}`,
                fontWeight: isActive ? 500 : 400, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 10, transition: 'all .15s',
              }}>
              <MoonGlyph phase={i} size={18} color={isActive ? 'var(--bg)' : 'var(--grn)'} bg="transparent" />
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 2 }}>
                <span>{p.label}</span>
                <span style={{ fontSize: 10, letterSpacing: '0.06em', textTransform: 'uppercase', opacity: 0.7 }}>{p.range}</span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Panneau phase */}
      <div className="frigo-panel" style={{ position: 'relative', overflow: 'hidden', marginBottom: 20 }}>
        <div style={{ position: 'absolute', right: -20, bottom: -20, opacity: 0.05, pointerEvents: 'none' }}>
          <MoonGlyph phase={phaseIndex} size={180} color="var(--grn)" bg="transparent" />
        </div>
        <div style={{ position: 'relative' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, marginBottom: 10, flexWrap: 'wrap' }}>
            <h3 className="frigo-panel-title" style={{ margin: 0 }}>{activePhase.title}</h3>
            <span style={{ fontSize: 11, letterSpacing: '0.08em', color: 'var(--grn)', display: 'inline-flex', alignItems: 'center', gap: 6, textTransform: 'uppercase' }}>
              {activePhase.moon} {activePhase.moonName}
            </span>
            <button onClick={() => setView('detail')} style={{
              marginLeft: 'auto', padding: '7px 14px', borderRadius: 999, fontSize: 13,
              background: 'var(--grn)', color: 'var(--bg)', border: 'none',
              cursor: 'pointer', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: 6,
            }}>
              En savoir plus →
            </button>
          </div>
          <p style={{ color: 'var(--txt2)', marginBottom: 20, lineHeight: 1.6 }}>{activePhase.desc}</p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 10, marginBottom: 20 }}>
            {activePhase.needs.map((n, i) => (
              <div key={i} style={{
                padding: '10px 14px', borderRadius: 10,
                background: 'var(--sur2)', border: '1px solid var(--brd)',
                display: 'flex', gap: 10, alignItems: 'flex-start',
              }}>
                <span style={{ fontSize: 20, flexShrink: 0 }}>{n.icon}</span>
                <div>
                  <strong style={{ fontSize: 13 }}>{n.label}</strong>
                  <p style={{ margin: '2px 0 0', fontSize: 11, color: 'var(--mut)', lineHeight: 1.4 }}>{n.detail}</p>
                </div>
              </div>
            ))}
          </div>

          {loadingCycle && <div className="skeleton skeleton-line" style={{ width: '100%', height: 60 }} />}
          {errorCycle   && <div className="state-msg state-msg--error">{errorCycle}</div>}
          {!loadingCycle && !errorCycle && cycleData?.ingredients?.length > 0 && (
            <div>
              <h4 style={{ marginBottom: 10, fontSize: 14, fontWeight: 500 }}>Ingrédients recommandés</h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
                {cycleData.ingredients.map((ing, idx) => (
                  <span key={idx} className="badge" style={{ background: 'var(--sur2)', color: 'var(--txt)', border: '1px solid var(--brd)' }}>
                    {(translations[ing] || ing).replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recettes */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 12 }}>Recettes · {activePhase.title}</h3>

        {/* Filtres identiques à la page d'accueil */}
        <FiltersBlock {...fs} onAnyChange={() => setCycleVisible(20)} />

        {/* Tri + temps */}
        <div className="sort-row" style={{ margin: '10px 0 14px' }}>
          {SORT_OPTIONS.map(o => (
            <button key={o.value}
              className={`pill pill--sm ${cycleSort === o.value ? 'pill--active' : ''}`}
              onClick={() => { setCycleSort(o.value); setCycleVisible(20); }}
              aria-pressed={cycleSort === o.value}
            >{o.icon} {o.label}</button>
          ))}
          <div className="time-filter">
            <span className="filter-label-inline">≤</span>
            <input type="number" placeholder="min" value={fs.maxTime}
              onChange={e => { fs.setMaxTime(e.target.value); setCycleVisible(20); }}
              className="time-input" min="5" max="300" step="5" />
          </div>
          {(cycleSort !== 'score' || fs.hasActiveFilters) && (
            <button className="filters-clear" onClick={() => {
              setCycleSort('score'); fs.clearAll(); setCycleVisible(20);
            }}>✕ Réinitialiser</button>
          )}
        </div>

        {loadingCycleRecipes ? (
          <div className="recipe-grid">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="skeleton-card">
                <div className="skeleton skeleton-img" />
              </div>
            ))}
          </div>
        ) : sortedCycle.length > 0 ? (
          <>
            <p style={{ fontSize: 12, color: 'var(--mut)', marginBottom: 12 }}>
              {sortedCycle.length} recette{sortedCycle.length > 1 ? 's' : ''} — {Math.min(cycleVisible, sortedCycle.length)} affichées
            </p>
            <div className="recipe-grid">
              {sortedCycle.slice(0, cycleVisible).map(recipe => (
                <RecipeCard key={recipe.id || recipe._id} recipe={recipe} />
              ))}
            </div>
            {cycleVisible < sortedCycle.length && (
              <button className="frigo-search-btn" onClick={() => setCycleVisible(v => v + 20)} style={{ marginTop: 16 }}>
                Voir plus ({sortedCycle.length - cycleVisible} restantes)
              </button>
            )}
          </>
        ) : (
          <p style={{ color: 'var(--mut)' }}>Aucune recette trouvée pour ces filtres.</p>
        )}
      </div>

      {/* Cartes phases */}
      <div>
        <h3 style={{ marginBottom: 14, fontSize: 18 }}>Explorer chaque phase en détail</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 }}>
          {CYCLE_PHASES.map((p, i) => {
            const isActive = p.id === phase;
            return (
              <button key={p.id} onClick={() => { setPhase(p.id); setView('detail'); }}
                style={{
                  background: 'var(--sur)', border: `1px solid ${isActive ? 'var(--grn)' : 'var(--brd)'}`,
                  borderRadius: 14, padding: 18, textAlign: 'left', cursor: 'pointer',
                  fontFamily: 'inherit', color: 'var(--txt)',
                  display: 'flex', flexDirection: 'column', gap: 10, transition: 'all .15s',
                }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <MoonGlyph phase={i} size={26} color="var(--grn)" bg="transparent" />
                  <span style={{ fontSize: 10, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--mut)' }}>{p.range}</span>
                </div>
                <div style={{ fontWeight: 500, fontSize: 16 }}>{p.label}</div>
                <div style={{ fontSize: 12, color: 'var(--txt2)', lineHeight: 1.5, minHeight: 40 }}>{p.title}</div>
                <div style={{
                  marginTop: 'auto', paddingTop: 8, borderTop: '1px solid var(--brd)',
                  fontSize: 10, letterSpacing: '0.06em', textTransform: 'uppercase',
                  color: 'var(--grn)', display: 'flex', justifyContent: 'space-between',
                }}>
                  <span>{p.symptoms.length} SYMPTÔMES</span>
                  <span>→</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
