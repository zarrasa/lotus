# Подпись кода через SignPath — что сделать

Подписанный Lotus меньше пугает Windows SmartScreen и антивирусы. SignPath Foundation
бесплатно подписывает открытые проекты, но заявку подаёт автор, а одобряют её люди
(обычно несколько дней). Гарантии одобрения нет.

## 1. Подать заявку

1. Открыть https://signpath.org/apply и заполнить форму:
   - **Project name:** Lotus
   - **Repository:** ссылка на этот репозиторий
   - **License:** MIT
   - **Description** (можно вставить как есть):
     > Lotus is a free open-source Windows app that restores access to YouTube, Discord,
     > Telegram, Steam and other services blocked by DPI (deep packet inspection) at the
     > ISP level, without a VPN. It is a GUI around the well-known open-source tools
     > zapret, GoodbyeDPI and tg-ws-proxy. Releases are built by GitHub Actions
     > (.github/workflows/release.yml) from this repository.
2. Дождаться письма. В нём будут: Organization ID, имя проекта (project slug) и политики подписи
   (signing policy slug — обычно `release-signing`).

## 2. Подключить к репозиторию

На GitHub: **Settings → Secrets and variables → Actions**

- вкладка **Variables** → New repository variable:
  - `SIGNPATH_ORGANIZATION_ID` — Organization ID из письма
  - `SIGNPATH_PROJECT_SLUG` — project slug
  - `SIGNPATH_POLICY_SLUG` — signing policy slug
- вкладка **Secrets** → New repository secret:
  - `SIGNPATH_API_TOKEN` — API-токен из кабинета SignPath (раздел Users → CI user → API token)

В SignPath, в настройках проекта, указать GitHub как Trusted Build System для этого репозитория
и artifact configuration: zip-архив с `LotusSetup.exe` и `Lotus.exe` (оба подписываются).

## 3. Готово

Следующий выпуск (новый тег версии) будет подписан автоматически — шаг «Подпись (SignPath)»
в `.github/workflows/release.yml` включается сам, когда заданы переменные выше.
