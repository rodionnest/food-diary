// AES-GCM: ключ получается из PIN, открытых записей в файлах снимка нет.
(function () {
  const storageKey = 'food-diary-decryption-key-v1';
  let resolve;
  window.diaryUnlocked = new Promise(done => { resolve = done; });
  const bytes = value => Uint8Array.from(atob(value), ch => ch.charCodeAt(0));
  const base64 = value => btoa(String.fromCharCode(...new Uint8Array(value)));

  async function decrypt(key) {
    const envelope = window.ENCRYPTED_DIARY;
    const data = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: bytes(envelope.iv) }, key, bytes(envelope.ciphertext));
    return JSON.parse(new TextDecoder().decode(data));
  }
  function unlock(snapshot) {
    resolve(snapshot);
    document.getElementById('pinGate')?.remove();
    document.documentElement.removeAttribute('data-pin-locked');
    window.dispatchEvent(new Event('resize'));
  }
  document.addEventListener('DOMContentLoaded', async () => {
    const gate = document.createElement('section');
    gate.id = 'pinGate';
    gate.setAttribute('aria-label', 'Вход в дневники');
    gate.innerHTML = `<form id="pinForm">
      <h1>Дневники питания</h1><p>Введи четырёхзначный код</p>
      <label for="diaryPin">PIN-код</label>
      <input id="diaryPin" type="password" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" minlength="4" required autocomplete="off" autofocus>
      <button type="submit">Открыть</button>
      <p id="pinError" role="status" aria-live="polite"></p>
    </form>`;
    document.body.append(gate);
    const input = gate.querySelector('input'), button = gate.querySelector('button'), error = gate.querySelector('#pinError');
    if (!window.crypto?.subtle || !window.ENCRYPTED_DIARY) {
      error.textContent = 'Не удалось загрузить шифрованный снимок. Открой сайт по HTTPS и обнови страницу.';
      input.disabled = button.disabled = true;
      return;
    }
    const envelope = window.ENCRYPTED_DIARY;
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey));
      if (saved?.salt === envelope.salt) {
        const key = await crypto.subtle.importKey('raw', bytes(saved.key), 'AES-GCM', false, ['decrypt']);
        unlock(await decrypt(key));
        return;
      }
    } catch (_) { /* Нет ключа или снимок обновился — запрашиваем PIN. */ }
    input.focus();
    gate.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      button.disabled = input.disabled = true;
      error.textContent = 'Открываю…';
      try {
        const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(input.value), 'PBKDF2', false, ['deriveKey']);
        const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: bytes(envelope.salt), iterations: envelope.iterations, hash: 'SHA-256' }, material, { name: 'AES-GCM', length: 256 }, true, ['decrypt']);
        const snapshot = await decrypt(key);
        try {
          sessionStorage.setItem(storageKey, JSON.stringify({ salt: envelope.salt, key: base64(await crypto.subtle.exportKey('raw', key)) }));
        } catch (_) {}
        input.value = '';
        unlock(snapshot);
      } catch (_) {
        error.textContent = 'Неверный код или снимок повреждён. Попробуй ещё раз.';
        input.value = '';
        button.disabled = input.disabled = false;
        input.focus();
      }
    });
  });
})();
