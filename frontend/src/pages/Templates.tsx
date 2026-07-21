import { useEffect, useState } from "react";
import type { Template } from "../lib/api";
import { api } from "../lib/api";

export default function TemplatesPage() {
  const [items, setItems] = useState<Template[]>([]);
  const [active, setActive] = useState<Template | null>(null);
  const [msg, setMsg] = useState("");
  const [filter, setFilter] = useState("");

  async function load() {
    try {
      setItems(await api.listTemplates());
    } catch (e) {
      setMsg("加载失败：" + (e as Error).message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  const categories = Array.from(new Set(items.map((t) => t.category || "未分类")));
  const shown = filter ? items.filter((t) => t.name.includes(filter) || t.category.includes(filter)) : items;

  function startNew() {
    setActive({ id: 0, name: "", category: "", system_prompt: "", user_template: "", builtin: false });
  }

  async function save(t: Template) {
    setMsg("");
    const body = { name: t.name, category: t.category, system_prompt: t.system_prompt, user_template: t.user_template };
    try {
      if (t.id === 0) {
        await api.createTemplate(body);
      } else {
        await api.updateTemplate(t.id, body);
      }
      await load();
      setActive(null);
      setMsg("已保存");
    } catch (e) {
      setMsg("保存失败：" + (e as Error).message);
    }
  }

  async function del(id: number) {
    if (!confirm("删除此模板？")) return;
    try {
      await api.deleteTemplate(id);
      await load();
      if (active?.id === id) setActive(null);
    } catch (e) {
      setMsg("删除失败：" + (e as Error).message);
    }
  }

  function copyAsNew(t: Template) {
    setActive({ id: 0, name: t.name + " (副本)", category: t.category, system_prompt: t.system_prompt, user_template: t.user_template, builtin: false });
  }

  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">模板列表</h2>
          <div className="flex gap-2">
            <input
              placeholder="搜索"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="px-2 py-1 text-sm border border-slate-300 rounded"
            />
            <button className="btn-primary" onClick={startNew}>
              + 新建
            </button>
          </div>
        </div>
        <div className="space-y-4 max-h-[70vh] overflow-auto pr-2">
          {categories.map((cat) => (
            <div key={cat}>
              <div className="text-xs text-slate-500 mb-1">{cat}</div>
              <ul className="space-y-1">
                {shown
                  .filter((t) => (t.category || "未分类") === cat)
                  .map((t) => (
                    <li
                      key={t.id}
                      onClick={() => setActive(t)}
                      className={`p-2 rounded border cursor-pointer text-sm ${
                        active?.id === t.id ? "bg-slate-100 border-slate-400" : "border-transparent hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{t.name}</span>
                        {t.builtin && <span className="text-[10px] px-1 bg-slate-200 rounded">内置</span>}
                      </div>
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="col-span-7">
        {active ? (
          <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-3">
            <input
              className="w-full text-lg font-semibold focus:outline-none border-b border-transparent focus:border-slate-300 pb-1"
              value={active.name}
              onChange={(e) => setActive({ ...active, name: e.target.value })}
              placeholder="模板名称"
            />
            <div>
              <div className="text-xs text-slate-500 mb-1">分类</div>
              <input
                className="w-full input"
                value={active.category}
                onChange={(e) => setActive({ ...active, category: e.target.value })}
                placeholder="如：折线、柱状、热图"
              />
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">System Prompt（留空则用默认科研绘图约束）</div>
              <textarea
                rows={5}
                className="w-full input font-mono text-xs"
                value={active.system_prompt}
                onChange={(e) => setActive({ ...active, system_prompt: e.target.value })}
              />
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">User Prompt 模板（用户填空后会发送给 LLM）</div>
              <textarea
                rows={10}
                className="w-full input font-mono text-xs"
                value={active.user_template}
                onChange={(e) => setActive({ ...active, user_template: e.target.value })}
              />
            </div>
            <div className="flex gap-2">
              <button className="btn-primary" onClick={() => save(active)}>
                保存
              </button>
              {active.builtin && (
                <button className="btn-ghost" onClick={() => copyAsNew(active)}>
                  另存为副本（再编辑）
                </button>
              )}
              {!active.builtin && active.id !== 0 && (
                <button className="btn-danger" onClick={() => del(active.id)}>
                  删除
                </button>
              )}
              <button className="btn-ghost" onClick={() => setActive(null)}>
                关闭
              </button>
            </div>
            {msg && <div className="text-sm">{msg}</div>}
          </div>
        ) : (
          <div className="text-slate-500 text-sm">点击左侧模板查看与编辑。</div>
        )}
      </div>

      <style>{`
        .input { padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
        .btn-primary { padding: 6px 14px; background: #0f172a; color: white; border-radius: 6px; font-size: 13px; }
        .btn-ghost { padding: 6px 14px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
        .btn-danger { padding: 6px 14px; color: #b91c1c; background: white; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px; }
      `}</style>
    </div>
  );
}
