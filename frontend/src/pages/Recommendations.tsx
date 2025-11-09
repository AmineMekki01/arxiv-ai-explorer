import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Chip,
  Button,
  Stack,
  Avatar,
  ToggleButtonGroup,
  ToggleButton,
  Skeleton,
  CircularProgress,
} from '@mui/material';
import {
  AutoAwesome as SparklesIcon,
  Favorite as FavoriteIcon,
  Bookmark as BookmarkIcon,
  Visibility as VisibilityIcon,
  Category as CategoryIcon,
  Insights as InsightsIcon,
  PictureAsPdf as PdfIcon,
} from '@mui/icons-material';
import { apiEndpoints } from '../services/api';

interface RecommendedPaper {
  arxiv_id: string;
  title: string;
  abstract: string | null;
  authors: string[];
  published_date: string | null;
  categories: string[];
  citation_count: number;
  recommendation_score: number;
  thumbnail_url?: string | null;
}

interface UserStats {
  views_count: number;
  saves_count: number;
  likes_count: number;
  shares_count: number;
  interactions_count: number;
  preferred_categories: string[];
  preferred_authors: string[];
}

const Recommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<RecommendedPaper[]>([]);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const [activeStrategy, setActiveStrategy] = useState<string>('all');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const navigate = useNavigate();
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const categoryColor = (cat: string): 'default' | 'primary' | 'secondary' | 'success' => {
    if (cat.startsWith('cs.AI')) return 'success';
    if (cat.startsWith('cs.LG') || cat.startsWith('stat.ML')) return 'primary';
    if (cat.startsWith('cs.CL')) return 'secondary';
    if (cat.startsWith('cs.CV')) return 'secondary';
    return 'default';
  };

  const LIMIT = 20;

  const fetchPage = async (targetPage: number, strategy: string) => {
    const strategies = strategy === 'all' ? 'content,citation,collaborative,trending' : strategy;
    const offset = targetPage * LIMIT;
    const isFirstPage = targetPage === 0;
    try {
      if (isFirstPage) setLoadingInitial(true); else setLoadingMore(true);
      const response = await apiEndpoints.getRecommendations(LIMIT, strategies, offset);
      const items: RecommendedPaper[] = response.data || [];
      setRecommendations((prev) => (isFirstPage ? items : [...prev, ...items]));
      setHasMore(items.length === LIMIT);
      setPage(targetPage);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      if (isFirstPage) setRecommendations([]);
      setHasMore(false);
    } finally {
      if (isFirstPage) setLoadingInitial(false); else setLoadingMore(false);
    }
  };

  const fetchUserStats = async () => {
    try {
      const response = await apiEndpoints.getUserStats();
      setUserStats(response.data);
      console.log("user stats: ", response.data)
    } catch (error) {
      console.error('Error fetching user stats:', error);
    }
  };

  useEffect(() => {
    setHasMore(true);
    setRecommendations([]);
    setPage(0);
    fetchPage(0, activeStrategy);
    fetchUserStats();
  }, [activeStrategy]);

  useEffect(() => {
    if (!hasMore || loadingInitial || loadingMore) return;
    const node = sentinelRef.current;
    if (!node) return;
    const observer = new IntersectionObserver((entries) => {
      const first = entries[0];
      if (first.isIntersecting && hasMore && !loadingMore) {
        fetchPage(page + 1, activeStrategy);
      }
    }, { root: null, rootMargin: '200px', threshold: 0 });
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, loadingInitial, loadingMore, page, activeStrategy]);

  const handlePaperClick = (arxivId: string, paperTitle: string) => {
    apiEndpoints.trackPaperView(arxivId, paperTitle);
    navigate(`/paper/${arxivId}`);
  };

  const strategyOptions = [
    { value: 'all', label: 'All Strategies', icon: '🎯' },
    { value: 'content', label: 'Similar to What You Like', icon: '📚' },
  ];

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'grey.50', py: 4 }}>
      <Container maxWidth="xl">
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            📖 Recommended for You
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Personalized paper recommendations based on your interests
          </Typography>
        </Box>

        {/* User Stats */}
        {userStats && userStats.views_count > 0 && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Your Reading Profile
              </Typography>
              <Grid container spacing={2} sx={{ mb: 1 }}>
                <Grid item xs={6} md={3}>
                  <Stack alignItems="center" spacing={1}>
                    <Avatar sx={{ bgcolor: 'primary.light', color: 'primary.dark', width: 40, height: 40 }}>
                      <VisibilityIcon />
                    </Avatar>
                    <Typography variant="h5" fontWeight={700} color="primary.main">
                      {userStats.views_count}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Papers Viewed</Typography>
                  </Stack>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Stack alignItems="center" spacing={1}>
                    <Avatar sx={{ bgcolor: 'success.light', color: 'success.dark', width: 40, height: 40 }}>
                      <BookmarkIcon />
                    </Avatar>
                    <Typography variant="h5" fontWeight={700} color="success.main">
                      {userStats.saves_count}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Papers Saved</Typography>
                  </Stack>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Stack alignItems="center" spacing={1}>
                    <Avatar sx={{ bgcolor: 'secondary.light', color: 'secondary.dark', width: 40, height: 40 }}>
                      <FavoriteIcon />
                    </Avatar>
                    <Typography variant="h5" fontWeight={700} color="secondary.main">
                      {userStats.likes_count}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Papers Liked</Typography>
                  </Stack>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Stack alignItems="center" spacing={1}>
                    <Avatar sx={{ bgcolor: 'warning.light', color: 'warning.dark', width: 40, height: 40 }}>
                      <InsightsIcon />
                    </Avatar>
                    <Typography variant="h5" fontWeight={700} color="warning.main">
                      {userStats.interactions_count}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Total Interactions</Typography>
                  </Stack>
                </Grid>
              </Grid>

              {userStats.preferred_categories.length > 0 && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    Your Top Categories:
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {userStats.preferred_categories.slice(0, 5).map((cat) => (
                      <Chip key={cat} label={cat} color={categoryColor(cat)} variant="outlined" size="small" icon={<CategoryIcon />} />
                    ))}
                  </Stack>
                </Box>
              )}

              {userStats.preferred_authors.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    Authors You Follow:
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {userStats.preferred_authors.slice(0, 5).map((author) => (
                      <Chip key={author} label={author} variant="outlined" size="small" />
                    ))}
                  </Stack>
                </Box>
              )}
            </CardContent>
          </Card>
        )}

        {/* Strategy Selector */}
        <Card sx={{ p: 1, mb: 3 }}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <Avatar sx={{ bgcolor: 'primary.light', color: 'primary.dark' }}>
              <SparklesIcon />
            </Avatar>
            <ToggleButtonGroup
              exclusive
              size="small"
              value={activeStrategy}
              onChange={(_, val) => val && setActiveStrategy(val)}
              color="primary"
            >
              {strategyOptions.map((option) => (
                <ToggleButton key={option.value} value={option.value}>
                  <Box component="span" sx={{ mr: 1 }}>{option.icon}</Box>
                  {option.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Stack>
        </Card>

        {/* Loading State */}
        {loadingInitial && (
          <Grid container spacing={3}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Grid item xs={12} sm={6} md={4} key={i}>
                <Card>
                  <Skeleton variant="rectangular" height={160} />
                  <CardContent>
                    <Skeleton width="60%" height={28} sx={{ mb: 1 }} />
                    <Skeleton width="40%" height={20} sx={{ mb: 2 }} />
                    <Skeleton width="100%" height={16} />
                    <Skeleton width="90%" height={16} />
                  </CardContent>
                  <CardActions sx={{ px: 2, pb: 2 }}>
                    <Skeleton variant="rectangular" width={90} height={32} sx={{ mr: 1 }} />
                    <Skeleton variant="rectangular" width={90} height={32} />
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}

        {/* No Recommendations */}
        {!loadingInitial && recommendations.length === 0 && (
          <Card sx={{ p: 6, textAlign: 'center' }}>
            <Typography variant="h2" sx={{ mb: 2 }}>📚</Typography>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 1 }}>Start Exploring!</Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              View some papers to get personalized recommendations
            </Typography>
            <Button variant="contained" onClick={() => navigate('/search')}>Browse Papers</Button>
          </Card>
        )}

        {/* Recommendations Grid */}
        {!loadingInitial && recommendations.length > 0 && (
          <Grid container spacing={2}>
            {recommendations.map((paper) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={paper.arxiv_id}>
                <Card
                  onClick={() => handlePaperClick(paper.arxiv_id, paper.title)}
                  sx={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', height: '100%', '&:hover': { boxShadow: 6 } }}
                  elevation={2}
                >
                  <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    {/* Score */}
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Score: {paper.recommendation_score}
                    </Typography>
                    
                    {/* Title */}
                    <Typography variant="subtitle1" fontWeight={700} gutterBottom sx={{ display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {paper.title}
                    </Typography>
                    {/* Authors */}
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      {paper.authors.slice(0, 3).join(', ')}
                      {paper.authors.length > 3 && ' et al.'}
                    </Typography>
                    {/* Abstract */}
                    {paper.abstract && (
                      <>
                        <Typography
                          variant="body2"
                          color="text.primary"
                          sx={{
                            mb: 1,
                            ...(expanded[paper.arxiv_id]
                              ? {}
                              : { display: '-webkit-box', WebkitLineClamp: 6, WebkitBoxOrient: 'vertical', overflow: 'hidden' }),
                          }}
                        >
                          {paper.abstract}
                        </Typography>
                        <Button
                          size="small"
                          variant="text"
                          onClick={(e) => { e.stopPropagation(); setExpanded((prev) => ({ ...prev, [paper.arxiv_id]: !prev[paper.arxiv_id] })); }}
                          sx={{ alignSelf: 'flex-start', mb: 1 }}
                        >
                          {expanded[paper.arxiv_id] ? 'Show less' : 'Show more'}
                        </Button>
                      </>
                    )}
                    {/* Categories */}
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
                      {paper.categories.slice(0, 3).map((cat) => (
                        <Chip key={cat} label={cat} size="small" color={categoryColor(cat)} variant="outlined" />
                      ))}
                    </Stack>
                    
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                          <Box component="span" sx={{ mr: 1 }}>{paper.arxiv_id}</Box>
                          {paper.published_date && (
                            <Box component="span">· {new Date(paper.published_date).toLocaleDateString()}</Box>
                          )}
                        </Typography>
                    </Box>
                    <Box sx={{ mt: 'auto', pt: 1 }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        
                        <Stack direction="row" spacing={1}>
                          <Button size="small" variant="contained" onClick={(e) => { e.stopPropagation(); handlePaperClick(paper.arxiv_id, paper.title); }}>
                            View Details
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<PdfIcon fontSize="small" />}
                            href={`https://arxiv.org/pdf/${paper.arxiv_id}.pdf`}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                          >
                            PDF
                          </Button>
                        </Stack>
                      </Stack>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
            {/* Sentinel for infinite scroll */}
            <Grid item xs={12}>
              <Box ref={sentinelRef} sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                {loadingMore && <CircularProgress size={24} />}
              </Box>
            </Grid>
          </Grid>
        )}
      </Container>
    </Box>
  );
};

export default Recommendations;
