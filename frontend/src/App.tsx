import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import ResearchWorkspace from './pages/ResearchWorkspace';
import { PaperDetail } from './pages/PaperDetail';

function App() {
  const [sidebarOpen, setSidebarOpen] = React.useState(true);

  const handleSidebarToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#F8FAFC' }}>
      <Navbar onMenuClick={handleSidebarToggle} />
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
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
          <Route path="/research" element={<ResearchWorkspace />} />
          <Route path="/paper/:arxivId" element={<PaperDetail />} />
          <Route path="/" element={<ResearchWorkspace />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;
