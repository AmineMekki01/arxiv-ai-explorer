import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, IconButton, useMediaQuery, useTheme } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import Sidebar from './components/layout/Sidebar';
import ResearchWorkspace from './pages/ResearchWorkspace';
import { PaperDetail } from './pages/PaperDetail';
import Login from './pages/Login';
import Register from './pages/Register';
import Settings from './pages/Settings';
import SavedPapers from './pages/SavedPapers';
import LikedPapers from './pages/LikedPapers';
import SearchPage from './pages/Search';
import CitationNetwork from './pages/CitationNetwork';
import Recommendations from './pages/Recommendations';
import { AuthProvider, useAuth } from './contexts/AuthContext';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <div />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

function App() {
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));
  const [sidebarOpen, setSidebarOpen] = React.useState(!isSmall);

  React.useEffect(() => {
    setSidebarOpen(!isSmall);
  }, [isSmall]);

  const handleSidebarToggle = () => setSidebarOpen((v) => !v);

  return (
    <AuthProvider>
      <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#F8FAFC' }}>
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            transition: 'margin-left 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
            p: { xs: 2, sm: 3, md: 4 },
            minHeight: '100vh',
            bgcolor: '#F8FAFC',

          }}
        >
          {isSmall && !sidebarOpen && (
            <IconButton
              aria-label="open sidebar"
              onClick={handleSidebarToggle}
              sx={{
                position: 'fixed',
                top: 12,
                left: 12,
                zIndex: (t) => t.zIndex.drawer + 2,
                background: 'rgba(255,255,255,0.9)',
                border: '1px solid rgba(15,23,42,0.08)'
              }}
            >
              <MenuIcon />
            </IconButton>
          )}
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
              path="/saved"
              element={
                <ProtectedRoute>
                  <SavedPapers />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recommendations"
              element={
                <ProtectedRoute>
                  <Recommendations />
                </ProtectedRoute>
              }
            />
            <Route
              path="/liked"
              element={
                <ProtectedRoute>
                  <LikedPapers />
                </ProtectedRoute>
              }
            />
            <Route
              path="/search"
              element={
                <ProtectedRoute>
                  <SearchPage />
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
              path="/paper/:arxivId/network"
              element={
                <ProtectedRoute>
                  <CitationNetwork />
                </ProtectedRoute>
              }
            />
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