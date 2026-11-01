const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = { window: {} };
vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname, '../local-entry.js'), 'utf8'), context);
const parse = (text, products = []) => context.window.localDiaryParse(text, { today: '2026-11-01', when: 'День', products });
const cottage = { name: 'Творог', kcal: 120, p: 18, f: 4, c: 3, micro: { ca: 100 }, wheat: false };

test('масса, КБЖУ, микроэлементы и каноническое название из справочника', () => {
  const result = parse('вчера\nвес 86,4\nОбед: творог 150 г\nзаметка: хорошо спал', [cottage]);
  assert.equal(result.date, '2026-10-31');
  assert.equal(result.weight, 86.4);
  assert.equal(result.note, 'хорошо спал');
  const item = result.items[0];
  assert.equal(item.when, 'Обед');
  assert.equal(item.name, 'Творог');
  assert.equal(item.kcal, 180);
  assert.equal(item.p, 27);
  assert.equal(item.micro.ca, 150);
  assert.equal(item.wheat, false);
});
test('неизвестный продукт принимается с явными КБЖУ всей порции', () => {
  const item = parse('Суп 250 г; ккал 180; Б 10; Ж 8; У 17').items[0];
  assert.equal(item.kcal, 180);
  assert.equal(item.grams, 250);
  assert.equal(item.p, 10);
});
test('готовые порции и штуки пересчитываются по справочнику', () => {
  assert.equal(parse('Обед 2 порции', [{ ...cottage, name: 'Обед', serving: 'готовый' }]).items[0].p, 36);
  assert.equal(parse('Творог 2 шт', [{ ...cottage, piece: 50 }]).items[0].kcal, 120);
});
test('неизвестная еда, несовместимые единицы и неполные КБЖУ отклоняются', () => {
  for (const text of ['Суп 250 г', 'Творог 1 шт', 'Творог 150 мл', 'Суп 250 г; ккал 180', 'Творог 0 г', 'убери творог']) {
    assert.throws(() => parse(text, [cottage]));
  }
});
test('некорректная дата и несколько дат отклоняются; старая дата сохраняется', () => {
  assert.throws(() => parse('2026-02-30\nвес 86'));
  assert.throws(() => parse('вчера\nсегодня\nвес 86'));
  assert.equal(parse('2025-01-01\nвес 86').date, '2025-01-01');
});
test('смешанная запись с неизвестной строкой отклоняется целиком', () => {
  assert.throws(() => parse('вес 86\nнепонятный текст'));
});
