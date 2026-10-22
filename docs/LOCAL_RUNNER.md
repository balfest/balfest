# БАЛФЕСТ IV: автоматический Docker-деплой в Ubuntu VirtualBox

GitHub Actions для репозитория [balfest/balfest](https://github.com/balfest/balfest)
запускает проверки приложения, при необходимости устанавливает Docker Engine и
Compose, поднимает **FastAPI + Nginx** и проверяет работу сайта.

**Результат — только локальный предпросмотр по HTTP.** Никакого размещения
на balfest.ru и изменений DNS workflow не выполняет.

## Что workflow может сделать автоматически

1. Проверить Ubuntu x86_64 и наличие непрерывного (noninteractive) sudo.
2. При отсутствии Docker установить его из официального apt-репозитория Docker.
3. Проверить движок Docker и Compose запуском тестового образа hello-world.
4. Проверить синтаксис Docker Compose.
5. Собрать test-stage Dockerfile и запустить весь suite tests/test_app.py.
6. Собрать и запустить контейнеры FastAPI и Nginx.
7. Выполнить nginx -t внутри веб-контейнера.
8. Проверить healthchecks двух контейнеров, главную страницу, дату,
   robots.txt, sitemap.xml, тему, CSS, JS, WebP и ответы HTTP 404.
9. При ошибке вывести диагностику контейнеров и логи.

Если Docker уже установлен и работает, установка пропускается (идемпотентно).

## Что один раз нужно подготовить вручную

Автоматизация GitHub Actions **не может сама запустить runner, если его ещё нет**.
Необходима включённая Ubuntu VM в VirtualBox и запущенный runner.

Откройте: https://github.com/balfest/balfest/settings/actions/runners/new
и выберите Linux, x64. В Ubuntu от обычного пользователя (не root) выполните
команды GitHub по скачиванию/проверке checksum/распаковке runner.
При конфигурировании задайте label **balfest-vm**:

~~~bash
./config.sh --url https://github.com/balfest/balfest --token TOKEN_FROM_GITHUB --labels balfest-vm
~~~

Токен берите на странице GitHub, никому не отправляйте и не публикуйте.
В каталоге runner установите службу:

~~~bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
~~~

Runner должен быть виден как **Online** на странице Settings → Actions → Runners,
с метками self-hosted, Linux, X64, balfest-vm.

### Неинтерактивный sudo (обязателен для автоматической установки)

Работающий как системная служба runner **не может запросить пароль sudo**.
Поэтому workflow проверяет sudo -n и останавливается с понятным сообщением,
если у runner отсутствуют необходимые полномочия.

Самый простой вариант для **изолированной, одноцелевой VM без личных файлов
и секретов** — разрешить только пользователю runner выполнять sudo без пароля.
В Ubuntu запустите:

~~~bash
whoami
sudo visudo -f /etc/sudoers.d/balfest-runner
~~~

В редакторе добавьте строку, подставив имя пользователя, которое вывела whoami:

~~~text
USERNAME ALL=(root) NOPASSWD: ALL
~~~

Это **высокие привилегии**: любой код workflow в main получает root-права
на Ubuntu VM. Не используйте такую схему на основном компьютере или машине
с личными файлами и ключами. Более безопасная альтернатива — установить
Docker в Ubuntu вручную и выполнять деплой на изолированном сервере
с отдельными учётными данными; либо держать репозиторий инфраструктуры
приватным. Не давайте runner доступ к хостовым папкам VirtualBox.

После сохранения проверьте в Ubuntu от того же пользователя:

~~~bash
sudo -n true && echo "sudo готов"
~~~

## Как запустить автоматизацию

После объединения PR в ветку main зайдите в GitHub → Actions →
**BALFEST local VM preview** → **Run workflow**.
Также каждый push в main автоматически запускает workflow.
Запуски из pull_request намеренно отсутствуют: это публичный репозиторий,
и запуск недоверенного PR-кода на self-hosted runner опасен.

Первый запуск установит Docker, пройдёт тесты и запустит Nginx на порту 8080.
VM должна быть включена и доступна по сети.

## Как открыть локальный сайт в браузере Windows

В Ubuntu тест: curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/

**Если VirtualBox настроен в NAT:** выключите VM, зайдите в Settings →
Network → Adapter 1 → NAT → Advanced → Port Forwarding. Добавьте:

| Настройка | Значение |
|---|---|
| Name | BALFEST_HTTP |
| Protocol | TCP |
| Host IP | 127.0.0.1 |
| Host Port | 8080 |
| Guest IP | пустой |
| Guest Port | 8080 |

Запустите VM. На Windows откройте **http://127.0.0.1:8080/**.
Этот вариант не открывает доступ с iPhone.

**Если VirtualBox использует Bridged Adapter:** в Ubuntu выполните
hostname -I, а на Windows или iPhone в том же Wi-Fi используйте
http://IP_ВИРТУАЛКИ:8080/ (если firewall и роутер разрешают соединение).
Не открывайте порт 8080 через интернет.

## Диагностика

В Ubuntu, из каталога с актуальным compose.yaml, при наличии прав sudo:

~~~bash
sudo docker compose --project-name balfest-preview ps
sudo docker compose --project-name balfest-preview logs --tail=100
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/
~~~

Если VM выключена, site-preview недоступен, а GitHub Actions ожидает runner.
В контейнерах нет зависимости от временной папки checkout: конфигурация
Nginx включена в Docker image.

При первой установке Docker потребуется доступ в интернет к apt-репозиториям
Ubuntu, download.docker.com и Docker Hub. Если в Ubuntu уже стоит конфликтующая
версия пакета docker.io, скрипт не удалит её автоматически — устраните
конфликт вручную.

## Ограничения безопасности

GitHub предупреждает о рисках self-hosted runners для публичных репозиториев.
Этот workflow **не запускает PR из форков**, однако любой код, допущенный
через merge в main, может исполняться на вашем компьютере в VM.
Проверяйте изменения до merge; не храните secrets и токены внутри VM.
Docker с sudo обладает привилегиями root. Это не production-окружение
и не замена размещению на Selectel с HTTPS.
