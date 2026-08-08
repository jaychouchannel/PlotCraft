import { useEffect, useState } from "react";
import type { GenerationRecord } from "../lib/api";
import { api } from "../lib/api";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { vscodeDark } from "@uiw/codemirror-theme-vscode";

export default function HistoryPage() {
  const [items, setItems] = useState<GenerationRecord[]>([]);
  const [active, setActive] = useState<GenerationRecord | null>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  async function load() {
    try {
      setItems(await api.listHistory());
    } catch (e) {
      setMsg("加载失败：" + (e as Error).message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function selectRecord(r: GenerationRecord) {
    setActive(r);
    setSvg(null);
    if (r.status === "success") {
      try {
        const res = await api.getHistorySvg(r.id);
        setSvg(res.svg);
      } catch {
        // SVG 可能不存在（如旧记录），静默处理
      }
    }
  }

  async function clearAll() {
    if (!confirm("清空全部历史？")) return;
    await api.clearHistory();
    setItems([]);
    setActive(null);
  }

  async function remove(id: number) {
    await api.deleteHistory(id);
    setActive(null);
    await load();
  }

  return (
    <div className="grid grid-cols-12 gap-5">
      <div className="col-span-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">历史记录</h2>
          {items.length > 0 && (
            <button className="btn-ghost" onClick={clearAll}>
              清空
            </button>
          )}
        </div>
        <ul className="space-y-2 max-h-[75vh] overflow-auto">
          {items.length === 0 ? (
            <div className="text-slate-500 text-sm">暂无记录。</div>
          ) : (
            items.map((r) => (
              <li
                key={r.id}
                onClick={() => selectRecord(r)}
                className={`p-3 border rounded cursor-pointer text-sm ${
                  active?.id === r.id ? "bg-slate-100 border-slate-400" : "hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="font-mono text-xs">#{r.id} · model={r.model_id} · tpl={r.template_id ?? "-"}</div>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded ${
                      r.status === "success"
                        ? "bg-emerald-100 text-emerald-700"
                        : r.status === "error"
                        ? "bg-rose-100 text-rose-700"
                        : "bg-slate-100"
                    }`}
                  >
                    {r.status}
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-1 truncate">{r.user_input || "(no input)"}</div>
                <div className="text-[10px] text-slate-400 mt-1">{r.created_at}</div>
              </li>
            ))
          )}
        </ul>
      </div>

      <div className="col-span-7">
        {active ? (
          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs text-slate-500 mb-1">用户输入</div>
              <pre className="text-xs whitespace-pre-wrap font-mono">{active.user_input}</pre>
              {active.error && (
                <div className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded p-2 mt-2">{active.error}</div>
              )}
              <div className="flex gap-2 mt-3">
                <button className="btn-ghost" onClick={() => remove(active.id)}>
                  删除此记录
                </button>
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="font-semibold text-sm mb-2">生成的代码</div>
              <CodeMirror
                value={active.generated_code || ""}
                height="320px"
                theme={vscodeDark}
                extensions={[python()]}
                editable={false}
              />
            </div>
            {active.status === "success" && (
              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <div className="font-semibold text-sm mb-2">SVG 预览</div>
                <div className="border border-slate-200 rounded bg-slate-50 flex items-center justify-center min-h-[200px] p-3">
                  {svg ? (
                    <div
                      className="w-full h-full flex items-center justify-center"
                      dangerouslySetInnerHTML={{ __html: svg }}
                      style={{ maxHeight: "50vh" }}
                    />
                  ) : (
                    <div className="text-slate-400 text-sm">加载中…</div>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-slate-500 text-sm">点击左侧查看详情。</div>
        )}
      </div>

      <style>{`
        .btn-ghost { padding: 6px 14px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
      `}</style>
    </div>
  );
}
