import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

// Lazy load pages for performance
const Landing = lazy(() => import('./pages/Landing'));
const Register = lazy(() => import('./pages/Register'));
const Login = lazy(() => import('./pages/Login'));
const VerifyOTP = lazy(() => import('./pages/VerifyOTP'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const PortalLogin = lazy(() => import('./pages/PortalLogin'));
const PortalRegister = lazy(() => import('./pages/PortalRegister'));

// Initial Loading Component with user's geometric logic
const AppLoader = () => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-background">
    <motion.div 
      initial={{ scale: 0, rotate: -45 }}
      animate={{ scale: [0, 1, 1.2, 1], rotate: [0, 0, 180, 270] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      className="w-16 h-16 bg-gradient-to-tr from-primary to-accent-cyan rounded-xl shadow-2xl shadow-primary/20"
    />
  </div>
);

const RequireAuth: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const token = localStorage.getItem('ingres_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

const App: React.FC = () => {
  return (
    <Router>
      <Suspense fallback={<AppLoader />}>
        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/verify-otp" element={<VerifyOTP />} />
            <Route path="/portal/login" element={<PortalLogin />} />
            <Route path="/portal/register" element={<PortalRegister />} />
            <Route path="/dashboard/*" element={<RequireAuth><Dashboard /></RequireAuth>} />
            <Route path="/auth" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AnimatePresence>
      </Suspense>
    </Router>
  );
};

export default App;
