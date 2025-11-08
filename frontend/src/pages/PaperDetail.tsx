import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  Chip,
  Button,
  Stack,
  Divider,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  OpenInNew as OpenInNewIcon,
  PushPin as PushPinIcon,
  PushPinOutlined as PushPinOutlinedIcon,
  Download as DownloadIcon,
  Chat as ChatIcon,
} from '@mui/icons-material';
import { apiEndpoints } from '../services/api';

interface PaperMetadata {
  arxiv_id: string;
  title: string;
  abstract: string;
  authors: string[];
  published_date: string;
  updated_date?: string;
  primary_category: string;
  categories: string[];
  citation_count: number;
  is_seminal: boolean;
}

export const PaperDetail: React.FC = () => {
  const { arxivId } = useParams<{ arxivId: string }>();
  const navigate = useNavigate();
  
  const [paper, setPaper] = useState<PaperMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);
  const [isFocusLoading, setIsFocusLoading] = useState(false);

  useEffect(() => {
    if (arxivId) {
      fetchPaperDetails(arxivId);
      checkIfFocused(arxivId);
    }
  }, [arxivId]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && arxivId) {
        checkIfFocused(arxivId);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [arxivId]);

  const checkIfFocused = (id: string) => {
    const chatId = sessionStorage.getItem('current_chat_id');
    if (!chatId) {
      setIsFocused(false);
      return;
    }

    const focusedPapersKey = `focused_papers_${chatId}`;
    const existingFocused = sessionStorage.getItem(focusedPapersKey);
    if (existingFocused) {
      try {
        const focusedPapers = JSON.parse(existingFocused);
        const isAlreadyFocused = focusedPapers.some((p: any) => p.arxiv_id === id);
        setIsFocused(isAlreadyFocused);
      } catch (error) {
        console.error('Failed to parse focused papers:', error);
        setIsFocused(false);
      }
    } else {
      setIsFocused(false);
    }
  };

  const fetchPaperDetails = async (id: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiEndpoints.getPaperDetail(id);
      
      if (response.data.status === 'success') {
        setPaper(response.data.data);
      } else {
        throw new Error('Failed to fetch paper details');
      }
      
      setLoading(false);
      
    } catch (err: any) {
      setError(err.message || 'Failed to load paper details');
      setLoading(false);
    }
  };

  const handleFocus = async () => {
    if (!paper || isFocusLoading) return;
    
    try {
      setIsFocusLoading(true);

      const chatId = sessionStorage.getItem('current_chat_id');
      if (!chatId) {
        alert('Please start a chat session first');
        navigate('/research');
        return;
      }

      const focusedPapersKey = `focused_papers_${chatId}`;
      const existingFocused = sessionStorage.getItem(focusedPapersKey);
      let focusedPapers = existingFocused ? JSON.parse(existingFocused) : [];

      if (isFocused) {
        await apiEndpoints.removeFocusedPaper(chatId, paper.arxiv_id);
        focusedPapers = focusedPapers.filter((p: any) => p.arxiv_id !== paper.arxiv_id);
        sessionStorage.setItem(focusedPapersKey, JSON.stringify(focusedPapers));
        
        setIsFocused(false);
      } else {
        const alreadyFocused = focusedPapers.some((p: any) => p.arxiv_id === paper.arxiv_id);
        if (alreadyFocused) {
          setIsFocused(true);
          setIsFocusLoading(false);
          return;
        }
        
        await apiEndpoints.addFocusedPaper(chatId, {
          arxiv_id: paper.arxiv_id,
          title: paper.title
        });
        
        focusedPapers.push({
          arxiv_id: paper.arxiv_id,
          title: paper.title
        });
        sessionStorage.setItem(focusedPapersKey, JSON.stringify(focusedPapers));
        
        setIsFocused(true);
      }
    } catch (error) {
      console.error('Failed to toggle focus:', error);
      alert('Failed to update focus. Please try again.');
    } finally {
      setIsFocusLoading(false);
    }
  };

  const handleChatAboutPaper = async () => {
    if (!paper) return;
    
    try {
      let chatId = sessionStorage.getItem('current_chat_id');
      if (!chatId) {
        chatId = `chat_${Date.now()}`;
        sessionStorage.setItem('current_chat_id', chatId);
      }

      await apiEndpoints.addFocusedPaper(chatId, {
        arxiv_id: paper.arxiv_id,
        title: paper.title
      });

      const focusedPapersKey = `focused_papers_${chatId}`;
      const existingFocused = sessionStorage.getItem(focusedPapersKey);
      let focusedPapers = existingFocused ? JSON.parse(existingFocused) : [];
      
      const alreadyFocused = focusedPapers.some((p: any) => p.arxiv_id === paper.arxiv_id);
      if (!alreadyFocused) {
        focusedPapers.push({
          arxiv_id: paper.arxiv_id,
          title: paper.title
        });
        sessionStorage.setItem(focusedPapersKey, JSON.stringify(focusedPapers));
      }

      navigate('/research');
    } catch (error) {
      console.error('Failed to focus paper:', error);
      navigate('/research');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Go Back
        </Button>
      </Container>
    );
  }

  if (!paper) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="warning">Paper not found</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Go Back
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Back Button */}
      <Button 
        startIcon={<ArrowBackIcon />} 
        onClick={() => navigate(-1)}
        sx={{ mb: 2 }}
      >
        Back
      </Button>

      {/* Main Paper Card */}
      <Paper elevation={3} sx={{ p: 4 }}>
        {/* Title */}
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          {paper.title}
        </Typography>

        {/* Badges */}
        <Stack direction="row" spacing={1} sx={{ mb: 3, flexWrap: 'wrap', gap: 1 }}>
          {paper.is_seminal && (
            <Chip 
              label={`⭐ Seminal Paper - ${paper.citation_count.toLocaleString()} citations`}
              color="warning"
              size="medium"
            />
          )}
          <Chip 
            label={`📅 ${formatDate(paper.published_date)}`}
            variant="outlined"
            size="medium"
          />
          <Chip 
            label={paper.primary_category}
            color="primary"
            variant="outlined"
            size="medium"
          />
        </Stack>

        {/* Action Buttons */}
        <Stack direction="row" spacing={2} sx={{ mb: 3, flexWrap: 'wrap', gap: 1 }}>
          <Button
            variant={isFocused ? "contained" : "outlined"}
            startIcon={isFocused ? <PushPinIcon /> : <PushPinOutlinedIcon />}
            onClick={handleFocus}
            color="primary"
            disabled={isFocusLoading}
          >
            {isFocusLoading ? 'Loading...' : (isFocused ? 'Focused' : 'Focus on This Paper')}
          </Button>
          
          <Button
            variant="contained"
            startIcon={<ChatIcon />}
            onClick={handleChatAboutPaper}
            color="secondary"
          >
            Chat About This Paper
          </Button>
          
          <Button
            variant="outlined"
            startIcon={<OpenInNewIcon />}
            href={`https://arxiv.org/abs/${paper.arxiv_id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            View on arXiv
          </Button>
          
          <Button
            variant="outlined"
            onClick={() => navigate(`/paper/${encodeURIComponent(paper.arxiv_id)}/network`)}
          >
            Citation Network
          </Button>
          
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            href={`https://arxiv.org/pdf/${paper.arxiv_id}.pdf`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Download PDF
          </Button>
        </Stack>

        <Divider sx={{ my: 3 }} />

        {/* Authors */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" fontWeight="bold" gutterBottom>
            Authors
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1 }}>
            {paper.authors.map((author, idx) => (
              <Chip 
                key={idx}
                label={author}
                variant="outlined"
                size="small"
              />
            ))}
          </Stack>
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* Abstract */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" fontWeight="bold" gutterBottom>
            Abstract
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.8 }}>
            {paper.abstract}
          </Typography>
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* Categories */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" fontWeight="bold" gutterBottom>
            Categories
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1 }}>
            {paper.categories.map((cat, idx) => (
              <Chip 
                key={idx}
                label={cat}
                color="primary"
                variant="outlined"
                size="small"
              />
            ))}
          </Stack>
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* Metadata Grid */}
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Citation Count
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {paper.citation_count.toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Primary Category
                </Typography>
                <Typography variant="h5" fontWeight="bold">
                  {paper.primary_category}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>

      {/* Placeholder for future features */}
      <Paper elevation={1} sx={{ p: 3, mt: 3, bgcolor: 'grey.50' }}>
        <Typography variant="h6" fontWeight="bold" gutterBottom>
          Coming Soon
        </Typography>
        <Stack spacing={1}>
          <Typography variant="body2" color="text.secondary">
            • Citation Network Visualization
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • Similar Papers Recommendations
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • Research Context Timeline
          </Typography>
        </Stack>
      </Paper>
    </Container>
  );
};
