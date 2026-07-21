import { useState } from "react";
import type { ModelConfig, ModelConfigInput } from "../lib/api";
import { api } from "../lib/api";

const PROVIDERS = [
  { value: "openai_compat", label: "OpenAI 兼容（OpenAI/DeepSeek/GLM/Moonshot/自建网关）", default_url: "https://api.openai.com/v1" },
  { value: "gemini", label: "Google Gemini", default_url: "" },
  { value: "replicate", label: "Replicate / FAL（位图模型，预留）", default_url: "" },
];

const SUGGESTED = [
  { label: "OpenAI", url: "https://api.openai.com/v1", models: "gpt-4o, gpt-4o-mini, o1" },
  { label: "DeepSeek", url: "https://api.deepseek.com", models: "deepseek-chat, deepseek-reasoner" },
  { label: "智谱 GLM", url: "https://open.bigmodel.cn/api/paas/v4", models: "glm-4-plus, glm-4-flash" },
  { label: "Moonshot", url: "https://api.moonshot.cn/v1", models: "moonshot-v1-8k, kimi-k2" },
  { label: "Gemini", url: "", models: "gemini-1.5-pro, gemini-2.0-flash" },
];

const empty: ModelConfigInput = { name: "", provider: "openai_compat", base_url: "", model_name: "", api_key: "" };

export default function ModelConfigPage() {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<ModelConfigInput>({ ...empty });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [msg, setMsg] = useState<string>("");

  async function load() {
    setLoading(true);
    try {
      setModels(await api.listModels());
    } catch (e) {
      setMsg("加载失败：" + (e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // 第一次进入时加载
  if (loading === false && models.length === 0 && !msg) load();

  function reset() {
    setEditing({ ...empty });
    setEditingId(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      if (editingId === null) {
        await api.createModel(editing);
        setMsg("已添加");
      } else {
        await api.updateModel(editingId, editing);
        setMsg("已更新");
      }
      reset();
      await load();
    } catch (err) {
      setMsg("保存失败：" + (err as Error).message);
    }
  }

  async function remove(id: number) {
    if (!confirm("删除这个模型配置？")) return;
    await api.deleteModel(id);
    await load();
  }

  function startEdit(m: ModelConfig) {
    setEditingId(m.id);
    setEditing({
      name: m.name,
      provider: m.provider as ModelConfigInput["provider"],
      base_url: m.base_url,
      model_name: m.model_name,
      api_key: "",
    });
  }

  function fillSuggested(url: string) {
    setEditing({ ...editing, base_url: url });
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-lg border border-slate-200 p-5">
        <h2 className="font-semibold text-base mb-4">
          {editingId === null ? "添加模型配置" : "编辑模型配置（id=" + editingId + "）"}
        </h2>
        <form onSubmit={submit} className="space-y-3">
          <Field label="名称（标识）">
            <input
              className="input"
              value={editing.name}
              onChange={(e) => setEditing({ ...editing, name: e.target.value })}
              required
              placeholder="我的 GPT-4o"
            />
          </Field>
          <Field label="Provider 类型">
            <select
              className="input"
              value={editing.provider}
              onChange={(e) => setEditing({ ...editing, provider: e.target.value as ModelConfigInput["provider"] })}
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </Field>
          {editing.provider === "openai_compat" && (
            <Field label="base_url">
              <input
                className="input"
                value={editing.base_url}
                onChange={(e) => setEditing({ ...editing, base_url: e.target.value })}
                placeholder="https://api.openai.com/v1"
              />
              <div className="flex flex-wrap gap-1 mt-2">
                {SUGGESTED.filter((s) => s.url).map((s) => (
                  <button
                    key={s.url}
                    type="button"
                    onClick={() => fillSuggested(s.url)}
                    className="px-2 py-0.5 text-xs rounded bg-slate-100 hover:bg-slate-200"
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </Field>
          )}
          <Field label="模型名">
            <input
              className="input"
              value={editing.model_name}
              onChange={(e) => setEditing({ ...editing, model_name: e.target.value })}
              required
              placeholder="gpt-4o-mini"
            />
          </Field>
          <Field label={`API Key${editingId !== null ? "（留空则不更新）" : ""}`}>
            <input
              type="password"
              className="input"
              value={editing.api_key || ""}
              onChange={(e) => setEditing({ ...editing, api_key: e.target.value })}
              placeholder="sk-..."
            />
            <div className="text-xs text-slate-500 mt-1">
              Key 用 Fernet 对称加密存于本地 SQLite，仅在调用时解密。
            </div>
          </Field>
          <div className="flex gap-2">
            <button className="btn-primary" type="submit">
              保存
            </button>
            {editingId !== null && (
              <button className="btn-ghost" type="button" onClick={reset}>
                取消
              </button>
            )}
          </div>
          {msg && <div className="text-sm text-slate-700">{msg}</div>}
        </form>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-5">
        <h2 className="font-semibold text-base mb-4">已配置模型</h2>
        {loading ? (
          <div>加载中…</div>
        ) : models.length === 0 ? (
          <div className="text-slate-500 text-sm">暂无模型配置，请在左侧添加。</div>
        ) : (
          <ul className="space-y-3">
            {models.map((m) => (
              <li key={m.id} className="border border-slate-200 rounded-md p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{m.name}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      {m.provider} · {m.model_name}
                      {m.base_url && ` · ${m.base_url}`}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">key: {m.api_key_masked || "（空）"}</div>
                  </div>
                  <div className="flex gap-2">
                    <button className="btn-ghost" onClick={() => startEdit(m)}>
                      编辑
                    </button>
                    <button className="btn-danger" onClick={() => remove(m.id)}>
                      删除
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <style>{`
        .input { width: 100%; padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }
        .btn-primary { padding: 6px 16px; background: #0f172a; color: white; border-radius: 6px; font-size: 14px; }
        .btn-ghost { padding: 6px 14px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }
        .btn-danger { padding: 6px 14px; background: white; border: 1px solid #e2e8f0; color: #b91c1c; border-radius: 6px; font-size: 14px; }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      {children}
    </label>
  );
}
