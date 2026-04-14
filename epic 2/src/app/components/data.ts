export interface ThreatenedSpecies {
  name: string;
  type: 'mammal' | 'bird' | 'reptile' | 'amphibian' | 'plant' | 'insect';
  status: 'critically_endangered' | 'endangered' | 'vulnerable';
}

export interface Supplier {
  id: string;
  name: string;
  region: string;
  lat: number;
  lng: number;
  riskScore: number; // 0-100
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  protectedAreaOverlap: number; // percentage
  threatenedSpeciesCount: number;
  vegetationCondition: number; // 0-100
  deforestationRate: number; // % per year
  waterStressIndex: number; // 0-100
  carbonStock: number; // tonnes/ha
  lastAssessment: string;
  industry: string;
  threatenedSpecies: ThreatenedSpecies[];
  notes: string;
}

export const suppliers: Supplier[] = [
  {
    id: 'SUP-001',
    name: 'Daintree Timber Co.',
    region: 'Far North Queensland',
    lat: -16.25,
    lng: 145.42,
    riskScore: 87,
    riskLevel: 'critical',
    protectedAreaOverlap: 42,
    threatenedSpeciesCount: 34,
    vegetationCondition: 28,
    deforestationRate: 2.4,
    waterStressIndex: 31,
    carbonStock: 285,
    lastAssessment: '2026-03-12',
    industry: 'Forestry & Logging',
    threatenedSpecies: [
      { name: 'Southern Cassowary', type: 'bird', status: 'endangered' },
      { name: 'Bennett\'s Tree-kangaroo', type: 'mammal', status: 'endangered' },
      { name: 'Spotted-tailed Quoll', type: 'mammal', status: 'vulnerable' },
      { name: 'Daintree River Ringtail Possum', type: 'mammal', status: 'critically_endangered' },
    ],
    notes: 'Adjacent to Daintree National Park. High overlap with World Heritage Area.',
  },
  {
    id: 'SUP-002',
    name: 'Kimberley Pastoral Ltd.',
    region: 'Kimberley, WA',
    lat: -15.77,
    lng: 128.74,
    riskScore: 72,
    riskLevel: 'high',
    protectedAreaOverlap: 28,
    threatenedSpeciesCount: 19,
    vegetationCondition: 45,
    deforestationRate: 1.8,
    waterStressIndex: 68,
    carbonStock: 142,
    lastAssessment: '2026-02-28',
    industry: 'Pastoral & Grazing',
    threatenedSpecies: [
      { name: 'Northern Quoll', type: 'mammal', status: 'endangered' },
      { name: 'Gouldian Finch', type: 'bird', status: 'endangered' },
      { name: 'Freshwater Sawfish', type: 'reptile', status: 'vulnerable' },
    ],
    notes: 'Operations near Mitchell River National Park. Seasonal flooding impacts.',
  },
  {
    id: 'SUP-003',
    name: 'Tarkine Minerals Pty.',
    region: 'North-West Tasmania',
    lat: -41.75,
    lng: 145.25,
    riskScore: 64,
    riskLevel: 'high',
    protectedAreaOverlap: 35,
    threatenedSpeciesCount: 22,
    vegetationCondition: 52,
    deforestationRate: 0.9,
    waterStressIndex: 18,
    carbonStock: 320,
    lastAssessment: '2026-03-05',
    industry: 'Mining & Extraction',
    threatenedSpecies: [
      { name: 'Tasmanian Devil', type: 'mammal', status: 'endangered' },
      { name: 'Giant Freshwater Crayfish', type: 'insect', status: 'vulnerable' },
      { name: 'Wedge-tailed Eagle (Tas.)', type: 'bird', status: 'endangered' },
    ],
    notes: 'Tarkine rainforest — one of the largest temperate rainforests globally.',
  },
  {
    id: 'SUP-004',
    name: 'Murray Basin Agri.',
    region: 'Murray-Darling Basin, NSW',
    lat: -34.75,
    lng: 143.92,
    riskScore: 51,
    riskLevel: 'medium',
    protectedAreaOverlap: 12,
    threatenedSpeciesCount: 11,
    vegetationCondition: 61,
    deforestationRate: 0.5,
    waterStressIndex: 82,
    carbonStock: 45,
    lastAssessment: '2026-01-18',
    industry: 'Agriculture',
    threatenedSpecies: [
      { name: 'Plains-wanderer', type: 'bird', status: 'critically_endangered' },
      { name: 'Murray Cod', type: 'reptile', status: 'vulnerable' },
    ],
    notes: 'Extreme water stress. Irrigation dependent operations.',
  },
  {
    id: 'SUP-005',
    name: 'Great Southern Plantation',
    region: 'Gippsland, VIC',
    lat: -37.82,
    lng: 147.61,
    riskScore: 38,
    riskLevel: 'medium',
    protectedAreaOverlap: 8,
    threatenedSpeciesCount: 9,
    vegetationCondition: 72,
    deforestationRate: 0.3,
    waterStressIndex: 35,
    carbonStock: 198,
    lastAssessment: '2026-02-10',
    industry: 'Plantation Forestry',
    threatenedSpecies: [
      { name: 'Leadbeater\'s Possum', type: 'mammal', status: 'critically_endangered' },
      { name: 'Long-footed Potoroo', type: 'mammal', status: 'endangered' },
    ],
    notes: 'Buffer zones maintained. Active rehabilitation programs.',
  },
  {
    id: 'SUP-006',
    name: 'Cape York Resources',
    region: 'Cape York, QLD',
    lat: -14.45,
    lng: 143.85,
    riskScore: 79,
    riskLevel: 'high',
    protectedAreaOverlap: 38,
    threatenedSpeciesCount: 27,
    vegetationCondition: 39,
    deforestationRate: 2.1,
    waterStressIndex: 25,
    carbonStock: 210,
    lastAssessment: '2026-03-01',
    industry: 'Mining & Extraction',
    threatenedSpecies: [
      { name: 'Palm Cockatoo', type: 'bird', status: 'vulnerable' },
      { name: 'Golden-shouldered Parrot', type: 'bird', status: 'endangered' },
      { name: 'Northern Bettong', type: 'mammal', status: 'endangered' },
    ],
    notes: 'Overlaps with Indigenous Protected Areas. Wet season access limitations.',
  },
  {
    id: 'SUP-007',
    name: 'Adelaide Hills Organics',
    region: 'Adelaide Hills, SA',
    lat: -35.02,
    lng: 138.72,
    riskScore: 22,
    riskLevel: 'low',
    protectedAreaOverlap: 3,
    threatenedSpeciesCount: 5,
    vegetationCondition: 85,
    deforestationRate: 0.1,
    waterStressIndex: 45,
    carbonStock: 95,
    lastAssessment: '2026-03-10',
    industry: 'Agriculture',
    threatenedSpecies: [
      { name: 'Yellow-footed Rock-wallaby', type: 'mammal', status: 'vulnerable' },
    ],
    notes: 'Certified organic. Strong biodiversity management plan.',
  },
  {
    id: 'SUP-008',
    name: 'Pilbara Iron Works',
    region: 'Pilbara, WA',
    lat: -22.31,
    lng: 118.35,
    riskScore: 58,
    riskLevel: 'medium',
    protectedAreaOverlap: 15,
    threatenedSpeciesCount: 13,
    vegetationCondition: 55,
    deforestationRate: 0.7,
    waterStressIndex: 91,
    carbonStock: 32,
    lastAssessment: '2026-02-22',
    industry: 'Mining & Extraction',
    threatenedSpecies: [
      { name: 'Pilbara Olive Python', type: 'reptile', status: 'vulnerable' },
      { name: 'Ghost Bat', type: 'mammal', status: 'vulnerable' },
      { name: 'Northern Quoll', type: 'mammal', status: 'endangered' },
    ],
    notes: 'Extreme water stress region. Mine site rehabilitation in progress.',
  },
];

export function getRiskColor(level: string) {
  switch (level) {
    case 'critical': return { bg: 'bg-rust-600', text: 'text-rust-700', light: 'bg-rust-50', border: 'border-rust-200', dot: '#dc2626' };
    case 'high': return { bg: 'bg-amber-600', text: 'text-amber-700', light: 'bg-amber-50', border: 'border-amber-200', dot: '#d97706' };
    case 'medium': return { bg: 'bg-[#e8a915]', text: 'text-[#a67c00]', light: 'bg-[#fdf6e3]', border: 'border-[#f0d78c]', dot: '#c99a00' };
    case 'low': return { bg: 'bg-forest-400', text: 'text-forest-700', light: 'bg-forest-50', border: 'border-forest-200', dot: '#67a383' };
    default: return { bg: 'bg-earth-500', text: 'text-earth-700', light: 'bg-earth-50', border: 'border-earth-200', dot: '#9b8a72' };
  }
}

export function getStatusLabel(status: string) {
  return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export function getSpeciesIcon(type: string) {
  switch (type) {
    case 'mammal': return '🦘';
    case 'bird': return '🦜';
    case 'reptile': return '🐊';
    case 'amphibian': return '🐸';
    case 'plant': return '🌿';
    case 'insect': return '🦀';
    default: return '🔬';
  }
}
