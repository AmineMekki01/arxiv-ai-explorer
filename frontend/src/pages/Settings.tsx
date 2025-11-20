import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Alert,
  CircularProgress,
  Divider,
  Grid,
} from '@mui/material';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Category {
  code: string;
  name: string;
}

interface UserPreferences {
  preferred_categories: string[];
  theme: string;
  items_per_page: string;
  email_notifications: boolean;
  default_search_limit: string;
  default_context_strategy: string;
}

const Settings: React.FC = () => {
  const { token, user } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [categoriesRes, preferencesRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/preferences/categories`),
        axios.get(`${API_BASE_URL}/preferences`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      setCategories(categoriesRes.data.categories);
      setPreferences(preferencesRes.data);
      setSelectedCategories(preferencesRes.data.preferred_categories || []);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryToggle = (categoryCode: string) => {
    setSelectedCategories((prev) =>
      prev.includes(categoryCode)
        ? prev.filter((c) => c !== categoryCode)
        : [...prev, categoryCode]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const res = await fetch(`${API_BASE_URL}/preferences`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ preferred_categories: selectedCategories }),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody?.detail || 'Failed to save preferences');
      }
      setSuccess('Preferences saved successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err?.message || 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Container>
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Settings
        </Typography>
        <Typography variant="body1" color="text.secondary" gutterBottom>
          Manage your account preferences
        </Typography>

        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Account Information
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">
                  Email
                </Typography>
                <Typography variant="body1">{user?.email}</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">
                  Username
                </Typography>
                <Typography variant="body1">{user?.username}</Typography>
              </Grid>
              {user?.full_name && (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">
                    Full Name
                  </Typography>
                  <Typography variant="body1">{user.full_name}</Typography>
                </Grid>
              )}
            </Grid>
          </CardContent>
        </Card>

        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Research Interests
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Select your preferred arXiv categories to get personalized recommendations
            </Typography>
            <Divider sx={{ my: 2 }} />

            {success && (
              <Alert severity="success" sx={{ mb: 2 }}>
                {success}
              </Alert>
            )}

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 3 }}>
              {categories.map((category) => (
                <Chip
                  key={category.code}
                  label={`${category.code} - ${category.name}`}
                  onClick={() => handleCategoryToggle(category.code)}
                  color={selectedCategories.includes(category.code) ? 'primary' : 'default'}
                  variant={selectedCategories.includes(category.code) ? 'filled' : 'outlined'}
                  sx={{ cursor: 'pointer' }}
                />
              ))}
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {selectedCategories.length} {selectedCategories.length === 1 ? 'category' : 'categories'} selected
              </Typography>
              <Button
                variant="contained"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? <CircularProgress size={24} /> : 'Save Preferences'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};

export default Settings;
