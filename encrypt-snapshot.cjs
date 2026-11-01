// Экспорт использует только встроенную криптографию Node.js, без npm-пакетов.
const { randomBytes, pbkdf2Sync, createCipheriv } = require('node:crypto');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', () => {
  const { pin, snapshot } = JSON.parse(input);
  const salt = randomBytes(16), iv = randomBytes(12), iterations = 600000;
  const key = pbkdf2Sync(pin, salt, iterations, 32, 'sha256');
  const cipher = createCipheriv('aes-256-gcm', key, iv);
  const ciphertext = Buffer.concat([cipher.update(JSON.stringify(snapshot), 'utf8'), cipher.final(), cipher.getAuthTag()]);
  const b64 = value => value.toString('base64');
  process.stdout.write(JSON.stringify({ version: 1, iterations, salt: b64(salt), iv: b64(iv), ciphertext: b64(ciphertext) }));
});
