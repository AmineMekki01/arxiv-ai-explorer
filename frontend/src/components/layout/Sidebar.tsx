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
  Avatar,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  Tooltip,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  Science as ScienceIcon,
  Search as SearchIcon,
  BookmarkBorder as BookmarkIcon,
  Recommend as RecommendIcon,
  FavoriteBorder as FavoriteBorderIcon,
  Logout as LogoutIcon,
  Login as LoginIcon,
  PersonAdd as PersonAddIcon,
  Science as AppIcon,
  KeyboardArrowDown as ArrowDownIcon,
} from '@mui/icons-material';
import '../../styles/animations.css';
import { useAuth } from '../../contexts/AuthContext';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}


const Sidebar: React.FC<SidebarProps> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, logout, user } = useAuth();
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));
  const [menuAnchor, setMenuAnchor] = React.useState<null | HTMLElement>(null);
  const openMenu = Boolean(menuAnchor);
  const handleMenuOpen = (e: React.MouseEvent<HTMLElement>) => setMenuAnchor(e.currentTarget);
  const handleMenuClose = () => setMenuAnchor(null);

  const authedItems = [
    { text: 'Research Workspace', icon: <ScienceIcon />, path: '/research' },
    { text: 'For You', icon: <RecommendIcon />, path: '/recommendations' },
    { text: 'Search History', icon: <SearchIcon />, path: '/search' },
    { text: 'Saved', icon: <BookmarkIcon />, path: '/saved' },
    { text: 'Liked', icon: <FavoriteBorderIcon />, path: '/liked' },
  ];

  const guestItems = [
    { text: 'Login', icon: <LoginIcon />, path: '/login' },
    { text: 'Register', icon: <PersonAddIcon />, path: '/register' },
  ];


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
      <Box sx={{ px: 2.5, pt: 2.5 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 40,
                height: 40,
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
                boxShadow: '0 4px 14px rgba(37, 99, 235, 0.25)',
              }}
            >
              <AppIcon sx={{ color: 'white', fontSize: 22 }} />
            </Box>
            <Box>
              <Typography sx={{ fontWeight: 700, letterSpacing: '-0.02em' }}>arXiv AI Explorer</Typography>
              <Typography variant="caption" color="text.secondary">Intelligent Research Assistant</Typography>
            </Box>
          </Stack>
          {isSmall && (
            <IconButton size="small" onClick={onClose} aria-label="Close sidebar">
              <LogoutIcon sx={{ transform: 'rotate(180deg)' }} />
            </IconButton>
          )}
        </Stack>
        <Typography 
          variant="caption" 
          sx={{ 
            mt: 3,
            display: 'block',
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
        {(isAuthenticated ? authedItems : guestItems).map((item) => (
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

      <List sx={{ px: 2, pb: 2 }}>
        {isAuthenticated && (
            <>
              <Tooltip title={user?.username || user?.email}>
                <IconButton size="small" onClick={handleMenuOpen} sx={{ ml: 1 }}>
                  <Avatar sx={{ width: 28, height: 28 }}>
                    {(user?.full_name || 'U').charAt(0).toUpperCase()}
                  </Avatar>
                   {user?.full_name}
                  <ArrowDownIcon sx={{ ml: 0.5 }} />
                </IconButton>
              </Tooltip>
              <Menu
                anchorEl={menuAnchor}
                open={openMenu}
                onClose={handleMenuClose}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                transformOrigin={{ vertical: 'top', horizontal: 'right' }}
              >
                <MenuItem onClick={() => { handleMenuClose(); handleNavigation('/settings'); }}>Settings</MenuItem>
                <MenuItem onClick={() => { handleMenuClose(); logout(); handleNavigation('/login'); }}>Logout</MenuItem>
              </Menu>
            </>
          )}
      </List>
    </Box>
  );

  return (
    <Drawer
      variant={isSmall ? 'temporary' : 'persistent'}
      anchor="left"
      open={open}
      onClose={onClose}
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
