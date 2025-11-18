import React, { useEffect, useState, useRef } from 'react';
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
  Favorite as FavoriteIcon,
  FavoriteBorder as FavoriteBorderIcon,
  Bookmark as BookmarkIcon,
  BookmarkBorder as BookmarkBorderIcon,
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

interface SimilarPaper {
  arxiv_id?: string | null;
  title: string;
  citation_count?: number | null;
  is_seminal?: boolean | null;
  similarity_score?: number | null;
  authors?: string[] | null;
  external_url?: string | null;
}

export const PaperDetail: React.FC = () => {
  const { arxivId } = useParams<{ arxivId: string }>();
  const navigate = useNavigate();
  
  const [paper, setPaper] = useState<PaperMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);
  const [isFocusLoading, setIsFocusLoading] = useState(false);
  const [isLiked, setIsLiked] = useState<boolean>(false);
  const [likeLoading, setLikeLoading] = useState<boolean>(false);
  const [isSaved, setIsSaved] = useState<boolean>(false);
  const [saveLoading, setSaveLoading] = useState<boolean>(false);
  const [stats, setStats] = useState<{ likes: number; saves: number; views_total: number; views_7d: number } | null>(null);
  const [similarPapers, setSimilarPapers] = useState<SimilarPaper[]>([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState<string | null>(null);
  const [similarMethod, setSimilarMethod] = useState<string>('combined');
  const trackedViewRef = useRef<string | null>(null);

  useEffect(() => {
    if (arxivId) {
      fetchPaperDetails(arxivId);
      checkIfFocused(arxivId);
      if (trackedViewRef.current !== arxivId) {
        trackPaperView(arxivId);
        trackedViewRef.current = arxivId;
      }
      checkLikeStatus(arxivId);
      checkSaveStatus(arxivId);
      fetchStats(arxivId);
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

  useEffect(() => {
    if (arxivId) {
      fetchSimilarPapers(arxivId, similarMethod);
    }
  }, [arxivId, similarMethod]);

  const checkLikeStatus = async (id: string) => {
    try {
      const res = await apiEndpoints.checkIfLiked(id);
      setIsLiked(!!res.data?.is_liked);
    } catch (e) {
      console.debug('Failed to check like status', e);
    }
  };

  const toggleLike = async () => {
    if (!paper || likeLoading) return;
    try {
      setLikeLoading(true);
      if (isLiked) {
        await apiEndpoints.unlikePaper(paper.arxiv_id);
        setIsLiked(false);
      } else {
        await apiEndpoints.likePaper(paper.arxiv_id, paper.title);
        setIsLiked(true);
      }
    } catch (e) {
      console.debug('Failed to toggle like', e);
    } finally {
      setLikeLoading(false);
      if (paper) fetchStats(paper.arxiv_id);
    }
  };

  const checkSaveStatus = async (id: string) => {
    try {
      const res = await apiEndpoints.checkIfSaved(id);
      setIsSaved(!!res.data?.is_saved);
    } catch (e) {
      console.debug('Failed to check save status', e);
    }
  };

  const toggleSave = async () => {
    if (!paper || saveLoading) return;
    try {
      setSaveLoading(true);
      if (isSaved) {
        await apiEndpoints.unsavePaper(paper.arxiv_id);
        setIsSaved(false);
      } else {
        await apiEndpoints.savePaper(paper.arxiv_id , paper.title);
        setIsSaved(true);
      }
    } catch (e) {
      console.debug('Failed to toggle save', e);
    } finally {
      setSaveLoading(false);
      if (paper) fetchStats(paper.arxiv_id);
    }
  };

  const fetchStats = async (id: string) => {
    try {
      const res = await apiEndpoints.getPaperStats(id);
      const d = res.data;
      setStats({ likes: d.likes || 0, saves: d.saves || 0, views_total: d.views_total || 0, views_7d: d.views_7d || 0 });
      if (typeof d.user_saved === 'boolean') setIsSaved(d.user_saved);
      if (typeof d.user_liked === 'boolean') setIsLiked(d.user_liked);
    } catch (e) {
      console.debug('Failed to fetch stats', e);
    }
  };

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

  const trackPaperView = async (id: string) => {
    try {
      await apiEndpoints.trackPaperView(id, paper?.title);
    } catch (error) {
      console.debug('Failed to track paper view:', error);
    }
  };

  const fetchSimilarPapers = async (id: string, method: string) => {
    try {
      setSimilarLoading(true);
      setSimilarError(null);
      const res = await apiEndpoints.getSimilarPapers(id, method, 6);
      setSimilarPapers(res.data || []);
    } catch (error) {
      console.debug('Failed to fetch similar papers', error);
      setSimilarError('Failed to load similar papers');
      setSimilarPapers([]);
    } finally {
      setSimilarLoading(false);
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
            variant={isSaved ? 'contained' : 'outlined'}
            color={isSaved ? 'primary' : 'inherit'}
            startIcon={isSaved ? <BookmarkIcon /> : <BookmarkBorderIcon />}
            onClick={toggleSave}
            disabled={saveLoading}
          >
            {isSaved ? 'Saved' : 'Save'}
          </Button>
          <Button
            variant={isLiked ? 'contained' : 'outlined'}
            color={isLiked ? 'error' : 'inherit'}
            startIcon={isLiked ? <FavoriteIcon /> : <FavoriteBorderIcon />}
            onClick={toggleLike}
            disabled={likeLoading}
          >
            {isLiked ? 'Liked' : 'Like'}
          </Button>
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

        {/* Interaction Stats */}
        {stats && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" fontWeight="bold" gutterBottom>
              Engagement
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1 }}>
              <Chip label={`Likes: ${stats.likes}`} variant="outlined" />
              <Chip label={`Saves: ${stats.saves}`} variant="outlined" />
              <Chip label={`Views (7d): ${stats.views_7d}`} variant="outlined" />
              <Chip label={`Views (all): ${stats.views_total}`} variant="outlined" />
            </Stack>
          </Box>
        )}

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

        <Divider sx={{ my: 3 }} />

        <Box sx={{ mt: 1 }}>
          <Typography variant="h6" fontWeight="bold" gutterBottom>
            Similar Papers
          </Typography>

          <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap', gap: 1 }}>
            <Chip
              label="Concept"
              size="small"
              color={similarMethod === 'concept' ? 'primary' : 'default'}
              onClick={() => setSimilarMethod('concept')}
            />
            <Chip
              label="Author"
              size="small"
              color={similarMethod === 'author' ? 'primary' : 'default'}
              onClick={() => setSimilarMethod('author')}
            />
            <Chip
              label="Citation"
              size="small"
              color={similarMethod === 'citation' ? 'primary' : 'default'}
              onClick={() => setSimilarMethod('citation')}
            />
            <Chip
              label="Combined"
              size="small"
              color={similarMethod === 'combined' ? 'primary' : 'default'}
              onClick={() => setSimilarMethod('combined')}
            />
          </Stack>

          {similarLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={24} />
            </Box>
          )}

          {similarError && !similarLoading && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {similarError}
            </Alert>
          )}

          {!similarLoading && !similarError && similarPapers.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No similar papers found for this method.
            </Typography>
          )}

          {!similarLoading && similarPapers.length > 0 && (
            <Grid container spacing={2}>
              {similarPapers.map((sp, index) => (
                <Grid
                  item
                  xs={12}
                  sm={6}
                  md={4}
                  key={sp.arxiv_id || sp.external_url || `${sp.title}-${index}`}
                >
                  <Card
                    variant="outlined"
                    sx={{
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      cursor: sp.arxiv_id || sp.external_url ? 'pointer' : 'default',
                    }}
                    onClick={() => {
                      if (sp.arxiv_id) {
                        navigate(`/paper/${encodeURIComponent(sp.arxiv_id)}`);
                      } else if (sp.external_url) {
                        window.open(sp.external_url, '_blank', 'noopener,noreferrer');
                      }
                    }}
                  >
                    <CardContent sx={{ flex: 1 }}>
                      <Typography
                        variant="subtitle1"
                        fontWeight="bold"
                        gutterBottom
                        sx={{
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                        }}
                      >
                        {sp.title}
                      </Typography>
                      {sp.authors && sp.authors.length > 0 && (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ mb: 1 }}
                        >
                          {sp.authors.slice(0, 3).join(', ')}
                          {sp.authors.length > 3 && ' et al.'}
                        </Typography>
                      )}
                      <Stack
                        direction="row"
                        spacing={0.5}
                        flexWrap="wrap"
                        sx={{ gap: 0.5 }}
                      >
                        {sp.citation_count != null && (
                          <Chip
                            label={`Citations: ${sp.citation_count}`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {sp.similarity_score != null && (
                          <Chip
                            label={`Score: ${sp.similarity_score.toFixed(2)}`}
                            size="small"
                            color="secondary"
                          />
                        )}
                        <Chip
                          label={similarMethod}
                          size="small"
                          color="primary"
                        />
                        {sp.is_seminal && (
                          <Chip
                            label="Seminal"
                            size="small"
                            color="warning"
                          />
                        )}
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </Box>
      </Paper>
    </Container>
  );
};
