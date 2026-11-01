// Чтение локального JSON-хранилища и подписки без внешних сервисов.
// Подключается в <head> с атрибутом data-diary="<имя дневника>".
(function () {
  const diary = document.currentScript?.dataset.diary;
  if (!diary || location.protocol === "file:") return;   // открыт как файл — сервера нет
  const POLL_MS = 4000;

  async function call(method, url, body) {
    let res;
    try {
      res = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
    } catch (e) { throw { code: "unavailable", message: "Сервер дневника не отвечает" }; }
    const out = await res.json().catch(() => null);
    if (!res.ok) throw { code: out?.code || "internal", message: out?.message };
    return out;
  }

  const colls = new Map();
  function collection(name) {
    if (!colls.has(name)) colls.set(name, makeCollection(name));
    return colls.get(name);
  }

  function makeCollection(name) {
    const base = `/api/db/${encodeURIComponent(diary)}/${encodeURIComponent(name)}`;
    const listeners = new Set();
    let rev = null;

    async function refresh(force) {
      if (!listeners.size) return;
      let r;
      try { r = await call("GET", base); }
      catch (e) { listeners.forEach(l => l.onError?.(e)); return; }
      if (!force && r.rev === rev) return;
      rev = r.rev;
      const docs = r.docs.map(d => ({ id: d.id, data: () => structuredClone(d.data) }));
      const snap = { empty: docs.length === 0, size: docs.length, docs };
      listeners.forEach(l => l.onNext(snap));
    }
    setInterval(() => { if (document.visibilityState === "visible") refresh(false); }, POLL_MS);
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") refresh(false); });

    return {
      onSnapshot(onNext, onError) {
        const l = { onNext, onError };
        listeners.add(l);
        refresh(true);
        return () => listeners.delete(l);
      }
    };
  }

  const db = { collection };
  window.claude = { use: async name => name === "db" ? db : null };
})();
