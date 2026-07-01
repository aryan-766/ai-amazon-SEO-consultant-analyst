import { create } from 'zustand';

export interface KeywordData {
  id: number;
  session_id: string;
  keyword: string;
  search_volume: number;
  cpr: number;
  position_bias_ctr: number;
  word_count: number;
  char_count: number;
  contains_number: boolean;
  contains_unit: boolean;
  contains_brand: boolean;
  contains_tech: boolean;
  brand_name: string | null;
  brand_type: string;
  product_type: string;
  tech_type: string | null;
  intent: string;
  buyer_stage: string;
  traffic_potential: number;
  ctr_potential: number;
  ranking_potential: number;
  commercial_potential: number;
  competitor_ranks: Record<string, number | null> | null;
  competitor_coverage: number;
  ranking_gap: boolean;
  topic_cluster: string | null;
  keyword_cluster_id: number | null;
  opportunity_score: number;
  revenue_score: number;
  competition_score: number;
  traffic_score: number;
  trend_score: number;
  gap_score: number;
  content_score: number;
  priority_score: number;
  business_score: number;
  seo_score: number;
  final_ai_score: number;
}

export interface ListingData {
  id?: number;
  session_id: string;
  title: string;
  bullet_points: string[];
  description: string;
  search_terms: string;
  aplus_content_ideas?: { section: string; concept: string }[];
  faq?: { question: string; answer: string }[];
  seo_score: number;
}

export interface AppState {
  sessionId: string | null;
  filename: string | null;
  sessionStatus: 'IDLE' | 'PENDING' | 'CLEANED' | 'ANALYZED' | 'ERROR';
  activeTab: 'dashboard' | 'explorer' | 'competitors' | 'optimizer' | 'chat' | 'reports' | 'settings';
  userBrand: string;
  competitors: string[];
  categories: string[];
  selectedKeyword: KeywordData | null;
  activeListing: ListingData | null;
  
  // Actions
  setSession: (sessionId: string | null, filename: string | null, status: AppState['sessionStatus']) => void;
  setSessionStatus: (status: AppState['sessionStatus']) => void;
  setActiveTab: (tab: AppState['activeTab']) => void;
  setUserBrand: (brand: string) => void;
  setCompetitors: (competitors: string[]) => void;
  setCategories: (categories: string[]) => void;
  setSelectedKeyword: (kw: KeywordData | null) => void;
  setActiveListing: (listing: ListingData | null) => void;
  resetSession: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  sessionId: null,
  filename: null,
  sessionStatus: 'IDLE',
  activeTab: 'dashboard',
  userBrand: '',
  competitors: [],
  categories: [],
  selectedKeyword: null,
  activeListing: null,

  setSession: (sessionId, filename, status) => set({ sessionId, filename, sessionStatus: status }),
  setSessionStatus: (status) => set({ sessionStatus: status }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setUserBrand: (userBrand) => set({ userBrand }),
  setCompetitors: (competitors) => set({ competitors }),
  setCategories: (categories) => set({ categories }),
  setSelectedKeyword: (selectedKeyword) => set({ selectedKeyword }),
  setActiveListing: (activeListing) => set({ activeListing }),
  resetSession: () => set({
    sessionId: null,
    filename: null,
    sessionStatus: 'IDLE',
    activeTab: 'dashboard',
    userBrand: '',
    competitors: [],
    categories: [],
    selectedKeyword: null,
    activeListing: null
  })
}));
