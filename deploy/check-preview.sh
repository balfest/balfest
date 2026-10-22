#!/usr/bin/env bash
# End-to-end checks against the real Nginx -> FastAPI connection.
set -Eeuo pipefail

BASE_URL="http://127.0.0.1:8080"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

app_id="$(sudo -n docker compose --project-name balfest-preview ps --quiet app)"
web_id="$(sudo -n docker compose --project-name balfest-preview ps --quiet web)"
if [[ -z "$app_id" || -z "$web_id" ]]; then
  echo "::error::Expected both app and web containers to be running." >&2
  exit 1
fi

for container_id in "$app_id" "$web_id"; do
  health="$(sudo -n docker inspect --format '{{.State.Health.Status}}' "$container_id")"
  if [[ "$health" != "healthy" ]]; then
    echo "::error::Container $container_id is not healthy: $health" >&2
    exit 1
  fi
done

# Retry while Nginx starts and verifies that the page contains real festival content.
curl --fail --silent --show-error --retry 10 --retry-delay 2 --retry-connrefused   "$BASE_URL/" -D "$TMP_DIR/headers.txt" -o "$TMP_DIR/home.html"
grep -q 'БАЛФЕСТ' "$TMP_DIR/home.html"
grep -q '4–6 декабря 2026' "$TMP_DIR/home.html"

curl --fail --silent --show-error "$BASE_URL/theme.css" -o "$TMP_DIR/theme.css"
grep -q -- '--bg:' "$TMP_DIR/theme.css"

curl --fail --silent --show-error "$BASE_URL/robots.txt" -o "$TMP_DIR/robots.txt"
grep -q 'Sitemap:' "$TMP_DIR/robots.txt"

curl --fail --silent --show-error "$BASE_URL/sitemap.xml" -o "$TMP_DIR/sitemap.xml"
grep -q 'balfest.ru' "$TMP_DIR/sitemap.xml"

for asset in styles.css site.js hero-1280.webp open-call-1280.webp; do
  curl --fail --silent --show-error "$BASE_URL/static/assets/$asset"     -o "$TMP_DIR/$asset"
  test -s "$TMP_DIR/$asset"
done

for path in /missing /static/missing.png; do
  status="$(curl --silent --show-error -o /dev/null -w '%{http_code}' "$BASE_URL$path")"
  if [[ "$status" != "404" ]]; then
    echo "::error::Expected HTTP 404 for $path; got $status" >&2
    exit 1
  fi
done

if ! grep -qi '^server: nginx' "$TMP_DIR/headers.txt"; then
  echo "::error::Expected Nginx to serve as the frontend." >&2
  exit 1
fi

echo "PASS: both containers healthy; page, date, theme, SEO, CSS, JS, images, 404 and Nginx."
echo "Local preview ready: $BASE_URL/"
