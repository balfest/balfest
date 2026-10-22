# BALFEST — удалённый Docker-деплой через GitHub Actions

Workflow: [.github/workflows/remote-preview.yml](../.github/workflows/remote-preview.yml).
**Runner размещён в GitHub (ubuntu-24.04).** На сервере GitHub runner не нужен.
GitHub подключается по SSH, проверяет Docker, устанавливает его при отсутствии,
тестирует сайт, копирует релиз, запускает FastAPI + Nginx и выполняет проверки.

Это **закрытый HTTP-предпросмотр**, а не публичный balfest.ru. Сайт на сервере
доступен только по 127.0.0.1:8080. На Windows открываем через SSH-туннель.

## 1. Сервер и доступ

Требуется отдельный Ubuntu-сервер x86_64 (24.04 или 26.04), доступный по SSH
из Интернета; с рабочим интернетом, свободным диском, tar, bash, sudo, systemd.
Например, VPS Selectel. Виртуалка VirtualBox за обычным NAT недоступна
из GitHub-hosted runner без отдельной публичной сети или туннеля.

Нужен отдельный SSH-пользователь с правом записывать файлы в свой home и
**неинтерактивным sudo** для установки Docker и запуска Docker Compose.
CI не может запрашивать пароль sudo. Для автоматической первой установки
привилегии должны быть предоставлены администратором заранее.

**Важное предупреждение:** произвольный bash с sudo эквивалентен root-доступу.
Используйте такую конфигурацию только на изолированном preview VPS, без личных
данных и других приложений. Не выдавайте NOPASSWD: ALL на повседневном ПК.
В production предпочтительны более узкие root-owned процедуры.

## 2. SSH-ключ

В Windows Git Bash создайте отдельный ключ для CI:

~~~bash
ssh-keygen -t ed25519 -f ~/.ssh/balfest_deploy -C "balfest github actions deploy"
~~~

Для GitHub Actions нужен ключ без passphrase, исключительно для deploy.
Приватный ключ НИКОГДА не публикуйте, не пересылайте в чат и не коммитьте.

На удалённом сервере добавьте публичную часть файла balfest_deploy.pub в
home SSH-пользователя: ~/.ssh/authorized_keys (каталог ~/.ssh: 700,
authorized_keys: 600). Если обычный вход по SSH уже работает, можно:

~~~bash
cat ~/.ssh/balfest_deploy.pub | ssh USER@SERVER 'umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys'
ssh -i ~/.ssh/balfest_deploy USER@SERVER whoami
~~~

Замените USER и SERVER; при нестандартном порте добавьте -p PORT.

## 3. GitHub Secrets

Откройте https://github.com/balfest/balfest/settings/secrets/actions .

Добавьте Repository secrets:

| Название | Значение |
|---|---|
| DEPLOY_HOST | публичный IPv4 или DNS-сервер |
| DEPLOY_USER | SSH-пользователь удалённого сервера |
| DEPLOY_SSH_KEY | приватный ключ ~/.ssh/balfest_deploy целиком |

SSH использует стандартный порт **22**. Дополнительная переменная порта
не требуется. Секрет DEPLOY_KNOWN_HOSTS больше не используется.

**Компромисс безопасности:** SSH настроен с StrictHostKeyChecking=accept-new.
При первом подключении GitHub runner автоматически доверяет предъявленному
сервером ключу. Поскольку runner создаётся заново при каждом запуске, это
не защищает первый контакт от подмены сервера (MITM). Для production лучше
вернуть закреплённый ключ хоста или другой надёжный механизм проверки.

В Settings → Environments создайте окружение preview; если доступны
deployment protection rules, включите ручное подтверждение. Workflow
запускается только из main и через workflow_dispatch, без запуска PR.

## 5. Удалённый sudo

На VPS выполните под выбранным пользователем:

~~~bash
sudo -n true && echo "sudo готов к CI"
~~~

Если требуется пароль, попросите администратора выдать полномочия для
изолированного VPS. Никогда не открывайте SSH-доступ root с паролем.
Скрипт install-docker.sh запускается через sudo -n bash -s: он проверяет
Docker Engine + Compose, запускает service при необходимости, а если Docker
отсутствует, устанавливает из официального apt-репозитория Docker.
Если есть конфликтующие пакеты (например старый docker.io без Compose),
скрипт завершится ошибкой и не будет их удалять.

## 6. Запуск и проверки

После слияния PR с main откройте:
https://github.com/balfest/balfest/actions
→ BALFEST remote preview deploy → Run workflow.

Также workflow запускается при каждом push в main.

Последовательность:
1. GitHub checkout и защищённая SSH-авторизация.
2. **На удалённом сервере:** проверить Docker, установить при необходимости.
3. На GitHub-hosted runner проверить Compose и unit-тесты FastAPI в Docker.
4. Передать только необходимые файлы релиза по SSH.
5. На VPS собрать контейнеры FastAPI + Nginx, проверить nginx -t.
6. Проверить здоровье контейнеров, HTML, дату, тему, CSS, JS, WebP,
   robots.txt, sitemap.xml и корректные HTTP 404.

Файлы будут под ~/balfest-preview/releases/<SHA_КОММИТА>.
Внутренний FastAPI слушает порт 8000, Nginx привязан к
127.0.0.1:8080 удалённого сервера.

## 7. Посмотреть в браузере

В Git Bash на Windows запустите:

~~~bash
ssh -i ~/.ssh/balfest_deploy -N -L 8080:127.0.0.1:8080 USER@SERVER
~~~

Держите этот терминал открытым. На ноутбуке откройте
http://127.0.0.1:8080/ . Порт SSH фиксирован: 22.

Не открывайте TCP 8080 в Интернет. У Docker свои правила публикации
портов и UFW не всегда ограничивает их. Для публичного balfest.ru
понадобятся отдельный HTTPS reverse proxy и DNS-настройки.

## 8. Диагностика

Логи действий доступны в GitHub Actions. На сервере:

~~~bash
sudo docker compose --project-name balfest-preview ps
sudo docker compose --project-name balfest-preview logs --tail=100
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/
~~~

Если Permission denied — проверить authorized_keys и ключ.
Если Host key verification failed — проверить SSH и известные ключи.
Если sudo requires password — исправить права. Если Connection timed out —
проверить публичную доступность SSH-порта и сетевые ограничения VPS.

Официальная инструкция Docker: https://docs.docker.com/engine/install/ubuntu/
