import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Button,
  Stack,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Science as ScienceIcon,
} from '@mui/icons-material';
import '../../styles/animations.css';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

interface NavbarProps {
  onMenuClick: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ onMenuClick }) => {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();
  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(20px) saturate(180%)',
        borderBottom: '1px solid rgba(15, 23, 42, 0.08)',
        color: 'text.primary',
        boxShadow: 'none',
      }}
    >
      <Toolbar sx={{ minHeight: 68, px: { xs: 2, sm: 3, md: 4 } }}>
        <IconButton
          aria-label="open drawer"
          onClick={onMenuClick}
          edge="start"
          sx={{ 
            mr: { xs: 1.5, sm: 2 },
            color: 'text.primary',
          }}
        >
          <MenuIcon />
        </IconButton>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 1.5, sm: 2 }, flexGrow: 1 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: { xs: 36, sm: 40 },
              height: { xs: 36, sm: 40 },
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
              boxShadow: '0 4px 14px rgba(37, 99, 235, 0.25)',
            }}
          >
            <ScienceIcon sx={{ color: 'white', fontSize: { xs: 20, sm: 22 } }} />
          </Box>
          <Box>
            <Typography 
              variant="h6" 
              noWrap 
              component="div" 
              sx={{ 
                fontWeight: 700,
                fontSize: { xs: '1.125rem', sm: '1.25rem' },
                color: '#0F172A',
                letterSpacing: '-0.025em',
              }}
            >
              arXiv AI Explorer
            </Typography>
            <Typography 
              variant="caption" 
              sx={{ 
                color: 'text.secondary',
                fontSize: { xs: '0.7rem', sm: '0.75rem' },
                display: { xs: 'none', sm: 'block' },
                lineHeight: 1,
              }}
            >
              Intelligent Research Assistant
            </Typography>
          </Box>
        </Box>

        {/* Right actions */}
        <Stack direction="row" spacing={{ xs: 1, sm: 1.5 }} alignItems="center">
          {isAuthenticated ? (
            <>
              <Button
                variant="text"
                size="small"
                onClick={() => navigate('/settings')}
                sx={{ textTransform: 'none', color: 'text.primary' }}
              >
                Settings
              </Button>
              <Button
                variant="contained"
                size="small"
                onClick={logout}
                sx={{ textTransform: 'none' }}
              >
                Logout
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="text"
                size="small"
                onClick={() => navigate('/login')}
                sx={{ textTransform: 'none', color: 'text.primary' }}
              >
                Login
              </Button>
              <Button
                variant="contained"
                size="small"
                onClick={() => navigate('/register')}
                sx={{ textTransform: 'none' }}
              >
                Sign up
              </Button>
            </>
          )}
        </Stack>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
