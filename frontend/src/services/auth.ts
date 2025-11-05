import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const register = async (
  email: string,
  username: string,
  password: string,
  fullName?: string
): Promise<TokenResponse> => {
  const response = await axios.post<TokenResponse>(`${API_BASE_URL}/auth/register`, {
    email,
    username,
    password,
    full_name: fullName,
  });
  return response.data;
};

export const login = async (email: string, password: string): Promise<TokenResponse> => {
  const response = await axios.post<TokenResponse>(`${API_BASE_URL}/auth/login`, {
    email,
    password,
  });
  return response.data;
};

export const logout = async (token: string): Promise<void> => {
  await axios.post(
    `${API_BASE_URL}/auth/logout`,
    {},
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
};

export const getCurrentUser = async (token: string): Promise<User> => {
  const response = await axios.get<User>(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};
