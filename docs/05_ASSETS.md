# Рабочие изображения

Публичные материалы — художественные иллюстрации, не фотографии площадки или документальные фотографии фестиваля. Визуальная концепция не объявляется утверждённым брендбуком.

- `source/media/hero-v2.png` — версия зимней композиции из MVP без встроенных надписей. Получена встроенным ImageGen; затем подготовлены WebP 768 / 1280 / 2048 px для сайта.
- `source/media/open-call-horizontal.png` — предоставленная продюсером новая горизонтальная афиша. В исходной композиции без искажения; подготовлены WebP 768 / 1280 / 1672 px.
- `static/assets/og-image.jpg` — социальное превью 1200 × 630 с точной типографикой, собранной средствами кода.
- `static/assets/favicon.svg` — отдельный знак для вкладки; `apple-touch-icon.png` — значок для домашнего экрана.

Запрос для первого изображения (встроенный ImageGen):

```text
Use case: precise-object-edit. Asset type: official BALFEST IV website panoramic hero illustration. Input image 1 is the edit target, the existing festival artwork. Preserve the wide panoramic composition, wintry Saint Petersburg riverfront, recognizable softly illuminated architecture, snow, deep midnight navy sky and warm gold light trails, and central pair in a graceful partnered dancing pose. Remove ALL baked-in text, letters, dates, numbers and typographic decorative symbols from the entire image, restoring a natural dark blue sky above and natural reflections below. Replace the woman's voluminous ivory bridal/historical dress with a flowing modern elegant deep copper-gold dance dress, not a wedding gown; the man wears a contemporary dark suit, no historical costume. This represents diverse partnered dance culture, not only historical balls. Keep the couple around the center-right so left has atmospheric sky and river space. Subtle cinematic warm lighting, refined cultural event art, fewer glitter particles, realistic proportional hands and faces, no logos, no text, no watermark. Very wide landscape 2048x1024 or similar.
```

Компрессия и изменение размеров сохраняют пропорции. Отдельное адаптивное кадрирование первого экрана выполняет CSS `object-fit: cover`; на этом изображении нет текста, который мог бы обрезаться. Open Call выводится целиком, а основное приглашение и контакт доступны в HTML. Изображение можно открыть в полном размере.
