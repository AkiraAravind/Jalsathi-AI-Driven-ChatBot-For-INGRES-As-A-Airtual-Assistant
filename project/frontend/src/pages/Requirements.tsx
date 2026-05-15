import React from 'react';
import { motion } from 'framer-motion';
import { 
    ClipboardCheck, 
    Target, 
    AlertCircle, 
    ShieldCheck, 
    Zap,
    Users
} from 'lucide-react';

const Requirements: React.FC = () => {
    const containers = [
        {
            title: "Problem Statement (SIH25066)",
            icon: AlertCircle,
            color: "text-red-400",
            bg: "bg-red-400/10",
            content: [
                "India faces a critical groundwater crisis with 17% of administrative units being Over-Exploited.",
                "Massive hydrological reports (GEC framework) are locked in dense Excel and PDF documents.",
                "Lack of real-time, natural-language queryability for policymakers and the public.",
                "Fragmented data across 36 states and thousands of assessment units."
            ]
        },
        {
            title: "Primary Objectives",
            icon: Target,
            color: "text-primary",
            bg: "bg-primary/10",
            content: [
                "Build a Retrieval-Augmented Generation (RAG) based AI chatbot for natural language queries.",
                "Ensure zero-hallucination by grounding AI responses in official GEC data.",
                "Provide district, state, and national-level insights instantly.",
                "Enable comparison across multiple assessment years (2017 to 2025)."
            ]
        },
        {
            title: "Technical Requirements",
            icon: Zap,
            color: "text-accent-cyan",
            bg: "bg-accent-cyan/10",
            content: [
                "Vectorized database using pgvector for semantic search.",
                "JWT-based secure authentication for government officials.",
                "Automated data ingestion pipeline for 153-column GEC reports.",
                "Interactive UI with scientific data visualization Support."
            ]
        },
        {
            title: "User Personas",
            icon: Users,
            color: "text-accent-violet",
            bg: "bg-accent-violet/10",
            content: [
                "Government Officials: Need granular block-level data and trends for policy.",
                "Researchers: Need raw metric extraction across different states.",
                "General Public: Need simplified groundwater health status for their region."
            ]
        }
    ];

    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="h-full flex flex-col gap-8 pb-10"
        >
            <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                    <div className="p-3 rounded-2xl bg-accent-gold/10 text-accent-gold border border-accent-gold/20 shadow-[0_0_15px_rgba(234,179,8,0.1)]">
                        <ClipboardCheck className="w-6 h-6" />
                    </div>
                    <div>
                        <h2 className="text-4xl font-serif font-black italic tracking-tight text-white leading-none">SIH25066 Requirements</h2>
                        <p className="text-[10px] font-bold text-text-muted uppercase tracking-[0.4em] mt-2">Team JalSathi Baseline Intelligence</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {containers.map((container, idx) => (
                    <motion.div 
                        key={idx}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.1 }}
                        className="glass-card p-6 flex flex-col gap-4 group hover:border-white/20 transition-all border border-white/5"
                    >
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-xl ${container.bg} ${container.color}`}>
                                    <container.icon className="w-5 h-5" />
                                </div>
                                <h3 className="font-bold text-white tracking-tight">{container.title}</h3>
                            </div>
                        </div>
                        <ul className="space-y-3">
                            {container.content.map((item, i) => (
                                <li key={i} className="flex gap-3 text-xs leading-relaxed text-text-muted group-hover:text-white/80 transition-colors">
                                    <div className="w-1.5 h-1.5 rounded-full bg-primary/40 mt-1.5 flex-shrink-0" />
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </motion.div>
                ))}
            </div>

            {/* Compliance Matrix Table */}
            <div className="glass-card overflow-hidden">
                <div className="px-6 py-4 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <ShieldCheck className="w-4 h-4 text-green-400" />
                        <span className="text-[10px] font-black uppercase tracking-widest text-text-muted">Compliance Matrix // v1.0</span>
                    </div>
                    <div className="text-[10px] font-bold text-accent-cyan uppercase">Project Status: In Development</div>
                </div>
                <div className="p-6 overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-white/5">
                                <th className="pb-4 text-[10px] font-bold uppercase tracking-widest text-text-muted">Requirement Module</th>
                                <th className="pb-4 text-[10px] font-bold uppercase tracking-widest text-text-muted">Status</th>
                                <th className="pb-4 text-[10px] font-bold uppercase tracking-widest text-text-muted">Component</th>
                            </tr>
                        </thead>
                        <tbody className="text-[11px] font-medium">
                            <tr className="border-b border-white/5">
                                <td className="py-4 text-white">RAG Engine / Data Grounding</td>
                                <td className="py-4"><span className="px-2 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30">COMPLIANT</span></td>
                                <td className="py-4 text-text-muted">backend/rag_engine.py</td>
                            </tr>
                            <tr className="border-b border-white/5">
                                <td className="py-4 text-white">JWT RBAC Session Handling</td>
                                <td className="py-4"><span className="px-2 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30">COMPLIANT</span></td>
                                <td className="py-4 text-text-muted">backend/main.py</td>
                            </tr>
                            <tr className="border-b border-white/5">
                                <td className="py-4 text-white">Trend / Trajectory Analysis</td>
                                <td className="py-4"><span className="px-2 py-0.5 rounded bg-accent-gold/20 text-accent-gold border border-accent-gold/30">PARTIAL</span></td>
                                <td className="py-4 text-text-muted">backend/jepa_engine (Planned)</td>
                            </tr>
                             <tr className="border-b border-white/5">
                                <td className="py-4 text-white">National Coverage (36 States)</td>
                                <td className="py-4"><span className="px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/30">INGESTING</span></td>
                                <td className="py-4 text-text-muted">backend/ingestion/</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </motion.div>
    );
};

export default Requirements;
