import React from 'react';
import { motion } from 'framer-motion';
import { BookOpen, Target, Users, ShieldCheck } from 'lucide-react';

const AboutSection: React.FC = () => {
    return (
        <motion.div 
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-6xl space-y-16 pb-20"
        >
            {/* Main Header */}
            <div className="text-center mb-16 relative">
                <motion.div 
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 mb-6"
                >
                    <ShieldCheck className="w-4 h-4 text-primary" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-primary">Certified GEC-2015 Intelligence</span>
                </motion.div>
                <h2 className="text-5xl font-serif font-black mb-6 italic tracking-tight text-white">Project INGRES</h2>
                <p className="mt-2 text-text-muted text-xl font-medium max-w-2xl mx-auto leading-relaxed">
                    A Next-Generation Hydrological Intelligence System developed at <span className="text-white">Vasavi College of Engineering</span>.
                </p>
                <div className="absolute -top-20 right-0 w-64 h-64 bg-primary/10 blur-[100px] rounded-full pointer-events-none" />
            </div>

            {/* Who, Why, How Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="glass-card p-10 group relative transition-transform hover:-translate-y-2 border-primary/10">
                    <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mb-6 text-primary shadow-lg group-hover:bg-primary group-hover:text-white transition-all duration-500">
                        <Users className="w-7 h-7" />
                    </div>
                    <h3 className="text-xl font-bold mb-3 tracking-tight">Who can use this website?</h3>
                    <p className="text-text-muted text-sm leading-relaxed">
                        This platform is built for **Government Officials** (CGWB, SGWD) for executing advanced multi-year resource planning, and **General Citizens, Researchers, and Policymakers** who wish to explore national groundwater trends dynamically using natural language.
                    </p>
                </div>

                <div className="glass-card p-10 group relative transition-transform hover:-translate-y-2 border-accent-gold/10">
                    <div className="w-14 h-14 rounded-2xl bg-accent-gold/10 flex items-center justify-center mb-6 text-accent-gold shadow-lg group-hover:bg-accent-gold group-hover:text-background transition-all duration-500">
                        <Target className="w-7 h-7" />
                    </div>
                    <h3 className="text-xl font-bold mb-3 tracking-tight">Why use the INGRES AI Hub?</h3>
                    <p className="text-text-muted text-sm leading-relaxed">
                        Because static PDFs and massive 150-column data tables are difficult to analyze. INGRES transforms raw data into instant, interactive visualizations and predictive trajectories allowing you to make rapid, data-driven decisions that could stabilize local water tables.
                    </p>
                </div>

                <div className="glass-card p-10 group relative transition-transform hover:-translate-y-2 border-accent-cyan/10">
                    <div className="w-14 h-14 rounded-2xl bg-accent-cyan/10 flex items-center justify-center mb-6 text-accent-cyan shadow-lg group-hover:bg-accent-cyan group-hover:text-background transition-all duration-500">
                        <ShieldCheck className="w-7 h-7" />
                    </div>
                    <h3 className="text-xl font-bold mb-3 tracking-tight">How is it helpful?</h3>
                    <p className="text-text-muted text-sm leading-relaxed">
                        It leverages our cutting edge **V-JEPA Engine** to predict which districts are trending toward "Critical" or "Over-Exploited" stages, catching risks *before* they occur. Furthermore, it strictly enforces GEC-2015 methodology guaranteeing scientific integrity in every query.
                    </p>
                </div>

                <div className="glass-card p-10 group relative transition-transform hover:-translate-y-2 border-accent-violet/10">
                    <div className="w-14 h-14 rounded-2xl bg-accent-violet/10 flex items-center justify-center mb-6 text-accent-violet shadow-lg group-hover:bg-accent-violet group-hover:text-white transition-all duration-500">
                        <BookOpen className="w-7 h-7" />
                    </div>
                    <h3 className="text-xl font-bold mb-3 tracking-tight">How to use</h3>
                    <ul className="text-text-muted text-sm leading-relaxed space-y-2 list-disc ml-4">
                        <li>Navigate to the **AI ChatBOT** console from the sidebar.</li>
                        <li>Ask complex questions like: <i>"Compare the extraction stage of Hyderabad and Nalgonda in 2022"</i>.</li>
                        <li>Ask for visualizations by explicitly saying "bar chart" or "line plot".</li>
                        <li>Use Hindi or Telugu for localized answers naturally matching your query language.</li>
                    </ul>
                </div>
            </div>
        </motion.div>
    );
};

export default AboutSection;
