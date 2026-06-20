// ClaimLens mobile (Expo / React Native) — "forensic editorial" theme, shared tokens.
// Self-contained: sign in / sign up / forgot password + a claim screen, demo auth (local
// state). Production: wire Supabase via expo-auth-session for Google + email/password.

import { useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextStyle,
} from "react-native";
import { theme, verdictMeta } from "@claimreview/shared";

type Screen = "signin" | "signup" | "forgot" | "app";

const C = theme.color;

export default function App() {
  const [screen, setScreen] = useState<Screen>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const go = (s: Screen) => {
    setNotice(null);
    setScreen(s);
  };

  if (screen === "app") return <AppScreen email={email} onSignOut={() => go("signin")} />;

  return (
    <ScrollView contentContainerStyle={s.screen} keyboardShouldPersistTaps="handled">
      <View style={s.brandRow}>
        <View style={s.mark}>
          <View style={s.markDot} />
        </View>
        <Text style={s.brand}>
          Claim<Text style={{ color: C.ember }}>Lens</Text>
        </Text>
      </View>

      <Text style={s.eyebrow}>EVIDENCE-GROUNDED ADJUDICATION</Text>
      <Text style={s.h1}>
        {screen === "signin" ? "Welcome back" : screen === "signup" ? "Create account" : "Reset password"}
      </Text>
      <Text style={s.sub}>
        {screen === "signin"
          ? "Sign in to review claims on your phone."
          : screen === "signup"
            ? "Adjudicate claims in minutes."
            : "We'll email you a secure reset link."}
      </Text>

      <View style={s.card}>
        {notice && <Text style={s.notice}>{notice}</Text>}

        {screen !== "forgot" && (
          <Pressable
            style={[s.btn, s.btnGhost]}
            onPress={() => {
              setEmail("demo@google.com");
              go("app");
            }}
          >
            <Text style={s.btnGhostText}>Continue with Google</Text>
          </Pressable>
        )}
        {screen !== "forgot" && <Text style={s.or}>or with email</Text>}

        {screen === "signup" && (
          <Field label="Full name" value={name} onChange={setName} placeholder="Avery Stone" />
        )}
        <Field label="Email" value={email} onChange={setEmail} placeholder="you@company.com" keyboard="email-address" />
        {screen !== "forgot" && (
          <Field label="Password" value={password} onChange={setPassword} placeholder="••••••••" secure />
        )}

        {screen === "signin" && (
          <Pressable onPress={() => go("forgot")} style={{ alignSelf: "flex-end" }}>
            <Text style={s.link}>Forgot password?</Text>
          </Pressable>
        )}

        <Pressable
          style={[s.btn, s.btnEmber]}
          onPress={() => {
            if (screen === "forgot") {
              setNotice("If an account exists, a reset link is on its way. (Demo)");
            } else {
              go("app");
            }
          }}
        >
          <Text style={s.btnEmberText}>
            {screen === "signin" ? "Sign in" : screen === "signup" ? "Create account" : "Send reset link"}
          </Text>
        </Pressable>
      </View>

      <View style={s.footRow}>
        {screen === "signin" && (
          <Text style={s.footText}>
            New here?{" "}
            <Text style={s.link} onPress={() => go("signup")}>
              Create an account
            </Text>
          </Text>
        )}
        {screen === "signup" && (
          <Text style={s.footText}>
            Have an account?{" "}
            <Text style={s.link} onPress={() => go("signin")}>
              Sign in
            </Text>
          </Text>
        )}
        {screen === "forgot" && (
          <Text style={s.link} onPress={() => go("signin")}>
            Back to sign in
          </Text>
        )}
      </View>
      <Text style={s.demoFlag}>demo mode · any details work</Text>
    </ScrollView>
  );
}

function AppScreen({ email, onSignOut }: { email: string; onSignOut: () => void }) {
  const v = verdictMeta("supported");
  return (
    <ScrollView contentContainerStyle={s.screen}>
      <View style={s.appBar}>
        <Text style={s.brand}>
          Claim<Text style={{ color: C.ember }}>Lens</Text>
        </Text>
        <Pressable onPress={onSignOut}>
          <Text style={s.link}>Sign out</Text>
        </Pressable>
      </View>
      <Text style={s.eyebrow}>SIGNED IN AS</Text>
      <Text style={[s.sub, { marginBottom: 18 }]}>{email}</Text>

      <View style={s.card}>
        <Text style={s.eyebrow}>SAMPLE DECISION · case_001 · car</Text>
        <Text style={[s.verdict, { color: v.color }]}>{v.label}</Text>
        <Text style={s.just}>
          img_1 clearly shows a dent on the rear bumper consistent with the customer&apos;s account;
          history adds no risk.
        </Text>
        <View style={s.statGrid}>
          <Stat label="Issue" value="dent" />
          <Stat label="Part" value="rear_bumper" />
          <Stat label="Severity" value="medium" />
          <Stat label="Authenticity" value="genuine" color={C.supported} />
        </View>
      </View>
      <Text style={s.demoFlag}>Connect the agent API to adjudicate live claims.</Text>
    </ScrollView>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  secure,
  keyboard,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  secure?: boolean;
  keyboard?: "email-address";
}) {
  return (
    <View style={{ marginBottom: 14 }}>
      <Text style={s.label}>{label}</Text>
      <TextInput
        style={s.input}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={C.inkFaint}
        secureTextEntry={secure}
        keyboardType={keyboard}
        autoCapitalize="none"
      />
    </View>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <View style={s.stat}>
      <Text style={s.statLabel}>{label}</Text>
      <Text style={[s.statValue, color ? { color } : null]}>{value}</Text>
    </View>
  );
}

const bold: TextStyle = { fontWeight: "700" };

const s = StyleSheet.create({
  screen: { flexGrow: 1, backgroundColor: C.paper, padding: 24, paddingTop: 72 },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 28 },
  mark: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 1.6,
    borderColor: C.ink,
    alignItems: "center",
    justifyContent: "center",
  },
  markDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: C.ember },
  brand: { fontSize: 22, color: C.ink, ...bold, letterSpacing: -0.5 },
  eyebrow: { fontSize: 11, letterSpacing: 2, color: C.emberDeep, ...bold },
  h1: { fontSize: 34, color: C.ink, ...bold, marginTop: 10, letterSpacing: -1 },
  sub: { fontSize: 15, color: C.inkSoft, marginTop: 8 },
  card: {
    backgroundColor: C.paperRaised,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: C.line,
    padding: 22,
    marginTop: 24,
  },
  label: { fontSize: 13, color: C.inkSoft, ...bold, marginBottom: 6 },
  input: {
    backgroundColor: C.paper,
    borderWidth: 1,
    borderColor: C.lineStrong,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 13,
    fontSize: 16,
    color: C.ink,
  },
  btn: { borderRadius: 999, paddingVertical: 15, alignItems: "center", marginTop: 6 },
  btnEmber: { backgroundColor: C.ember },
  btnEmberText: { color: "#fff", fontSize: 16, ...bold },
  btnGhost: { borderWidth: 1, borderColor: C.lineStrong, backgroundColor: "transparent" },
  btnGhostText: { color: C.ink, fontSize: 15, ...bold },
  or: { textAlign: "center", color: C.inkFaint, fontSize: 13, marginVertical: 14 },
  link: { color: C.emberDeep, ...bold, fontSize: 14 },
  footRow: { alignItems: "center", marginTop: 22 },
  footText: { color: C.inkSoft, fontSize: 14 },
  demoFlag: { textAlign: "center", color: C.inkFaint, fontSize: 12, marginTop: 18 },
  notice: {
    color: C.supported,
    backgroundColor: "rgba(63,125,91,0.1)",
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
    fontSize: 13,
  },
  appBar: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 22 },
  verdict: { fontSize: 30, ...bold, marginTop: 8 },
  just: { color: C.inkSoft, fontSize: 14, marginTop: 8, lineHeight: 20 },
  statGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 18 },
  stat: {
    flexBasis: "47%",
    backgroundColor: C.paper,
    borderWidth: 1,
    borderColor: C.line,
    borderRadius: 10,
    padding: 12,
  },
  statLabel: { fontSize: 11, color: C.inkFaint, letterSpacing: 0.5 },
  statValue: { fontSize: 15, color: C.ink, marginTop: 3, ...bold },
});
