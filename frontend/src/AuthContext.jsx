/**
 * AuthContext.jsx — État auth global (token JWT + user)
 *
 * Usage :
 *   const { user, login, logout, loading } = useAuth();
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { auth as authApi, getToken, setToken } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [loading, setLoading] = useState(true); // vrai tant que le token n'est pas vérifié

  // Au montage : si un token existe, récupérer le profil utilisateur
  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }

    authApi.me()
      .then(setUser)
      .catch(() => setToken(null)) // token expiré ou invalide
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const data = await authApi.login(email, password);
    setToken(data.access_token);
    const me = await authApi.me();
    setUser(me);
    return me;
  };

  const register = async (email, password, name) => {
    const data = await authApi.register(email, password, name);
    setToken(data.access_token);
    const me = await authApi.me();
    setUser(me);
    return me;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
