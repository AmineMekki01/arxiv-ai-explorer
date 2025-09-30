import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import App from './App';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2563EB',
      light: '#60A5FA',
      dark: '#1E40AF',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#7C3AED',
      light: '#A78BFA',
      dark: '#5B21B6',
      contrastText: '#FFFFFF',
    },
    success: {
      main: '#059669',
      light: '#10B981',
      dark: '#047857',
    },
    warning: {
      main: '#D97706',
      light: '#F59E0B',
      dark: '#B45309',
    },
    error: {
      main: '#DC2626',
      light: '#EF4444',
      dark: '#B91C1C',
    },
    info: {
      main: '#0891B2',
      light: '#06B6D4',
      dark: '#0E7490',
    },
    background: {
      default: '#F8FAFC',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#0F172A',
      secondary: '#64748B',
    },
    divider: 'rgba(15, 23, 42, 0.08)',
  },
  typography: {
    fontFamily: '"Inter", "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: '2.5rem',
      lineHeight: 1.2,
      letterSpacing: '-0.025em',
      color: '#0F172A',
    },
    h2: {
      fontWeight: 700,
      fontSize: '2rem',
      lineHeight: 1.25,
      letterSpacing: '-0.02em',
      color: '#0F172A',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.5rem',
      lineHeight: 1.3,
      letterSpacing: '-0.015em',
      color: '#0F172A',
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.25rem',
      lineHeight: 1.4,
      letterSpacing: '-0.01em',
      color: '#0F172A',
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.125rem',
      lineHeight: 1.5,
      color: '#0F172A',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1rem',
      lineHeight: 1.5,
      color: '#0F172A',
    },
    subtitle1: {
      fontSize: '1.125rem',
      lineHeight: 1.7,
      fontWeight: 500,
      letterSpacing: '0.005em',
    },
    subtitle2: {
      fontSize: '1rem',
      lineHeight: 1.65,
      fontWeight: 500,
      letterSpacing: '0.005em',
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.75,
      letterSpacing: '0.01em',
      color: '#1E293B',
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.7,
      letterSpacing: '0.01em',
      color: '#475569',
    },
    button: {
      fontWeight: 500,
      textTransform: 'none',
      letterSpacing: '0.025em',
      fontSize: '0.9375rem',
    },
    caption: {
      fontSize: '0.75rem',
      lineHeight: 1.6,
      letterSpacing: '0.02em',
      color: '#64748B',
    },
  },
  shape: {
    borderRadius: 12,
  },
  spacing: 8,
  shadows: [
    'none',
    '0px 1px 2px rgba(15, 23, 42, 0.04), 0px 1px 3px rgba(15, 23, 42, 0.05)',
    '0px 1px 3px rgba(15, 23, 42, 0.05), 0px 2px 6px rgba(15, 23, 42, 0.06)',
    '0px 2px 4px rgba(15, 23, 42, 0.05), 0px 4px 8px rgba(15, 23, 42, 0.06)',
    '0px 2px 6px rgba(15, 23, 42, 0.06), 0px 6px 12px rgba(15, 23, 42, 0.07)',
    '0px 4px 8px rgba(15, 23, 42, 0.07), 0px 8px 16px rgba(15, 23, 42, 0.08)',
    '0px 6px 12px rgba(15, 23, 42, 0.08), 0px 10px 20px rgba(15, 23, 42, 0.09)',
    '0px 8px 16px rgba(15, 23, 42, 0.09), 0px 12px 24px rgba(15, 23, 42, 0.10)',
    '0px 10px 20px rgba(15, 23, 42, 0.10), 0px 16px 32px rgba(15, 23, 42, 0.11)',
    '0px 12px 24px rgba(15, 23, 42, 0.11), 0px 20px 40px rgba(15, 23, 42, 0.12)',
    '0px 14px 28px rgba(15, 23, 42, 0.12), 0px 24px 48px rgba(15, 23, 42, 0.13)',
    '0px 16px 32px rgba(15, 23, 42, 0.13), 0px 28px 56px rgba(15, 23, 42, 0.14)',
    '0px 18px 36px rgba(15, 23, 42, 0.14), 0px 32px 64px rgba(15, 23, 42, 0.15)',
    '0px 20px 40px rgba(15, 23, 42, 0.15), 0px 36px 72px rgba(15, 23, 42, 0.16)',
    '0px 22px 44px rgba(15, 23, 42, 0.16), 0px 40px 80px rgba(15, 23, 42, 0.17)',
    '0px 24px 48px rgba(15, 23, 42, 0.17), 0px 44px 88px rgba(15, 23, 42, 0.18)',
    '0px 26px 52px rgba(15, 23, 42, 0.18), 0px 48px 96px rgba(15, 23, 42, 0.19)',
    '0px 28px 56px rgba(15, 23, 42, 0.19), 0px 52px 104px rgba(15, 23, 42, 0.20)',
    '0px 30px 60px rgba(15, 23, 42, 0.20), 0px 56px 112px rgba(15, 23, 42, 0.21)',
    '0px 32px 64px rgba(15, 23, 42, 0.21), 0px 60px 120px rgba(15, 23, 42, 0.22)',
    '0px 34px 68px rgba(15, 23, 42, 0.22), 0px 64px 128px rgba(15, 23, 42, 0.23)',
    '0px 36px 72px rgba(15, 23, 42, 0.23), 0px 68px 136px rgba(15, 23, 42, 0.24)',
    '0px 38px 76px rgba(15, 23, 42, 0.24), 0px 72px 144px rgba(15, 23, 42, 0.25)',
    '0px 40px 80px rgba(15, 23, 42, 0.25), 0px 76px 152px rgba(15, 23, 42, 0.26)',
    '0px 42px 84px rgba(15, 23, 42, 0.26), 0px 80px 160px rgba(15, 23, 42, 0.27)',
  ],
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          padding: '10px 20px',
          fontSize: '0.9375rem',
          fontWeight: 500,
          boxShadow: 'none',
          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            boxShadow: '0px 2px 8px rgba(15, 23, 42, 0.08)',
            transform: 'translateY(-1px)',
          },
          '&:active': {
            transform: 'translateY(0px)',
          },
        },
        contained: {
          boxShadow: '0px 1px 3px rgba(15, 23, 42, 0.1)',
          '&:hover': {
            boxShadow: '0px 4px 12px rgba(15, 23, 42, 0.15)',
          },
        },
        outlined: {
          borderWidth: '1.5px',
          '&:hover': {
            borderWidth: '1.5px',
            backgroundColor: 'rgba(37, 99, 235, 0.04)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0px 1px 3px rgba(15, 23, 42, 0.06), 0px 2px 8px rgba(15, 23, 42, 0.04)',
          transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
          border: '1px solid rgba(15, 23, 42, 0.06)',
          backgroundImage: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          backgroundImage: 'none',
        },
        elevation1: {
          boxShadow: '0px 1px 3px rgba(15, 23, 42, 0.05), 0px 2px 6px rgba(15, 23, 42, 0.04)',
        },
        elevation2: {
          boxShadow: '0px 2px 4px rgba(15, 23, 42, 0.06), 0px 4px 12px rgba(15, 23, 42, 0.05)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 10,
            backgroundColor: '#FFFFFF',
            transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
            '& fieldset': {
              borderColor: 'rgba(15, 23, 42, 0.12)',
              borderWidth: '1.5px',
            },
            '&:hover fieldset': {
              borderColor: 'rgba(37, 99, 235, 0.4)',
            },
            '&.Mui-focused fieldset': {
              borderWidth: '2px',
              borderColor: '#2563EB',
            },
            '&.Mui-focused': {
              boxShadow: '0px 0px 0px 3px rgba(37, 99, 235, 0.1)',
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
          height: '28px',
          fontSize: '0.8125rem',
          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        },
        filled: {
          backgroundColor: 'rgba(37, 99, 235, 0.1)',
          color: '#1E40AF',
        },
        outlined: {
          borderWidth: '1.5px',
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            backgroundColor: 'rgba(37, 99, 235, 0.08)',
          },
        },
      },
    },
  },
});

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
