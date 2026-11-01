// Данные доступны только после расшифровки снимка; API и запись не используются.
(function () {
  const diary = document.currentScript.dataset.diary;

  window.claude = {
    async use(name) {
      if (name !== 'db') return null;
      const snapshot = await window.diaryUnlocked;
      const collections = snapshot.diaries[diary];
      return {
        collection(name) {
          return {
            onSnapshot(onNext) {
              const docs = Object.entries(collections[name] || {}).map(([id, data]) => ({
                id, data: () => structuredClone(data)
              }));
              onNext({ empty: !docs.length, size: docs.length, docs });
              return () => {};
            }
          };
        }
      };
    }
  };
  window.diaryUnlocked.then(snapshot => {
    const status = document.getElementById('storageStatus');
    status.textContent = `Только просмотр. Снимок обновлён: ${snapshot.updatedAt}.`;
  });
})();
