import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { vscodeDark } from "@uiw/codemirror-theme-vscode";
import { diffLines, Change } from "diff";
import type { GenerateResponse, ModelConfig, Template } from "../lib/api";
import { api } from "../lib/api";

export default function GeneratePage() {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [modelId, setModelId] = useState<number | null>(null);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [userPrompt, setUserPrompt] = useState("");
  const [systemOverride, setSystemOverride] = useState("");
  const [showSystem, setShowSystem] = useState(false);
  const [temperature, setTemperature] = useState(0.2);
  const [render, setRender] = useState(true);
  const [busy, setBusy] = useState(false);
  const [resp, setResp] = useState<GenerateResponse | null>(null);
  const [err, setErr] = useState("");
  const [code, setCode] = useState("");
  const [originalCode, setOriginalCode] = useState("");
  const [showDiff, setShowDiff] = useState(false);
  const svgRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const userModifiedRef = useRef(false); // 追踪用户是否手动修改了 systemOverride

  useEffect(() => {
    return () => {
      // 离开页面时取消正在进行的请求
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [m, t] = await Promise.all([api.listModels(), api.listTemplates()]);
        setModels(m);
        setTemplates(t);
        if (m.length && modelId === null) setModelId(m[0].id);
      } catch (e) {
        setErr("加载失败：" + (e as Error).message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 当用户选择模板，把 user_template 灌入编辑框
  const tpl = useMemo(() => templates.find((t) => t.id === templateId) || null, [templates, templateId]);
  useEffect(() => {
    // 切换模板时重置用户修改标记
    userModifiedRef.current = false;
    if (tpl?.user_template && !userPrompt) {
      setUserPrompt(tpl.user_template);
    }
    // 仅在用户未手动修改时，才将 systemOverride 同步为模板默认值
    if (tpl?.system_prompt && !userModifiedRef.current) {
      setSystemOverride(tpl.system_prompt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templateId]);

  // 用户手动编辑 systemOverride 时标记为已修改
  const handleSystemOverrideChange = useCallback((value: string) => {
    userModifiedRef.current = true;
    setSystemOverride(value);
  }, []);

  async function run() {
    if (!modelId) {
      setErr("请先在「模型」页配置 AI 模型");
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setBusy(true);
    setErr("");
    setResp(null);
    try {
      const r = await api.generate({
        model_id: modelId,
        template_id: templateId,
        system_prompt: systemOverride || null,
        user_prompt: userPrompt,
        temperature,
        render,
      }, ac.signal);
      if (ac.signal.aborted) return;
      setResp(r);
      setCode(r.generated_code || "");
      setOriginalCode(r.generated_code || "");
      if (r.status === "error") setErr(r.error || "生成失败");
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setErr("请求失败：" + (e as Error).message);
    } finally {
      if (!abortRef.current?.signal.aborted) setBusy(false);
    }
  }

  async function rerender() {
    if (!code) return;
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setBusy(true);
    setErr("");
    try {
      const r = await api.render(code, ac.signal);
      if (ac.signal.aborted) return;
      setResp(r);
      if (r.status === "error") setErr(r.error);
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setErr("渲染失败：" + (e as Error).message);
    } finally {
      if (!abortRef.current?.signal.aborted) setBusy(false);
    }
  }

  async function downloadFormat(fmt: "png" | "pdf" | "svg") {
    if (!code) return;
    setBusy(true);
    setErr("");
    try {
      const res = await api.downloadFormat(code, fmt);
      if (!res.ok) {
        const t = await res.text().catch(() => res.statusText);
        setErr(`下载失败: ${res.status} ${t}`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `plot.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr("下载失败：" + (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function downloadCode() {
    if (!code) return;
    const blob = new Blob([code], { type: "text/x-python" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "plot.py";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="grid grid-cols-12 gap-5">
      {/* 左：配置 + 输入 */}
      <div className="col-span-5 space-y-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
          <div>
            <label className="text-xs text-slate-500">模型</label>
            <select
              className="w-full input mt-1"
              value={modelId ?? ""}
              onChange={(e) => setModelId(Number(e.target.value))}
            >
              <option value="">— 选择模型 —</option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} · {m.model_name}
                </option>
              ))}
            </select>
            {models.length === 0 && (
              <div className="text-xs text-rose-600 mt-1">尚未配置模型，请到「模型」页添加。</div>
            )}
          </div>
          <div>
            <label className="text-xs text-slate-500">模板</label>
            <select
              className="w-full input mt-1"
              value={templateId ?? ""}
              onChange={(e) => setTemplateId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">— 不使用模板 —</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  [{t.category}] {t.name}
                  {t.builtin ? " · 内置" : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={render} onChange={(e) => setRender(e.target.checked)} />
              生成后立即渲染
            </label>
            <label className="flex items-center gap-2">
              temperature
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={temperature}
                onChange={(e) => setTemperature(Number(e.target.value))}
                className="w-16 input"
              />
            </label>
          </div>
          <div>
            <button
              className="text-xs text-slate-500 underline"
              onClick={() => setShowSystem((v) => !v)}
            >
              {showSystem ? "收起" : "自定义"} System Prompt
            </button>
            {showSystem && (
              <textarea
                rows={5}
                className="w-full input font-mono text-xs mt-2"
                value={systemOverride}
                onChange={(e) => handleSystemOverrideChange(e.target.value)}
                placeholder="留空则使用后端默认科研绘图约束；选择模板时默认填入模板的 system_prompt"
              />
            )}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs text-slate-500">用户提示词（如选了模板会自动填入模板内容，可继续修改）</label>
            <button
              className="text-xs text-slate-500 underline"
              onClick={() => setUserPrompt("")}
            >
              清空
            </button>
          </div>
          <textarea
            rows={14}
            className="w-full input font-mono text-xs"
            value={userPrompt}
            onChange={(e) => setUserPrompt(e.target.value)}
            placeholder={"描述你要绘制的图，例如：\n- 5 条曲线，x 是 0~10，y 是 sin 函数，标签 Time (s) / Amplitude\n- 5 个分组柱状图，比较 A/B/C/D/E 5 种处理下的细胞活力\n- 散点 + 线性回归，x 是细胞大小，y 是蛋白表达"}
          />
          <button className="btn-primary w-full" onClick={busy ? () => { abortRef.current?.abort(); setBusy(false); } : run} disabled={!busy && !modelId}>
            {busy ? "取消生成" : "生成"}
          </button>
        </div>
      </div>

      {/* 右：代码 + SVG 预览 */}
      <div className="col-span-7 space-y-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold text-sm">生成的 Python 代码</div>
            <div className="flex gap-2">
              <button
                className="btn-ghost"
                onClick={() => setShowDiff((v) => !v)}
                disabled={!originalCode || !code}
                title={showDiff ? "回到编辑视图" : "显示与 LLM 原始代码的差异"}
              >
                {showDiff ? "隐藏 diff" : "显示 diff"}
              </button>
              <button className="btn-ghost" onClick={downloadCode} disabled={!code}>
                下载 .py
              </button>
              <button className="btn-ghost" onClick={rerender} disabled={busy || !code}>
                重新渲染
              </button>
            </div>
          </div>
          {showDiff && originalCode ? (
            <DiffView original={originalCode} current={code} />
          ) : (
            <CodeMirror
              value={code}
              height="280px"
              theme={vscodeDark}
              extensions={[python()]}
              onChange={(val) => setCode(val)}
            />
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold text-sm">SVG 预览</div>
            <div className="flex gap-2">
              <button className="btn-ghost" onClick={() => downloadFormat("svg")} disabled={!code || busy}>
                下载 .svg
              </button>
              <button className="btn-ghost" onClick={() => downloadFormat("png")} disabled={!code || busy}>
                下载 .png
              </button>
              <button className="btn-ghost" onClick={() => downloadFormat("pdf")} disabled={!code || busy}>
                下载 .pdf
              </button>
            </div>
          </div>
          {err && <div className="text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded p-2 mb-2">{err}</div>}
          <div ref={svgRef} className="border border-slate-200 rounded bg-slate-50 flex items-center justify-center min-h-[320px] p-3">
            {resp?.svg ? (
              <div
                className="w-full h-full flex items-center justify-center"
                // SVG 直接 inline 渲染（沙箱已限制不联网，仅本地图）
                dangerouslySetInnerHTML={{ __html: resp.svg }}
                style={{ maxHeight: "70vh" }}
              />
            ) : (
              <div className="text-slate-400 text-sm">{busy ? "渲染中…" : "尚未生成结果"}</div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        .input { padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
        .btn-primary { padding: 8px 16px; background: #0f172a; color: white; border-radius: 6px; font-size: 13px; }
        .btn-ghost { padding: 6px 14px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
      `}</style>
    </div>
  );
}

/* ---------- Diff 视图组件 ---------- */
function DiffView({ original, current }: { original: string; current: string }) {
  const changes: Change[] = useMemo(() => diffLines(original, current), [original, current]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      // 自动滚动到第一个变更处
      const firstChange = ref.current.querySelector("[data-diff-changed]");
      if (firstChange) firstChange.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [changes]);

  // 行号追踪
  let origLine = 0;
  let curLine = 0;

  return (
    <div ref={ref} className="border border-slate-200 rounded overflow-hidden" style={{ maxHeight: "320px", overflowY: "auto" }}>
      <table className="w-full text-xs font-mono border-collapse">
        <thead>
          <tr className="bg-slate-100 sticky top-0">
            <th className="w-12 text-right px-1 py-0.5 text-slate-400 border-r border-slate-200">原</th>
            <th className="w-12 text-right px-1 py-0.5 text-slate-400 border-r border-slate-200">改</th>
            <th className="px-2 py-0.5 text-left text-slate-400">代码</th>
          </tr>
        </thead>
        <tbody>
          {changes.map((change, ci) => {
            const lines = change.value.split("\n");
            // 去掉最后的空行分割
            if (lines[lines.length - 1] === "") lines.pop();

            const bg = change.added ? "bg-green-50" : change.removed ? "bg-red-50" : "";
            const sign = change.added ? "+" : change.removed ? "-" : " ";

            return lines.map((line, li) => {
              const isFirst = li === 0;
              const key = `${ci}-${li}`;

              if (change.added) {
                curLine++;
              } else if (change.removed) {
                origLine++;
              } else {
                origLine++;
                curLine++;
              }

              return (
                <tr
                  key={key}
                  className={bg + " hover:bg-opacity-60"}
                  data-diff-changed={change.added || change.removed ? "1" : undefined}
                >
                  <td className="w-12 text-right px-1 py-0 text-slate-400 border-r border-slate-200 select-none">
                    {change.added ? "" : origLine}
                  </td>
                  <td className="w-12 text-right px-1 py-0 text-slate-400 border-r border-slate-200 select-none">
                    {change.removed ? "" : curLine}
                  </td>
                  <td className={"px-2 py-0 whitespace-pre " + (change.added ? "text-green-800" : change.removed ? "text-red-800" : "")}>
                    {sign}{line}
                  </td>
                </tr>
              );
            });
          })}
        </tbody>
      </table>
    </div>
  );
}
