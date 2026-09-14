import { useState } from 'react';
import { navigate } from '../Router';

// ── Palette FODMAP ────────────────────────────────────────────────────────────
const C = {
  hi:  '#e05252',   // rouge  — FODMAP élevé
  mid: '#e3a53a',   // orange — FODMAP moyen
  lo:  '#3fb950',   // vert   — FODMAP faible
  acc: '#58a6ff',   // bleu   — accent général
  dim: (hex) => hex + '18',
  brd: (hex) => hex + '40',
};

// ── Données ───────────────────────────────────────────────────────────────────

const FODMAP_GROUPS = [
  {
    id: 'F', name: 'Fermentescibles', color: C.acc,
    desc: 'Tous les sucres FODMAP sont fermentés par les bactéries du côlon, produisant gaz, ballonnements et inconfort.',
    detail: 'C\'est la propriété commune de tous les FODMAP. La fermentation bactérienne n\'est pas mauvaise en soi — elle est essentielle pour la santé du microbiote — mais chez les personnes avec intestin sensible (SII), les gaz produits distendent le tube digestif et déclenchent douleurs et crampes.',
  },
  {
    id: 'O', name: 'Oligosaccharides', color: '#a371f7',
    desc: 'Fructanes (blé, oignon, ail) et galacto-oligosaccharides — GOS (légumineuses). Non digestibles par l\'intestin grêle humain.',
    detail: 'Le fructane est la source de problèmes n°1 en Europe : on le trouve dans le blé, l\'orge, le seigle, mais aussi l\'oignon, l\'ail, les poireaux, les artichauts, et même certaines tisanes. Le GOS (galactooligosaccharides) vient essentiellement des légumineuses (pois chiches, lentilles, haricots). Tous deux fermentent abondamment.',
    examples: { high: ['Blé, orge, seigle', 'Oignon, ail, échalote', 'Poireau, fenouil', 'Artichaut, topinambour', 'Pois chiches, lentilles (grosses quantités)', 'Betterave', 'Pistache, noix de cajou'], low: ['Riz, avoine certifiée', 'Pomme de terre, patate douce', 'Carottes, courgettes', 'Poivron', 'Tofu ferme', 'Ail huilé (huile seule)', 'Oignon vert (partie verte uniquement)'] },
  },
  {
    id: 'D', name: 'Disaccharides', color: '#f0883e',
    desc: 'Le lactose — sucre du lait — nécessite la lactase pour être digéré. En son absence, il fermente dans le côlon.',
    detail: 'La production de lactase diminue naturellement après l\'enfance chez 65% de la population mondiale (davantage en Asie et Afrique). En Europe, environ 30% des adultes sont intolérants. Le lactose pose problème dans le lait liquide, les fromages frais et la crème. Les fromages affinés (parmesan, emmental, cheddar) et les yaourts fermentés ont un lactose quasi nul et sont généralement bien tolérés. Les œufs ne contiennent pas de lactose — ils sont toujours autorisés.',
    examples: { high: ['Lait de vache, brebis, chèvre', 'Yaourt liquide, fromage blanc', 'Crème fraîche épaisse', 'Ricotta, mascarpone', 'Crème glacée lactée', 'Lait condensé'], low: ['Fromages affinés (parmesan, emmental, cheddar)', 'Yaourt nature fermenté (petit pot)', 'Lait sans lactose', 'Lait végétal (avoine certifiée, riz, amande)', 'Beurre (traces résiduelles)', 'Œufs (zéro lactose)'] },
  },
  {
    id: 'M', name: 'Monosaccharides', color: '#f5c542',
    desc: 'L\'excès de fructose (fructose > glucose) — fruits sucrés, miel, sirop agave — dépasse la capacité d\'absorption de l\'intestin.',
    detail: 'Le fructose est absorbé par un transporteur (GLUT-5) de capacité limitée. Quand il est seul (sans glucose pour l\'aider), il déborde vers le côlon. Les fruits à indice élevé sont la pomme, la poire, la mangue, la cerise, la pastèque. Le miel et le sirop d\'agave sont particulièrement problématiques. Le fructose "accompagné" du glucose (banane, raisin) est généralement mieux toléré.',
    examples: { high: ['Pomme, poire, mangue', 'Cerise, pastèque, figue', 'Miel (toutes origines)', 'Sirop d\'agave, sirop de maïs', 'Jus de fruits concentrés', 'Sauce teriyaki (souvent), ketchup industriel'], low: ['Banane (mûre pas trop)', 'Orange, mandarine, citron', 'Fraise, myrtille, raisin', 'Kiwi, ananas', 'Sirop d\'érable (petite quantité)', 'Sucre de table (saccharose — glucose+fructose équilibré)'] },
  },
  {
    id: 'A', name: 'And Polyols', color: '#3fb950',
    desc: 'Alcools de sucre (sorbitol, mannitol, xylitol) — naturels dans certains fruits et champignons, ou ajoutés comme édulcorants.',
    detail: 'Les polyols sont partiellement absorbés — le reste fermente. On les trouve naturellement dans les abricots, pêches, prunes, champignons et le chou-fleur. En tant qu\'additifs, cherchez les numéros E420 (sorbitol), E421 (mannitol), E965 (maltitol), E966 (lactitol), E967 (xylitol) sur les étiquettes de chewing-gums, bonbons "sans sucre", médicaments sirupeux et certains yaourts allégés.',
    examples: { high: ['Abricot, pêche, prune, nectarine', 'Mûre, cerise', 'Avocat (grande quantité)', 'Champignons de Paris, shiitaké', 'Chou-fleur', 'Chewing-gum/bonbon sans sucre (xylitol, sorbitol)', 'Médicaments en sirop (vérifier)'], low: ['Banane, raisin, fraise', 'Orange, pamplemousse', 'Carotte, concombre, tomate', 'Poivron, épinards', 'Riz, quinoa, avoine'] },
  },
];

const THREE_PHASES = [
  {
    num: '01', title: 'Élimination', duration: '2 à 6 semaines', color: C.hi,
    icon: '🚫',
    desc: 'Suppression stricte de tous les aliments FODMAP élevés. L\'objectif n\'est pas de guérir mais de "vider le système" et d\'évaluer si les symptômes s\'améliorent.',
    tips: [
      'Suivre scrupuleusement la liste : même de petites quantités d\'aliments élevés peuvent maintenir les symptômes.',
      'Tenir un journal alimentaire + symptômes (intensité de 1 à 10) chaque jour.',
      'Ne pas rester plus de 6 semaines — risque d\'appauvrissement du microbiote.',
      'S\'accompagner d\'un diététicien spécialisé est fortement recommandé.',
      'Les sorties au restaurant sont difficiles : prévoir ses repas ou appeler à l\'avance.',
    ],
  },
  {
    num: '02', title: 'Réintroduction', duration: '6 à 8 semaines', color: C.mid,
    icon: '🔬',
    desc: 'Réintroduction méthodique d\'un FODMAP à la fois, en quantité croissante, pour identifier précisément vos seuils de tolérance.',
    tips: [
      'Tester un seul groupe FODMAP à la fois, 3 jours de suite minimum.',
      'Revenir à la phase 1 entre chaque test (3 jours de "lavage").',
      'Ordre recommandé : lactose → fructose → sorbitol → mannitol → fructanes → GOS.',
      'Garder des notes précises : quelle quantité → quels symptômes, combien d\'heures après.',
      'Ne pas se décourager si un test échoue — c\'est une information précieuse, pas un échec.',
    ],
  },
  {
    num: '03', title: 'Personnalisation', duration: 'À vie', color: C.lo,
    icon: '✨',
    desc: 'Régime adapté à votre propre profil de tolérance. La plupart des gens peuvent réintégrer la majorité des aliments à des doses qui n\'entraînent pas de symptômes.',
    tips: [
      'La tolérance peut varier avec le stress, le cycle hormonal, la fatigue, les antibiotiques.',
      'L\'effet cumulatif existe : 1 FODMAP à un repas peut être OK, 3 en même temps — non.',
      'Le microbiote s\'adapte : certaines tolérances s\'améliorent avec le temps.',
      'Conserver un suivi régulier avec votre diététicien ou gastro.',
      'Vous pouvez tester à nouveau des aliments qui posaient problème — les seuils changent.',
    ],
  },
];

const PRACTICAL_SWAPS = [
  { avoid: 'Oignon', use: 'Partie verte de l\'oignon vert', why: 'Les fructanes sont dans le bulbe, pas dans les feuilles' },
  { avoid: 'Ail', use: 'Huile infusée à l\'ail', why: 'Les FODMAP ne passent pas dans l\'huile — l\'arôme oui' },
  { avoid: 'Blé (pâtes, pain)', use: 'Riz, quinoa, pâtes sans gluten certifiées', why: 'Les grains sans fructanes : riz, avoine, maïs, sarrasin' },
  { avoid: 'Lait de vache', use: 'Lait d\'amande, de riz ou sans lactose', why: 'Éliminer le lactose suffit — la protéine n\'est pas en cause' },
  { avoid: 'Pomme, poire', use: 'Orange, fraise, raisin, kiwi', why: 'Fruits à ratio fructose/glucose équilibré' },
  { avoid: 'Miel, sirop d\'agave', use: 'Sirop d\'érable (petite quantité), sucre de table', why: 'Le saccharose = glucose + fructose à parts égales' },
  { avoid: 'Légumineuses (grandes quantités)', use: 'Tofu ferme, tempeh, protéines de chanvre', why: 'La fermentation réduit les GOS (ex : lentilles en conserve rincées)' },
  { avoid: 'Chewing-gum/bonbons "sans sucre"', use: 'Vérifier l\'absence de xylitol/sorbitol/mannitol', why: 'Les polyols artificiels sont de puissants FODMAP' },
  { avoid: 'Champignons', use: 'Courgette, poivron, haricots verts', why: 'Même texture sautée, zéro polyol' },
  { avoid: 'Jus de pomme/poire', use: 'Eau citronnée, eau de coco (petite quantité)', why: 'Concentré en fructose libre' },
];

const MYTHS = [
  {
    myth: 'Les FODMAP sont mauvais pour la santé',
    truth: 'Non — ils nourrissent le microbiote (prébiotiques naturels). La restriction n\'est que temporaire et ciblée sur les personnes avec SII ou hypersensibilité viscérale.',
  },
  {
    myth: 'C\'est comme un régime sans gluten',
    truth: 'Différent. Les fructanes du blé (et non le gluten lui-même) sont souvent en cause. Beaucoup de gens qui "ne tolèrent pas le gluten" tolèrent en fait des céréales sans fructanes. La maladie cœliaque, elle, implique bien le gluten.',
  },
  {
    myth: 'Il faut éviter tous les FODMAP à vie',
    truth: 'Faux. La phase 3 (personnalisation) vise à réintégrer le maximum d\'aliments. La restriction permanente appauvrit le microbiote et n\'est pas recommandée.',
  },
  {
    myth: 'Le pain au levain est autorisé',
    truth: 'Partiellement vrai. La fermentation longue du levain dégrade une partie des fructanes — le pain au levain de blé peut être mieux toléré que le pain industriel, mais pas nécessairement faible en FODMAP.',
  },
  {
    myth: 'Si j\'ai des ballonnements, j\'ai le SII et je dois faire le régime FODMAP',
    truth: 'Non. Les ballonnements ont de nombreuses causes (dysmotilité, dysbiose, SIBO, stress…). Le régime low-FODMAP est efficace dans ~70% des cas de SII mais doit être prescrit après diagnostic médical.',
  },
  {
    myth: 'L\'avoccat est interdit',
    truth: 'En grande quantité, oui (sorbitol). Mais ⅛ d\'avoccat (30g) est généralement bien toléré en phase basse-FODMAP.',
  },
];

const NUTR_WATCH = [
  { icon: '🦴', label: 'Calcium', risk: 'Éviction des produits laitiers riches en lactose', solution: 'Fromages affinés (parmesan, emmental), yaourt nature, boissons végétales enrichies, tofu enrichi, amandes, figues, brocoli' },
  { icon: '🌾', label: 'Fibres & prébiotiques', risk: 'Restriction des légumineuses et blé', solution: 'Légumes verts tolérés, graines de chia, avoine certifiée, psyllium (testé progressivement), graines de lin' },
  { icon: '🩸', label: 'Fer', risk: 'Réduction des légumineuses', solution: 'Quinoa, épinards, tofu ferme, graines de courge, betterave, graines de lin, cacao cru' },
  { icon: '💊', label: 'Vitamines B', risk: 'Éviction du blé enrichi', solution: 'Levure nutritionnelle, œufs, riz brun, graines de tournesol, tempeh, légumes verts feuillus' },
  { icon: '🧬', label: 'Microbiote', risk: 'Perte de diversité bactérienne si restriction prolongée', solution: 'Réintroduire dès que possible, fermentés tolérés (yaourt nature, kéfir, kombucha, cornichons, miso)' },
];

// ── Sous-composants ───────────────────────────────────────────────────────────

function Tag({ color, children }) {
  return (
    <span style={{
      padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600,
      letterSpacing: '0.04em', display: 'inline-flex', alignItems: 'center', gap: 4,
      background: color + '20', color, border: `1px solid ${color}40`,
    }}>{children}</span>
  );
}

function SectionTitle({ children, sub }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <h2 style={{ margin: 0, fontSize: 'clamp(18px,3vw,24px)', fontWeight: 500, letterSpacing: '-0.02em' }}>
        {children}
      </h2>
      {sub && <p style={{ margin: '6px 0 0', fontSize: 14, color: 'var(--mut)', lineHeight: 1.5 }}>{sub}</p>}
    </div>
  );
}

function Panel({ children, style }) {
  return (
    <div className="frigo-panel" style={style}>
      {children}
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function FodmapPage() {
  const [activeGroup, setActiveGroup] = useState(null);
  const [activePhase, setActivePhase] = useState(null);
  const [mythOpen, setMythOpen]       = useState(null);

  const group = FODMAP_GROUPS.find(g => g.id === activeGroup);

  return (
    <div className="page-home" style={{ padding: '0 24px', maxWidth: 1100, margin: '0 auto' }}>

      {/* ── Hero ── */}
      <div style={{ position: 'relative', overflow: 'hidden', paddingBottom: 32, marginBottom: 36 }}>
        <div style={{
          position: 'absolute', right: -20, top: -30, fontSize: 220,
          fontWeight: 900, opacity: 0.03, letterSpacing: '-0.04em', pointerEvents: 'none',
          color: 'var(--txt)', lineHeight: 1,
        }}>
          FODMAP
        </div>
        <div style={{ position: 'relative' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
            <Tag color={C.hi}>Sensibilité intestinale</Tag>
            <Tag color={C.acc}>SII / IBS</Tag>
            <Tag color={C.lo}>Nutrition clinique</Tag>
          </div>
          <h1 style={{ margin: '0 0 14px', fontSize: 'clamp(32px,6vw,58px)', fontWeight: 500, letterSpacing: '-0.03em', lineHeight: 1.05 }}>
            Guide{' '}
            <em style={{ color: C.acc, fontStyle: 'italic' }}>FODMAP</em>
          </h1>
          <p style={{ margin: 0, fontSize: 17, color: 'var(--txt2)', maxWidth: 620, lineHeight: 1.75 }}>
            Les FODMAP sont des sucres fermentescibles naturellement présents dans de nombreux aliments.
            Comprendre comment ils fonctionnent — et comment les gérer — peut transformer la vie de millions
            de personnes souffrant du syndrome de l'intestin irritable.
          </p>
        </div>
      </div>

      {/* ── Qu'est-ce que c'est ? ── */}
      <div style={{ marginBottom: 48 }}>
        <SectionTitle sub="L'acronyme décodé, la science simplifiée.">Qu'est-ce que les FODMAP ?</SectionTitle>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 14, marginBottom: 24 }}>
          <Panel>
            <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: C.acc, marginBottom: 10 }}>
              Le mécanisme
            </div>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.8, color: 'var(--txt2)' }}>
              Les FODMAP sont de petits glucides mal absorbés par l'intestin grêle.
              Ils atteignent le côlon intacts, où les bactéries les fermentent — produisant
              des gaz (H₂, CO₂, méthane). Ils exercent aussi un effet osmotique,
              attirant l'eau dans l'intestin.
            </p>
          </Panel>
          <Panel>
            <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: C.hi, marginBottom: 10 }}>
              Pourquoi ça fait mal ?
            </div>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.8, color: 'var(--txt2)' }}>
              Chez les personnes avec un intestin irritable (SII), la paroi intestinale est
              hypersensible : les capteurs de douleur réagissent à une distension normale
              comme si elle était intense. C'est l'hypersensibilité viscérale — le problème
              n'est pas la fermentation elle-même mais la réponse ampliée du système nerveux entérique.
            </p>
          </Panel>
          <Panel>
            <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: C.lo, marginBottom: 10 }}>
              Qui est concerné ?
            </div>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.8, color: 'var(--txt2)' }}>
              Le SII touche 10–15% de la population mondiale (60–70% de femmes).
              Le régime low-FODMAP, développé par l'Université Monash (Australie) en 2008,
              réduit les symptômes chez <strong>70% des patients</strong>.
              C'est l'approche nutritionnelle la mieux validée scientifiquement pour le SII.
            </p>
          </Panel>
        </div>

        {/* Bannière chiffres */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))',
          gap: 1, borderRadius: 14, overflow: 'hidden',
          border: '1px solid var(--brd)',
        }}>
          {[
            { val: '70%', label: 'de patients SII améliorés par le régime low-FODMAP', color: C.lo },
            { val: '2008', label: 'année de développement par l\'Univ. Monash, Melbourne', color: C.acc },
            { val: '5', label: 'catégories de FODMAP identifiées : F–O–D–M–A', color: '#a371f7' },
            { val: '3', label: 'phases distinctes pour un protocole complet', color: C.mid },
          ].map((s, i) => (
            <div key={i} style={{
              padding: '20px 18px', background: 'var(--sur2)',
              borderRight: i < 3 ? '1px solid var(--brd)' : 'none',
            }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: s.color, letterSpacing: '-0.03em', lineHeight: 1 }}>
                {s.val}
              </div>
              <div style={{ fontSize: 12, color: 'var(--mut)', marginTop: 6, lineHeight: 1.5 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── L'acronyme interactif ── */}
      <div style={{ marginBottom: 48 }}>
        <SectionTitle sub="Cliquez sur chaque lettre pour explorer la catégorie et ses exemples.">
          Les 5 familles FODMAP
        </SectionTitle>

        {/* Lettres interactives */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}>
          {FODMAP_GROUPS.map(g => {
            const isActive = activeGroup === g.id;
            return (
              <button key={g.id}
                onClick={() => setActiveGroup(isActive ? null : g.id)}
                style={{
                  padding: '12px 20px', borderRadius: 12, cursor: 'pointer',
                  fontFamily: 'inherit', transition: 'all .15s',
                  background: isActive ? g.color : 'var(--sur2)',
                  border: `2px solid ${isActive ? g.color : 'var(--brd)'}`,
                  color: isActive ? '#fff' : 'var(--txt)',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  minWidth: 80,
                }}>
                <span style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1 }}>
                  {g.id}
                </span>
                <span style={{ fontSize: 10, fontWeight: 500, letterSpacing: '0.06em', textTransform: 'uppercase', opacity: 0.85 }}>
                  {g.name.split(' ')[0]}
                </span>
              </button>
            );
          })}
        </div>

        {/* Détail du groupe sélectionné */}
        {group && (
          <div style={{ animation: 'fadeIn 0.2s ease-out' }}>
            <Panel style={{ borderColor: group.color + '50', background: group.color + '08', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
                <h3 style={{ margin: 0, fontSize: 22, fontWeight: 600, color: group.color }}>
                  {group.id} — {group.name}
                </h3>
              </div>
              <p style={{ margin: '0 0 12px', fontSize: 15, color: 'var(--txt)', lineHeight: 1.7 }}>
                {group.desc}
              </p>
              <p style={{ margin: 0, fontSize: 13, color: 'var(--txt2)', lineHeight: 1.8 }}>
                {group.detail}
              </p>
            </Panel>

            {group.examples && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <Panel style={{ border: `1px solid ${C.hi}40`, background: C.hi + '08' }}>
                  <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: C.hi, marginBottom: 12 }}>
                    🚫 FODMAP élevé — à éviter en phase 1
                  </div>
                  <ul style={{ margin: 0, padding: '0 0 0 18px', fontSize: 13, lineHeight: 2, color: 'var(--txt)' }}>
                    {group.examples.high.map(x => <li key={x}>{x}</li>)}
                  </ul>
                </Panel>
                <Panel style={{ border: `1px solid ${C.lo}40`, background: C.lo + '08' }}>
                  <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: C.lo, marginBottom: 12 }}>
                    ✓ FODMAP faible — généralement toléré
                  </div>
                  <ul style={{ margin: 0, padding: '0 0 0 18px', fontSize: 13, lineHeight: 2, color: 'var(--txt)' }}>
                    {group.examples.low.map(x => <li key={x}>{x}</li>)}
                  </ul>
                </Panel>
              </div>
            )}
          </div>
        )}

        {!group && (
          <Panel style={{ textAlign: 'center', padding: '32px 24px', opacity: 0.6 }}>
            <p style={{ margin: 0, fontSize: 14, color: 'var(--mut)' }}>
              Sélectionnez une lettre ci-dessus pour explorer la famille FODMAP correspondante.
            </p>
          </Panel>
        )}
      </div>

      {/* ── Les 3 phases ── */}
      <div style={{ marginBottom: 48 }}>
        <SectionTitle sub="Un protocole en 3 actes. Cliquez sur chaque phase pour les détails pratiques.">
          Le protocole en 3 phases
        </SectionTitle>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 14 }}>
          {THREE_PHASES.map((ph, i) => {
            const isOpen = activePhase === i;
            return (
              <div key={i}>
                <button onClick={() => setActivePhase(isOpen ? null : i)} style={{
                  width: '100%', textAlign: 'left', cursor: 'pointer',
                  padding: 20, borderRadius: 14, fontFamily: 'inherit',
                  background: isOpen ? ph.color + '15' : 'var(--sur)',
                  border: `1px solid ${isOpen ? ph.color + '60' : 'var(--brd)'}`,
                  transition: 'all .15s', color: 'var(--txt)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10, marginBottom: 12 }}>
                    <div style={{
                      fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
                      color: ph.color, background: ph.color + '20', border: `1px solid ${ph.color}40`,
                      borderRadius: 6, padding: '3px 8px',
                    }}>
                      Phase {ph.num}
                    </div>
                    <span style={{ fontSize: 20 }}>{ph.icon}</span>
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 6 }}>{ph.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--mut)', marginBottom: 10 }}>⏱ {ph.duration}</div>
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--txt2)', lineHeight: 1.6 }}>{ph.desc}</p>
                  <div style={{ marginTop: 12, fontSize: 11, color: ph.color, fontWeight: 500 }}>
                    {isOpen ? '▲ Réduire' : '▼ Voir les conseils pratiques'}
                  </div>
                </button>

                {isOpen && (
                  <Panel style={{ marginTop: 8, border: `1px solid ${ph.color}30`, background: ph.color + '06' }}>
                    <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: ph.color, marginBottom: 12 }}>
                      Conseils pratiques
                    </div>
                    <ul style={{ margin: 0, padding: '0 0 0 18px', listStyle: 'none', paddingLeft: 0 }}>
                      {ph.tips.map((tip, j) => (
                        <li key={j} style={{ display: 'flex', gap: 10, marginBottom: 10, alignItems: 'flex-start', fontSize: 13, lineHeight: 1.6, color: 'var(--txt2)' }}>
                          <span style={{ color: ph.color, flexShrink: 0, marginTop: 1 }}>→</span>
                          {tip}
                        </li>
                      ))}
                    </ul>
                  </Panel>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Swaps pratiques ── */}
      <div style={{ marginBottom: 48 }}>
        <SectionTitle sub="Les substitutions du quotidien pour manger savoureux sans déclencher de symptômes.">
          Substitutions intelligentes
        </SectionTitle>

        <div style={{ overflowX: 'auto', borderRadius: 14, border: '1px solid var(--brd)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--sur2)', borderBottom: '1px solid var(--brd)' }}>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--mut)', width: '28%' }}>
                  🚫 À éviter
                </th>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--mut)', width: '30%' }}>
                  ✓ Remplacer par
                </th>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--mut)' }}>
                  Pourquoi ça marche
                </th>
              </tr>
            </thead>
            <tbody>
              {PRACTICAL_SWAPS.map((s, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--brd)', background: i % 2 === 0 ? 'transparent' : 'var(--sur2)' }}>
                  <td style={{ padding: '12px 16px', color: C.hi, fontWeight: 500 }}>{s.avoid}</td>
                  <td style={{ padding: '12px 16px', color: C.lo, fontWeight: 500 }}>{s.use}</td>
                  <td style={{ padding: '12px 16px', color: 'var(--txt2)', lineHeight: 1.5 }}>{s.why}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Vigilances nutritionnelles ── */}
      <div style={{ marginBottom: 48 }}>
        <SectionTitle sub="Un régime restrictif peut créer des carences si on ne compense pas intelligemment.">
          Points de vigilance nutritionnelle
        </SectionTitle>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 }}>
          {NUTR_WATCH.map((n, i) => (
            <Panel key={i}>
              <span style={{ fontSize: 28, display: 'block', marginBottom: 10 }}>{n.icon}</span>
              <strong style={{ fontSize: 14, color: C.hi, display: 'block', marginBottom: 6 }}>{n.label}</strong>
              <div style={{ fontSize: 11, color: 'var(--mut)', marginBottom: 8, lineHeight: 1.5 }}>
                <strong>Risque :</strong> {n.risk}
              </div>
              <div style={{ fontSize: 12, color: 'var(--txt2)', lineHeight: 1.6 }}>
                <strong style={{ color: C.lo }}>Solution :</strong> {n.solution}
              </div>
            </Panel>
          ))}
        </div>
      </div>

      {/* ── Mythes et réalités ── */}
      <div style={{ marginBottom: 48 }}>
        <SectionTitle sub="Ce que vous avez probablement mal compris — ou qu'on vous a mal expliqué.">
          Mythes & réalités
        </SectionTitle>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {MYTHS.map((m, i) => {
            const isOpen = mythOpen === i;
            return (
              <div key={i} style={{ borderRadius: 12, overflow: 'hidden', border: `1px solid ${isOpen ? C.acc + '50' : 'var(--brd)'}`, transition: 'border-color .15s' }}>
                <button onClick={() => setMythOpen(isOpen ? null : i)} style={{
                  width: '100%', textAlign: 'left', padding: '16px 20px', cursor: 'pointer',
                  background: isOpen ? C.acc + '08' : 'var(--sur)',
                  border: 'none', fontFamily: 'inherit', color: 'var(--txt)',
                  display: 'flex', alignItems: 'center', gap: 14, transition: 'background .15s',
                }}>
                  <span style={{
                    flexShrink: 0, width: 28, height: 28, borderRadius: 8,
                    background: C.hi + '20', color: C.hi,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 14, fontWeight: 700,
                  }}>✗</span>
                  <span style={{ flex: 1, fontSize: 14, fontWeight: 500, fontStyle: 'italic' }}>
                    "{m.myth}"
                  </span>
                  <span style={{ fontSize: 12, color: C.acc, fontWeight: 500, flexShrink: 0 }}>
                    {isOpen ? '▲' : '▼'}
                  </span>
                </button>
                {isOpen && (
                  <div style={{ padding: '0 20px 18px 62px', background: C.acc + '08' }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                      <span style={{
                        flexShrink: 0, width: 24, height: 24, borderRadius: 6,
                        background: C.lo + '25', color: C.lo,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 13, fontWeight: 700, marginTop: 1,
                      }}>✓</span>
                      <p style={{ margin: 0, fontSize: 14, color: 'var(--txt2)', lineHeight: 1.75 }}>
                        {m.truth}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── FODMAP et cuisine ── */}
      <div style={{ marginBottom: 48 }}>
        <SectionTitle sub="La cuisine low-FODMAP n'est pas triste — elle demande juste de la méthode.">
          FODMAP & cuisine au quotidien
        </SectionTitle>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 14 }}>
          {[
            {
              icon: '🧄', title: 'L\'ail sans les FODMAP',
              text: 'L\'ail libère ses fructanes dans l\'eau mais pas dans l\'huile. Faites-le revenir dans l\'huile d\'olive 2 minutes, retirez-le : l\'arôme reste, les FODMAP aussi — dans la poubelle. Ou achetez directement de l\'huile aromatisée à l\'ail certifiée low-FODMAP.',
            },
            {
              icon: '🍞', title: 'Le pain au levain',
              text: 'La fermentation longue (12–24h) par les bactéries du levain dégrade une partie significative des fructanes du blé. Un pain au levain artisanal maison est souvent mieux toléré qu\'une baguette industrielle. Testez en phase 2 avec une petite quantité.',
            },
            {
              icon: '🥫', title: 'Les légumineuses en conserve',
              text: 'Rincer abondamment les légumineuses en conserve (pois chiches, lentilles) réduit le GOS de 40 à 60%. Les petites portions (2–3 cuillères à soupe) de lentilles corail cuites sont souvent tolérées. La quantité est la clé.',
            },
            {
              icon: '📱', title: 'L\'application Monash FODMAP',
              text: 'L\'outil de référence mondial. Développée par l\'université qui a créé le régime, elle liste 900+ aliments avec leur teneur en FODMAP par portion. Indispensable pour les courses, le restaurant, les voyages. Payante (~9€) mais irremplaçable.',
            },
            {
              icon: '🍽️', title: 'L\'effet cumulatif',
              text: 'C\'est le piège le plus fréquent. Un aliment "moyen FODMAP" peut être toléré seul mais pas en combinaison avec d\'autres. Si un repas contient 3 aliments à teneur modérée, les FODMAP s\'accumulent et dépassent votre seuil. Cuisiner simple, un aliment à la fois.',
            },
            {
              icon: '🌍', title: 'Cuisines naturellement low-FODMAP',
              text: 'La cuisine japonaise (riz, tofu, algues, edamame, gingembre, sauce soja en petite quantité) est particulièrement adaptée. La cuisine thaïlandaise (avec vigilance sur l\'ail et l\'oignon) aussi. La cuisine méditerranéenne demande plus d\'adaptation (ail, oignon omniprésents) mais reste réalisable.',
            },
          ].map((card, i) => (
            <Panel key={i}>
              <span style={{ fontSize: 28, display: 'block', marginBottom: 10 }}>{card.icon}</span>
              <strong style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>{card.title}</strong>
              <p style={{ margin: 0, fontSize: 13, color: 'var(--txt2)', lineHeight: 1.75 }}>{card.text}</p>
            </Panel>
          ))}
        </div>
      </div>

      {/* ── Quand consulter ── */}
      <Panel style={{
        marginBottom: 48,
        background: 'linear-gradient(135deg, rgba(88,166,255,0.06), rgba(63,185,80,0.04))',
        border: `1px solid ${C.acc}30`,
      }}>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <span style={{ fontSize: 42, flexShrink: 0 }}>⚕️</span>
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: C.acc, marginBottom: 10 }}>
              Important — à ne pas négliger
            </div>
            <h3 style={{ margin: '0 0 12px', fontSize: 18, fontWeight: 600 }}>
              Le régime low-FODMAP ne s'autogère pas seul
            </h3>
            <p style={{ margin: '0 0 12px', fontSize: 14, color: 'var(--txt2)', lineHeight: 1.75 }}>
              Avant de démarrer, consultez un <strong>gastro-entérologue</strong> pour confirmer le diagnostic de SII
              et exclure une maladie cœliaque, une maladie de Crohn ou un cancer colorectal —
              des pathologies qui présentent des symptômes similaires.
            </p>
            <p style={{ margin: 0, fontSize: 14, color: 'var(--txt2)', lineHeight: 1.75 }}>
              Faites-vous accompagner par un <strong>diététicien-nutritionniste</strong> spécialisé
              pour les phases 1 et 2 — l'auto-gestion augmente le risque de restriction excessive,
              de carences et d'échec du protocole.
            </p>
          </div>
        </div>
      </Panel>

      {/* ── Lien vers recettes ── */}
      <div style={{ textAlign: 'center', paddingBottom: 48 }}>
        <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 16 }}>
          Passer à la pratique
        </div>
        <h3 style={{ margin: '0 0 10px', fontSize: 22, fontWeight: 500 }}>Trouvez des recettes low-FODMAP</h3>
        <p style={{ margin: '0 0 24px', fontSize: 14, color: 'var(--mut)', maxWidth: 420, marginLeft: 'auto', marginRight: 'auto' }}>
          Filtrez les recettes par allergie ou régime depuis la page d'accueil pour trouver des idées adaptées.
        </p>
        <button onClick={() => navigate('/')} style={{
          padding: '14px 36px', borderRadius: 999, fontSize: 15, fontWeight: 600,
          background: C.acc, color: '#fff', border: 'none', cursor: 'pointer',
          fontFamily: 'inherit', boxShadow: `0 4px 20px ${C.acc}40`,
          transition: 'transform .15s, box-shadow .15s',
        }}>
          Voir les recettes →
        </button>
      </div>
    </div>
  );
}
