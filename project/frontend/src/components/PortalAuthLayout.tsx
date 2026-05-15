import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck } from 'lucide-react';

interface PortalAuthLayoutProps {
  children: React.ReactNode;
  title: string;
}

const PortalAuthLayout: React.FC<PortalAuthLayoutProps> = ({ children, title }) => {
  return (
    <div className="min-h-screen bg-[#05070a] flex items-center justify-center p-6 relative overflow-hidden">
      {/* Structural Official Background */}
      <div className="absolute inset-0 opacity-20 pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_50%_50%,#1e293b_0%,transparent_70%)]" />
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-10" />
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-xl bg-surface/80 backdrop-blur-2xl border border-white/10 rounded-[2rem] p-12 shadow-2xl relative z-10"
      >
        <div className="flex flex-col items-center mb-10 text-center">
          <div className="flex items-center gap-6 mb-8 px-6 py-3 bg-white/5 rounded-2xl border border-white/10">
            <img src="https://upload.wikimedia.org/wikipedia/commons/8/84/Government_of_India_logo.svg" alt="GOI" className="h-12 brightness-0 invert" />
            <div className="w-px h-10 bg-white/10" />
            <h4 className="text-[10px] font-black uppercase tracking-[0.4em] text-accent-gold leading-tight">National Groundwater<br/>Intelligence Portal</h4>
          </div>
          
          <h1 className="text-3xl font-serif font-black italic text-white mb-2">{title}</h1>
          <div className="flex items-center gap-2 text-[9px] font-black uppercase tracking-widest text-text-muted/60">
             <ShieldCheck className="w-3 h-3 text-accent-cyan" />
             GEC-2015 OFFICIAL_AUTHORIZATION_NODE
          </div>
        </div>

        {children}

        <div className="mt-12 flex justify-between items-center opacity-30">
          <p className="text-[8px] font-black uppercase tracking-widest">MINISTRY OF JAL SHAKTI</p>
          <p className="text-[8px] font-black uppercase tracking-widest">SECURE_GATE_V2</p>
        </div>
      </motion.div>
    </div>
  );
};

export default PortalAuthLayout;
