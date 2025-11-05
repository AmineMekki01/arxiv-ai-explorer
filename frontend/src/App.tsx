import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import ResearchWorkspace from './pages/ResearchWorkspace';
import { PaperDetail } from './pages/PaperDetail';
import Login from './pages/Login';
import Register from './pages/Register';
import Settings from './pages/Settings';
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Simple ProtectedRoute component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <div />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

// Render children only when authenticated
const AuthOnly: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : null;
};

function App() {
  const [sidebarOpen, setSidebarOpen] = React.useState(true);

  const handleSidebarToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <AuthProvider>
      <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#F8FAFC' }}>
        <AuthOnly>
          <Navbar onMenuClick={handleSidebarToggle} />
        </AuthOnly>
        <AuthOnly>
          <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        </AuthOnly>
        
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            mt: '68px',
            transition: 'margin-left 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
            p: { xs: 2, sm: 3, md: 4 },
            minHeight: '100vh',
            bgcolor: '#F8FAFC',
          }}
        >
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/research/:chatId"
              element={
                <ProtectedRoute>
                  <ResearchWorkspace />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              }
            />
            <Route
              path="/research"
              element={
                <ProtectedRoute>
                  <ResearchWorkspace />
                </ProtectedRoute>
              }
            />
            <Route path="/paper/:arxivId" element={<PaperDetail />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <ResearchWorkspace />
                </ProtectedRoute>
              }
            />
          </Routes>
        </Box>
      </Box>
    </AuthProvider>
  );
}

export default App;
