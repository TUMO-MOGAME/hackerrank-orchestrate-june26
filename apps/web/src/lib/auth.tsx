"use client";

// Auth provider: uses Supabase Auth (email/password, Google OAuth, password reset) when
// configured, otherwise a local demo mode (localStorage) so the UI runs without any keys.
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { supabase, supabaseEnabled } from "./supabase";

export interface AuthUser {
  email: string;
  name?: string;
  avatarUrl?: string;
}

export type Role = "user" | "admin";

export function roleFor(email?: string | null): Role {
  return email && /admin|adjuster|reviewer/i.test(email) ? "admin" : "user";
}

interface AuthState {
  user: AuthUser | null;
  role: Role;
  loading: boolean;
  demo: boolean; // true when running without Supabase
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const DEMO_KEY = "claimlens.demo.user";
const AuthContext = createContext<AuthState | null>(null);

function readDemoUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(DEMO_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    if (supabaseEnabled && supabase) {
      supabase.auth.getSession().then(({ data }) => {
        if (!active) return;
        const u = data.session?.user;
        setUser(u ? toUser(u) : null);
        setLoading(false);
      });
      const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
        setUser(session?.user ? toUser(session.user) : null);
      });
      return () => {
        active = false;
        sub.subscription.unsubscribe();
      };
    }
    // demo mode
    setUser(readDemoUser());
    setLoading(false);
    return () => {
      active = false;
    };
  }, []);

  const setDemo = useCallback((u: AuthUser | null) => {
    if (typeof window !== "undefined") {
      if (u) window.localStorage.setItem(DEMO_KEY, JSON.stringify(u));
      else window.localStorage.removeItem(DEMO_KEY);
    }
    setUser(u);
  }, []);

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (supabaseEnabled && supabase) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw new Error(error.message);
        return;
      }
      if (!email || !password) throw new Error("Enter your email and password.");
      setDemo({ email, name: email.split("@")[0] });
    },
    [setDemo],
  );

  const signUp = useCallback(
    async (name: string, email: string, password: string) => {
      if (supabaseEnabled && supabase) {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { name } },
        });
        if (error) throw new Error(error.message);
        return;
      }
      if (!email || password.length < 6)
        throw new Error("Use a valid email and a 6+ character password.");
      setDemo({ email, name: name || email.split("@")[0] });
    },
    [setDemo],
  );

  const signInWithGoogle = useCallback(async () => {
    if (supabaseEnabled && supabase) {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: `${window.location.origin}/dashboard` },
      });
      if (error) throw new Error(error.message);
      return;
    }
    setDemo({ email: "demo@google.com", name: "Demo User" });
  }, [setDemo]);

  const resetPassword = useCallback(async (email: string) => {
    if (supabaseEnabled && supabase) {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (error) throw new Error(error.message);
      return;
    }
    if (!email) throw new Error("Enter the email tied to your account.");
    // demo: nothing to send, just resolve
  }, []);

  const signOut = useCallback(async () => {
    if (supabaseEnabled && supabase) await supabase.auth.signOut();
    setDemo(null);
  }, [setDemo]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      role: roleFor(user?.email),
      loading,
      demo: !supabaseEnabled,
      signIn,
      signUp,
      signInWithGoogle,
      resetPassword,
      signOut,
    }),
    [user, loading, signIn, signUp, signInWithGoogle, resetPassword, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toUser(u: any): AuthUser {
  return {
    email: u.email ?? "",
    name: u.user_metadata?.name ?? u.user_metadata?.full_name,
    avatarUrl: u.user_metadata?.avatar_url,
  };
}
