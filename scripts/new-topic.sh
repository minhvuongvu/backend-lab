#!/usr/bin/env bash
# Create a new topic from templates/. Invoked by `make new-topic SLUG=...`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SLUG="${1:-}"

if [[ ! "$SLUG" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "error: SLUG must be kebab-case (a-z, 0-9, '-'), got: '$SLUG'" >&2
  exit 1
fi

TOPIC_DIR="$ROOT/topics/$SLUG"
if [[ -e "$TOPIC_DIR" ]]; then
  echo "error: topic already exists: topics/$SLUG" >&2
  exit 1
fi

# Human-readable title: "transactional-outbox" -> "Transactional Outbox"
TOPIC="$(echo "$SLUG" | tr '-' ' ' | awk '{for (i = 1; i <= NF; i++) $i = toupper(substr($i, 1, 1)) substr($i, 2)} 1')"
DATE="$(date +%Y-%m-%d)"

mkdir -p "$TOPIC_DIR"/{system,experiments,results/raw,results/charts,deploy}
for d in system experiments results/raw results/charts deploy; do
  touch "$TOPIC_DIR/$d/.gitkeep"
done

# Templates live one level below the repo root (templates/), topics two levels (topics/<slug>/),
# so shared asset paths are rewritten from ../shared/ to ../../shared/ on copy.
render() {
  sed -e "s/{{TOPIC}}/$TOPIC/g" -e "s/{{SLUG}}/$SLUG/g" -e "s/{{DATE}}/$DATE/g" \
      -e 's|"\.\./shared/|"../../shared/|g' "$1" > "$2"
}

render "$ROOT/templates/topic-README.md" "$TOPIC_DIR/README.md"
# One HTML document per phase: 01-research.html ... 07-production.html
for tpl in "$ROOT"/templates/0[1-7]-*.html; do
  render "$tpl" "$TOPIC_DIR/$(basename "$tpl")"
done

cat > "$TOPIC_DIR/results/env.md" <<EOF
# Môi trường chạy thí nghiệm — $TOPIC

<!-- Điền ở phase 5, TRƯỚC khi chạy. Lấy bằng lệnh thật, không ghi theo trí nhớ. -->

| Mục | Giá trị | Lệnh lấy |
|---|---|---|
| CPU (model, số core) | | \`lscpu\` / \`wmic cpu get name,NumberOfCores\` |
| RAM | | \`free -h\` / \`systeminfo\` |
| OS | | \`uname -a\` / \`ver\` |
| Docker / Compose | | \`docker version\`, \`docker compose version\` |
| Tài nguyên cấp cho Docker (CPU/RAM) | | \`docker info\` |
| JDK | | \`java -version\` |
| Spring Boot | | \`system/pom.xml\` |
| PostgreSQL / Redis / Kafka | | image tag trong \`experiments/docker-compose.yml\` |
| k6 | | \`k6 version\` |
| Cấu hình JVM (heap, GC) | | |
| Cấu hình riêng của lần chạy | | |
| Ngày chạy | | |

## Ghi chú
<!-- Máy có đang chạy tác vụ nặng khác không? Laptop cắm sạc? Thermal throttling? -->
EOF

# Append a row to the topic table in the root README (before the end marker).
ROW="| $SLUG | 0 — chưa bắt đầu | [README](topics/$SLUG/README.md) |"
README="$ROOT/README.md"
if ! grep -q '<!-- topics:end -->' "$README"; then
  echo "error: marker '<!-- topics:end -->' not found in README.md" >&2
  exit 1
fi
awk -v row="$ROW" '/<!-- topics:end -->/ { print row } { print }' "$README" > "$README.tmp"
mv "$README.tmp" "$README"

echo "Created topics/$SLUG (title: $TOPIC, date: $DATE)"
