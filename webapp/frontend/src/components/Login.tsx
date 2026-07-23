import { useState } from "react";
import { Loader2, ArrowRight } from "lucide-react";
import { api } from "../api/client";
import { setToken } from "../lib/auth";
import { Logo } from "./Logo";
import { Card } from "./ui/Card";
import { Input } from "./ui/Input";

/** Single-password gate. Shown when the backend requires auth and we have no token. */
export function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!password.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const { token } = await api.login(password);
      setToken(token);
      onSuccess();
    } catch {
      setError("口令错误，请重试");
      setBusy(false);
    }
  };

  return (
    <div className="bg-dots relative flex h-screen w-screen items-center justify-center overflow-hidden bg-[var(--color-canvas)]">
      {/* breathing ambient glow behind the card */}
      <div
        className="breathe pointer-events-none absolute left-1/2 top-1/3 h-[380px] w-[620px] rounded-full opacity-50 blur-[110px]"
        style={{ background: "radial-gradient(closest-side, rgba(6,193,103,0.16), transparent)" }}
      />
      <Card
        role="dialog"
        aria-modal="true"
        aria-label="访问口令登录"
        className="relative w-[24rem] animate-pop p-8"
      >
        <div
          className="mb-5 grid h-12 w-12 place-items-center rounded-2xl"
          style={{ boxShadow: "var(--shadow-brand)" }}
        >
          <Logo size={48} className="rounded-2xl" />
        </div>
        <h1 className="text-xl font-black tracking-tight text-[var(--color-ink)]">
          Drom<span className="gradient-text-static">X</span>
        </h1>
        <p className="mt-1 mb-6 text-sm text-[var(--color-ink-soft)]">让 AI 读懂每一支股票 · 输入访问口令以继续</p>

        <Input
          tone="inset"
          size="lg"
          type="password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="访问口令"
          aria-label="访问口令"
          className="text-sm"
        />
        {error && <p className="mt-2 text-sm text-[var(--color-bear)]">{error}</p>}

        <button
          onClick={submit}
          disabled={busy || !password.trim()}
          className="btn-brand mt-5 flex w-full items-center justify-center gap-2 rounded-[var(--radius-btn)] px-4 py-2.5 font-semibold"
        >
          {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
          进入
        </button>
      </Card>
    </div>
  );
}
