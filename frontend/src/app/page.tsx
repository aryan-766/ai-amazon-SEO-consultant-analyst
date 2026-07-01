'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAppStore, KeywordData, ListingData } from '@/store/useAppStore';
import api from '@/lib/api';
import {
  LayoutDashboard,
  TableProperties,
  ShieldAlert,
  FileEdit,
  MessageSquareText,
  FileSpreadsheet,
  Settings as SettingsIcon,
  Upload,
  ArrowRight,
  RefreshCw,
  Search,
  Filter,
  CheckCircle,
  XCircle,
  Download,
  Send,
  Sparkles,
  Info,
  ChevronRight,
  TrendingUp,
  Award,
  AlertTriangle
} from 'lucide-react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  LineChart,
  Line,
  CartesianGrid
} from 'recharts';

export default function WorkspacePage() {
  const queryClient = useQueryClient();
  
  // App store states
  const {
    sessionId,
    filename,
    sessionStatus,
    activeTab,
    userBrand,
    competitors,
    selectedKeyword,
    activeListing,
    setSession,
    setSessionStatus,
    setActiveTab,
    setUserBrand,
    setCompetitors,
    setCategories,
    setSelectedKeyword,
    setActiveListing,
    resetSession
  } = useAppStore();

  // Local UI States
  const [file, setFile] = useState<File | null>(null);
  const [brandInput, setBrandInput] = useState('');
  const [competitorsInput, setCompetitorsInput] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Listing local state
  const [listingTitle, setListingTitle] = useState('');
  const [listingBullets, setListingBullets] = useState<string[]>(['', '', '', '', '']);
  const [listingDesc, setListingDesc] = useState('');
  const [listingTerms, setListingTerms] = useState('');

  // Search & Filter local state for Keyword Explorer
  const [keywordSearch, setKeywordSearch] = useState('');
  const [intentFilter, setIntentFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortBy, setSortBy] = useState('opportunity_score');
  const [sortDesc, setSortDesc] = useState(true);
  const [kwPage, setKwPage] = useState(0);
  const itemsPerPage = 15;

  // Chat local state
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<{ role: string; content: string }[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Settings State
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [ollamaModel, setOllamaModel] = useState('qwen2.5:7b');

  // Trigger scroll to bottom on new chat messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Mutations
  const uploadMutation = useMutation({
    mutationFn: (uploadedFile: File) => api.uploadDataset(uploadedFile),
    onSuccess: (data) => {
      setSession(data.id, data.filename, 'CLEANED');
      // Extract automatically identified competitors/columns
      const meta = data.summary_metadata || {};
      const foundComps = meta.competitors || [];
      setCompetitors(foundComps);
      setCompetitorsInput(foundComps.join(', '));
      setErrorMsg(null);
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.detail || 'Failed to upload. Please check file format.');
    }
  });

  const analyzeMutation = useMutation({
    mutationFn: () => {
      const compsList = competitorsInput.split(',').map(c => c.trim()).filter(Boolean);
      return api.analyzeDataset(sessionId!, brandInput, compsList);
    },
    onMutate: () => {
      setSessionStatus('PENDING');
      setErrorMsg(null);
    },
    onSuccess: () => {
      setSessionStatus('ANALYZED');
      // Set default user brand
      setUserBrand(brandInput);
      const compsList = competitorsInput.split(',').map(c => c.trim()).filter(Boolean);
      setCompetitors(compsList);
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: ['dashboard', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['keywords', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['competitors', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['categories', sessionId] });
    },
    onError: (err: any) => {
      setSessionStatus('CLEANED');
      setErrorMsg(err.response?.data?.detail || 'Analysis execution failed.');
    }
  });

  // Queries
  const { data: dashboardData, isLoading: isDashLoading } = useQuery({
    queryKey: ['dashboard', sessionId, sessionStatus],
    queryFn: () => api.getDashboard(sessionId!),
    enabled: !!sessionId && sessionStatus === 'ANALYZED',
  });

  const { data: keywordsData, isLoading: isKwLoading } = useQuery({
    queryKey: [
      'keywords',
      sessionId,
      sessionStatus,
      keywordSearch,
      intentFilter,
      categoryFilter,
      sortBy,
      sortDesc,
      kwPage
    ],
    queryFn: () =>
      api.getKeywords(sessionId!, {
        search: keywordSearch,
        intent: intentFilter,
        category: categoryFilter,
        sort_by: sortBy,
        sort_desc: sortDesc,
        limit: itemsPerPage,
        offset: kwPage * itemsPerPage,
      }),
    enabled: !!sessionId && sessionStatus === 'ANALYZED',
  });

  const { data: competitorData } = useQuery({
    queryKey: ['competitors', sessionId, sessionStatus],
    queryFn: () => api.getCompetitors(sessionId!),
    enabled: !!sessionId && sessionStatus === 'ANALYZED',
  });

  const { data: categoryData } = useQuery({
    queryKey: ['categories', sessionId, sessionStatus],
    queryFn: () => api.getCategories(sessionId!),
    enabled: !!sessionId && sessionStatus === 'ANALYZED',
  });

  // Save list of categories to appStore when loaded
  useEffect(() => {
    if (categoryData?.categories) {
      setCategories(categoryData.categories);
    }
  }, [categoryData, setCategories]);

  // Live Listing Optimizer score check query
  const { data: listingAnalysis, refetch: reanalyzeListing } = useQuery({
    queryKey: ['listingAnalysis', sessionId, listingTitle, listingBullets, listingDesc, listingTerms],
    queryFn: () =>
      api.analyzeListing(
        sessionId!,
        listingTitle,
        listingBullets.filter(Boolean),
        listingDesc,
        listingTerms
      ),
    enabled: !!sessionId && sessionStatus === 'ANALYZED' && (!!listingTitle || !!listingDesc),
  });

  const generateListingMutation = useMutation({
    mutationFn: () => {
      // Pull top 5 keywords for generation
      const targetKws = keywordsData?.keywords?.slice(0, 5).map(k => k.keyword) || [];
      return api.generateListing(sessionId!, targetKws);
    },
    onSuccess: (data) => {
      setActiveListing(data);
      setListingTitle(data.title || '');
      setListingBullets(data.bullet_points || ['', '', '', '', '']);
      setListingDesc(data.description || '');
      setListingTerms(data.search_terms || '');
      setSuccessMsg('SEO Copy successfully generated by local Copilot!');
      setTimeout(() => setSuccessMsg(null), 3000);
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.detail || 'Listing writer failed.');
    }
  });

  const chatMutation = useMutation({
    mutationFn: (message: string) => api.chatCopilot(sessionId!, message),
    onSuccess: (data) => {
      // Replace message list with database history
      const formattedHistory = data.history.map((m: any) => ({
        role: m.role,
        content: m.content
      }));
      setChatMessages(formattedHistory);
    },
    onError: (err: any) => {
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Connection error. Please ensure FastAPI and Ollama are online.' }
      ]);
    }
  });

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      setFile(droppedFile);
      uploadMutation.mutate(droppedFile);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      uploadMutation.mutate(selectedFile);
    }
  };

  const handleSendChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    
    const userQuery = chatInput;
    setChatMessages(prev => [...prev, { role: 'user', content: userQuery }]);
    setChatInput('');
    
    // Call mutation
    chatMutation.mutate(userQuery);
  };

  const handlePresetChat = (query: string) => {
    setChatMessages(prev => [...prev, { role: 'user', content: query }]);
    chatMutation.mutate(query);
  };

  const downloadReport = async (format: 'xlsx' | 'pdf') => {
    try {
      const data = await api.exportData(sessionId!, format);
      const url = window.URL.createObjectURL(new Blob([data]));
      const link = document.createElement('a');
      link.href = url;
      const fileLabel = format === 'xlsx' ? 'Keyword_Spreadsheet.xlsx' : 'Executive_Summary_Report.pdf';
      link.setAttribute('download', `${filename?.split('.')[0]}_${fileLabel}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setErrorMsg('Failed to export. Please check analysis states.');
    }
  };

  // Recharts custom colors
  const COLORS = ['#8b5cf6', '#6366f1', '#ec4899', '#3b82f6', '#10b981', '#f59e0b'];

  return (
    <div className="flex h-screen bg-bg-deep font-sans overflow-hidden">
      
      {/* ================= SIDEBAR NAVIGATION ================= */}
      {sessionId && (
        <aside className="w-64 glass-panel border-r border-card-border flex flex-col justify-between shrink-0">
          <div>
            {/* Brand Header */}
            <div className="p-6 flex items-center space-x-3 border-b border-card-border">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-brand-primary to-brand-secondary flex items-center justify-center glow-glow">
                <Sparkles className="h-5 w-5 text-white animate-pulse" />
              </div>
              <div>
                <h1 className="font-bold text-sm tracking-wide text-white">SEO COPILOT</h1>
                <span className="text-[10px] text-gray-400 font-semibold tracking-wider uppercase">AMAZON ACCELERATOR</span>
              </div>
            </div>

            {/* Nav Menu */}
            <nav className="p-4 space-y-1.5">
              {[
                { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, disabled: sessionStatus !== 'ANALYZED' },
                { id: 'explorer', label: 'Keyword Explorer', icon: TableProperties, disabled: sessionStatus !== 'ANALYZED' },
                { id: 'competitors', label: 'Competitor Gaps', icon: ShieldAlert, disabled: sessionStatus !== 'ANALYZED' },
                { id: 'optimizer', label: 'Listing Optimizer', icon: FileEdit, disabled: sessionStatus !== 'ANALYZED' },
                { id: 'chat', label: 'AI Copilot Chat', icon: MessageSquareText, disabled: sessionStatus !== 'ANALYZED' },
                { id: 'reports', label: 'Export Reports', icon: FileSpreadsheet, disabled: sessionStatus !== 'ANALYZED' },
                { id: 'settings', label: 'App Settings', icon: SettingsIcon, disabled: false },
              ].map((item) => {
                const IconComponent = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    disabled={item.disabled}
                    onClick={() => setActiveTab(item.id as any)}
                    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-gradient-to-r from-brand-primary/20 to-brand-secondary/20 border border-brand-secondary/30 text-white shadow-md'
                        : item.disabled
                        ? 'text-gray-600 cursor-not-allowed'
                        : 'text-gray-400 hover:bg-white/5 hover:text-white'
                    }`}
                  >
                    <IconComponent className={`h-4.5 w-4.5 ${isActive ? 'text-brand-primary' : 'text-current'}`} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Active File / Reset */}
          <div className="p-4 border-t border-card-border bg-black/20">
            <div className="flex flex-col space-y-2">
              <span className="text-[11px] text-gray-400 font-semibold uppercase">Active Dataset</span>
              <p className="text-xs text-gray-200 truncate font-mono">{filename}</p>
              <button
                onClick={resetSession}
                className="w-full text-center text-xs text-brand-secondary hover:text-white font-medium hover:underline py-1"
              >
                Reset & Upload New
              </button>
            </div>
          </div>
        </aside>
      )}

      {/* ================= MAIN CONTAINER ================= */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto relative">
        
        {/* Alerts / Error messages */}
        {errorMsg && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-300 px-6 py-3 text-sm flex items-center space-x-3 shrink-0">
            <XCircle className="h-5 w-5 text-red-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 px-6 py-3 text-sm flex items-center space-x-3 shrink-0">
            <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* ================= 1. LANDING & UPLOAD VIEW ================= */}
        {!sessionId && (
          <div className="flex-1 flex items-center justify-center p-8 bg-gradient-to-b from-bg-deep to-black/30">
            <div className="max-w-2xl w-full flex flex-col space-y-8">
              {/* Headline */}
              <div className="text-center space-y-3">
                <div className="inline-flex h-14 w-14 rounded-2xl bg-gradient-to-tr from-brand-primary to-brand-secondary items-center justify-center glow-glow mb-2">
                  <Sparkles className="h-7 w-7 text-white" />
                </div>
                <h2 className="text-4xl font-extrabold tracking-tight text-white">Amazon SEO Copilot</h2>
                <p className="text-gray-400 text-lg max-w-md mx-auto">
                  Extract deep opportunity scores, semantic clusters, and optimize listings using local LLM intelligence.
                </p>
              </div>

              {/* Upload Dropzone */}
              <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                className={`glass-panel border-2 border-dashed rounded-2xl p-12 text-center transition-all ${
                  dragActive ? 'border-brand-primary bg-brand-primary/5' : 'border-card-border hover:border-brand-secondary/40'
                }`}
              >
                <input
                  type="file"
                  id="file-upload-input"
                  className="hidden"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileChange}
                />
                
                {uploadMutation.isPending ? (
                  <div className="space-y-4">
                    <RefreshCw className="h-10 w-10 text-brand-primary animate-spin mx-auto" />
                    <p className="text-gray-300 font-medium">Reading and validating competitor datasets...</p>
                  </div>
                ) : (
                  <label htmlFor="file-upload-input" className="cursor-pointer space-y-4 flex flex-col items-center">
                    <div className="h-12 w-12 rounded-full bg-white/5 flex items-center justify-center">
                      <Upload className="h-6 w-6 text-gray-400" />
                    </div>
                    <div>
                      <p className="text-white font-semibold text-lg">Upload competitor keyword dataset</p>
                      <p className="text-gray-400 text-sm mt-1">Support Helium 10, Semrush or standard Excel/CSV sheets</p>
                    </div>
                    <button className="bg-brand-primary hover:bg-brand-primary/95 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-all shadow-lg shadow-brand-primary/20">
                      Select File
                    </button>
                  </label>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ================= 2. CONFIGURATION / CLEANED VIEW ================= */}
        {sessionId && sessionStatus === 'CLEANED' && (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="max-w-md w-full glass-panel rounded-2xl p-8 space-y-6">
              <div className="space-y-2">
                <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-sm">
                  <CheckCircle className="h-4 w-4" />
                  <span>File Parsed Successfully</span>
                </div>
                <h3 className="text-2xl font-bold text-white">Configure Analysis Parameters</h3>
                <p className="text-xs text-gray-400 leading-relaxed">
                  Map brand configurations so we can flag generic keywords, detect branded searches, and compute listing opportunities.
                </p>
              </div>

              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold uppercase text-gray-400">Your Brand Name</label>
                  <input
                    type="text"
                    value={brandInput}
                    onChange={(e) => setBrandInput(e.target.value)}
                    placeholder="e.g. Ambrane"
                    className="w-full bg-black/30 border border-card-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-primary text-white"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold uppercase text-gray-400">Competitors (Comma-separated)</label>
                  <input
                    type="text"
                    value={competitorsInput}
                    onChange={(e) => setCompetitorsInput(e.target.value)}
                    placeholder="e.g. Anker, Boat, Belkin"
                    className="w-full bg-black/30 border border-card-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-primary text-white"
                  />
                  <p className="text-[10px] text-gray-500">We auto-detected: {competitors.join(', ') || 'None'}</p>
                </div>

                <button
                  disabled={!brandInput.trim() || analyzeMutation.isPending}
                  onClick={() => analyzeMutation.mutate()}
                  className="w-full bg-gradient-to-r from-brand-primary to-brand-secondary hover:opacity-90 disabled:opacity-40 text-white font-bold py-3.5 rounded-xl transition-all flex items-center justify-center space-x-2 text-sm shadow-xl shadow-brand-primary/10"
                >
                  <span>Run NLP & Feature Engineering</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Loading overlay for Running analysis */}
        {sessionId && sessionStatus === 'PENDING' && (
          <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-6">
            <div className="relative flex items-center justify-center h-20 w-20">
              <div className="absolute inset-0 rounded-full border-4 border-brand-primary/20 border-t-brand-primary animate-spin" />
              <Sparkles className="h-8 w-8 text-brand-secondary animate-pulse" />
            </div>
            <div className="text-center space-y-2">
              <h4 className="text-xl font-bold text-white">Running Strategic SEO Pipeline</h4>
              <p className="text-gray-400 text-sm max-w-sm">
                Normalizing spelling, classifying keyword intents, clustering semantics, and computing opportunity metrics...
              </p>
            </div>
          </div>
        )}

        {/* ================= 3. CORE APPLICATIONS WORKSPACE ================= */}
        {sessionId && sessionStatus === 'ANALYZED' && (
          <div className="p-8 space-y-8 flex-1">
            
            {/* Header bar */}
            <header className="flex justify-between items-start shrink-0">
              <div>
                <span className="text-[11px] text-brand-primary font-bold uppercase tracking-wider">WORKSPACE MANAGER</span>
                <h2 className="text-3xl font-extrabold text-white">Amazon Competitor Keyword Intelligence</h2>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => downloadReport('xlsx')}
                  className="glass-panel hover:bg-white/5 border border-card-border text-gray-300 font-semibold px-4 py-2 rounded-xl text-sm transition-all flex items-center space-x-2"
                >
                  <Download className="h-4 w-4" />
                  <span>Download Excel</span>
                </button>
                <button
                  onClick={() => downloadReport('pdf')}
                  className="bg-brand-primary hover:bg-brand-primary/90 text-white font-bold px-4 py-2 rounded-xl text-sm transition-all flex items-center space-x-2 shadow-lg shadow-brand-primary/15"
                >
                  <Download className="h-4 w-4" />
                  <span>Download PDF</span>
                </button>
              </div>
            </header>

            {/* ================= TAB CONTENT 1: DASHBOARD ================= */}
            {activeTab === 'dashboard' && dashboardData && (
              <div className="space-y-8">
                
                {/* KPI metrics cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-5">
                  {[
                    { label: 'Keywords Indexed', val: dashboardData.kpis.total_keywords.toLocaleString(), icon: TableProperties, color: 'from-blue-500/20 to-indigo-500/10' },
                    { label: 'Total Categories', val: dashboardData.kpis.total_categories, icon: LayoutDashboard, color: 'from-violet-500/20 to-purple-500/10' },
                    { label: 'Competitors Tracked', val: dashboardData.kpis.total_competitors, icon: ShieldAlert, color: 'from-pink-500/20 to-rose-500/10' },
                    { label: 'Easy Wins', val: dashboardData.kpis.easy_wins, icon: Award, color: 'from-emerald-500/20 to-teal-500/10' },
                    { label: 'High Opp Keywords', val: dashboardData.kpis.high_opportunity_keywords, icon: TrendingUp, color: 'from-amber-500/20 to-yellow-500/10' },
                    { label: 'Search Volume Vol.', val: dashboardData.kpis.total_search_volume.toLocaleString(), icon: Sparkles, color: 'from-cyan-500/20 to-sky-500/10' }
                  ].map((card, i) => {
                    const CardIcon = card.icon;
                    return (
                      <div key={i} className={`glass-panel bg-gradient-to-br ${card.color} rounded-xl p-5 border border-card-border/60 hover:scale-[1.02] transition-all`}>
                        <div className="flex justify-between items-start">
                          <span className="text-[11px] text-gray-400 font-bold uppercase">{card.label}</span>
                          <CardIcon className="h-4 w-4 text-gray-400" />
                        </div>
                        <p className="text-2xl font-black text-white mt-2 tracking-tight">{card.val}</p>
                      </div>
                    );
                  })}
                </div>

                {/* Charts Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Category Distribution */}
                  <div className="glass-panel rounded-2xl p-6 flex flex-col h-96">
                    <h3 className="text-lg font-bold text-white mb-4">Category Distribution</h3>
                    <div className="flex-1 min-h-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={dashboardData.category_distribution}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="name" stroke="#888" fontSize={11} />
                          <YAxis stroke="#888" fontSize={11} />
                          <Tooltip contentStyle={{ background: '#111928', borderColor: 'rgba(255,255,255,0.1)' }} />
                          <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]}>
                            {dashboardData.category_distribution.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Intent Distribution */}
                  <div className="glass-panel rounded-2xl p-6 flex flex-col h-96">
                    <h3 className="text-lg font-bold text-white mb-4">Keyword Intent Share</h3>
                    <div className="flex-1 min-h-0 flex items-center justify-center">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={dashboardData.intent_distribution}
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                          >
                            {dashboardData.intent_distribution.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip contentStyle={{ background: '#111928', borderColor: 'rgba(255,255,255,0.1)' }} />
                          <Legend verticalAlign="bottom" height={36} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Share of Voice by Competitor */}
                  <div className="glass-panel rounded-2xl p-6 flex flex-col h-96">
                    <h3 className="text-lg font-bold text-white mb-4">Competitor Organic Share of Voice (SOV)</h3>
                    <div className="flex-1 min-h-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={dashboardData.competitor_comparison}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="name" stroke="#888" fontSize={11} />
                          <YAxis stroke="#888" fontSize={11} />
                          <Tooltip contentStyle={{ background: '#111928', borderColor: 'rgba(255,255,255,0.1)' }} />
                          <Bar dataKey="top_10_count" name="Top 10 Keywords Count" fill="#ec4899" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="top_30_count" name="Top 30 Keywords Count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Buyer Journey Stage */}
                  <div className="glass-panel rounded-2xl p-6 flex flex-col h-96">
                    <h3 className="text-lg font-bold text-white mb-4">Buyer Stage Keywords Volume</h3>
                    <div className="flex-1 min-h-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={dashboardData.buyer_journey}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="name" stroke="#888" fontSize={11} />
                          <YAxis stroke="#888" fontSize={11} />
                          <Tooltip contentStyle={{ background: '#111928', borderColor: 'rgba(255,255,255,0.1)' }} />
                          <Line type="monotone" dataKey="value" name="Keywords Count" stroke="#8b5cf6" strokeWidth={3} dot={{ fill: '#8b5cf6', r: 4 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

              </div>
            )}

            {/* ================= TAB CONTENT 2: KEYWORD EXPLORER ================= */}
            {activeTab === 'explorer' && (
              <div className="space-y-6">
                
                {/* Search / Filters Bar */}
                <div className="glass-panel rounded-2xl p-5 flex flex-col md:flex-row gap-4 items-center justify-between">
                  <div className="relative w-full md:w-80 shrink-0">
                    <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-gray-500" />
                    <input
                      type="text"
                      placeholder="Search keywords..."
                      value={keywordSearch}
                      onChange={(e) => { setKeywordSearch(e.target.value); setKwPage(0); }}
                      className="w-full bg-black/20 border border-card-border rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-brand-primary text-white"
                    />
                  </div>

                  <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-end">
                    {/* Category Filter */}
                    <div className="relative">
                      <select
                        value={categoryFilter}
                        onChange={(e) => { setCategoryFilter(e.target.value); setKwPage(0); }}
                        className="bg-black/20 border border-card-border rounded-xl px-4 py-2.5 text-sm focus:outline-none text-white cursor-pointer"
                      >
                        <option value="">All Categories</option>
                        {categories.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </div>

                    {/* Intent Filter */}
                    <div className="relative">
                      <select
                        value={intentFilter}
                        onChange={(e) => { setIntentFilter(e.target.value); setKwPage(0); }}
                        className="bg-black/20 border border-card-border rounded-xl px-4 py-2.5 text-sm focus:outline-none text-white cursor-pointer"
                      >
                        <option value="">All Intents</option>
                        <option value="Transactional">Transactional</option>
                        <option value="Commercial">Commercial</option>
                        <option value="Informational">Informational</option>
                        <option value="Comparison">Comparison</option>
                        <option value="Review">Review</option>
                        <option value="Navigational">Navigational</option>
                      </select>
                    </div>

                    {/* Sort Selector */}
                    <div className="relative">
                      <select
                        value={`${sortBy}:${sortDesc}`}
                        onChange={(e) => {
                          const [field, desc] = e.target.value.split(':');
                          setSortBy(field);
                          setSortDesc(desc === 'true');
                          setKwPage(0);
                        }}
                        className="bg-black/20 border border-card-border rounded-xl px-4 py-2.5 text-sm focus:outline-none text-white cursor-pointer"
                      >
                        <option value="opportunity_score:true">Opportunity: High to Low</option>
                        <option value="opportunity_score:false">Opportunity: Low to High</option>
                        <option value="search_volume:true">Volume: High to Low</option>
                        <option value="cpr:true">Competition (CPR): High to Low</option>
                        <option value="cpr:false">Competition (CPR): Low to High</option>
                        <option value="final_ai_score:true">Final Score: High to Low</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Keywords Table Container */}
                <div className="glass-panel rounded-2xl overflow-hidden">
                  {isKwLoading ? (
                    <div className="p-12 text-center space-y-4">
                      <RefreshCw className="h-8 w-8 text-brand-primary animate-spin mx-auto" />
                      <p className="text-gray-400 text-sm">Querying database...</p>
                    </div>
                  ) : (
                    <table className="w-full border-collapse text-left">
                      <thead>
                        <tr className="border-b border-card-border bg-black/10">
                          <th className="p-4 text-xs font-bold uppercase text-gray-400">Keyword</th>
                          <th className="p-4 text-xs font-bold uppercase text-gray-400 text-right">Search Volume</th>
                          <th className="p-4 text-xs font-bold uppercase text-gray-400 text-right">CPR</th>
                          <th className="p-4 text-xs font-bold uppercase text-gray-400 text-right">Opportunity</th>
                          <th className="p-4 text-xs font-bold uppercase text-gray-400 text-right">Competition</th>
                          <th className="p-4 text-xs font-bold uppercase text-gray-400">Search Intent</th>
                          <th className="p-4 text-xs font-bold uppercase text-gray-400">Category</th>
                          <th className="p-4 text-xs font-bold uppercase text-gray-400">Semantic Cluster</th>
                          <th className="p-4 text-xs font-bold uppercase text-gray-400 text-right">AI Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {keywordsData?.keywords?.map((kw: KeywordData) => (
                          <tr
                            key={kw.id}
                            onClick={() => setSelectedKeyword(kw)}
                            className="border-b border-card-border/50 hover:bg-white/2 cursor-pointer transition-colors"
                          >
                            <td className="p-4 text-sm font-semibold text-white truncate max-w-[200px]">{kw.keyword}</td>
                            <td className="p-4 text-sm text-gray-200 text-right font-mono">{kw.search_volume.toLocaleString()}</td>
                            <td className="p-4 text-sm text-gray-300 text-right font-mono">{kw.cpr.toLocaleString()}</td>
                            <td className="p-4 text-sm text-right">
                              <span className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${
                                kw.opportunity_score >= 70 ? 'bg-emerald-500/10 text-emerald-400' :
                                kw.opportunity_score >= 40 ? 'bg-amber-500/10 text-amber-400' :
                                'bg-red-500/10 text-red-400'
                              }`}>
                                {kw.opportunity_score.toFixed(0)}
                              </span>
                            </td>
                            <td className="p-4 text-sm text-right">
                              <span className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${
                                kw.competition_score >= 75 ? 'bg-red-500/10 text-red-400' :
                                kw.competition_score >= 40 ? 'bg-amber-500/10 text-amber-400' :
                                'bg-emerald-500/10 text-emerald-400'
                              }`}>
                                {kw.competition_score.toFixed(0)}
                              </span>
                            </td>
                            <td className="p-4 text-xs font-medium">
                              <span className={`px-2 py-0.5 rounded ${
                                kw.intent === 'Transactional' ? 'bg-purple-500/10 text-purple-400' :
                                kw.intent === 'Commercial' ? 'bg-blue-500/10 text-blue-400' :
                                kw.intent === 'Navigational' ? 'bg-pink-500/10 text-pink-400' :
                                'bg-gray-500/10 text-gray-400'
                              }`}>
                                {kw.intent}
                              </span>
                            </td>
                            <td className="p-4 text-sm text-gray-400">{kw.product_type}</td>
                            <td className="p-4 text-sm text-gray-400 truncate max-w-[150px]">{kw.topic_cluster}</td>
                            <td className="p-4 text-sm font-bold text-right text-brand-primary font-mono">{kw.final_ai_score.toFixed(0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}

                  {/* Pagination Bar */}
                  {keywordsData && (
                    <div className="p-4 border-t border-card-border flex items-center justify-between text-sm text-gray-400">
                      <div>
                        Showing {kwPage * itemsPerPage + 1} - {Math.min((kwPage + 1) * itemsPerPage, keywordsData.total)} of {keywordsData.total} items
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          disabled={kwPage === 0}
                          onClick={() => setKwPage(p => p - 1)}
                          className="px-3 py-1.5 rounded-lg border border-card-border hover:bg-white/5 disabled:opacity-40 disabled:hover:bg-transparent"
                        >
                          Previous
                        </button>
                        <button
                          disabled={(kwPage + 1) * itemsPerPage >= keywordsData.total}
                          onClick={() => setKwPage(p => p + 1)}
                          className="px-3 py-1.5 rounded-lg border border-card-border hover:bg-white/5 disabled:opacity-40 disabled:hover:bg-transparent"
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Keyword Details Drawer */}
                {selectedKeyword && (
                  <div className="fixed inset-y-0 right-0 w-96 glass-panel border-l border-card-border shadow-2xl p-6 space-y-6 overflow-y-auto z-50 animate-in slide-in-from-right duration-200">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-[10px] text-brand-primary font-bold uppercase tracking-wide">KEYWORD DEEP-DIVE</span>
                        <h4 className="text-xl font-bold text-white mt-1">{selectedKeyword.keyword}</h4>
                      </div>
                      <button
                        onClick={() => setSelectedKeyword(null)}
                        className="text-gray-500 hover:text-white text-xs font-semibold uppercase px-2 py-1 rounded bg-white/5"
                      >
                        Close
                      </button>
                    </div>

                    <div className="space-y-4">
                      {/* Metric widgets */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-black/20 p-3.5 rounded-xl border border-card-border">
                          <span className="text-[10px] text-gray-400 font-bold uppercase">Volume</span>
                          <p className="text-lg font-bold text-white mt-1 font-mono">{selectedKeyword.search_volume.toLocaleString()}</p>
                        </div>
                        <div className="bg-black/20 p-3.5 rounded-xl border border-card-border">
                          <span className="text-[10px] text-gray-400 font-bold uppercase">Cerebro CPR</span>
                          <p className="text-lg font-bold text-white mt-1 font-mono">{selectedKeyword.cpr.toLocaleString()}</p>
                        </div>
                      </div>

                      {/* Score break-downs */}
                      <div className="space-y-3">
                        <h5 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Strategic Scores</h5>
                        {[
                          { label: 'Opportunity Score', val: selectedKeyword.opportunity_score, desc: 'High search volume vs competitor penetration.' },
                          { label: 'Competition Score', val: selectedKeyword.competition_score, desc: 'Overall bid velocity and active competitor ranks.' },
                          { label: 'Revenue Score', val: selectedKeyword.revenue_score, desc: 'Projected monthly revenue yield based on intent.' },
                          { label: 'Trend Score', val: selectedKeyword.trend_score, desc: 'Demand acceleration rate over the last quarter.' },
                          { label: 'Gap Score', val: selectedKeyword.gap_score, desc: 'Opportunity index where competitors own SERP.' },
                          { label: 'SEO Relevance', val: selectedKeyword.seo_score, desc: 'Linguistic match fitting for Title and Backend.' }
                        ].map((score, i) => (
                          <div key={i} className="space-y-1">
                            <div className="flex justify-between text-xs font-medium">
                              <span className="text-gray-300">{score.label}</span>
                              <span className="text-brand-primary font-mono">{score.val.toFixed(1)}/100</span>
                            </div>
                            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                              <div className="h-full bg-brand-primary rounded-full" style={{ width: `${score.val}%` }} />
                            </div>
                            <p className="text-[10px] text-gray-500">{score.desc}</p>
                          </div>
                        ))}
                      </div>

                      {/* Competitor Ranks */}
                      <div className="space-y-3 pt-2">
                        <h5 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Competitor SERP Ranks</h5>
                        <div className="bg-black/20 rounded-xl border border-card-border overflow-hidden divide-y divide-card-border/50">
                          {selectedKeyword.competitor_ranks &&
                            Object.entries(selectedKeyword.competitor_ranks).map(([comp, rank]) => (
                              <div key={comp} className="flex justify-between items-center p-3 text-xs">
                                <span className="font-semibold text-gray-300">{comp}</span>
                                <span className={`font-mono font-bold ${rank && rank <= 20 ? 'text-emerald-400' : 'text-gray-400'}`}>
                                  {rank && rank <= 100 ? `Pos ${rank}` : 'Unranked (100+)'}
                                </span>
                              </div>
                            ))}
                        </div>
                      </div>

                    </div>
                  </div>
                )}

              </div>
            )}

            {/* ================= TAB CONTENT 3: COMPETITOR GAPS ================= */}
            {activeTab === 'competitors' && competitorData && (
              <div className="space-y-6">
                <div className="glass-panel rounded-2xl p-6 space-y-2">
                  <h3 className="text-lg font-bold text-white">Competitor Overlap & Share of Voice</h3>
                  <p className="text-xs text-gray-400 max-w-2xl leading-relaxed">
                    Identify listings ranking on top terms where your product fails to index. The table below highlights keyword coverage gaps.
                  </p>
                </div>

                {/* Overlap matrix */}
                {competitorData.analysis && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {competitorData.analysis.overlap_matrix &&
                      Object.entries(competitorData.analysis.overlap_matrix).map(([comp, overlaps]: any) => (
                        <div key={comp} className="glass-panel rounded-2xl p-5 space-y-4">
                          <div className="flex justify-between items-center">
                            <h4 className="font-bold text-white">{comp}</h4>
                            <span className="text-[10px] text-gray-500 font-mono">Overlap Matrix</span>
                          </div>
                          <div className="space-y-2">
                            {Object.entries(overlaps).map(([other, val]: any) => (
                              <div key={other} className="flex justify-between text-xs items-center">
                                <span className="text-gray-400">vs {other}</span>
                                <span className="font-mono text-white font-semibold">{val}% overlap</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                  </div>
                )}

                {/* Gaps Data Table preview */}
                <div className="glass-panel rounded-2xl overflow-hidden">
                  <div className="p-4 bg-black/10 border-b border-card-border">
                    <h4 className="text-sm font-bold text-white uppercase tracking-wide">Identified Ranking Gap Keywords</h4>
                  </div>
                  <div className="p-12 text-center text-gray-400 text-sm space-y-2">
                    <AlertTriangle className="h-8 w-8 text-brand-primary mx-auto animate-bounce" />
                    <p className="font-bold text-white">Keyword Gaps Identified</p>
                    <p className="text-xs max-w-sm mx-auto">
                      Navigate to the <b>Keyword Explorer</b> and filter/sort by Opportunity or Gap score to see exact gap listings.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* ================= TAB CONTENT 4: LISTING OPTIMIZER ================= */}
            {activeTab === 'optimizer' && (
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
                
                {/* Editor column */}
                <div className="xl:col-span-7 glass-panel rounded-2xl p-6 space-y-6">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="text-lg font-bold text-white">Amazon SEO Copy Editor</h3>
                      <p className="text-xs text-gray-400">Edit listing fields. Real-time checklist evaluates optimization indexing.</p>
                    </div>
                    <button
                      disabled={generateListingMutation.isPending}
                      onClick={() => generateListingMutation.mutate()}
                      className="bg-brand-primary hover:bg-brand-primary/95 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center space-x-1.5 shadow-lg shadow-brand-primary/10 transition-all"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>{generateListingMutation.isPending ? 'Writing Copy...' : 'AI Generate Listing'}</span>
                    </button>
                  </div>

                  <div className="space-y-4">
                    {/* Title */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center">
                        <label className="text-xs font-semibold uppercase text-gray-400">Product Title</label>
                        <span className="text-[10px] text-gray-500">{listingTitle.length}/200 chars</span>
                      </div>
                      <input
                        type="text"
                        value={listingTitle}
                        onChange={(e) => setListingTitle(e.target.value.slice(0, 200))}
                        placeholder="Paste or write listing title..."
                        className="w-full bg-black/30 border border-card-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-primary text-white"
                      />
                    </div>

                    {/* Bullet Points */}
                    <div className="space-y-2">
                      <label className="text-xs font-semibold uppercase text-gray-400">Bullet Points (5 Key Features)</label>
                      {listingBullets.map((bullet, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between items-center text-[10px] text-gray-500">
                            <span>Bullet {idx + 1}</span>
                            <span>{bullet.length}/250 chars</span>
                          </div>
                          <input
                            type="text"
                            value={bullet}
                            onChange={(e) => {
                              const newBullets = [...listingBullets];
                              newBullets[idx] = e.target.value.slice(0, 250);
                              setListingBullets(newBullets);
                            }}
                            placeholder={`e.g. HIGH SPEED CHARGING: Engineered with PD 3.0 technology...`}
                            className="w-full bg-black/30 border border-card-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-brand-primary text-white"
                          />
                        </div>
                      ))}
                    </div>

                    {/* Description */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center">
                        <label className="text-xs font-semibold uppercase text-gray-400">Product Description</label>
                        <span className="text-[10px] text-gray-500">{listingDesc.length}/2000 chars</span>
                      </div>
                      <textarea
                        rows={5}
                        value={listingDesc}
                        onChange={(e) => setListingDesc(e.target.value.slice(0, 2000))}
                        placeholder="HTML formatted story, product specification list, packaging details..."
                        className="w-full bg-black/30 border border-card-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-primary text-white resize-none"
                      />
                    </div>

                    {/* Search Terms */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center">
                        <label className="text-xs font-semibold uppercase text-gray-400">Backend Search Terms</label>
                        <span className="text-[10px] text-gray-500">{listingTerms.length}/249 bytes</span>
                      </div>
                      <input
                        type="text"
                        value={listingTerms}
                        onChange={(e) => setListingTerms(e.target.value.slice(0, 249))}
                        placeholder="Space separated keywords (e.g. charger brick gan block block charging adapter)"
                        className="w-full bg-black/30 border border-card-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-primary text-white"
                      />
                    </div>
                  </div>
                </div>

                {/* Score & Checklist column */}
                <div className="xl:col-span-5 space-y-6">
                  {/* Score dial card */}
                  <div className="glass-panel rounded-2xl p-6 text-center space-y-4">
                    <h4 className="text-sm font-bold text-gray-300 uppercase tracking-wide">SEO Listing Quality Score</h4>
                    
                    <div className="relative inline-flex items-center justify-center">
                      <svg className="w-36 h-36 transform -rotate-90">
                        <circle cx="72" cy="72" r="64" stroke="rgba(255,255,255,0.05)" strokeWidth="8" fill="transparent" />
                        <circle
                          cx="72"
                          cy="72"
                          r="64"
                          stroke="#8b5cf6"
                          strokeWidth="8"
                          fill="transparent"
                          strokeDasharray={402}
                          strokeDashoffset={402 - (402 * (listingAnalysis?.score || 0)) / 100}
                          className="transition-all duration-500 ease-out"
                        />
                      </svg>
                      <div className="absolute flex flex-col items-center">
                        <span className="text-4xl font-black text-white font-mono">{listingAnalysis?.score || 0}</span>
                        <span className="text-[10px] text-gray-400 font-bold uppercase">Points</span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <p className="text-sm font-semibold text-white">Recommendations Summary</p>
                      <div className="text-left bg-black/10 p-3 rounded-xl border border-card-border/50 max-h-40 overflow-y-auto space-y-1.5 text-xs text-gray-400">
                        {listingAnalysis?.suggestions?.map((s: string, idx: number) => (
                          <div key={idx} className="flex items-start space-x-2">
                            <span className="text-brand-primary mt-0.5">•</span>
                            <span>{s}</span>
                          </div>
                        )) || <div>Start editing elements to see optimization guidelines.</div>}
                      </div>
                    </div>
                  </div>

                  {/* Target Keywords checklist */}
                  <div className="glass-panel rounded-2xl p-6 space-y-4 flex flex-col h-96">
                    <div className="flex justify-between items-center">
                      <h4 className="text-sm font-bold text-white uppercase tracking-wide">Target Keyword Checklist</h4>
                      <span className="text-[10px] text-brand-primary font-bold">TOP 30 OPPORTUNITIES</span>
                    </div>

                    <div className="flex-1 overflow-y-auto space-y-2 pr-1 text-xs">
                      {listingAnalysis?.matches &&
                        Object.entries(listingAnalysis.matches).map(([kw, matched]) => (
                          <div key={kw} className="flex justify-between items-center p-2 rounded bg-black/10 border border-card-border/50">
                            <span className="font-medium text-gray-300">{kw}</span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              matched ? 'bg-emerald-500/10 text-emerald-400' : 'bg-gray-500/10 text-gray-500'
                            }`}>
                              {matched ? 'Matched' : 'Unused'}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>

              </div>
            )}

            {/* ================= TAB CONTENT 5: AI CHAT ================= */}
            {activeTab === 'chat' && (
              <div className="glass-panel rounded-2xl flex flex-col h-[calc(100vh-13rem)] overflow-hidden">
                {/* Chat window Header */}
                <div className="p-4 bg-black/15 border-b border-card-border flex items-center space-x-3">
                  <div className="h-7 w-7 rounded bg-brand-primary/20 flex items-center justify-center">
                    <Sparkles className="h-4 w-4 text-brand-primary" />
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-white">Copilot Strategic Assistant</h3>
                    <p className="text-[10px] text-gray-500">Retrieves context and stats from your active competitor dataset.</p>
                  </div>
                </div>

                {/* Messages feed */}
                <div className="flex-1 p-6 overflow-y-auto space-y-4">
                  {chatMessages.length === 0 && (
                    <div className="text-center space-y-6 py-12 max-w-md mx-auto">
                      <MessageSquareText className="h-12 w-12 text-brand-primary/40 mx-auto" />
                      <div className="space-y-1">
                        <p className="text-white font-bold">Ask anything about your Amazon data</p>
                        <p className="text-xs text-gray-400 leading-relaxed">
                          Your questions are processed by a RAG retrieval system using Sentence Transformers and Ollama.
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-left text-xs font-medium">
                        {[
                          'Show top opportunities',
                          'Find low competition items',
                          'Find power bank gaps',
                          'Show competitor overlap'
                        ].map((preset, i) => (
                          <button
                            key={i}
                            onClick={() => handlePresetChat(preset)}
                            className="p-3 bg-black/10 border border-card-border rounded-xl text-gray-300 hover:text-white hover:border-brand-primary transition-all text-center"
                          >
                            {preset}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {chatMessages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-xl rounded-2xl px-5 py-3 text-sm shadow-md leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-brand-primary text-white rounded-br-none'
                          : 'bg-black/20 border border-card-border/80 text-gray-200 rounded-bl-none font-mono whitespace-pre-line'
                      }`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  
                  {chatMutation.isPending && (
                    <div className="flex justify-start">
                      <div className="bg-black/20 border border-card-border/80 rounded-2xl rounded-bl-none px-5 py-3 flex items-center space-x-2 text-xs text-gray-400">
                        <RefreshCw className="h-4.5 w-4.5 animate-spin text-brand-primary" />
                        <span>Searching embeddings & reasoning...</span>
                      </div>
                    </div>
                  )}
                  
                  <div ref={chatEndRef} />
                </div>

                {/* Form Input */}
                <form onSubmit={handleSendChat} className="p-4 border-t border-card-border bg-black/10 flex items-center gap-3">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask Copilot (e.g. Find highest search volume keywords under charger category)..."
                    className="flex-1 bg-black/20 border border-card-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-primary text-white"
                  />
                  <button
                    type="submit"
                    disabled={!chatInput.trim() || chatMutation.isPending}
                    className="bg-brand-primary hover:bg-brand-primary/95 disabled:opacity-40 text-white p-3 rounded-xl transition-all shadow-md shrink-0"
                  >
                    <Send className="h-4.5 w-4.5" />
                  </button>
                </form>
              </div>
            )}

            {/* ================= TAB CONTENT 6: EXPORT REPORTS ================= */}
            {activeTab === 'reports' && (
              <div className="space-y-6">
                <div className="glass-panel rounded-2xl p-6 space-y-2">
                  <h3 className="text-lg font-bold text-white">Generate Executive Strategic Reports</h3>
                  <p className="text-xs text-gray-400">Download formatted business intelligence reports to share with brands.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Excel sheet */}
                  <div className="glass-panel rounded-2xl p-6 flex flex-col justify-between space-y-4">
                    <div className="space-y-2">
                      <FileSpreadsheet className="h-8 w-8 text-emerald-400" />
                      <h4 className="font-bold text-white text-lg">Cleaned Keyword Database (Excel)</h4>
                      <p className="text-xs text-gray-400 leading-relaxed">
                        Export the complete list of keywords including all 10 strategic scores, search volume, Cerebro rank, product types, clusters, and competitor biases. Fully styled with freeze panes and autowidth headers.
                      </p>
                    </div>
                    <button
                      onClick={() => downloadReport('xlsx')}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center space-x-2 shadow-lg transition-all"
                    >
                      <Download className="h-4 w-4" />
                      <span>Download Styled Spreadsheet</span>
                    </button>
                  </div>

                  {/* PDF executive summary */}
                  <div className="glass-panel rounded-2xl p-6 flex flex-col justify-between space-y-4">
                    <div className="space-y-2">
                      <Sparkles className="h-8 w-8 text-brand-primary animate-pulse" />
                      <h4 className="font-bold text-white text-lg">Executive Summary Report (PDF)</h4>
                      <p className="text-xs text-gray-400 leading-relaxed">
                        Download a styled presentation PDF report containing Executive Summaries, high-opportunity charts, competitor positioning charts, keyword gaps listings, and listing SEO audits.
                      </p>
                    </div>
                    <button
                      onClick={() => downloadReport('pdf')}
                      className="bg-brand-primary hover:bg-brand-primary/95 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center space-x-2 shadow-lg transition-all"
                    >
                      <Download className="h-4 w-4" />
                      <span>Download Executive PDF</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ================= TAB CONTENT 7: APP SETTINGS ================= */}
            {activeTab === 'settings' && (
              <div className="glass-panel rounded-2xl p-6 max-w-xl space-y-6">
                <div className="space-y-1">
                  <h3 className="text-lg font-bold text-white">App Configurations</h3>
                  <p className="text-xs text-gray-400">Configure local LLM servers, Ollama URLs, and opportunity weights.</p>
                </div>

                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold uppercase text-gray-400">Local Ollama Endpoint</label>
                    <input
                      type="text"
                      value={ollamaUrl}
                      onChange={(e) => setOllamaUrl(e.target.value)}
                      className="w-full bg-black/30 border border-card-border rounded-xl px-4 py-2.5 text-sm focus:outline-none text-white font-mono"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold uppercase text-gray-400">Target Chat LLM Model</label>
                    <input
                      type="text"
                      value={ollamaModel}
                      onChange={(e) => setOllamaModel(e.target.value)}
                      className="w-full bg-black/30 border border-card-border rounded-xl px-4 py-2.5 text-sm focus:outline-none text-white font-mono"
                    />
                    <span className="text-[10px] text-gray-500">Typically qwen2.5:7b, llama3, or similar locally loaded.</span>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold uppercase text-gray-400">Opportunity Score weights</label>
                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div className="p-3 bg-black/20 rounded-xl border border-card-border">
                        <span className="text-gray-400">Search Volume weight</span>
                        <p className="font-bold text-white font-mono mt-1">60%</p>
                      </div>
                      <div className="p-3 bg-black/20 rounded-xl border border-card-border">
                        <span className="text-gray-400">Competition bias</span>
                        <p className="font-bold text-white font-mono mt-1">40%</p>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setSuccessMsg('Settings saved successfully!');
                      setTimeout(() => setSuccessMsg(null), 3000);
                    }}
                    className="bg-brand-primary hover:bg-brand-primary/95 text-white font-bold px-6 py-2.5 rounded-xl text-sm transition-all"
                  >
                    Save Configuration
                  </button>
                </div>
              </div>
            )}

          </div>
        )}

      </main>
    </div>
  );
}
