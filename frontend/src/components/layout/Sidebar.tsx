import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Typography,
} from '@mui/material';
import {
  Science as ScienceIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import '../../styles/animations.css';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const menuItems = [
  { text: 'Research Workspace', icon: <ScienceIcon />, path: '/research' },
  { text: 'Search', icon: <SearchIcon />, path: '/search' },
];



const Sidebar: React.FC<SidebarProps> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleNavigation = (path: string) => {
    navigate(path);
    if (window.innerWidth < 600) {
      onClose();
    }
  };

  const drawerContent = (
    <Box 
      sx={{ 
        width: 260, 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        background: '#FFFFFF',
        borderRight: '1px solid rgba(15, 23, 42, 0.08)',
      }}
    >
      <Box sx={{ p: 3, mt: 9 }}>
        <Typography 
          variant="caption" 
          sx={{ 
            color: 'text.secondary',
            fontWeight: 600,
            letterSpacing: '0.08em',
            fontSize: '0.6875rem',
            textTransform: 'uppercase',
          }}
        >
          Navigation
        </Typography>
      </Box>
      
      <List sx={{ flexGrow: 1, px: 2 }}>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              onClick={() => handleNavigation(item.path)}
              selected={location.pathname === item.path}
              sx={{
                borderRadius: 2,
                py: 1.25,
                px: 2,
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  background: 'rgba(37, 99, 235, 0.06)',
                },
                '&.Mui-selected': {
                  background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.12) 0%, rgba(59, 130, 246, 0.08) 100%)',
                  color: 'primary.main',
                  fontWeight: 600,
                  borderLeft: '3px solid',
                  borderColor: 'primary.main',
                  pl: 'calc(16px - 3px)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.15) 0%, rgba(59, 130, 246, 0.10) 100%)',
                  },
                  '& .MuiListItemIcon-root': {
                    color: 'primary.main',
                  },
                  '& .MuiListItemText-primary': {
                    fontWeight: 600,
                  },
                },
              }}
            >
              <ListItemIcon 
                sx={{ 
                  minWidth: 36,
                  color: 'text.secondary',
                  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText 
                primary={item.text}
                primaryTypographyProps={{
                  fontSize: '0.9375rem',
                  fontWeight: 500,
                }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      <Divider sx={{ mx: 2, borderColor: 'rgba(15, 23, 42, 0.08)' }} />
      
      <Box sx={{ p: 3 }}>
        <Typography 
          variant="caption" 
          sx={{ 
            color: 'text.secondary',
            fontSize: '0.75rem',
            display: 'block',
            textAlign: 'center',
          }}
        >
          v1.0.0 Beta
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Drawer
      variant="persistent"
      anchor="left"
      open={open}
      sx={{
        width: open ? 260 : 0,
        transition: 'width 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: 260,
          boxSizing: 'border-box',
          border: 'none',
        },
      }}
    >
      {drawerContent}
    </Drawer>
  );
};

export default Sidebar;
