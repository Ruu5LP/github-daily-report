# GitHub Daily Report

GitHub の活動を自動集計し、毎日 Discord（または他のサービス）へ日報として送信する CLI ツールです。

---

## 概要

指定した Organization・ユーザー・リポジトリに対して、その日の

- 作成 PR / Merge PR
- Close Issue
- Commit
- Review 待ち PR

を集計し、Markdown 形式の日報を生成します。

---

## 特徴

- **柔軟なターゲット指定**: Org 全体 / ユーザー全体 / 特定リポジトリを環境変数で切り替え
- **複数通知先**: Discord Webhook をネイティブ対応。Lark / LINE は拡張可能なスタブ実装
- **GitHub Actions 対応**: 毎日 JST 10:00 (UTC 01:00) に自動実行するワークフロー付き
- **型安全**: Python 3.12 + dataclasses + BasedPyright で静的型検査
- **テスト**: pytest + pytest-mock でビジネスロジックをカバー

---

## 必要環境

- Python 3.12 以上
- [uv](https://docs.astral.sh/uv/) (パッケージマネージャー)

---

## インストール

### uv のセットアップ

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# または Homebrew
brew install uv
```

### リポジトリのクローンと依存関係のインストール

```bash
git clone https://github.com/YOUR_ORG/github-daily-report.git
cd github-daily-report

# 依存関係のインストール（仮想環境も自動作成）
uv sync
```

---

## 環境変数一覧

`.env` ファイルを作成するか、環境変数として設定してください。

### GitHub Secrets（機密情報）

| 変数名                      | 説明                                    | 必須 |
| --------------------------- | --------------------------------------- | ---- |
| `GH_TOKEN`                  | GitHub Personal Access Token            | ✅   |
| `DISCORD_WEBHOOK_URL`       | Discord Webhook URL                     | ※1  |
| `LARK_WEBHOOK_URL`          | Lark Webhook URL（将来実装）            | -    |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot チャンネルアクセストークン（将来実装） | -    |

※1 `NOTIFY_PROVIDER=discord` の場合に必須

### GitHub Variables（非機密設定）

| 変数名                  | 説明                                                         | デフォルト  |
| ----------------------- | ------------------------------------------------------------ | ----------- |
| `GITHUB_TARGET_TYPE`    | `org_all` / `user_all` / `repos` のいずれか                 | `user_all`  |
| `GITHUB_TARGET_ORG`     | 対象 Organization 名（`org_all` 時に必須）                   | -           |
| `GITHUB_TARGET_USER`    | 対象ユーザー名（`user_all` 時に必須）                        | -           |
| `GITHUB_TARGET_REPOS`   | カンマ区切りの `owner/repo` リスト（`repos` 時に必須）       | -           |
| `NOTIFY_PROVIDER`       | `discord` / `lark` / `line`（未設定時は stdout のみ）        | -           |
| `LINE_TO`               | LINE 送信先（将来実装）                                      | -           |

---

## GitHub Secrets 一覧

GitHub リポジトリの **Settings → Secrets and variables → Actions → Secrets** で設定します。

| Secret 名                   | 値の例                                      |
| --------------------------- | ------------------------------------------- |
| `GH_TOKEN`                  | `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`  |
| `DISCORD_WEBHOOK_URL`       | `https://discord.com/api/webhooks/ID/TOKEN` |
| `LARK_WEBHOOK_URL`          | `https://open.larksuite.com/open-apis/...`  |
| `LINE_CHANNEL_ACCESS_TOKEN` | `<LINE Channel Access Token>`               |

---

## GitHub Variables 一覧

GitHub リポジトリの **Settings → Secrets and variables → Actions → Variables** で設定します。

| Variable 名             | 値の例                            |
| ----------------------- | --------------------------------- |
| `GITHUB_TARGET_TYPE`    | `org_all`                         |
| `GITHUB_TARGET_ORG`     | `COFFISO`                         |
| `GITHUB_TARGET_USER`    | `Ruu5LP`                          |
| `GITHUB_TARGET_REPOS`   | `COFFISO/kouchare-tv,COFFISO/ai-sensei` |
| `NOTIFY_PROVIDER`       | `discord`                         |

---

## GitHub Actions 設定方法

1. 上記の Secrets / Variables を設定する
2. `.github/workflows/daily-report.yml` がリポジトリに含まれていることを確認する
3. **Actions タブ** → **Daily Report** → **Run workflow** で手動実行してテスト
4. 以降は毎日 JST 10:00 に自動実行されます

---

## 実行方法

### 通常実行

```bash
uv run daily-report
```

### オプション

```bash
# データを収集するが通知を送信しない
uv run daily-report --dry-run

# 通知に加えて stdout にも出力する
uv run daily-report --stdout

# 特定の日付を指定
uv run daily-report --date 2026-06-29

# 組み合わせ
uv run daily-report --dry-run --date 2026-06-28 --stdout
```

---

## 出力例

```markdown
# 開発日報 2026-06-29

## 全体サマリ

- 更新Repositoryの数: 3
- 作成PR: 2
- Merge PR: 1
- Close Issue: 3
- Commit数: 8
- Review待ちPR: 1

## 人別進捗

### alice

#### 作成PR
- [#42 feat: ユーザー認証を追加](https://github.com/COFFISO/kouchare-tv/pull/42) @ COFFISO/kouchare-tv

#### Commit
- abc1234: fix: typo in README @ COFFISO/ai-sensei

### bob

#### MergePR
- [#38 chore: 依存関係を更新](https://github.com/COFFISO/kouchare-tv/pull/38) @ COFFISO/kouchare-tv

#### Review待ち
- [#42 feat: ユーザー認証を追加](https://github.com/COFFISO/kouchare-tv/pull/42) @ COFFISO/kouchare-tv (requested by: alice)

## Repository別

### COFFISO/kouchare-tv

#### PR
- [#42 feat: ユーザー認証を追加](https://github.com/COFFISO/kouchare-tv/pull/42) - open
- [#38 chore: 依存関係を更新](https://github.com/COFFISO/kouchare-tv/pull/38) - merged

#### Commit
- def5678: feat: add login page (by: alice)
```

---

## 開発方法

### テスト実行

```bash
uv run pytest
uv run pytest -v  # 詳細表示
```

### Lint / フォーマット

```bash
# Lint チェック
uv run ruff check .

# 自動修正
uv run ruff check --fix .

# フォーマットチェック
uv run ruff format --check .

# フォーマット適用
uv run ruff format .
```

### 型チェック

```bash
uv run basedpyright
```

### 全チェックを一括実行

```bash
uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run pytest
```
