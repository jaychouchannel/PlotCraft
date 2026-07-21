import { NavLink, Route, Routes } from "react-router-dom";
import ModelConfigPage from "./pages/ModelConfig";
import TemplatesPage from "./pages/Templates";
import GeneratePage from "./pages/Generate";
import HistoryPage from "./pages/History";

const link = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm font-medium ${
    isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-200"
  }`;

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
          <div className="font-bold text-lg">科研论文矢量图生成器</div>
          <nav className="flex gap-2">
            <NavLink to="/" className={link} end>
              生成
            </NavLink>
            <NavLink to="/models" className={link}>
              模型
            </NavLink>
            <NavLink to="/templates" className={link}>
              模板
            </NavLink>
            <NavLink to="/history" className={link}>
              历史
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        <Routes>
          <Route path="/" element={<GeneratePage />} />
          <Route path="/models" element={<ModelConfigPage />} />
          <Route path="/templates" element={<TemplatesPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </div>
  );
}
