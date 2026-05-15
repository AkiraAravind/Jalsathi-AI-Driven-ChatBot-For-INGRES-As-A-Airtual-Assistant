import React from 'react';
import { motion } from 'framer-motion';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}

const AuthLayout: React.FC<AuthLayoutProps> = ({ children, title, subtitle }) => {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-6 relative overflow-hidden perspective-1000">
      {/* 3D Animated Background Elements */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <motion.div 
          animate={{ 
            rotate: [0, 360],
            scale: [1, 1.2, 1]
          }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-primary/10 blur-[150px] rounded-full"
        />
        <motion.div 
          animate={{ 
            rotate: [360, 0],
            scale: [1, 1.3, 1]
          }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-accent-violet/10 blur-[150px] rounded-full"
        />
      </div>

      {/* Main Glassmorphic Container */}
      <motion.div 
        initial={{ opacity: 0, y: 40, rotateX: -10 }}
        animate={{ opacity: 1, y: 0, rotateX: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="w-full max-w-lg glass-card p-10 relative z-10 preserve-3d depth-3"
      >
        <div className="text-center mb-10">
          <motion.div 
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            className="w-16 h-16 bg-primary/20 rounded-2xl flex items-center justify-center mx-auto mb-6 border border-primary/30"
          >
            <img src="/ingres-icon.png" alt="INGRES" className="w-10 h-10 object-contain" 
                 onError={(e) => { e.currentTarget.src = 'https://cdn-icons-png.flaticon.com/512/2099/2099192.png' }} />
          </motion.div>
          <h1 className="text-4xl font-serif font-black italic text-white tracking-tight mb-2">{title}</h1>
          <p className="text-sm font-bold text-text-muted uppercase tracking-[0.2em]">{subtitle}</p>
        </div>

        {children}

        {/* Branding Footer */}
        <div className="mt-12 text-center">
          <p className="text-[10px] font-black text-text-muted/40 uppercase tracking-[0.4em]">Project INGRES // Team JalSathi</p>
        </div>
      </motion.div>
    </div>
  );
};

export default AuthLayout;
