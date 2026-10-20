# Публикация на Selectel — Ubuntu 24.04 LTS

Рекомендуемый вариант: **Caddy**. Он обслуживает статические файлы и получает HTTPS-сертификат. Готовый сайт независим от ChatGPT. Сервер, SSH и DNS из этой сессии не изменялись: доступы не предоставлены.

## 1. Домен и доступ

В DNS-зоне, обслуживающей домен REG.RU, укажите публичный IP VDS. Если домен использует сторонние NS, записи меняются у владельца этих NS.

| Домен | Запись | Значение |
|---|---|---|
| `balfest.ru` | A, имя `@` | IPv4 вашего Selectel VDS |
| `www.balfest.ru` — опционально | CNAME, имя `www` | `balfest.ru.` |
| `балфест.рф` — опционально | A, имя `@` | тот же IPv4 |

Для `балфест.рф` ASCII-имя: `xn--80abnx5agl.xn--p1ai`. Если опубликована запись AAAA, IPv6 также должен вести на сервер; иначе удалите устаревшую AAAA. Не меняйте почтовые MX-записи при настройке сайта.

В сетевых правилах Selectel и Ubuntu разрешите входящие TCP 80 и 443. SSH разрешайте с вашего доверенного адреса. Исходящий доступ к DNS и HTTPS нужен для сертификата. Если UFW уже используется:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Убедитесь, что SSH разрешён, прежде чем включать или менять firewall. Если сервер уже обслуживает другие сайты, используйте существующий веб-сервер и добавьте виртуальный хост вместо установки второго на те же порты.

## 2. Установка Caddy на чистый сервер

Для нового сервера без другого веб-сервера:

```bash
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg rsync unzip
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
sudo chmod o+r /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

## 3. Загрузка готового сайта

Распакуйте скачанный архив на компьютере. Из каталога, содержащего папку `BALFEST_IV_2026`, скопируйте её на сервер. Замените `YOUR_SSH_USER` и `YOUR_SERVER_IP`:

```bash
scp -r BALFEST_IV_2026 YOUR_SSH_USER@YOUR_SERVER_IP:/tmp/
```

На сервере создайте первый релиз:

```bash
sudo mkdir -p /var/www/balfest/releases/2026-10-12-v1
sudo rsync -a --chmod=D755,F644 /tmp/BALFEST_IV_2026/dist/ /var/www/balfest/releases/2026-10-12-v1/
sudo ln -sfn /var/www/balfest/releases/2026-10-12-v1 /var/www/balfest/current
```

Сервер должен отдавать **содержимое `dist/`**, а не корень проекта с исходниками, инструкциями и настройками. Директории `/var/www/balfest` и `releases` должны быть доступны Caddy на чтение и проход, обычно права 755.

На чистом сервере установите конфигурацию:

```bash
sudo cp /tmp/BALFEST_IV_2026/deploy/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

На сервере с существующим Caddy добавьте блок `balfest.ru` в текущий Caddyfile, сохранив другие сайты. После распространения DNS и открытия портов Caddy выпустит сертификат. При ошибке:

```bash
sudo journalctl -u caddy -n 80 --no-pager
```

Редиректы `www` и `балфест.рф` закомментированы. Раскомментируйте блок только после настройки DNS **для каждого** перечисленного имени. Получение сертификатов требует, чтобы эти имена были доступны на сервере. Все алиасы направляются на `https://balfest.ru/` с сохранением пути; canonical всегда основной домен.

## 4. Проверка публикации

```bash
curl -I https://balfest.ru/
curl -I http://balfest.ru/
curl -I https://balfest.ru/does-not-exist
curl https://balfest.ru/robots.txt
curl https://balfest.ru/sitemap.xml
```

Ожидается: главная — 200; HTTP — перенаправление на HTTPS; несуществующая страница — 404. Проверьте реальный iPhone, десктоп, меню, изображения, переходы в VK и консоль. Обязательная матрица ширин: 320, 375, 390, 768, 1024, 1440 px.

## Обновления и откат

Соберите новые файлы на компьютере и загрузите их в **новую** папку релиза. Не удаляйте предыдущий релиз. Для переключения без частично загруженной страницы:

```bash
sudo ln -s /var/www/balfest/releases/NEW_RELEASE /var/www/balfest/current-next
sudo mv -Tf /var/www/balfest/current-next /var/www/balfest/current
```

`NEW_RELEASE` замените на созданное имя релиза. Для отката повторите эти две команды с путём к предыдущему релизу. Перезапуск сервиса для замены содержимого не нужен.

## Альтернатива: Nginx

Используйте вместо Caddy. Пример `deploy/nginx-http.conf` рассчитан на первичную HTTP-настройку. После подготовки DNS:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp /tmp/BALFEST_IV_2026/deploy/nginx-http.conf /etc/nginx/sites-available/balfest
sudo ln -s /etc/nginx/sites-available/balfest /etc/nginx/sites-enabled/balfest
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d balfest.ru
```

Выберите перенаправление HTTP на HTTPS, если мастер предлагает выбор. После выпуска повторите `sudo nginx -t` и проверку URL. При добавлении алиасов настройте отдельный redirect-хост и сертификаты для этих имён; схема основного домена остаётся прежней.

## Официальные справочники

- [Установка Caddy на Ubuntu](https://caddyserver.com/docs/install#debian-ubuntu-raspbian)
- [HTTPS в Caddy](https://caddyserver.com/docs/quick-starts/https)
- [Статические файлы Caddy](https://caddyserver.com/docs/quick-starts/static-files)
- [Обработка 404 в Caddy](https://caddyserver.com/docs/caddyfile/directives/handle_errors)
- [Группы безопасности Selectel](https://docs.selectel.ru/cloud-servers/security-groups/about/about-security-groups/)
- [Nginx: try_files и error_page](https://nginx.org/en/docs/http/ngx_http_core_module.html)

Справочники проверены 12 октября 2026. Конфигурации требуют `caddy validate` / `nginx -t` на вашем сервере: локальные бинарные файлы этих веб-серверов в рабочем окружении отсутствуют.
