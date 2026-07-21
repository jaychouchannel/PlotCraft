import { useState } from "react";

const DEFAULT_MSG = `尚未初始化后端 .env 中的 ONE_ENCRYPT_KEY — 模型 API Key 无法加密保存。请在 backend 目录执行：\n\n  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"\n\n把输出的 44 字符密钥写到 backend/.env 的 ONE_ENCRYPT_KEY= 后面。`;

export default function SetupBanner() {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return (
    <div className="bg-amber-50 border border-amber-200 text-amber-900 p-3 rounded-lg text-sm whitespace-pre-wrap mb-3">
      {DEFAULT_MSG}
      <button className="underline ml-2" onClick={() => setDismissed(true)}>
        知道了
      </button>
    </div>
  );
}
