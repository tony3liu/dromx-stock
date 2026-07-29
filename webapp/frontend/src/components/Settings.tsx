import { useEffect, useState } from "react";
import { Settings as SettingsIcon, Loader2, Send, CheckCircle2, XCircle } from "lucide-react";
import { api } from "../api/client";
import type { NotifyChannels } from "../api/types";
import { cn } from "../lib/format";
import { getQuoteColorMode, setQuoteColorMode, type QuoteColorMode } from "../lib/quoteColor";
import { PageHeader } from "./PageHeader";
import { Input } from "./ui/Input";

export function Settings() {
  const [channels, setChannels] = useState<NotifyChannels | null>(null);
  const [loading, setLoading] = useState(true);
  const [quoteMode, setQuoteMode] = useState<QuoteColorMode>(getQuoteColorMode);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [systemEnabled, setSystemEnabled] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const loadChannels = () => {
    api.notifyChannels()
      .then((c) => { setChannels(c); setSystemEnabled(c.system.enabled); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(loadChannels, []);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await api.updateNotify({
        system: { enabled: systemEnabled },
        // Only send webhook fields the user actually filled (empty leaves prior value).
        feishu: { ...(webhookUrl.trim() ? { webhook_url: webhookUrl.trim() } : {}), ...(secret.trim() ? { secret: secret.trim() } : {}) },
      });
      setMsg({ ok: true, text: "已保存" });
      loadChannels();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "保存失败" });
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    setMsg(null);
    try {
      const res = await api.testNotify();
      const parts = Object.entries(res.results).map(([ch, ok]) => `${ch}: ${ok ? "✓" : "✗"}`);
      setMsg({ ok: res.ok, text: `测试发送：${parts.join("  ") || "无可用渠道"}` });
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "测试失败" });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        icon={<SettingsIcon size={18} />}
        title="设置 · 通知"
        subtitle="分析完成 / 监控告警的推送渠道（全免费）"
        maxWidth="760px"
      />

      <div className="mx-auto max-w-[760px] px-8 py-6">
      {/* 涨跌配色：全局立即生效，无需保存 */}
      <div className="mb-4 flex items-center justify-between rounded-[var(--radius-panel)] border border-[var(--color-border)] px-4 py-4">
        <div>
          <div className="text-sm font-semibold text-[var(--color-ink)]">涨跌配色</div>
          <div className="mt-0.5 text-xs text-[var(--color-ink-faint)]">
            海外习惯绿涨红跌，A 股习惯红涨绿跌
          </div>
        </div>
        <div className="flex overflow-hidden rounded-[var(--radius-control)] border border-[var(--color-border)]">
          {(["intl", "cn"] as const).map((m) => (
            <button
              key={m}
              onClick={() => { setQuoteColorMode(m); setQuoteMode(m); }}
              className={cn(
                "px-3 py-1.5 text-xs transition",
                quoteMode === m
                  ? "bg-[var(--color-brand)] text-white"
                  : "bg-[var(--color-surface)] text-[var(--color-ink-soft)] hover:bg-[var(--color-surface-2)]",
              )}
            >
              {m === "intl" ? "绿涨红跌" : "红涨绿跌"}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="flex items-center gap-2 py-16 text-sm text-[var(--color-ink-faint)]"><Loader2 size={16} className="animate-spin" /> 加载中…</div>
      ) : (
        <div className="rounded-[var(--radius-panel)] border border-[var(--color-border)] divide-y divide-[var(--color-border)]">
          {/* system notifications */}
          <div className="flex items-center justify-between px-4 py-4">
            <div>
              <div className="text-sm font-semibold text-[var(--color-ink)]">系统弹窗</div>
              <div className="mt-0.5 text-xs text-[var(--color-ink-faint)]">
                桌面通知中心弹窗{channels && !channels.system.available && "（当前平台不可用）"}
              </div>
            </div>
            <button
              onClick={() => setSystemEnabled((v) => !v)}
              className={cn("relative h-6 w-11 rounded-full transition-colors", systemEnabled ? "bg-[var(--color-brand)]" : "bg-[var(--color-border-strong)]")}
            >
              <span className={cn("absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-all", systemEnabled ? "left-[22px]" : "left-0.5")} />
            </button>
          </div>

          {/* feishu webhook */}
          <div className="px-4 py-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold text-[var(--color-ink)]">飞书 Webhook</div>
              {channels && (
                <span className={cn("flex items-center gap-1 text-xs", channels.feishu.configured ? "text-[var(--color-brand-dark)]" : "text-[var(--color-ink-faint)]")}>
                  <span className={cn("inline-block h-1.5 w-1.5 rounded-full", channels.feishu.configured ? "bg-[var(--color-brand)]" : "bg-[var(--color-border-strong)]")} />
                  {channels.feishu.configured ? "已配置" : "未配置"}
                </span>
              )}
            </div>
            <div className="space-y-2.5">
              <div>
                <label className="mb-1 block text-xs font-medium text-[var(--color-ink-faint)]">Webhook URL</label>
                <Input value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)}
                  placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/…" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-[var(--color-ink-faint)]">签名密钥（可选）</label>
                <Input type="password" value={secret} onChange={(e) => setSecret(e.target.value)}
                  placeholder="启用签名校验时填写" />
              </div>
              <p className="text-xs text-[var(--color-ink-faint)]">
                飞书群 → 设置 → 群机器人 → 添加「自定义机器人」，复制 Webhook 地址。留空则保留原值。
              </p>
            </div>
          </div>

          {/* actions row */}
          <div className="flex items-center gap-2 px-4 py-4">
            <button onClick={save} disabled={saving}
              className="btn-brand flex items-center gap-2 rounded-[var(--radius-control)] px-4 py-1.5 text-sm font-semibold disabled:opacity-50">
              {saving && <Loader2 size={15} className="animate-spin" />} 保存配置
            </button>
            <button onClick={test} disabled={testing}
              className="flex items-center gap-2 rounded-[var(--radius-control)] border border-[var(--color-border)] px-4 py-1.5 text-sm font-medium text-[var(--color-ink-soft)] transition hover:border-[var(--color-brand)] hover:text-[var(--color-brand-dark)] disabled:opacity-50">
              {testing ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />} 发送测试通知
            </button>
            {msg && (
              <span className={cn("flex items-center gap-1.5 text-sm", msg.ok ? "text-[var(--color-brand-dark)]" : "text-[var(--color-bear)]")}>
                {msg.ok ? <CheckCircle2 size={15} /> : <XCircle size={15} />} {msg.text}
              </span>
            )}
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
