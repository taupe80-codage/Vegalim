/**
 * FAQPage.jsx — Foire Aux Questions ALIM v6
 *
 * Accordéon animé par thème, barre de recherche live,
 * persistance de l'onglet ouvert en localStorage.
 */

import { useState, useMemo } from 'react';
import { navigate } from '../Router';

const FAQ_KEY = 'alim_faq_open';

// ── Données ───────────────────────────────────────────────────────────────────

const FAQ_SECTIONS = [
  {
    id: 'recettes',
    icon: '🍽️',
    title: 'Les recettes',
    color: '#1d6b40',
    items: [
      {
        q: 'Comment sont sélectionnées les recettes ?',
        a: `Les recettes d'ALIM sont sourcées depuis des bases de données culinaires vérifiées et enrichies manuellement. Chaque recette passe par un processus de validation nutritionnelle basé sur les données CIQUAL (table de composition des aliments de l'ANSES). Nous privilégions les recettes végétales, équilibrées et accessibles en moins de 45 minutes.`,
      },
      {
        q: 'Que signifie le score NRF (score nutritionnel) ?',
        a: `Le score NRF (Nutrient-Rich Food) est un index scientifique qui évalue la qualité nutritionnelle d'un aliment en tenant compte de 9 nutriments bénéfiques (protéines, fibres, calcium, fer, zinc, magnésium, vitamines A/C/E) et de 3 nutriments à limiter (graisses saturées, sucres ajoutés, sodium). Plus le score est élevé, plus la recette est nutritionnellement dense. ALIM affiche ce score sur chaque carte recette.`,
      },
      {
        q: 'Comment filtrer par régime alimentaire ?',
        a: `Sur la page Recettes, utilisez les filtres disponibles en haut de la liste : vegan, végétarien, sans gluten, sans lactose, riche en protéines, riche en fibres, faible en calories, etc. Vous pouvez combiner plusieurs filtres. Vos préférences sont sauvegardées automatiquement dans votre navigateur et persistent même sans connexion.`,
      },
      {
        q: 'Comment envoyer une recette dans le planning ?',
        a: `Sur chaque carte recette, cliquez sur le bouton ▦ (icône planning). Une fenêtre s'ouvre pour choisir le jour (Lundi → Dimanche) et le repas (Petit-déjeuner, Déjeuner, Dîner). La recette est immédiatement ajoutée à votre planning hebdomadaire. Vous pouvez aussi le faire depuis la page de détail d'une recette via le bouton "Ajouter au planning".`,
      },
      {
        q: 'Comment voir la valeur nutritionnelle d\'une recette ?',
        a: `Cliquez sur le bouton ◉ sur la carte recette ou sur "Voir l'AJR" dans la page détail. Vous serez redirigé vers la page Nutrition en vue "Recette", qui affiche les apports en protéines, glucides, lipides, fibres, vitamines et minéraux, comparés aux Apports Journaliers Recommandés (AJR). Une analyse IA approfondie est également disponible via le bouton "Analyse IA".`,
      },
      {
        q: 'Puis-je ajouter mes propres recettes ?',
        a: `Cette fonctionnalité est en cours de développement. Dans une prochaine version, vous pourrez créer des recettes personnalisées, les tagger avec vos propres ingrédients et les intégrer dans le planning. En attendant, vous pouvez utiliser la fonction Favoris pour retrouver rapidement vos recettes préférées.`,
      },
    ],
  },
  {
    id: 'frigo',
    icon: '🧊',
    title: 'Mon Frigo',
    color: '#2563a8',
    items: [
      {
        q: 'Comment fonctionne la suggestion par ingrédients ?',
        a: `La page "Mon Frigo" vous permet de sélectionner les ingrédients que vous avez chez vous. ALIM analyse ensuite votre sélection et vous propose des recettes réalisables avec ces ingrédients, en priorisant celles qui en utilisent le plus grand nombre. Les recettes sont triées par score nutritionnel NRF et par nombre d'ingrédients correspondants.`,
      },
      {
        q: 'Mes sélections sont-elles sauvegardées si je me déconnecte ?',
        a: `Oui, toutes vos sélections d'ingrédients dans le Frigo sont sauvegardées automatiquement dans le stockage local de votre navigateur (localStorage). Elles persistent même si vous vous déconnectez ou fermez l'application. Elles restent disponibles jusqu'à ce que vous les effaciez manuellement via le bouton "Vider la sélection", ou que vous vidiez les données de votre navigateur.`,
      },
      {
        q: 'Comment ajouter un ingrédient qui n\'est pas dans la liste ?',
        a: `Utilisez la barre de recherche en haut de la page Frigo. En tapant au moins 2 caractères, ALIM propose des suggestions issues de la base d'ingrédients complète (plus de 2 000 ingrédients). Cliquez sur une suggestion pour l'ajouter à votre sélection. Son nom s'affichera correctement en français dans vos chips d'ingrédients sélectionnés.`,
      },
      {
        q: 'Combien d\'ingrédients puis-je sélectionner ?',
        a: `Il n'y a pas de limite fixe. Cependant, pour de meilleures suggestions, nous recommandons de sélectionner entre 3 et 10 ingrédients principaux. Avec trop d'ingrédients, les résultats se rapprochent de la liste complète des recettes. L'idéal est de sélectionner ce que vous avez réellement sous la main, en particulier les ingrédients frais que vous souhaitez utiliser rapidement.`,
      },
      {
        q: 'Les suggestions prennent-elles en compte mes filtres de régime ?',
        a: `Oui. Les filtres (vegan, sans gluten, etc.) s'appliquent également aux suggestions du Frigo. Vous pouvez combiner vos ingrédients disponibles avec vos restrictions alimentaires pour des suggestions encore plus pertinentes.`,
      },
    ],
  },
  {
    id: 'planning',
    icon: '▦',
    title: 'Le Planning',
    color: '#7c3aed',
    items: [
      {
        q: 'Comment créer un planning hebdomadaire ?',
        a: `Accédez à la page Planning depuis la navigation. Vous pouvez y ajouter des recettes pour chaque jour de la semaine (Lundi au Dimanche) et pour chaque repas (Petit-déjeuner, Déjeuner, Dîner). Ajoutez une recette en cliquant sur le bouton ▦ depuis n'importe quelle carte recette dans l'application.`,
      },
      {
        q: 'Puis-je planifier plusieurs recettes par repas ?',
        a: `Oui, chaque créneau repas peut contenir plusieurs recettes. Cela est utile si vous préparez un repas avec plusieurs plats (entrée + plat, dessert, etc.) ou si vous souhaitez avoir plusieurs options pour le même repas.`,
      },
      {
        q: 'Le planning est-il lié à mon compte ou local ?',
        a: `Dans la version actuelle, le planning est sauvegardé localement dans votre navigateur (localStorage). Il persiste entre les sessions mais est propre à votre appareil. Une synchronisation avec votre compte en ligne pour accéder à votre planning depuis plusieurs appareils est prévue dans une prochaine version.`,
      },
      {
        q: 'Comment générer une liste de courses depuis le planning ?',
        a: `Depuis la page Courses (icône 🛒 dans la navigation), ALIM analyse les recettes planifiées et génère automatiquement une liste de courses consolidée. Les ingrédients communs à plusieurs recettes sont regroupés et les quantités additionnées. Vous pouvez cocher les articles au fur et à mesure de vos achats.`,
      },
      {
        q: 'Puis-je exporter ou partager mon planning ?',
        a: `Cette fonctionnalité est en développement. Dans une future version, vous pourrez exporter votre planning en PDF ou le partager avec d'autres utilisateurs ALIM (idéal pour les couples ou les familles qui coordonnent leurs repas).`,
      },
    ],
  },
  {
    id: 'nutrition',
    icon: '◉',
    title: 'Nutrition & AJR',
    color: '#059669',
    items: [
      {
        q: 'Qu\'est-ce qu\'un AJR (Apport Journalier Recommandé) ?',
        a: `Les AJR (Apports Journaliers Recommandés) sont des valeurs de référence établies par les autorités sanitaires européennes pour indiquer la quantité quotidienne de chaque nutriment nécessaire au bon fonctionnement de l'organisme. Ils varient selon l'âge, le sexe et l'état physiologique. ALIM utilise les valeurs de référence européennes (UE) comme base de calcul.`,
      },
      {
        q: 'Comment analyser la nutrition d\'une recette ?',
        a: `Depuis n'importe quelle recette, cliquez sur ◉ pour être redirigé vers la vue "Recette" de la page Nutrition. Vous y verrez des barres de progression indiquant le pourcentage d'AJR couvert par la recette pour chaque nutriment clé : énergie, protéines, glucides, lipides, fibres, fer, calcium, magnésium, zinc, vitamines C, A et B12. Pour une analyse plus approfondie avec identification des déficiences, utilisez le bouton "Analyse IA".`,
      },
      {
        q: 'Comment voir mon bilan nutritionnel sur la semaine ?',
        a: `Sur la page Nutrition, sélectionnez la vue "Ma semaine" (icône ▦). ALIM agrège automatiquement les données nutritionnelles de toutes les recettes présentes dans votre planning hebdomadaire et calcule le cumul sur 7 jours, comparé aux AJR × 7. Cela vous donne une vision globale de l'équilibre de votre alimentation sur la semaine.`,
      },
      {
        q: 'Les calculs nutritionnels sont-ils fiables ?',
        a: `Les données nutritionnelles proviennent de la table CIQUAL de l'ANSES (Agence nationale de sécurité sanitaire), qui est la référence officielle française pour la composition des aliments. Les calculs sont indicatifs et peuvent varier selon les variétés d'ingrédients, les modes de cuisson et les proportions exactes utilisées. Ils sont faits pour vous guider, non pour remplacer un suivi diététique professionnel.`,
      },
      {
        q: 'Puis-je personnaliser mes objectifs nutritionnels ?',
        a: `Sur la page Nutrition, vue "Mes apports", vous pouvez ajuster vos objectifs via le profil nutritionnel (calorique cible, répartition macros). Cette fonctionnalité est accessible depuis la page Profil et permet de personaliser les AJR en fonction de votre niveau d'activité physique et de vos objectifs (perte de poids, prise de masse, maintien).`,
      },
    ],
  },
  {
    id: 'cycle',
    icon: '🌑',
    title: 'Cycle féminin',
    color: '#9333ea',
    items: [
      {
        q: 'Comment ALIM adapte les recettes à mon cycle ?',
        a: `La page Cycle propose des recommandations nutritionnelles adaptées aux 4 phases du cycle menstruel : menstruelle, folliculaire, ovulatoire et lutéale. Chaque phase a des besoins spécifiques — en fer pendant les règles, en antioxydants en phase folliculaire, en zinc et magnésium en phase lutéale. ALIM met en avant les ingrédients et les recettes qui soutiennent votre corps à chaque étape.`,
      },
      {
        q: 'Les données de mon cycle sont-elles privées ?',
        a: `Oui, totalement. Votre phase de cycle sélectionnée est sauvegardée uniquement dans votre navigateur (localStorage), aucune donnée liée à votre cycle n'est envoyée sur nos serveurs. Ces informations restent strictement sur votre appareil et ne sont partagées avec personne.`,
      },
      {
        q: 'Comment utiliser la section "En savoir plus" des phases ?',
        a: `Sur la page Cycle, sélectionnez votre phase actuelle puis cliquez sur "En savoir plus →". Vous accéderez à une vue détaillée avec : la courbe hormonale caractéristique de la phase, les symptômes courants, les aliments à favoriser et à éviter, des conseils d'activité physique, les nutriments clés à surveiller et des exemples de recettes adaptées.`,
      },
      {
        q: 'ALIM remplace-t-il un suivi médical ?',
        a: `Non. Les informations présentées dans la section Cycle sont à titre éducatif et informatif uniquement. Elles ne constituent pas un avis médical. Si vous avez des symptômes préoccupants liés à votre cycle, consultez un professionnel de santé (gynécologue, médecin généraliste, nutritionniste).`,
      },
    ],
  },
  {
    id: 'astro',
    icon: '✨',
    title: 'Astrologie culinaire',
    color: '#d97706',
    items: [
      {
        q: 'Sur quoi est basée la recommandation astrologique ?',
        a: `La section Astro d'ALIM propose une approche ludique et culturelle de la nutrition en associant les 12 signes astrologiques à leurs 4 éléments (Feu, Terre, Air, Eau). Chaque élément correspond à des saveurs, textures et modes de cuisson typiques. C'est une invitation à explorer de nouveaux horizons culinaires, non une prescription médicale ou diététique.`,
      },
      {
        q: 'Puis-je choisir un autre signe que le mien ?',
        a: `Bien sûr ! Vous pouvez sélectionner n'importe lequel des 12 signes depuis la grille. Votre sélection est sauvegardée et persiste entre les sessions. Certains utilisateurs choisissent leur ascendant ou explorent plusieurs signes pour varier les recommandations culinaires.`,
      },
      {
        q: 'Ma sélection de signe est-elle sauvegardée ?',
        a: `Oui. Votre signe sélectionné est automatiquement mémorisé dans votre navigateur. Il sera restauré à votre prochaine visite, même sans connexion et même si vous vous déconnectez de votre compte.`,
      },
      {
        q: 'Comment les recettes sont-elles filtrées par élément ?',
        a: `Chaque recette de la base ALIM est associée à un ou plusieurs éléments astrologiques en fonction de ses ingrédients dominants, de ses saveurs et de son mode de cuisson. Par exemple, les recettes épicées et rapides sont associées au Feu, les plats mijotés aux racines à la Terre, les salades légères et croquantes à l'Air, les bouillons et soupes à l'Eau.`,
      },
    ],
  },
  {
    id: 'compte',
    icon: '👤',
    title: 'Compte & données',
    color: '#0891b2',
    items: [
      {
        q: 'Mes données sont-elles sauvegardées sans connexion ?',
        a: `Oui. La majorité de vos préférences (ingrédients du frigo, planning, favoris, phase de cycle, signe astrologique, filtres, vue nutrition) sont sauvegardées dans le stockage local de votre navigateur (localStorage). Elles fonctionnent parfaitement sans compte et sans connexion internet. Un compte vous permet uniquement de synchroniser ces données entre plusieurs appareils.`,
      },
      {
        q: 'Quels sont les avantages d\'un compte ALIM ?',
        a: `Avec un compte ALIM, vous bénéficiez de : la synchronisation de vos favoris et de votre planning sur tous vos appareils, des recommandations personnalisées basées sur votre historique, la sauvegarde sécurisée de votre profil nutritionnel, et l'accès aux futures fonctionnalités sociales (partage de planning, recettes communautaires).`,
      },
      {
        q: 'Comment supprimer mon compte ?',
        a: `Pour supprimer votre compte, rendez-vous sur la page Profil, puis dans la section "Paramètres du compte". Vous trouverez l'option "Supprimer mon compte". Cette action est irréversible et supprimera toutes vos données personnelles de nos serveurs. Les données locales (localStorage) devront être effacées manuellement depuis les paramètres de votre navigateur.`,
      },
      {
        q: 'ALIM utilise-t-il mes données personnelles ?',
        a: `ALIM ne vend ni ne partage vos données personnelles avec des tiers. Les données de santé (cycle, préférences nutritionnelles) restent locales sur votre appareil. Seul votre email et votre profil nutritionnel (si vous créez un compte) sont stockés sur nos serveurs sécurisés, conformément au RGPD. Vous pouvez demander l'export ou la suppression de ces données à tout moment.`,
      },
      {
        q: 'Comment modifier mon profil nutritionnel ?',
        a: `Accédez à la page Profil (icône avatar en haut à droite si connecté, ou via la navigation). Vous pouvez y renseigner votre âge, sexe, poids, taille, niveau d'activité physique et objectif alimentaire. Ces informations ajustent les AJR affichés dans la page Nutrition pour qu'ils correspondent à vos besoins réels.`,
      },
    ],
  },
  {
    id: 'technique',
    icon: '🔧',
    title: 'Technique & compatibilité',
    color: '#6b7280',
    items: [
      {
        q: 'L\'application fonctionne-t-elle hors connexion ?',
        a: `Partiellement. L'interface, vos sélections et préférences sauvegardées localement sont accessibles hors ligne. En revanche, le chargement des recettes, les suggestions du Frigo et l'analyse nutritionnelle IA nécessitent une connexion internet pour interroger notre serveur. Une version PWA (Progressive Web App) avec cache avancé est envisagée pour une future version.`,
      },
      {
        q: 'Sur quels appareils ALIM est-il disponible ?',
        a: `ALIM est une application web responsive, accessible depuis n'importe quel navigateur moderne : Chrome, Firefox, Safari, Edge. Elle s'adapte aux smartphones, tablettes et ordinateurs. Pour une expérience optimale, nous recommandons Chrome ou Firefox à jour. L'interface mobile a été soigneusement optimisée avec un menu hamburger dédié.`,
      },
      {
        q: 'Pourquoi certaines recettes n\'ont pas d\'image ?',
        a: `Les images des recettes sont chargées depuis des URLs externes. Si une image n'est pas disponible (lien rompu, hébergeur inaccessible), ALIM affiche un placeholder avec un emoji représentatif de la catégorie de plat. Nous travaillons à enrichir notre base d'images pour assurer un affichage complet.`,
      },
      {
        q: 'Les données de mon navigateur sont-elles sécurisées ?',
        a: `Les données stockées dans le localStorage de votre navigateur sont accessibles uniquement au domaine ALIM — aucun autre site ne peut les lire. Elles ne sont pas chiffrées par défaut (c'est une limitation du navigateur), nous vous déconseillons donc d'utiliser ALIM sur un ordinateur partagé ou public pour des données sensibles. Sur votre appareil personnel, elles sont aussi sécurisées que votre navigateur lui-même.`,
      },
      {
        q: 'Comment signaler un bug ou suggérer une amélioration ?',
        a: `Nous sommes à l'écoute ! Vous pouvez nous contacter via la page Profil, section "Feedback". Décrivez le bug (étapes pour le reproduire, navigateur utilisé, capture d'écran si possible) ou votre suggestion d'amélioration. Chaque retour est lu et pris en compte dans notre feuille de route produit.`,
      },
    ],
  },
];

// ── Composant accordéon ───────────────────────────────────────────────────────

function FAQItem({ item, isOpen, onToggle, accentColor }) {
  return (
    <div
      className={`faq-item ${isOpen ? 'faq-item--open' : ''}`}
      style={{ '--faq-accent': accentColor }}
    >
      <button
        className="faq-question"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span className="faq-question-text">{item.q}</span>
        <span className="faq-chevron" aria-hidden="true">
          {isOpen ? '−' : '+'}
        </span>
      </button>
      {isOpen && (
        <div className="faq-answer">
          <p>{item.a}</p>
        </div>
      )}
    </div>
  );
}

// ── Section thématique ────────────────────────────────────────────────────────

function FAQSection({ section, openKey, setOpenKey }) {
  return (
    <div className="faq-section" id={`faq-${section.id}`}>
      <div className="faq-section-header">
        <span className="faq-section-icon" style={{ background: section.color + '18', color: section.color }}>
          {section.icon}
        </span>
        <h2 className="faq-section-title" style={{ color: section.color }}>{section.title}</h2>
        <span className="faq-section-count">{section.items.length} questions</span>
      </div>

      <div className="faq-items">
        {section.items.map((item, idx) => {
          const key = `${section.id}-${idx}`;
          return (
            <FAQItem
              key={key}
              item={item}
              isOpen={openKey === key}
              onToggle={() => setOpenKey(openKey === key ? null : key)}
              accentColor={section.color}
            />
          );
        })}
      </div>
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function FAQPage() {
  const [openKey, setOpenKey] = useState(() => {
    try { return localStorage.getItem(FAQ_KEY) || null; } catch { return null; }
  });
  const [query, setQuery] = useState('');
  const [activeSection, setActiveSection] = useState(null);

  // Persistance de l'item ouvert
  const handleOpen = (key) => {
    setOpenKey(key);
    try {
      if (key) localStorage.setItem(FAQ_KEY, key);
      else localStorage.removeItem(FAQ_KEY);
    } catch { /* ignore */ }
  };

  // Recherche live
  const q = query.toLowerCase().trim();
  const filteredSections = useMemo(() => {
    if (!q) {
      return activeSection
        ? FAQ_SECTIONS.filter(s => s.id === activeSection)
        : FAQ_SECTIONS;
    }
    return FAQ_SECTIONS
      .map(section => ({
        ...section,
        items: section.items.filter(item =>
          item.q.toLowerCase().includes(q) || item.a.toLowerCase().includes(q)
        ),
      }))
      .filter(s => s.items.length > 0);
  }, [q, activeSection]);

  const totalQuestions = FAQ_SECTIONS.reduce((n, s) => n + s.items.length, 0);
  const filteredCount  = filteredSections.reduce((n, s) => n + s.items.length, 0);

  return (
    <div className="faq-page">

      {/* En-tête héro */}
      <div className="faq-hero">
        <div className="faq-hero-inner">
          <div className="faq-hero-badge">❓ FAQ</div>
          <h1 className="faq-hero-title">Questions fréquentes</h1>
          <p className="faq-hero-sub">
            Tout ce que vous devez savoir sur ALIM — recettes, nutrition, planning, et bien-être.
          </p>

          {/* Barre de recherche */}
          <div className="faq-search-wrap">
            <span className="faq-search-icon" aria-hidden="true">🔍</span>
            <input
              type="search"
              className="faq-search"
              placeholder="Rechercher une question…"
              value={query}
              onChange={e => { setQuery(e.target.value); setActiveSection(null); }}
              aria-label="Rechercher dans la FAQ"
            />
            {query && (
              <button
                className="faq-search-clear"
                onClick={() => setQuery('')}
                aria-label="Effacer la recherche"
              >✕</button>
            )}
          </div>

          {/* Compteur résultats */}
          {q && (
            <p className="faq-search-count">
              {filteredCount === 0
                ? "Aucun résultat — essayez d'autres mots-clés"
                : `${filteredCount} résultat${filteredCount > 1 ? 's' : ''} sur ${totalQuestions}`}
            </p>
          )}
        </div>
      </div>

      <div className="faq-layout">

        {/* Sidebar navigation thèmes */}
        <aside className="faq-sidebar">
          <div className="faq-sidebar-inner">
            <p className="faq-sidebar-label">Thèmes</p>
            <button
              className={`faq-nav-btn ${!activeSection && !q ? 'faq-nav-btn--active' : ''}`}
              onClick={() => { setActiveSection(null); setQuery(''); }}
            >
              <span aria-hidden="true">📋</span> Tous les thèmes
              <span className="faq-nav-count">{totalQuestions}</span>
            </button>
            {FAQ_SECTIONS.map(s => (
              <button
                key={s.id}
                className={`faq-nav-btn ${activeSection === s.id && !q ? 'faq-nav-btn--active' : ''}`}
                style={activeSection === s.id && !q ? { borderColor: s.color, color: s.color } : {}}
                onClick={() => { setActiveSection(s.id); setQuery(''); setOpenKey(null); }}
              >
                <span aria-hidden="true">{s.icon}</span> {s.title}
                <span className="faq-nav-count">{s.items.length}</span>
              </button>
            ))}

            {/* CTA contact */}
            <div className="faq-sidebar-cta">
              <p className="faq-sidebar-cta-text">Vous n'avez pas trouvé la réponse ?</p>
              <button
                className="faq-sidebar-cta-btn"
                onClick={() => navigate('/profil')}
              >
                Nous contacter →
              </button>
            </div>
          </div>
        </aside>

        {/* Contenu principal */}
        <main className="faq-main">
          {filteredSections.length === 0 && (
            <div className="faq-empty">
              <span className="faq-empty-icon">🔍</span>
              <p className="faq-empty-title">Aucun résultat pour « {query} »</p>
              <p className="faq-empty-sub">Essayez d'autres mots-clés ou parcourez les thèmes ci-contre.</p>
              <button className="faq-empty-reset" onClick={() => setQuery('')}>
                Réinitialiser la recherche
              </button>
            </div>
          )}

          {filteredSections.map(section => (
            <FAQSection
              key={section.id}
              section={section}
              openKey={openKey}
              setOpenKey={handleOpen}
            />
          ))}

          {/* Bloc contact bas de page */}
          {!q && !activeSection && (
            <div className="faq-contact-block">
              <div className="faq-contact-icon">💬</div>
              <h3 className="faq-contact-title">Une question non répertoriée ?</h3>
              <p className="faq-contact-sub">
                Notre équipe est disponible pour répondre à toutes vos questions sur ALIM, la nutrition ou les données.
              </p>
              <div className="faq-contact-actions">
                <button className="faq-contact-btn faq-contact-btn--primary" onClick={() => navigate('/profil')}>
                  Contacter l'équipe
                </button>
                <button className="faq-contact-btn" onClick={() => navigate('/')}>
                  Explorer les recettes
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
