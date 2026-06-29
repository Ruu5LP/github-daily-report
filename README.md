# GitHub Daily Report

GitHub Organization・ユーザー・リポジトリの開発アクティビティを自動集計し、毎朝 Discord へ日報として送信する CLI ツールです。

---

## 特徴

- **柔軟なターゲット指定** — Org 全体 / ユーザー全体 / 特定リポジトリを環境変数で切り替え
- **全ブランチのコミットを取得** — デフォルトブランチだけでなく、PR の feature branch のコミットも収集
- **Discord 通知** — 2000 文字超えを自動分割して送信。Lark / LINE は拡張可能なスタブ実装
- **GitHub Actions 対応** — 毎朝 JST 10:00 に前日のアクティビティを自動通知
- **設定は Secrets のみで完結** — `GH_TOKEN` と `DISCORD_WEBHOOK_URL` を設定すれば動く
- **型安全** — Python 3.12 + dataclasses + BasedPyright
- **テスト** — pytest + pytest-mock

---

## 必要環境

- Python 3.12 以上
- [uv](https://docs.astral.sh/uv/)

---

## インストール

```bash
# uv のインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# リポジトリをクローン
git clone https://github.com/Ruu5LP/github-daily-report.git
cd github-daily-report

# 依存関係のインストール
uv sync
```

---

## 環境変数

### Secrets（GitHub リポジトリの Settings → Secrets and variables → Actions → Secrets）

| 変数名 | 説明 | 必須 |
| --- | --- | --- |
| `GH_TOKEN` | GitHub Personal Access Token（`repo`, `read:org` スコープ） | ✅ |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL | Discord 通知時 |
| `LARK_WEBHOOK_URL` | Lark Webhook URL（将来実装） | - |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot トークン（将来実装） | - |
| `TARGET_TYPE` | `org_all` / `user_all` / `repos` | ✅ |
| `TARGET_ORG` | 対象 Organization 名（`org_all` 時） | - |
| `TARGET_USER` | 対象ユーザー名（`user_all` 時） | - |
| `TARGET_REPOS` | カンマ区切り `owner/repo`（`repos` 時） | - |
| `NOTIFY_PROVIDER` | `discord` / `lark` / `line`（未設定時は stdout のみ） | - |
| `LINE_TO` | LINE 送信先（将来実装） | - |

> Secrets と Variables どちらで設定しても動きます（Secrets が優先）。

---

## GitHub Actions 設定方法

1. 上記の Secrets を設定する
2. **Actions タブ → Daily Report → Run workflow** で手動実行して確認
3. 以降は毎朝 JST 10:00 に前日のアクティビティが自動送信されます

### 最小構成（Org 全体を Discord に通知する場合）

| Secret 名 | 値 |
| --- | --- |
| `GH_TOKEN` | `ghp_xxxx...` |
| `DISCORD_WEBHOOK_URL` | `https://discord.com/api/webhooks/...` |
| `TARGET_TYPE` | `org_all` |
| `TARGET_ORG` | `your-org-name` |
| `NOTIFY_PROVIDER` | `discord` |

---

## 実行方法

```bash
# 通常実行（前日分を通知）
uv run daily-report

# 通知せず stdout だけに出力
uv run daily-report --stdout

# 通知を送らずにレポートだけ生成（動作確認用）
uv run daily-report --dry-run

# 日付を指定
uv run daily-report --date 2026-06-28
```

---

## 出力例（Discord）

```
📋 **開発日報 2026-06-28**

**今日のまとめ**
　リポジトリ更新: 3
　PR作成: 6
　Merge: 9
　Issue完了: 9
　今日のCommit: 12
　Review待ち: 6

────────────────────────────────────
**メンバーの動き**

👤 **username**

  **作成PR**
  • `your-repo` [#123 機能追加: ○○の実装](https://github.com/...)

  **今日のCommit** (3件)
  • `your-repo` `a1b2c3d` 実装完了
  • `your-repo` `e4f5g6h` レビュー指摘を修正
  • `your-repo` `i7j8k9l` 命名を修正
```

---

## 開発方法

```bash
# テスト
uv run pytest

# Lint
uv run ruff check .
uv run ruff format .

# 型チェック
uv run basedpyright

# 全チェック一括
uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run pytest
```
