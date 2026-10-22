# BALFEST: локальный GitHub Actions runner на Ubuntu VirtualBox

Схема: GitHub Actions (self-hosted runner) → тесты FastAPI → Docker Compose → Nginx → сайт в браузере.
Это **тестовый HTTP-стенд**: он не публикует balfest.ru в интернете.
Nginx слушает TCP 8080 в Ubuntu-госте; Uvicorn слушает 8000 только внутри Docker.

## 1. Docker в Ubuntu 24.04

Все команды ниже выполняются в **терминале Ubuntu внутри VirtualBox**, а не в Git Bash Windows.
Проверьте архитектуру: uname -m (ожидается x86_64).

~~~bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
~~~

**Выйдите из сеанса Ubuntu и войдите снова** (или выполните newgrp docker);
проверьте docker version и docker compose version.
Группа docker фактически даёт root-права: для runner используйте только отдельную VM
без личных файлов и production-секретов.

## 2. Запуск контейнеров вручную

~~~bash
git clone https://github.com/balfest/balfest.git
cd balfest
git checkout feature/local-vm-docker-preview
docker build --target test -t balfest-preview-tests:latest .
docker compose up -d --build --wait --wait-timeout 120
docker compose ps
curl -I http://127.0.0.1:8080/
~~~

Ожидаемый HTTP-ответ: 200 OK. После слияния PR используйте main вместо
feature/local-vm-docker-preview. Для диагностики:
docker compose logs --tail=100.
Для остановки: docker compose down.

## 3. GitHub self-hosted runner

Откройте https://github.com/balfest/balfest/settings/actions/runners/new .
Выберите **Linux → x64**. Выполните в Ubuntu **актуальные команды GitHub** для
загрузки runner, проверки checksum и распаковки — от обычного пользователя, НЕ root.

К команде конфигурации добавьте пользовательскую метку balfest-vm.
Образец (одноразовый token брать ТОЛЬКО на странице GitHub, никогда не отправлять в чат):

~~~bash
./config.sh --url https://github.com/balfest/balfest --token TOKEN_FROM_GITHUB --labels balfest-vm
~~~

Затем из каталога actions-runner запустите службу:

~~~bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
~~~

На GitHub Settings → Actions → Runners должен отображаться Online runner с
метками self-hosted, Linux, X64, balfest-vm.

После слияния PR с main откройте GitHub → Actions → BALFEST local VM preview →
Run workflow. Каждый push в main также обновит предпросмотр в работающей VM.
Тесты выполняются при сборке Docker test stage; затем запускаются FastAPI и Nginx,
и проверяются HTTP-страница, robots.txt и sitemap.xml.

## 4. Как открыть сайт на Windows

**Внутри Ubuntu:** http://127.0.0.1:8080/

### Вариант NAT (простой и безопасный для проверки на Windows)

Выключите VM. VirtualBox → Settings → Network → Adapter 1 → NAT →
Advanced → Port Forwarding. Добавьте правило:

| Поле | Значение |
|---|---|
| Name | BALFEST_HTTP |
| Protocol | TCP |
| Host IP | 127.0.0.1 |
| Host Port | 8080 |
| Guest IP | пусто |
| Guest Port | 8080 |

Включите VM. **На Windows:** http://127.0.0.1:8080/ .
iPhone с таким правилом доступа не получит.

### Вариант Bridged Adapter (проверка также с iPhone)

Настройте VirtualBox Adapter 1 → Bridged Adapter.
В Ubuntu выполните hostname -I и найдите IP виртуалки.
На Windows и iPhone в той же локальной Wi-Fi-сети откройте:
http://IP_ВИРТУАЛКИ:8080/ .
Работа зависит от настроек роутера, UFW и изоляции устройств в Wi-Fi.
**Нельзя** пробрасывать порт 8080 в интернет с домашнего роутера.

## 5. Обслуживание и риски

~~~bash
docker compose --project-name balfest-preview ps
docker compose --project-name balfest-preview logs --tail=100
curl -I http://127.0.0.1:8080/
~~~

Если Ubuntu VM выключена, workflow будет ждать runner, а сайт не откроется.
Runner разрешён только для main и ручного запуска: **нет pull_request trigger**.
GitHub предупреждает, что self-hosted runner в **публичном** репозитории
потенциально опасен. Не запускайте недоверенный PR-код, проверяйте изменения
перед merge, лучше используйте приватный репозиторий для инфраструктуры.
Не кладите токены, пароли и production-ключи в виртуалку.
Для balfest.ru потребуется отдельный сервер с TLS/HTTPS; DNS домена не менять
на домашний IP.
