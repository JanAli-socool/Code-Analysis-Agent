import React, { createContext, useState, useEffect, useContext } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  }, []);

  const login = (userData) => {
    const userDataWithAvatar = {
      ...userData,
      avatar: userData.name?.charAt(0)?.toUpperCase() || 'U'
    };
    setUser(userDataWithAvatar);
    localStorage.setItem('user', JSON.stringify(userDataWithAvatar));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  const loginWithGoogle = () => {
    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    window.location.href = `${window.location.origin}/auth/google`;
  };

  const loginWithGithub = () => {
    window.location.href = `${window.location.origin}/auth/github`;
  };

  const value = {
    user,
    loading,
    login,
    logout,
    loginWithGoogle,
    loginWithGithub,
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}