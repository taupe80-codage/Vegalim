import { useState, useEffect, useMemo } from 'react';
import { cycle as cycleApi, recipes as recipesApi } from '../api';
import RecipeCard, { computeAlimScore } from '../components/RecipeCard';
import { useFilterState, FiltersBlock, localFilterRecipes } from '../components/RecipeFiltersShared';
import translations from '../translations.json';

const CYCLE_KEY      = 'alim_cycle_phase';
const MENOPAUSE_KEY  = 'alim_menopause';

// ── Données ménopause ─────────────────────────────────────────────────────────
const MENO_COLOR     = '#c97eb8';
const MENO_COLOR_DIM = 'rgba(201,126,184,0.12)';

const MENO_NEEDS = [
  { icon: '🦴', label: 'Calcium',          detail: '1 200 mg/j — fromages affinés, yaourt, tofu enrichi, boissons végétales enrichies, amandes, brocoli', priority: true },
  { icon: '☀️', label: 'Vitamine D',        detail: '800–1 000 UI/j — exposition solaire (source principale), œuf, supplémentation D3 si besoin', priority: true },
  { icon: '💪', label: 'Protéines',         detail: '1,1–1,3 g/kg/j — légumineuses, tofu, tempeh, œufs, fromage blanc, graines de chanvre (sarcopénie)', priority: true },
  { icon: '🫐', label: 'Phyto-œstrogènes', detail: 'Soja, lin, légumineuses — modulent les récepteurs œstrogéniques', priority: true },
  { icon: '🌱', label: 'Oméga-3',          detail: 'Lin, chia, chanvre, noix, algues (DHA vegan) — cardioprotecteur & anti-inflammatoire', priority: true },
  { icon: '🧲', label: 'Magnésium',        detail: '350 mg/j — sommeil, humeur, santé osseuse — noix, graines, chocolat', priority: false },
  { icon: '🥬', label: 'Vitamine K2',      detail: 'Fixation du calcium sur les os — kale, fermentés (natto)', priority: false },
  { icon: '🧬', label: 'Vitamines B',      detail: 'B6 (humeur), B12 (énergie, risque carence post-50 ans), folates', priority: false },
  { icon: '🌿', label: 'Fibres',           detail: '25–30 g/j — microbiote, poids, cardiovasculaire — légumineuses, graines', priority: false },
  { icon: '🍊', label: 'Vitamine C & E',   detail: 'Antioxydants — peau, immunité, protection cardiovasculaire', priority: false },
];

const MENO_SYMPTOMS = [
  {
    icon: '🌡️', label: 'Bouffées de chaleur',
    foods: ['Phyto-œstrogènes (soja, lin)', 'Sauge officinale (tisane)', 'Aliments frais & crus'],
    avoid: ['Alcool', 'Café en excès', 'Épices fortes', 'Sucres rapides'],
  },
  {
    icon: '💤', label: 'Troubles du sommeil',
    foods: ['Magnésium (amandes, graines de courge)', 'Tryptophane (banane, noix, graines de courge)', 'Mélatonine naturelle (cerise, kiwi)'],
    avoid: ['Caféine après 14h', 'Alcool le soir', 'Repas lourds tardifs'],
  },
  {
    icon: '😔', label: 'Humeur & anxiété',
    foods: ['Oméga-3 (noix, lin, chia, algues)', 'Vitamine B6 (banane, pois chiches)', 'Magnésium', 'Fermentés (axe intestin-cerveau)'],
    avoid: ['Sucres raffinés (pic puis chute)', 'Alcool (dépresseur)', 'Ultra-transformés'],
  },
  {
    icon: '🦴', label: 'Densité osseuse',
    foods: ['Calcium (fromages affinés, tofu, amandes, brocoli)', 'Vitamine D3 (soleil, œuf)', 'Vitamine K2 (natto, kale)', 'Protéines (légumineuses, œufs, fromage blanc)'],
    avoid: ['Sel en excès (fuites calciques)', 'Alcool', 'Caféine excessive'],
  },
  {
    icon: '❤️', label: 'Santé cardiovasculaire',
    foods: ['Oméga-3', 'Fibres (avoine, légumineuses)', 'Polyphénols (baies, thé vert)', 'Huile d\'olive'],
    avoid: ['Graisses saturées', 'Sel', 'Sucres ajoutés', 'Charcuteries'],
  },
  {
    icon: '⚖️', label: 'Poids & métabolisme',
    foods: ['Protéines à chaque repas (satiété)', 'Fibres (légumineuses, légumes)', 'Glucides complexes', 'Index glycémique bas'],
    avoid: ['Sucres rapides', 'Alcool (calories vides)', 'Ultra-transformés', 'Grignotages'],
  },
  {
    icon: '🧠', label: 'Mémoire & concentration',
    foods: ['Oméga-3 DHA (algues, chia, lin, noix)', 'Vitamine B12 (levure nutritionnelle, œuf)', 'Antioxydants (baies, cacao)', 'Curcuma + poivre noir'],
    avoid: ['Alcool (neurotoxique)', 'Manque d\'hydratation', 'Sucres rapides'],
  },
  {
    icon: '🌸', label: 'Peau & muqueuses',
    foods: ['Oméga-3 & 6 (huile de lin, chanvre)', 'Vitamine E (noix, huile d\'olive)', 'Vitamine C (agrumes, poivron)', 'Hydratation (1,5–2L/j)'],
    avoid: ['Alcool (déshydratant)', 'Sel en excès', 'Tabac'],
  },
];

const MENO_FAVOR = [
  'Soja & edamame (phyto-œstrogènes)',
  'Graines de lin moulues (lignanes)',
  'Algues & spiruline (minéraux, DHA, chlorophylle)',
  'Tofu & tempeh (calcium, protéines)',
  'Légumineuses quotidiennes',
  'Légumes crucifères (brocoli, kale)',
  'Baies & fruits rouges (antioxydants)',
  'Avoine & céréales complètes',
  'Noix, amandes, graines de courge',
  'Huile d\'olive & avocat',
  'Thé vert & tisanes de sauge',
  'Kéfir végétal & kombucha (microbiote)',
];

const MENO_AVOID = [
  'Alcool — bouffées de chaleur, os, foie',
  'Sel excessif — rétention, hypertension, calcium',
  'Sucres raffinés — poids, glycémie, humeur',
  'Graisses saturées — cardiovasculaire',
  'Caféine excessive — sommeil, anxiété, calcium',
  'Ultra-transformés — inflammation, poids',
  'Épices fortes le soir — bouffées de chaleur',
];

const MENO_ACTIVITY = 'Marche rapide & cardio modéré (30 min/j) pour la santé cardio-vasculaire. Musculation 2×/semaine indispensable contre la sarcopénie et pour préserver la densité osseuse. Yoga & cohérence cardiaque pour les bouffées de chaleur et l\'anxiété. Natation si douleurs articulaires.';

const MENO_INGREDIENTS = [
  'Graines de lin', 'Edamame', 'Tofu soyeux', 'Sardines', 'Saumon',
  'Amandes', 'Graines de courge', 'Kale', 'Brocoli', 'Avoine',
  'Myrtilles', 'Grenade', 'Avoccat', 'Noix', 'Tempeh',
];

const MENO_TIPS = [
  {
    icon: '🌿', title: 'Phytothérapie',
    content: 'La sauge officinale (tisane 2×/j) réduit les bouffées de chaleur chez 60% des femmes. Le trèfle rouge (isoflavones) est une alternative aux phyto-œstrogènes alimentaires. La valériane aide au sommeil. Consultez votre médecin avant toute supplémentation.',
  },
  {
    icon: '🧘', title: 'Gestion du stress',
    content: 'La cohérence cardiaque (5 min, 3×/j) réduit le cortisol chronique qui aggrave les symptômes. Le yoga de la ménopause améliore le sommeil et réduit les bouffées de chaleur. Le stress augmente la perméabilité intestinale — favorisez les fermentés.',
  },
  {
    icon: '💧', title: 'Hydratation',
    content: 'Les œstrogènes aidaient à retenir l\'eau dans les tissus. Sans eux, les besoins augmentent : 1,8–2L/j minimum. Les tisanes (sauge, mélisse, aubépine) hydratent et ont des effets ciblés. Évitez l\'alcool et le café à jeun.',
  },
  {
    icon: '🕐', title: 'Chrono-nutrition',
    content: 'Le métabolisme ralentit (~200 kcal/j de moins à 50 ans vs 30 ans). Concentrez les glucides complexes le matin et à midi, privilégiez protéines + légumes le soir. Le jeûne intermittent doux (12-14h) peut aider à la gestion du poids sans stress métabolique.',
  },
  {
    icon: '🔬', title: 'Suppléments utiles',
    content: 'Vitamine D3 (1 000–2 000 UI/j) : quasi-universellement déficitaire. Calcium si apports insuffisants (<900 mg/j). Magnésium bisglycinate (300 mg soir) pour le sommeil. Oméga-3 EPA/DHA (huile d\'algues ou poissons gras). Bilan sanguin annuel recommandé (B12, D, fer).',
  },
  {
    icon: '🫀', title: 'Suivi médical',
    content: 'La ménopause augmente le risque cardiovasculaire (cholestérol LDL monte quand les œstrogènes baissent). Bilan lipidique annuel. Contrôle de la tension. Mammographie + os (ostéodensitométrie) tous les 2 ans. Discutez du traitement hormonal (THM) avec votre gynécologue.',
  },
];

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
    favor: ['Fermentés (kombucha, miso, kimchi, tempeh)', 'Crudités, salades fraîches', 'Smoothies verts', 'Graines germées'],
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

// ── Cycle Beads ───────────────────────────────────────────────────────────────

const BEAD_COLORS = {
  menstrual:  '#f47373',
  follicular: '#4cba8a',
  ovulatory:  '#f5c542',
  luteal:     '#9b6fd4',
};

const PHASE_DAY_RANGES = [
  { id: 'menstrual',  from: 1,  to: 5  },
  { id: 'follicular', from: 6,  to: 14 },
  { id: 'ovulatory',  from: 15, to: 17 },
  { id: 'luteal',     from: 18, to: 28 },
];

const CYCLE_START_KEY = 'alim_cycle_start';

function dayToPhase(day) {
  return PHASE_DAY_RANGES.find(p => day >= p.from && day <= p.to) || null;
}

function CycleBeads({ activePhase, onPhaseSelect }) {
  const [startDate, setStartDate] = useState(() => localStorage.getItem(CYCLE_START_KEY) || null);
  const [hoveredDay, setHoveredDay] = useState(null);
  const [editDay, setEditDay]       = useState('');

  const currentDay = useMemo(() => {
    if (!startDate) return null;
    const start = new Date(startDate + 'T00:00:00');
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const diff  = Math.round((today - start) / 86400000);
    if (diff < 0 || diff > 365) return null;
    return (diff % 28) + 1;
  }, [startDate]);

  const applyDay = (day) => {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const start = new Date(today);
    start.setDate(today.getDate() - (day - 1));
    const ds = start.toISOString().split('T')[0];
    localStorage.setItem(CYCLE_START_KEY, ds);
    setStartDate(ds);
    const p = dayToPhase(day);
    if (p) onPhaseSelect(p.id);
  };

  const N = 28, CX = 190, CY = 120, RX = 162, RY = 86;

  const beads = Array.from({ length: N }, (_, i) => {
    const day   = i + 1;
    const angle = (i / N) * 2 * Math.PI - Math.PI / 2;
    const ph    = dayToPhase(day);
    return { day, angle, x: CX + RX * Math.cos(angle), y: CY + RY * Math.sin(angle), phaseId: ph?.id };
  });

  const displayDay   = hoveredDay || currentDay;
  const displayPhase = displayDay ? dayToPhase(displayDay) : null;
  const displayMeta  = displayPhase ? CYCLE_PHASES.find(p => p.id === displayPhase.id) : null;
  const KEY_DAYS     = new Set([1, 6, 14, 15, 17, 18, 28]);

  return (
    <div className="frigo-panel" style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 16 }}>
        🫧 Collier du cycle
      </div>

      <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'flex-start' }}>

        {/* ── Anneau SVG ── */}
        <svg width={CX * 2} height={CY * 2 + 20} viewBox={`0 0 ${CX * 2} ${CY * 2 + 20}`}
          style={{ flex: '0 0 auto', maxWidth: '100%', display: 'block', overflow: 'visible' }}>

          {/* Fil du collier */}
          <ellipse cx={CX} cy={CY} rx={RX} ry={RY}
            fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1.5" strokeDasharray="3 2" />

          {beads.map(({ day, angle, x, y, phaseId }) => {
            const color    = BEAD_COLORS[phaseId] || '#555';
            const isCurrent = day === currentDay;
            const isHover   = day === hoveredDay;
            const isPhase   = phaseId === activePhase;
            const r         = isCurrent ? 11 : isHover ? 9.5 : 7;
            const opacity   = (isCurrent || isHover || isPhase) ? 1 : 0.35;
            const lx        = CX + (RX + 22) * Math.cos(angle);
            const ly        = CY + (RY + 22) * Math.sin(angle) + 3.5;

            return (
              <g key={day} style={{ cursor: 'pointer' }}
                onClick={() => applyDay(day)}
                onMouseEnter={() => setHoveredDay(day)}
                onMouseLeave={() => setHoveredDay(null)}>

                {/* Halo pour le jour courant */}
                {isCurrent && <circle cx={x} cy={y} r={19} fill={color} opacity="0.18" />}

                {/* Grain */}
                <circle cx={x} cy={y} r={r} fill={color} opacity={opacity}
                  stroke={isCurrent ? 'rgba(255,255,255,0.9)' : 'none'} strokeWidth="2" />

                {/* Pastille blanche J1 */}
                {day === 1 && (
                  <circle cx={x} cy={y} r={3.5} fill="rgba(255,255,255,0.9)"
                    style={{ pointerEvents: 'none' }} />
                )}

                {/* Étiquettes jours clés */}
                {KEY_DAYS.has(day) && (
                  <text x={lx} y={ly} textAnchor="middle" fontSize="8.5" fill="var(--mut)"
                    style={{ pointerEvents: 'none', userSelect: 'none' }}>
                    J{day}
                  </text>
                )}
              </g>
            );
          })}

          {/* ── Centre : jour + phase ── */}
          <text x={CX} y={CY - 18} textAnchor="middle"
            fill={displayPhase ? BEAD_COLORS[displayPhase.id] : 'var(--txt)'}
            style={{ fontSize: 32, fontWeight: 700, fontFamily: 'Outfit, sans-serif' }}>
            {displayDay ? `J${displayDay}` : '—'}
          </text>
          <text x={CX} y={CY + 7} textAnchor="middle" fontSize="12.5"
            fill={displayPhase ? BEAD_COLORS[displayPhase.id] : 'var(--mut)'}>
            {displayMeta?.label || (currentDay ? '' : 'cliquez un grain')}
          </text>
          {displayDay && (
            <text x={CX} y={CY + 24} textAnchor="middle" fontSize="10" fill="var(--mut)">
              {displayDay === currentDay
                ? (28 - currentDay > 0 ? `encore ${28 - currentDay} j.` : 'dernier jour')
                : displayMeta?.range || ''}
            </text>
          )}
        </svg>

        {/* ── Légende + contrôles ── */}
        <div style={{ flex: 1, minWidth: 190 }}>

          {/* Légende phases */}
          <div style={{ marginBottom: 16 }}>
            {PHASE_DAY_RANGES.map(p => {
              const meta     = CYCLE_PHASES.find(cp => cp.id === p.id);
              const isActive = p.id === activePhase;
              return (
                <div key={p.id} onClick={() => onPhaseSelect(p.id)}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px',
                    borderRadius: 8, marginBottom: 4, cursor: 'pointer',
                    background: isActive ? `${BEAD_COLORS[p.id]}15` : 'transparent',
                    border: `1px solid ${isActive ? BEAD_COLORS[p.id] + '50' : 'transparent'}`,
                    transition: 'all .12s' }}>
                  <span style={{ width: 10, height: 10, borderRadius: '50%', flexShrink: 0,
                    background: BEAD_COLORS[p.id],
                    boxShadow: isActive ? `0 0 8px ${BEAD_COLORS[p.id]}` : 'none' }} />
                  <span style={{ fontSize: 13, fontWeight: isActive ? 500 : 400 }}>{meta?.label}</span>
                  <span style={{ fontSize: 11, color: 'var(--mut)', marginLeft: 'auto' }}>J{p.from}–{p.to}</span>
                </div>
              );
            })}
          </div>

          {/* Contrôles */}
          <div style={{ borderTop: '1px solid var(--brd)', paddingTop: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--mut)', marginBottom: 10, lineHeight: 1.6 }}>
              {startDate
                ? `Début : ${new Date(startDate + 'T12:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })}`
                : 'Indiquez votre position dans le cycle'}
            </div>

            <button onClick={() => applyDay(1)}
              style={{ width: '100%', padding: '9px 14px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                background: 'var(--grn)', color: 'var(--bg)', border: 'none', cursor: 'pointer',
                marginBottom: 10 }}>
              📍 Aujourd'hui = J1 (1er jour des règles)
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--mut)', whiteSpace: 'nowrap' }}>Je suis au jour :</span>
              <input type="number" min={1} max={28} placeholder="n°"
                value={editDay}
                onChange={e => setEditDay(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    const d = parseInt(editDay, 10);
                    if (d >= 1 && d <= 28) { applyDay(d); setEditDay(''); }
                  }
                }}
                onBlur={() => {
                  const d = parseInt(editDay, 10);
                  if (d >= 1 && d <= 28) applyDay(d);
                  setEditDay('');
                }}
                style={{ width: 54, padding: '6px 8px', background: 'var(--sur2)',
                  border: '1px solid var(--brd)', borderRadius: 6, color: 'var(--txt)',
                  fontSize: 14, fontFamily: 'inherit', textAlign: 'center' }}
              />
              <span style={{ fontSize: 12, color: 'var(--mut)' }}>/ 28</span>
            </div>
          </div>

          {/* Tip phase active */}
          {displayMeta && (
            <div style={{ marginTop: 16, padding: '10px 12px', borderRadius: 8,
              background: `${BEAD_COLORS[displayPhase.id]}10`,
              border: `1px solid ${BEAD_COLORS[displayPhase.id]}30`, fontSize: 12, lineHeight: 1.6,
              color: 'var(--txt2)' }}>
              <strong style={{ color: BEAD_COLORS[displayPhase.id] }}>{displayMeta.title}</strong>
              <br />
              {displayMeta.needs.map(n => n.icon + ' ' + n.label).join(' · ')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

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

// ── Vue Ménopause ─────────────────────────────────────────────────────────────
function MenopauseView() {
  const [tab, setTab] = useState('nutrition');
  const [recipes, setRecipes] = useState([]);
  const [loadingRecipes, setLoadingRecipes] = useState(false);
  const [visible, setVisible] = useState(20);

  useEffect(() => {
    let cancelled = false;
    setLoadingRecipes(true);
    recipesApi.list({ tags: 'calcium,omega3,phytoestrogens,protein', limit: 500 })
      .catch(() => recipesApi.list({ limit: 200 }))
      .then(data => { if (!cancelled) setRecipes(data.results || []); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingRecipes(false); });
    return () => { cancelled = true; };
  }, []);

  const TAB_STYLE = (active) => ({
    padding: '10px 22px', borderRadius: 10, fontSize: 14, fontWeight: active ? 600 : 400,
    background: active ? MENO_COLOR : 'transparent',
    color: active ? '#fff' : 'var(--txt2)',
    border: `1px solid ${active ? MENO_COLOR : 'var(--brd)'}`,
    cursor: 'pointer', fontFamily: 'inherit', transition: 'all .15s',
  });

  return (
    <div>
      {/* En-tête */}
      <div style={{ position: 'relative', overflow: 'hidden', paddingBottom: 28, marginBottom: 24 }}>
        <div style={{ position: 'absolute', right: -10, top: -10, fontSize: 180, opacity: 0.05, pointerEvents: 'none', lineHeight: 1 }}>
          ♀
        </div>
        <div style={{ position: 'relative' }}>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: MENO_COLOR, marginBottom: 10 }}>
            ♀ Mode ménopause activé
          </div>
          <h1 style={{ margin: '0 0 8px', fontSize: 'clamp(28px,5vw,48px)', fontWeight: 500, letterSpacing: '-0.03em', lineHeight: 1 }}>
            Alimentation &{' '}
            <em style={{ color: MENO_COLOR, fontStyle: 'italic' }}>ménopause</em>
          </h1>
          <p style={{ margin: 0, fontSize: 16, color: 'var(--txt2)', maxWidth: 620, lineHeight: 1.6 }}>
            La ménopause n'est pas une maladie — c'est une transition hormonale qui redéfinit vos besoins nutritionnels. Une alimentation adaptée réduit significativement les symptômes et protège votre santé à long terme.
          </p>
        </div>
      </div>

      {/* Onglets */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 28 }}>
        <button style={TAB_STYLE(tab === 'nutrition')} onClick={() => setTab('nutrition')}>
          🥗 Nutrition
        </button>
        <button style={TAB_STYLE(tab === 'conseils')} onClick={() => setTab('conseils')}>
          💡 Conseils & bien-être
        </button>
      </div>

      {/* ── Onglet Nutrition ── */}
      {tab === 'nutrition' && (
        <div>
          {/* Priorités clés */}
          <div style={{ marginBottom: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 6 }}>Priorités nutritionnelles</h2>
            <p style={{ fontSize: 13, color: 'var(--mut)', marginBottom: 16 }}>
              Les 5 premiers sont incontournables — les autres viennent en complément.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 12 }}>
              {MENO_NEEDS.map((n, i) => (
                <div key={i} className="frigo-panel" style={{
                  border: `1px solid ${n.priority ? MENO_COLOR + '50' : 'var(--brd)'}`,
                  background: n.priority ? MENO_COLOR_DIM : 'var(--sur)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <span style={{ fontSize: 24, flexShrink: 0 }}>{n.icon}</span>
                    <strong style={{ fontSize: 14, color: n.priority ? MENO_COLOR : 'var(--txt)' }}>{n.label}</strong>
                    {n.priority && (
                      <span style={{ marginLeft: 'auto', fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
                        textTransform: 'uppercase', color: MENO_COLOR, background: MENO_COLOR + '20',
                        border: `1px solid ${MENO_COLOR}40`, borderRadius: 4, padding: '2px 6px' }}>
                        Essentiel
                      </span>
                    )}
                  </div>
                  <p style={{ margin: 0, fontSize: 12, color: 'var(--txt2)', lineHeight: 1.5 }}>{n.detail}</p>
                </div>
              ))}
            </div>
          </div>

          {/* À privilégier / À modérer */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 28 }}>
            <div className="frigo-panel" style={{
              background: 'color-mix(in srgb, #3a7d44 8%, var(--sur))',
              border: '1px solid color-mix(in srgb, #3a7d44 25%, transparent)',
            }}>
              <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#3a7d44', marginBottom: 10, textTransform: 'uppercase' }}>
                ✓ À privilégier
              </div>
              <ul style={{ margin: 0, padding: '0 0 0 18px', fontSize: 13, lineHeight: 2, color: 'var(--txt)' }}>
                {MENO_FAVOR.map(x => <li key={x}>{x}</li>)}
              </ul>
            </div>
            <div className="frigo-panel" style={{
              background: 'color-mix(in srgb, #c87a4a 8%, var(--sur))',
              border: '1px solid color-mix(in srgb, #c87a4a 25%, transparent)',
            }}>
              <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#c87a4a', marginBottom: 10, textTransform: 'uppercase' }}>
                ⚠ À modérer
              </div>
              <ul style={{ margin: 0, padding: '0 0 0 18px', fontSize: 13, lineHeight: 2, color: 'var(--txt)' }}>
                {MENO_AVOID.map(x => <li key={x}>{x}</li>)}
              </ul>
            </div>
          </div>

          {/* Activité physique */}
          <div className="frigo-panel" style={{ marginBottom: 28, display: 'flex', alignItems: 'flex-start', gap: 18 }}>
            <span style={{ fontSize: 36, flexShrink: 0 }}>🏋️‍♀️</span>
            <div>
              <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 6 }}>
                ACTIVITÉ PHYSIQUE — ESSENTIELLE POST-MÉNOPAUSE
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--txt)' }}>{MENO_ACTIVITY}</div>
            </div>
          </div>

          {/* Ingrédients recommandés */}
          <div style={{ marginBottom: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 12 }}>Ingrédients à intégrer</h2>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {MENO_INGREDIENTS.map(ing => (
                <span key={ing} style={{
                  padding: '7px 14px', borderRadius: 999, fontSize: 13,
                  background: MENO_COLOR_DIM, color: MENO_COLOR,
                  border: `1px solid ${MENO_COLOR}35`,
                }}>{ing}</span>
              ))}
            </div>
          </div>

          {/* Recettes */}
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 6 }}>Recettes adaptées</h2>
            <p style={{ fontSize: 13, color: 'var(--mut)', marginBottom: 14 }}>
              Riches en calcium, oméga-3, protéines et phyto-œstrogènes.
            </p>
            {loadingRecipes ? (
              <div className="recipe-grid">
                {[1,2,3,4,5,6].map(i => (
                  <div key={i} className="skeleton-card"><div className="skeleton skeleton-img" /></div>
                ))}
              </div>
            ) : recipes.length > 0 ? (
              <>
                <div className="recipe-grid">
                  {recipes.slice(0, visible).map(r => (
                    <RecipeCard key={r.id || r._id} recipe={r} />
                  ))}
                </div>
                {visible < recipes.length && (
                  <button className="frigo-search-btn" onClick={() => setVisible(v => v + 20)} style={{ marginTop: 16 }}>
                    Voir plus ({recipes.length - visible} restantes)
                  </button>
                )}
              </>
            ) : (
              <p style={{ color: 'var(--mut)' }}>Aucune recette trouvée.</p>
            )}
          </div>
        </div>
      )}

      {/* ── Onglet Conseils ── */}
      {tab === 'conseils' && (
        <div>
          {/* Symptômes & solutions nutritionnelles */}
          <div style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 6 }}>Symptômes & réponses nutritionnelles</h2>
            <p style={{ fontSize: 13, color: 'var(--mut)', marginBottom: 16 }}>
              Chaque symptôme a des leviers alimentaires spécifiques — agissez sur les causes, pas juste les effets.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 14 }}>
              {MENO_SYMPTOMS.map((s, i) => (
                <div key={i} className="frigo-panel">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                    <span style={{ fontSize: 26 }}>{s.icon}</span>
                    <strong style={{ fontSize: 15, color: MENO_COLOR }}>{s.label}</strong>
                  </div>
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#3a7d44', marginBottom: 6 }}>
                      ✓ Aliments bénéfiques
                    </div>
                    <ul style={{ margin: 0, padding: '0 0 0 16px', fontSize: 12, lineHeight: 1.8, color: 'var(--txt)' }}>
                      {s.foods.map(f => <li key={f}>{f}</li>)}
                    </ul>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#c87a4a', marginBottom: 6 }}>
                      ⚠ À éviter
                    </div>
                    <ul style={{ margin: 0, padding: '0 0 0 16px', fontSize: 12, lineHeight: 1.8, color: 'var(--txt2)' }}>
                      {s.avoid.map(a => <li key={a}>{a}</li>)}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Conseils pratiques */}
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 16 }}>Conseils pratiques</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 14 }}>
              {MENO_TIPS.map((t, i) => (
                <div key={i} className="frigo-panel">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                    <span style={{ fontSize: 24 }}>{t.icon}</span>
                    <strong style={{ fontSize: 14, color: MENO_COLOR }}>{t.title}</strong>
                  </div>
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--txt2)', lineHeight: 1.7 }}>{t.content}</p>
                </div>
              ))}
            </div>
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

const GENDER_KEY      = 'alim_gender';
const COOK_FOR_HER_KEY = 'alim_cook_for_her';

function CookForHerLanding({ onActivate }) {
  return (
    <div style={{ padding: '0 24px', maxWidth: 700, margin: '0 auto' }}>
      {/* En-tête */}
      <div style={{ textAlign: 'center', padding: '48px 0 36px' }}>
        <div style={{ fontSize: 64, marginBottom: 20, lineHeight: 1 }}>🍳</div>
        <h1 style={{ margin: '0 0 14px', fontSize: 'clamp(26px,5vw,40px)', fontWeight: 500, letterSpacing: '-0.02em', lineHeight: 1.15 }}>
          Et si vous cuisiniez{' '}
          <em style={{ color: MENO_COLOR, fontStyle: 'italic' }}>pour elle ?</em>
        </h1>
        <p style={{ margin: '0 auto', fontSize: 16, color: 'var(--txt2)', maxWidth: 500, lineHeight: 1.7 }}>
          Le corps féminin a des besoins nutritionnels qui varient tout au long du mois. Comprendre ces cycles, c'est cuisiner avec plus d'attention — et parfois, ça change tout.
        </p>
      </div>

      {/* 4 raisons visuelles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 14, marginBottom: 36 }}>
        {[
          { icon: '🩸', title: 'Phase menstruelle', desc: 'Elle a besoin de fer, de chaleur, de douceur. Un bouillon de lentilles peut faire plus qu\'un médicament.' },
          { icon: '⚡', title: 'Phase folliculaire', desc: 'Énergie au top — c\'est le moment des repas légers, croquants, colorés. Elle sera au maximum.' },
          { icon: '🌕', title: 'Phase ovulatoire', desc: 'Pic hormonal. Les crucifères et les antioxydants l\'aident à métaboliser les œstrogènes.' },
          { icon: '🍫', title: 'Phase lutéale', desc: 'Les envies de sucre sont hormonales. Le magnésium et les glucides complexes calment vraiment le SPM.' },
        ].map((card, i) => (
          <div key={i} className="frigo-panel" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 10 }}>{card.icon}</div>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8, color: MENO_COLOR }}>{card.title}</div>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--txt2)', lineHeight: 1.6 }}>{card.desc}</p>
          </div>
        ))}
      </div>

      {/* Citation */}
      <div className="frigo-panel" style={{
        textAlign: 'center', marginBottom: 36,
        background: 'linear-gradient(135deg, rgba(201,126,184,0.08), rgba(88,166,255,0.04))',
        border: `1px solid ${MENO_COLOR}30`,
      }}>
        <p style={{ margin: 0, fontSize: 15, fontStyle: 'italic', color: 'var(--txt2)', lineHeight: 1.8 }}>
          "Cuisiner pour quelqu'un en comprenant son corps,<br />c'est une forme d'intelligence — et de soin."
        </p>
      </div>

      {/* CTA */}
      <div style={{ textAlign: 'center', paddingBottom: 48 }}>
        <button onClick={onActivate} style={{
          padding: '16px 40px', borderRadius: 999, fontSize: 16, fontWeight: 600,
          background: `linear-gradient(135deg, ${MENO_COLOR}, #a855a8)`,
          color: '#fff', border: 'none', cursor: 'pointer',
          boxShadow: `0 6px 24px ${MENO_COLOR}50`, fontFamily: 'inherit',
          transition: 'transform .15s, box-shadow .15s',
        }}>
          Accéder au guide du cycle féminin →
        </button>
        <p style={{ marginTop: 12, fontSize: 12, color: 'var(--mut)' }}>
          Vous pouvez désactiver cet accès à tout moment dans Mon profil.
        </p>
      </div>
    </div>
  );
}

export default function CyclePage() {
  const gender         = localStorage.getItem(GENDER_KEY) || '';
  const [isMenopause] = useState(() => localStorage.getItem(MENOPAUSE_KEY) === 'true');
  const [cookForHer, setCookForHer] = useState(
    () => localStorage.getItem(COOK_FOR_HER_KEY) === 'true'
  );

  const activateCookForHer = () => {
    localStorage.setItem(COOK_FOR_HER_KEY, 'true');
    setCookForHer(true);
  };
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

  // Profil masculin sans activation "cuisine pour elle" → landing
  if (gender === 'male' && !cookForHer) {
    return (
      <div className="page-home">
        <CookForHerLanding onActivate={activateCookForHer} />
      </div>
    );
  }

  if (isMenopause) {
    return (
      <div className="page-home" style={{ padding: '0 24px', maxWidth: 1100, margin: '0 auto' }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
            <h1 className="page-title" style={{ margin: 0 }}>
              <span className="page-icon" style={{ color: MENO_COLOR }}>♀</span> Cycle Féminin
            </h1>
            <span style={{ fontSize: 12, color: 'var(--mut)', padding: '5px 12px', borderRadius: 8,
              background: MENO_COLOR_DIM, border: `1px solid ${MENO_COLOR}35` }}>
              Mode ménopause · Modifiable dans Mon profil
            </span>
          </div>
        </div>
        <MenopauseView />
      </div>
    );
  }

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

      {/* En-tête */}
      <div className="page-header" style={{ marginBottom: 20 }}>
        <h1 className="page-title"><span className="page-icon">🌑</span> Cycle Féminin</h1>
        <p className="page-sub">Adaptez votre alimentation aux variations hormonales — phase par phase.</p>
        {gender === 'male' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10,
            padding: '8px 14px', borderRadius: 10, background: `${MENO_COLOR}10`,
            border: `1px solid ${MENO_COLOR}30`, width: 'fit-content' }}>
            <span style={{ fontSize: 16 }}>🍳</span>
            <span style={{ fontSize: 13, color: 'var(--txt2)' }}>Mode "cuisiner pour elle" activé</span>
            <button onClick={() => { localStorage.setItem(COOK_FOR_HER_KEY, 'false'); setCookForHer(false); }}
              style={{ marginLeft: 8, fontSize: 11, color: 'var(--mut)', background: 'transparent',
                border: '1px solid var(--brd)', borderRadius: 6, padding: '2px 8px',
                cursor: 'pointer', fontFamily: 'inherit' }}>
              Désactiver
            </button>
          </div>
        )}
      </div>

      {/* Collier du cycle */}
      <CycleBeads activePhase={phase} onPhaseSelect={p => { setPhase(p); setView('overview'); }} />

      {/* ── 4 colonnes fusionnées : sélecteur + contenu phase + En savoir plus ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        {CYCLE_PHASES.map((p, i) => {
          const isActive = phase === p.id;
          const c = BEAD_COLORS[p.id];
          return (
            <div key={p.id} onClick={() => setPhase(p.id)} style={{
              borderRadius: 16, overflow: 'hidden',
              border: `1px solid ${isActive ? c + '70' : 'var(--brd)'}`,
              background: isActive ? `color-mix(in srgb, ${c} 10%, var(--sur))` : 'var(--sur)',
              boxShadow: isActive ? `0 4px 24px ${c}22` : 'none',
              transition: 'all .2s', display: 'flex', flexDirection: 'column', cursor: 'pointer',
            }}>

              {/* Bande header colorée */}
              <div style={{
                padding: '12px 14px',
                background: `color-mix(in srgb, ${c} ${isActive ? 18 : 10}%, transparent)`,
                borderBottom: `1px solid ${c}22`,
                display: 'flex', alignItems: 'center', gap: 9,
                position: 'relative', overflow: 'hidden',
              }}>
                <span style={{
                  position: 'absolute', right: -6, top: -10, fontSize: 52,
                  opacity: 0.12, lineHeight: 1, pointerEvents: 'none', userSelect: 'none',
                }}>{p.moon}</span>
                <MoonGlyph phase={i} size={20} color={c} bg="transparent" />
                <div style={{ position: 'relative' }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: isActive ? c : 'var(--txt)', lineHeight: 1.1 }}>
                    {p.label}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--mut)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    {p.range} · {p.moonName}
                  </div>
                </div>
              </div>

              {/* Corps */}
              <div style={{ padding: '12px 14px', flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>

                {/* Titre fonctionnel */}
                <div style={{ fontSize: 13, fontWeight: 600, color: isActive ? c : 'var(--txt)', lineHeight: 1.3 }}>
                  {p.title}
                </div>

                {/* Description courte */}
                <p style={{ fontSize: 12, color: 'var(--txt2)', lineHeight: 1.65, margin: 0 }}>
                  {p.desc}
                </p>

                {/* Nutriments clés */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {p.needs.map(n => (
                    <span key={n.label} style={{
                      fontSize: 10.5, padding: '2px 8px', borderRadius: 20,
                      background: `color-mix(in srgb, ${c} ${isActive ? 14 : 8}%, transparent)`,
                      color: isActive ? c : 'var(--mut)', fontWeight: 500,
                      border: `1px solid ${c}22`,
                    }}>{n.icon} {n.label}</span>
                  ))}
                </div>

                {/* Ingrédients phare (statiques) */}
                {p.ingredients?.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {p.ingredients.slice(0, 5).map((ing, idx) => (
                      <span key={idx} style={{
                        fontSize: 10, padding: '2px 7px', borderRadius: 6,
                        background: 'var(--sur2)', color: 'var(--txt2)',
                        border: '1px solid var(--brd)',
                      }}>{ing}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Footer : En savoir plus */}
              <div style={{ padding: '10px 14px', borderTop: `1px solid ${c}18` }}>
                <button
                  onClick={e => { e.stopPropagation(); setPhase(p.id); setView('detail'); }}
                  style={{
                    width: '100%', padding: '8px 12px', borderRadius: 9, fontSize: 12, fontWeight: 600,
                    background: isActive ? c : 'transparent',
                    color: isActive ? '#fff' : c,
                    border: `1px solid ${c}50`,
                    cursor: 'pointer', transition: 'all .15s',
                    fontFamily: 'inherit',
                  }}>
                  En savoir plus →
                </button>
              </div>
            </div>
          );
        })}
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
