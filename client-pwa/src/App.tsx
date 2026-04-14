import { useState, useEffect, createContext, useContext } from 'react';
import { authAPI } from './services/api';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import AppShell from './components/AppShell';
import './index.css';

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  name: string;
}

interface AuthContextType {
  user: User;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | null>(null);
export const useAuth = () => useContext(AuthContext)!;

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [showRegister, setShowRegister] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);

  // Check for password reset token in URL
  const resetToken = (() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('reset_token') || '';
  })();

  useEffect(() => {
    const token = localStorage.getItem('client_access_token');
    if (token) {
      authAPI.me()
        .then(res => setUser(res.data))
        .catch(() => {
          localStorage.removeItem('client_access_token');
          localStorage.removeItem('client_refresh_token');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogin = (userData: User, accessToken: string, refreshToken: string) => {
    localStorage.setItem('client_access_token', accessToken);
    localStorage.setItem('client_refresh_token', refreshToken);
    setUser(userData);
  };

  const handleLogout = async () => {
    const refresh = localStorage.getItem('client_refresh_token');
    if (refresh) {
      try { await authAPI.logout(refresh); } catch { }
    }
    localStorage.removeItem('client_access_token');
    localStorage.removeItem('client_refresh_token');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" style={{ width: 40, height: 40 }}></div>
        <div className="loading-screen-text">Loading IntZam...</div>
      </div>
    );
  }

  if (!user) {
    // Handle password reset link from email
    if (resetToken) {
      return (
        <ResetPasswordPage
          token={resetToken}
          onSuccess={() => {
            // Clear token from URL and show login
            window.history.replaceState({}, document.title, window.location.pathname);
            window.location.reload();
          }}
        />
      );
    }

    if (showRegister) {
      return <RegisterPage onRegister={handleLogin} onBack={() => setShowRegister(false)} />;
    }

    if (showForgotPassword) {
      return <ForgotPasswordPage onBack={() => setShowForgotPassword(false)} />;
    }

    return (
      <LoginPage
        onLogin={handleLogin}
        onNavigateRegister={() => setShowRegister(true)}
        onForgotPassword={() => setShowForgotPassword(true)}
      />
    );
  }

  return (
    <AuthContext.Provider value={{ user, logout: handleLogout }}>
      <AppShell />
    </AuthContext.Provider>
  );
}

export default App;
