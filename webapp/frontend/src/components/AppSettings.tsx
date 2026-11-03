import { useEffect, useState } from "react";
import { SlidersHorizontal, Loader2, CheckCircle2, XCircle, RotateCcw } from "lucide-react";
import { api } from "../api/client";
import type { EnvSettingItem } from "../api/types";
import { cn } from "../lib/format";
import { PageHeader } from "./PageHeader";
import { Input } from "./ui/Input";

const GROUP_ORDER = ["模型", "模型密钥", "数据源"];

export function AppSettings() {
  const [items, setItems] = useState<EnvSettingItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  // 页面编辑态：key → 输入框内容（只记录被用户改过的）
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = () => {
    api.envSettings()
      .then((r) => setItems(r.settings))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const save = async () => {
    if (!Object.keys(edits).length) return;
    setSaving(true);
    setMsg(null);
    try {
      const res = await api.updateEnvSettings(edits);
      setEdits({});
      setMsg({
        ok: true,
        text: res.llm_changed ? "已保存，模型配置已生效（投研助手下次提问使用新配置）" : "已保存",
      });
      load();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "保存失败" });
    } finally {
      setSaving(false);
    }
  };

  // 清除某个 key 的页面配置（回落 .env）
  const clearOverride = async (key: string) => {
    setSaving(true);
    setMsg(null);
    try {
      await api.updateEnvSettings({ [key]: "" });
      setEdits((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
      setMsg({ ok: true, text: "已清除页面配置，回落到 .env" });
      load();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "操作失败" });
    } finally {
      setSaving(false);
    }
  };

  const groups = GROUP_ORDER
    .map((g) => ({ name: g, items: (items ?? []).filter((i) => i.group === g) }))
    .filter((g) => g.items.length > 0);

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        icon={<SlidersHorizontal size={18} />}
        title="应用配置"
        subtitle="模型与数据源密钥，页面配置优先级高于 .env（.env 为保底）"
        maxWidth="760px"
      />

      <div className="mx-auto max-w-[760px] px-8 py-6">
        {loading ? (
          <div className="flex items-center gap-2 py-16 text-sm text-[var(--color-ink-faint)]">
            <Loader2 size={16} className="animate-spin" /> 加载中…
          </div>
        ) : (
          <div className="space-y-4">
            {groups.map((group) => (
              <div
                key={group.name}
                className="rounded-[var(--radius-panel)] border border-[var(--color-border)]"
              >
                <div className="border-b border-[var(--color-border)] px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-[var(--color-ink-faint)]">
                  {group.name}
                </div>
                <div className="divide-y divide-[var(--color-border)]">
                  {group.items.map((item) => (
                    <SettingRow
                      key={item.key}
                      item={item}
                      edit={edits[item.key]}
                      onEdit={(v) =>
                        setEdits((prev) => ({ ...prev, [item.key]: v }))
                      }
                      onClear={() => clearOverride(item.key)}
                      disabled={saving}
                    />
                  ))}
                </div>
              </div>
            ))}

            <div className="flex items-center justify-between pt-2">
              <div>
                {msg && (
                  <span
                    className={cn(
                      "flex items-center gap-1.5 text-sm",
                      msg.ok ? "text-[var(--color-brand-dark)]" : "text-[var(--color-danger)]",
                    )}
                  >
                    {msg.ok ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                    {msg.text}
                  </span>
                )}
              </div>
              <button
                onClick={save}
                disabled={saving || !Object.keys(edits).length}
                className="btn-brand rounded-[var(--radius-control)] px-5 py-2 text-sm font-semibold disabled:opacity-50"
              >
                {saving ? "保存中…" : "保存配置"}
              </button>
            </div>

            <p className="text-xs leading-relaxed text-[var(--color-ink-faint)]">
              页面配置保存在 ~/.dromx/user_settings.json，立即生效；清空输入框并保存（或点「重置」）
              即清除页面配置、回落到 .env 的值。密钥只保存不显示原文。
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function SettingRow({
  item,
  edit,
  onEdit,
  onClear,
  disabled,
}: {
  item: EnvSettingItem;
  edit: string | undefined;
  onEdit: (v: string) => void;
  onClear: () => void;
  disabled: boolean;
}) {
  const dirty = edit !== undefined && edit !== (item.value ?? "");
  const sourceBadge =
    item.source === "page" ? (
      <span className="rounded bg-[var(--color-brand-tint)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-brand-dark)]">
        页面配置
      </span>
    ) : item.source === "env" ? (
      <span className="rounded bg-[var(--color-surface-2)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-ink-faint)]">
        .env
      </span>
    ) : (
      <span className="rounded bg-[var(--color-surface-2)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-ink-faint)]">
        未配置
      </span>
    );

  return (
    <div className="px-4 py-3">
      <div className="mb-1.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[var(--color-ink)]">{item.label}</span>
          {sourceBadge}
          {item.secret && item.configured && (
            <span className="text-xs text-[var(--color-ink-faint)]">{item.preview}</span>
          )}
        </div>
        {item.source === "page" && (
          <button
            onClick={onClear}
            disabled={disabled}
            title="清除页面配置，回落 .env"
            className="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-[var(--color-ink-faint)] transition hover:bg-[var(--color-surface-2)] hover:text-[var(--color-danger)]"
          >
            <RotateCcw size={11} /> 重置
          </button>
        )}
      </div>
      <Input
        type={item.secret ? "password" : "text"}
        value={edit ?? (item.secret ? "" : item.value ?? "")}
        onChange={(e) => onEdit(e.target.value)}
        placeholder={
          item.secret
            ? item.configured
              ? "已配置，输入新值以覆盖"
              : item.placeholder || `输入 ${item.key}`
            : item.placeholder
        }
        disabled={disabled}
        className={cn(dirty && "border-[var(--color-brand)]")}
      />
      {item.hint && <p className="mt-1 text-xs text-[var(--color-ink-faint)]">{item.hint}</p>}
    </div>
  );
}
