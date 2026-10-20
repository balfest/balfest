# БАЛФЕСТ IV — сайт на FastAPI

Сайт фестиваля парного танца: 4–6 декабря 2026, Санкт-Петербург.
FastAPI формирует HTML через Jinja2 и отдаёт CSS, JavaScript и изображения.
Тексты, направления танцев, FAQ и изображения перенесены из исходного сайта.
Сохранено оформление страницы. Старый генератор статического сайта, `dist/`,
скрипты сборки, дубликаты изображений и инструкции для прежнего развёртывания удалены.

## Быстрый запуск в VS Code: Windows + Git Bash

Нужен установленный Python 3.10 или новее. Распакуйте архив и откройте
папку `BALFEST_FASTAPI` через **File → Open Folder** в VS Code.
Откройте терминал: **Terminal → New Terminal**, профиль **Git Bash**.
Команды выполняются из корня проекта — папки с этим README.

```bash
py -3 --version
py -3 -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Откройте в браузере **http://127.0.0.1:8000/**.
Терминал с сервером оставьте открытым. Остановка: **Ctrl+C**.

Если `py` не найден, но `python --version` показывает Python 3.10+,
вместо первых двух команд используйте:

```bash
python --version
python -m venv .venv
```

Если Python не установлен, установите его для Windows, включив опцию
**Add Python to PATH**, затем полностью перезапустите VS Code.
Сообщение «Python was not found» при `python3` в Git Bash означает,
что Windows вызвала псевдоним Microsoft Store. Для создания окружения
используйте `py -3`, а внутри активированного окружения — `python`.

При следующих запусках установка зависимостей не нужна:

```bash
source .venv/Scripts/activate
python -m uvicorn app.main:app --reload
```

Если порт 8000 занят:

```bash
python -m uvicorn app.main:app --reload --port 8001
```

Тогда адрес страницы: **http://127.0.0.1:8001/**.

## Linux / macOS: Bash

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Откройте **http://127.0.0.1:8000/**.

## Структура проекта

| Путь | Назначение |
|---|---|
| `app/main.py` | Приложение FastAPI, главная страница, статика, robots, sitemap, 404 |
| `app/content.py` | Чтение контента, даты, статусы и данные для шаблонов |
| `app/data/content.json` | Тексты, даты, ссылки, программа и параметры оформления |
| `app/templates/base.html` | Общая HTML-оболочка и метаданные |
| `app/templates/index.html` | Главная страница, шапка и подвал |
| `app/templates/sections/` | Разделы главной страницы |
| `app/templates/404.html` | Страница для неизвестных адресов |
| `app/static/assets/` | Стили, JavaScript и используемые изображения |
| `requirements.txt` | Зависимости приложения |
| `requirements-dev.txt` | Зависимости для проверок |
| `tests/test_app.py` | Проверки HTTP, статики, статусов и экранирования |

## Как редактировать сайт

Тексты меняйте в **`app/data/content.json`**. Файл читается при запросе:
достаточно сохранить его и обновить страницу в браузере. Сборка не нужна.
JSON должен оставаться корректным: строки в двойных кавычках, без комментариев.

- `site`: название, даты, город, описание и публичный URL. `site.url` влияет
  на canonical, Open Graph и sitemap; локальный сервер работает по адресу выше.
- `hero`, `about`, `directions`, `faq`: тексты и карточки разделов.
- `program.days`: даты программы; показываются только сессии с `confirmed: true`.
  Для сессии нужны `time` в формате `HH:MM`, `title`, `directionId`;
  `hall` и `level` можно не указывать.
- `venue`: для публикации площадки заполните `name`, `address` и установите
  `confirmed: true`. `mapUrl` — необязательная HTTPS-ссылка на карту.
- `tickets`: продажи появятся при `status: "on_sale"` и заполненном `url`.
  В `options` публикуются записи с `confirmed: true`, `name` и неотрицательным `price`.
- `openCall`: `enabled` включает раздел. Подтверждённый `deadline` в формате
  `YYYY-MM-DD` действует до конца указанного дня по московскому времени;
  после него раздел и пункты меню скрываются. При `deadlineConfirmed: false`
  дата не применяется.
- `contacts`: почта показывается только при `emailVerified: true`.
- `studios` и `partners`: публикуются записи с `confirmed: true`.
  Студия: `name`, `description`, `url`. Партнёр: `name`, `url`, необязательный
  `logo` — путь относительно `app/static/`, например `assets/partner.webp`.
- `theme`: цвета в формате `#RRGGBB`; сервер отдаёт их через `/theme.css`.

Верстку меняйте в `app/templates/`, стили — в `app/static/assets/styles.css`,
поведение мобильного меню — в `app/static/assets/site.js`.
После изменения шаблонов, стилей или изображений обновите страницу.

Сейчас программа и площадка ожидают подтверждения, билеты ещё не продаются.
Ссылки ведут в официальное сообщество VK. Базы данных, административной панели,
платёжной интеграции и аналитики в этом проекте нет.

## Проверка

В активированном окружении, из корня проекта:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Проверяются главная страница и её ресурсы, 404, SEO-файлы, срок Open Call,
подтверждённые продажи и площадка, экранирование текстов.

## Запуск без автоматической перезагрузки

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`--reload` предназначен для локальной разработки. Для размещения на сервере
используйте HTTPS через обратный прокси и настройте автозапуск процесса Uvicorn.
Чтобы URL в статических ресурсах учитывали HTTPS за доверенным прокси,
настройте его forwarded headers и доверенные адреса в Uvicorn под своё окружение.
