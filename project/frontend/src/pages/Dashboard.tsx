import React from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import TopNav from '../components/TopNav';
import ChatInterface from '../components/ChatInterface';
import AboutSection from '../components/AboutSection';
import ContactSection from '../components/ContactSection';
import Requirements from './Requirements';
import { ShieldX, Waves, Radar, MapPinned, AlertTriangle, CheckCircle2 } from 'lucide-react';

import { chatService } from '../services/api';
import type { PortalStateLevel } from '../services/api';

const FALLBACK_STATE_WATER_LEVELS: PortalStateLevel[] = [
    { state: 'Andhra Pradesh', level: 58 },
    { state: 'Arunachal Pradesh', level: 34 },
    { state: 'Assam', level: 41 },
    { state: 'Bihar', level: 69 },
    { state: 'Chhattisgarh', level: 55 },
    { state: 'Goa', level: 47 },
    { state: 'Gujarat', level: 86 },
    { state: 'Haryana', level: 118 },
    { state: 'Himachal Pradesh', level: 39 },
    { state: 'Jharkhand', level: 61 },
    { state: 'Karnataka', level: 73 },
    { state: 'Kerala', level: 44 },
    { state: 'Madhya Pradesh', level: 79 },
    { state: 'Maharashtra', level: 91 },
    { state: 'Manipur', level: 49 },
    { state: 'Meghalaya', level: 35 },
    { state: 'Mizoram', level: 33 },
    { state: 'Nagaland', level: 38 },
    { state: 'Odisha', level: 63 },
    { state: 'Punjab', level: 131 },
    { state: 'Rajasthan', level: 112 },
    { state: 'Sikkim', level: 31 },
    { state: 'Tamil Nadu', level: 84 },
    { state: 'Telangana', level: 77 },
    { state: 'Tripura', level: 46 },
    { state: 'Uttar Pradesh', level: 95 },
    { state: 'Uttarakhand', level: 53 },
    { state: 'West Bengal', level: 68 },
    { state: 'Andaman and Nicobar Islands', level: 28 },
    { state: 'Chandigarh', level: 66 },
    { state: 'Dadra and Nagar Haveli and Daman and Diu', level: 57 },
    { state: 'Delhi', level: 123 },
    { state: 'Jammu and Kashmir', level: 62 },
    { state: 'Ladakh', level: 26 },
    { state: 'Lakshadweep', level: 22 },
    { state: 'Puducherry', level: 71 },
];

const GovPortal = () => {
    const role = localStorage.getItem('ingres_role');
    const [liveData, setLiveData] = React.useState({ extraction: 64.1, blocks: 152, updateTime: new Date().toLocaleTimeString() });
    const [stateWaterLevels, setStateWaterLevels] = React.useState<PortalStateLevel[]>(FALLBACK_STATE_WATER_LEVELS);
    const [dataSource, setDataSource] = React.useState<'live' | 'fallback'>('fallback');

    const highestStress = React.useMemo(
        () => [...stateWaterLevels].sort((a, b) => b.level - a.level).slice(0, 5),
        [stateWaterLevels]
    );

    const lowStress = React.useMemo(
        () => [...stateWaterLevels].sort((a, b) => a.level - b.level).slice(0, 5),
        [stateWaterLevels]
    );
    
    const sliderImages = [
        "https://images.unsplash.com/photo-1520209759809-a9bcb6cb3241?q=80&w=2000",
        "https://images.unsplash.com/photo-1473773508845-188df298d2d1?q=80&w=2000",
        "https://images.unsplash.com/photo-1489515217757-5fd1be406fef?q=80&w=2000"
    ];
    const [bgIndex, setBgIndex] = React.useState(0);

    // Simulate "live" changing data
    React.useEffect(() => {
        const timer = setInterval(() => {
            setLiveData(prev => ({ ...prev, updateTime: new Date().toLocaleTimeString() }));
        }, 15000);

        const sliderTimer = setInterval(() => {
            setBgIndex(prev => (prev + 1) % sliderImages.length);
        }, 5000);
        
        return () => {
            clearInterval(timer);
            clearInterval(sliderTimer);
        };
    }, []);

    React.useEffect(() => {
        if (role !== 'official') return;
        let active = true;

        const fetchPortalData = async () => {
            try {
                const data = await chatService.getPortalDashboardData();
                if (!active) return;

                if (Array.isArray(data.state_levels) && data.state_levels.length > 0) {
                    setStateWaterLevels(data.state_levels);
                    setDataSource('live');
                } else {
                    setStateWaterLevels(FALLBACK_STATE_WATER_LEVELS);
                    setDataSource('fallback');
                }

                if (data.summary) {
                    setLiveData(prev => ({
                        extraction: typeof data.summary.extraction_avg === 'number' ? data.summary.extraction_avg : prev.extraction,
                        blocks: typeof data.summary.at_risk_blocks === 'number' ? data.summary.at_risk_blocks : prev.blocks,
                        updateTime: new Date().toLocaleTimeString(),
                    }));
                }
            } catch (error) {
                if (!active) return;
                console.error('Failed to fetch live portal data:', error);
                setStateWaterLevels(FALLBACK_STATE_WATER_LEVELS);
                setDataSource('fallback');
            }
        };

        fetchPortalData();
        const refresh = setInterval(fetchPortalData, 60000);
        return () => {
            active = false;
            clearInterval(refresh);
        };
    }, [role]);

    if (role !== 'official') {
        return (
            <div className="glass-card p-20 text-center flex flex-col items-center gap-6">
                <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center text-red-500 border border-red-500/40 shadow-[0_0_30px_rgba(239,68,68,0.2)]">
                    <ShieldX className="w-8 h-8" />
                </div>
                <div>
                    <h2 className="text-3xl font-serif font-black italic text-white mb-2 underline decoration-red-500">Access Denied</h2>
                    <p className="text-text-muted font-bold uppercase tracking-widest text-xs">Official Credentials Required for GEC-2015 Reporting</p>
                </div>
                <p className="text-sm text-text-muted leading-relaxed max-w-md">
                    This terminal is reserved for registered Government Officials from CGWB and State Ground Water Departments. Please authenticate at the Official Gate.
                </p>
                <div className="h-px w-20 bg-white/10" />
                <button 
                    onClick={() => window.location.href = '/portal/login'}
                    className="px-8 py-3 rounded-xl bg-white/5 border border-white/10 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-white/10 transition-all text-white"
                >
                    Return to Official Gate
                </button>
            </div>
        );
    }
    
    const featureCards = [
        {
            icon: Waves,
            title: 'Aquifer Stress Scan',
            detail: 'Automated extraction stress scoring for every jurisdiction with threshold-based flags.',
        },
        {
            icon: Radar,
            title: 'Real-time Risk Signals',
            detail: 'Live telemetry pulse aligned with official reporting windows and policy checkpoints.',
        },
        {
            icon: MapPinned,
            title: '36-State Coverage',
            detail: 'State and UT level monitoring view with a single comparative governance pane.',
        },
        {
            icon: AlertTriangle,
            title: 'Priority Escalation',
            detail: 'Critical-state queue for immediate intervention and district-level drilldown.',
        },
    ];

    const stateCount = stateWaterLevels.length;
    const graphWidth = Math.max(1400, stateCount * 46);
    const graphHeight = 370;
    const graphTop = 22;
    const graphBottom = 300;
    const graphRange = graphBottom - graphTop;
    const graphMax = 140;

    const yFromLevel = (level: number) => graphBottom - Math.min(graphMax, Math.max(0, level)) / graphMax * graphRange;

    const linePoints = stateWaterLevels
        .map((item, index) => {
            const x = 35 + index * 46 + 9;
            const y = yFromLevel(item.level);
            return `${x},${y}`;
        })
        .join(' ');

    return (
        <div className="flex flex-col gap-6 pb-16">
            <div className="glass-card text-left shadow-2xl relative overflow-hidden min-h-[340px] flex flex-col justify-end p-10 border border-white/10 rounded-3xl group">
                <AnimatePresence initial={false}>
                    <motion.img 
                        key={bgIndex}
                        src={sliderImages[bgIndex]}
                        initial={{ opacity: 0, scale: 1.05 }}
                        animate={{ opacity: 0.58, scale: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 1.5 }}
                        className="absolute inset-0 w-full h-full object-cover z-0 grayscale-[18%] opacity-60 transition-transform duration-10000 group-hover:scale-110"
                    />
                </AnimatePresence>
                <div className="absolute inset-0 bg-gradient-to-t from-[#04111a] via-[#04111a]/60 to-transparent z-10" />
                
                <div className="relative z-20 max-w-4xl">
                    <h2 className="text-5xl font-serif font-black italic text-white mb-3">Government Groundwater Command Portal</h2>
                    <div className="flex flex-wrap items-center gap-3">
                        <span className="text-xs font-bold text-accent-cyan uppercase tracking-[0.35em]">National Water Governance Command Grid</span>
                        <span className="w-2 h-2 rounded-full bg-accent-cyan animate-pulse" />
                        <span className="text-[10px] text-white/60 font-mono font-bold bg-white/5 py-1 px-3 rounded-full backdrop-blur-md border border-white/10">Last Sync: {liveData.updateTime}</span>
                    </div>
                    <p className="text-sm text-white/80 mt-4 leading-relaxed max-w-3xl">
                        Integrated decision console for officials to monitor groundwater extraction, compare all 36 states and UTs, and identify escalation zones through visual analytics and risk intelligence.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="glass-card p-6 border-white/5 flex flex-col justify-center">
                    <p className="text-[10px] font-black uppercase tracking-widest text-text-muted mb-2">National Stage of Extraction</p>
                    <div className="text-5xl font-black text-white">{liveData.extraction.toFixed(2)}%</div>
                    <p className="text-xs text-accent-green mt-2">↑ 0.05% trending upward</p>
                </div>
                <div className="glass-card p-6 border-white/5 flex flex-col justify-center">
                    <p className="text-[10px] font-black uppercase tracking-widest text-text-muted mb-2">At-Risk Blocks Identified</p>
                    <div className="text-5xl font-black text-accent-gold">{liveData.blocks}</div>
                    <p className="text-xs text-text-muted mt-2">Requires immediate ML verification</p>
                </div>
                <div className="glass-card p-6 border-white/5 flex flex-col justify-center">
                    <p className="text-[10px] font-black uppercase tracking-widest text-text-muted mb-2">Monitored Jurisdictions</p>
                    <div className="text-5xl font-black text-primary">{stateWaterLevels.length}</div>
                    <p className="text-xs text-text-muted mt-2">{dataSource === 'live' ? 'Live DB aggregation active' : 'Fallback dataset active'}</p>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div className="xl:col-span-2 glass-card p-6 border-white/5">
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                        <div>
                            <h3 className="text-xl font-black text-white">Groundwater Level Graph - All 36 States/UTs</h3>
                            <p className="text-xs text-text-muted">Stage of extraction (%) with bar + trend line overlay for official comparison</p>
                        </div>
                        <span className={`text-[10px] uppercase tracking-widest font-bold border rounded-full px-3 py-1 ${dataSource === 'live' ? 'text-accent-cyan bg-accent-cyan/10 border-accent-cyan/30' : 'text-amber-300 bg-amber-300/10 border-amber-300/30'}`}>
                            {dataSource === 'live' ? 'Live national analytical view' : 'Fallback analytical view'}
                        </span>
                    </div>

                    <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#07131b] p-3">
                        <svg width={graphWidth} height={graphHeight} role="img" aria-label="Groundwater extraction graph for 36 states and union territories">
                            {[0, 35, 70, 105, 140].map((tick) => {
                                const y = yFromLevel(tick);
                                return (
                                    <g key={tick}>
                                        <line x1={20} y1={y} x2={graphWidth - 20} y2={y} stroke="rgba(148,163,184,0.25)" strokeDasharray="4 5" />
                                        <text x={4} y={y + 4} fill="#cbd5e1" fontSize="10">{tick}</text>
                                    </g>
                                );
                            })}

                            <polyline
                                fill="none"
                                stroke="#38bdf8"
                                strokeWidth="2.5"
                                points={linePoints}
                            />

                            {stateWaterLevels.map((item, index) => {
                                const x = 35 + index * 46;
                                const y = yFromLevel(item.level);
                                const color = item.level > 100 ? '#ef4444' : item.level >= 70 ? '#f59e0b' : '#22c55e';
                                return (
                                    <g key={item.state}>
                                        <rect x={x} y={y} width={18} height={graphBottom - y} fill={color} rx={3} />
                                        <circle cx={x + 9} cy={y} r={3.2} fill="#e2e8f0" />
                                        <text x={x + 9} y={y - 8} fill="#f8fafc" fontSize="10" textAnchor="middle">{item.level}</text>
                                        <text
                                            x={x + 8}
                                            y={graphBottom + 12}
                                            fill="#94a3b8"
                                            fontSize="9"
                                            transform={`rotate(-38 ${x + 8} ${graphBottom + 12})`}
                                        >
                                            {item.state}
                                        </text>
                                    </g>
                                );
                            })}
                        </svg>
                    </div>
                </div>

                <div className="glass-card p-6 border-white/5">
                    <h3 className="text-lg font-bold text-white mb-4">Operational Features</h3>
                    <div className="space-y-3">
                        {featureCards.map((card) => {
                            const Icon = card.icon;
                            return (
                                <div key={card.title} className="rounded-xl bg-white/5 border border-white/10 p-3">
                                    <div className="flex items-center gap-2 mb-1.5">
                                        <Icon className="w-4 h-4 text-accent-cyan" />
                                        <h4 className="text-sm font-bold text-white">{card.title}</h4>
                                    </div>
                                    <p className="text-xs text-text-muted leading-relaxed">{card.detail}</p>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <div className="glass-card p-6 border-white/5">
                    <h3 className="text-lg font-bold text-white mb-4">High Stress States (Top 5)</h3>
                    <ul className="space-y-4">
                        {highestStress.map((item) => (
                            <li key={item.state} className="flex justify-between items-center bg-white/5 p-3 rounded-lg border border-white/5 hover:border-red-500/30 transition-colors">
                                <div>
                                    <span className="font-bold text-white text-sm">{item.state}</span>
                                    <p className="text-xs text-red-400">Stage: {item.level}%</p>
                                </div>
                                <span className="text-[10px] uppercase font-bold text-red-500 px-2 py-1 bg-red-500/10 rounded">Critical Watch</span>
                            </li>
                        ))}
                    </ul>
                 </div>
                 
                 <div className="glass-card p-6 border-white/5">
                    <h3 className="text-lg font-bold text-white mb-4">Low Stress States (Top 5)</h3>
                    <ul className="space-y-4 mb-5">
                        {lowStress.map((item) => (
                            <li key={item.state} className="flex justify-between items-center bg-white/5 p-3 rounded-lg border border-white/5 hover:border-emerald-500/40 transition-colors">
                                <div>
                                    <span className="font-bold text-white text-sm">{item.state}</span>
                                    <p className="text-xs text-emerald-400">Stage: {item.level}%</p>
                                </div>
                                <span className="text-[10px] uppercase font-bold text-emerald-400 px-2 py-1 bg-emerald-400/10 rounded">Healthy</span>
                            </li>
                        ))}
                    </ul>
                    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                        <h4 className="text-sm font-bold text-white mb-2">Operational Features Enabled</h4>
                        <p className="text-xs text-text-muted leading-relaxed">District anomaly watch, extraction stress ranking, scheduled reporting, and state-level comparative analytics are all visible in this portal for official decision support.</p>
                    </div>
                 </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="glass-card p-0 overflow-hidden border-white/10">
                    <img
                        src="https://images.unsplash.com/photo-1581092335397-9583eb92d232?q=80&w=1600"
                        alt="Groundwater infrastructure inspection"
                        className="w-full h-44 object-cover"
                    />
                    <div className="p-4">
                        <h4 className="text-sm font-bold text-white">Field Inspection Intelligence</h4>
                        <p className="text-xs text-text-muted mt-1">Real inspection imagery integration for infrastructure monitoring and maintenance planning.</p>
                    </div>
                </div>

                <div className="glass-card p-0 overflow-hidden border-white/10">
                    <img
                        src="https://images.unsplash.com/photo-1472396961693-142e6e269027?q=80&w=1600"
                        alt="Water resource landscape monitoring"
                        className="w-full h-44 object-cover"
                    />
                    <div className="p-4">
                        <h4 className="text-sm font-bold text-white">Terrain and Recharge Mapping</h4>
                        <p className="text-xs text-text-muted mt-1">Visual context for recharge zones, seasonal stress, and field-priority geographies.</p>
                    </div>
                </div>

                <div className="glass-card p-0 overflow-hidden border-white/10">
                    <img
                        src="https://images.unsplash.com/photo-1509395062183-67c5ad6faff9?q=80&w=1600"
                        alt="Control room analytics dashboard"
                        className="w-full h-44 object-cover"
                    />
                    <div className="p-4">
                        <h4 className="text-sm font-bold text-white">Command Center Analytics</h4>
                        <p className="text-xs text-text-muted mt-1">Unified governance cockpit for policy analysts and state groundwater departments.</p>
                    </div>
                </div>
            </div>

            <div className="glass-card p-5 border-white/10 flex flex-wrap items-center gap-3 text-xs">
                <span className="inline-flex items-center gap-2 text-emerald-400 font-bold"><CheckCircle2 className="w-4 h-4" /> Under 70: Stable</span>
                <span className="inline-flex items-center gap-2 text-amber-300 font-bold"><CheckCircle2 className="w-4 h-4" /> 70 to 100: Stressed</span>
                <span className="inline-flex items-center gap-2 text-red-400 font-bold"><AlertTriangle className="w-4 h-4" /> Above 100: Over-Exploited</span>
                <span className="text-text-muted ml-auto">Data scope: 36 States and UTs (official monitoring panel)</span>
            </div>
        </div>
    );
};
const ProfileSection = () => {
    const [name, setName] = React.useState(localStorage.getItem('ingres_name') || 'Citizen');
    const [role] = React.useState(localStorage.getItem('ingres_role') || 'user');
    
    const handleSave = async () => {
        try {
            await chatService.updateProfile(name);
            localStorage.setItem('ingres_name', name);
            window.dispatchEvent(new Event('profileUpdated'));
            alert('Profile configuration synced to cloud successfully.');
        } catch (error) {
            console.error(error);
            alert("Failed to sync profile over cloud");
        }
    };

    return (
        <div className="glass-card p-10 max-w-xl mx-auto mt-20 text-center flex flex-col gap-6">
            <div>
                <h2 className="text-2xl font-serif font-black italic text-white mb-2">User Profile Hub</h2>
                <p className="text-[10px] font-bold text-accent-cyan uppercase tracking-[0.3em]">Identity & Access Verification</p>
            </div>
            
            <div className="space-y-4 text-left border border-white/10 p-6 rounded-2xl bg-white/5">
                <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase tracking-widest text-text-muted ml-1">Citizen Identity / Name</label>
                    <input 
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-4 px-4 text-sm outline-none focus:border-primary/50 transition-all font-bold text-white placeholder:text-white/20"
                        value={name}
                        placeholder="Your Legal Name"
                        onChange={e => setName(e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase tracking-widest text-text-muted ml-1">System Role Allocation</label>
                    <input 
                        disabled
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-4 px-4 text-sm font-bold text-text-muted opacity-60 cursor-not-allowed"
                        value={role === 'official' ? 'Government Official' : (role === 'user' ? 'General User' : role)}
                    />
                    <p className="text-[9px] text-text-muted/80 leading-tight mt-2 ml-1">
                        * Roles are assigned securely during registration based on credential clearance and require new node authorization to modify.
                    </p>
                </div>
            </div>

            <button 
                onClick={handleSave}
                className="w-full py-4 mt-2 rounded-xl bg-primary text-[10px] font-black uppercase tracking-widest text-white shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
            >
                Synchronize Identity
            </button>
        </div>
    );
};

const Dashboard: React.FC = () => {
    const location = useLocation();

    return (
        <div className="min-h-screen bg-background text-text-main relative overflow-x-hidden">
            {/* Global Immersive Background Layer */}
            <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 'var(--z-background)' }}>
                <div className="absolute top-[-10%] right-[-5%] w-[60%] h-[60%] bg-primary/10 blur-[120px] animate-pulse-slow" />
                <div className="absolute bottom-[-10%] left-[10%] w-[40%] h-[40%] bg-accent-violet/5 blur-[100px]" />
                <div className="absolute top-[20%] left-[-10%] w-[50%] h-[50%] bg-accent-cyan/5 blur-[110px]" />
            </div>

            <TopNav />

            {/* Main Command Center Layout */}
            <main className="relative pt-20 h-screen flex flex-col" style={{ zIndex: 'var(--z-base)' }}>
                {/* Status Bar - Neatly ordered under Nav */}
                <div className="h-12 flex items-center justify-between px-10 border-b border-white/5 bg-white/[0.01] backdrop-blur-sm shadow-inner">
                    <div className="flex items-center gap-4">
                        <div className="flex gap-1.5 items-center">
                           <div className="w-2 h-2 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                           <div className="w-2 h-2 rounded-full bg-accent-cyan animate-pulse delay-75 opacity-50" />
                        </div>
                        <h2 className="text-[10px] font-black uppercase tracking-[0.4em] text-text-muted/60">
                            CORE_LINK_STABLE // 1.0.4-S
                        </h2>
                    </div>

                    <div className="flex gap-3">
                        <div className="px-3 py-1 rounded-md bg-white/5 border border-white/5 flex items-center gap-2">
                            <span className="w-1 h-1 rounded-full bg-green-500 shadow-[0_0_5px_rgba(34,197,94,0.5)]" />
                            <span className="text-[9px] font-bold text-text-muted uppercase">GEC-2015 Node</span>
                        </div>
                    </div>
                </div>

                {/* Dynamic Content Router Container */}
                <div className="flex-1 overflow-hidden relative flex flex-col">
                    <div className="flex-1 overflow-y-auto px-3 md:px-5 lg:px-6 py-6 scrollbar-hide perspective-1000">
                        <AnimatePresence mode="wait">
                            <Routes location={location} key={location.pathname}>
                                <Route 
                                    path="/" 
                                    element={
                                        <motion.div 
                                          initial={{ opacity: 0, y: 15 }} 
                                          animate={{ opacity: 1, y: 0 }} 
                                          exit={{ opacity: 0, y: -15 }} 
                                          className="h-full flex flex-col gap-6"
                                        >
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h2 className="text-4xl font-serif font-black italic tracking-tight text-white">Hydrological Console</h2>
                                                    <p className="text-[10px] font-bold text-accent-cyan uppercase tracking-[0.3em] mt-1 opacity-70">India National AI Nexus</p>
                                                </div>
                                            </div>

                                            <div className="flex-1 min-h-0 depth-2 rounded-3xl overflow-hidden relative">
                                                <ChatInterface />
                                            </div>
                                        </motion.div>
                                    } 
                                />
                                <Route 
                                    path="/portal" 
                                    element={
                                        <motion.div 
                                          initial={{ opacity: 0, scale: 0.98 }} 
                                          animate={{ opacity: 1, scale: 1 }} 
                                          exit={{ opacity: 0, scale: 1.02 }} 
                                          className="h-full"
                                        >
                                            <GovPortal />
                                        </motion.div>
                                    } 
                                />
                                <Route 
                                    path="/about" 
                                    element={
                                        <motion.div 
                                          initial={{ opacity: 0, rotateY: 15 }} 
                                          animate={{ opacity: 1, rotateY: 0 }} 
                                          exit={{ opacity: 0, rotateY: -15 }} 
                                          className="flex justify-center preserve-3d"
                                        >
                                            <AboutSection />
                                        </motion.div>
                                    } 
                                />
                                <Route 
                                    path="/contact" 
                                    element={
                                        <motion.div 
                                          initial={{ opacity: 0, x: 20 }} 
                                          animate={{ opacity: 1, x: 0 }} 
                                          exit={{ opacity: 0, x: -20 }} 
                                          className="flex justify-center"
                                        >
                                            <ContactSection />
                                        </motion.div>
                                    } 
                                />
                                 <Route 
                                    path="/requirements" 
                                    element={
                                        <motion.div 
                                          initial={{ opacity: 0, scale: 0.98 }} 
                                          animate={{ opacity: 1, scale: 1 }} 
                                          exit={{ opacity: 0, scale: 1.02 }} 
                                        >
                                            <Requirements />
                                        </motion.div>
                                    } 
                                />
                                <Route 
                                    path="/profile" 
                                    element={
                                        <motion.div 
                                          initial={{ opacity: 0, scale: 0.95 }} 
                                          animate={{ opacity: 1, scale: 1 }} 
                                          className="h-full"
                                        >
                                            <ProfileSection />
                                        </motion.div>
                                    } 
                                />
                            </Routes>
                        </AnimatePresence>
                    </div>

                    {/* Subtle Interface Elements */}
                    <div className="absolute bottom-6 left-10 pointer-events-none opacity-20">
                        <p className="text-[9px] font-black text-text-muted uppercase tracking-[0.5em]">INGRES_SYSTEM_VCE_HYD</p>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default Dashboard;
