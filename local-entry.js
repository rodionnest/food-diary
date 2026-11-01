// Детерминированный разбор: неизвестные продукты не оцениваются автоматически.
(function () {
  const number = s => Number(String(s).replace(",", "."));
  const norm = s => s.trim().toLocaleLowerCase("ru").replace(/ё/g, "е");
  const fail = message => { throw new Error(message); };
  const n = "(\\d+(?:[.,]\\d+)?)";

  function parse(text, { products = [], today, when = "День" } = {}) {
    const result = { date: today, remove: [], items: [], trains: [] };
    const lines = text.split(/\n/).map(s => s.trim()).filter(Boolean);
    let dated = false;
    for (let line of lines) {
      let m;
      if (/^(?:\d{4}-\d{2}-\d{2}|сегодня|вчера|позавчера|завтра)$/i.test(line)) {
        if (dated) fail("Укажи одну дату для всей записи.");
        dated = true;
        if (/^\d{4}/.test(line)) {
          const date = new Date(`${line}T12:00:00Z`);
          if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== line) fail("Некорректная дата.");
          result.date = line;
        } else {
          const date = new Date(`${today}T12:00:00Z`);
          date.setUTCDate(date.getUTCDate() + ({ сегодня: 0, вчера: -1, позавчера: -2, завтра: 1 })[norm(line)]);
          result.date = date.toISOString().slice(0, 10);
        }
        continue;
      }
      if ((m = line.match(new RegExp(`^вес\\s*:?\\s*${n}\\s*(?:кг)?$`, "i")))) {
        result.weight = number(m[1]);
        if (result.weight <= 30 || result.weight > 400) fail("Проверь вес: допустимо больше 30 и до 400 кг.");
        continue;
      }
      if ((m = line.match(/^заметка\s*:\s*(.+)$/i))) {
        result.note = [result.note, m[1]].filter(Boolean).join("; ");
        continue;
      }
      let mealWhen = when;
      if ((m = line.match(/^(Утро|Обед|День|Ужин|Вечер)\s*:\s*(.+)$/i))) {
        mealWhen = m[1][0].toUpperCase() + m[1].slice(1).toLowerCase();
        line = m[2];
      }
      const parts = line.split(";").map(s => s.trim());
      m = parts[0].match(new RegExp(`^(.+?)\\s+${n}\\s*(г|мл|шт|порция|порции|порций)$`, "i"));
      if (!m) fail(`Не разобрана строка «${line}». Укажи название и количество, например «Творог 150 г», либо «вес 86,4» / «заметка: текст».`);
      const [, name, qtyText, rawUnit] = m;
      const qty = number(qtyText), unit = norm(rawUnit);
      if (qty <= 0) fail("Количество должно быть больше нуля.");
      const matches = products.filter(p => norm(p.name) === norm(name));
      const product = matches[0];
      let macros, micro, grams = ["г", "мл"].includes(unit) ? qty : null;
      if (parts.length > 1) {
        macros = {};
        for (const part of parts.slice(1)) {
          const field = part.match(new RegExp(`^(ккал|б|ж|у)\\s*:?\\s*${n}$`, "i"));
          if (!field) fail(`Не разобрано «${part}». Формат: ккал 180; Б 10; Ж 8; У 17 — на всю порцию.`);
          const key = ({ ккал: "kcal", б: "p", ж: "f", у: "c" })[norm(field[1])];
          if (key in macros) fail("Каждое значение КБЖУ указывай один раз.");
          macros[key] = number(field[2]);
        }
        if (!["kcal", "p", "f", "c"].every(k => k in macros)) fail("Укажи все четыре значения: ккал, Б, Ж, У на всю порцию.");
      } else {
        if (!product) fail(`Продукта «${name}» нет в справочнике. Добавь его во вкладке продуктов или укажи КБЖУ порции: ; ккал 180; Б 10; Ж 8; У 17.`);
        if (matches.length > 1) fail(`В справочнике несколько продуктов «${name}». Укажи КБЖУ порции явно.`);
        let scale;
        if (product.serving) {
          if (!unit.startsWith("порци")) fail(`Для «${name}» укажи количество порций, например «${name} 1 порция».`);
          scale = qty;
        } else {
          const baseUnit = product.unit || "г";
          if (unit === "шт" && Number(product.piece) > 0) grams = qty * Number(product.piece);
          else if (unit !== baseUnit) fail(`Для «${name}» укажи количество в ${baseUnit}${product.piece ? " или шт" : ""}.`);
          scale = grams / 100;
        }
        macros = Object.fromEntries(["kcal", "p", "f", "c"].map(k => [k, Number(product[k]) * scale]));
        if (product.micro) micro = Object.fromEntries(Object.entries(product.micro).map(([k, v]) => [k, Number(v) * scale]));
      }
      if (!Object.values(macros).every(v => Number.isFinite(v) && v >= 0)) fail(`Проверь КБЖУ продукта «${name}».`);
      const item = { when: mealWhen, name: product?.name || name, qty: `${qty} ${unit}`, grams,
        kcal: Math.round(macros.kcal), p: Math.round(macros.p * 10) / 10,
        f: Math.round(macros.f * 10) / 10, c: Math.round(macros.c * 10) / 10 };
      if (micro) item.micro = micro;
      if (product) for (const k of ["wheat", "cocoa"]) if (typeof product[k] === "boolean") item[k] = product[k];
      result.items.push(item);
    }
    if (!lines.length) fail("Введи запись.");
    return result;
  }
  window.localDiaryParse = parse;
})();
