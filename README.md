# Crypto Balance Tracker

Автоматический сбор остатков USDT/USDC/ETH на кошельках в блокчейнах TRC20 и ERC20.  
Данные собираются ежедневно в **00:00 UTC** через GitHub Actions и публикуются на GitHub Pages.

## Возможности

- Сбор балансов TRC20 (USDT) и ERC20 (ETH, USDT, USDC)
- История снимков по дням
- Фильтр по кошельку и блокчейну
- Тёмный дашборд, работает прямо из GitHub Pages

## Быстрый старт

### 1. Форкнуть / клонировать репозиторий

```bash
git clone https://github.com/YOUR_USERNAME/crypto-balance-tracker.git
cd crypto-balance-tracker
```

### 2. Добавить кошельки

Отредактировать `wallets.json`:

```json
{
  "wallets": [
    {
      "id": "wallet_1",
      "label": "Основной",
      "trc": "TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "erc": "0xXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    },
    {
      "id": "wallet_2",
      "label": "Резервный",
      "trc": "",
      "erc": "0xYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"
    }
  ]
}
```

- Если кошелёк используется только в одном блокчейне — оставьте второй адрес пустой строкой.

### 3. Получить API-ключи

| Сервис | Ключ | Ссылка | Бесплатно |
|--------|------|--------|-----------|
| Etherscan | `ETHERSCAN_API_KEY` | https://etherscan.io/myapikey | ✅ |
| TronGrid *(опционально)* | `TRONGRID_API_KEY` | https://www.trongrid.io/ | ✅ |

Без TronGrid скрипт использует TronScan API без ключа (лимиты ниже).

### 4. Добавить секреты в GitHub

`Settings → Secrets and variables → Actions → New repository secret`:

- `ETHERSCAN_API_KEY` — обязательно для ERC20
- `TRONGRID_API_KEY` — опционально для TRC20

### 5. Включить GitHub Pages

`Settings → Pages → Source: Deploy from branch → branch: main → folder: / (root)`

### 6. Первый запуск

`Actions → Collect Balances → Run workflow` — запустить вручную, не дожидаясь полуночи.

## Структура файлов

```
├── index.html                 # Дашборд (GitHub Pages)
├── wallets.json               # Список кошельков
├── scripts/
│   └── collect.py             # Скрипт сбора балансов
├── data/
│   ├── index.json             # Список доступных дат
│   └── history/
│       ├── 2025-01-01.json    # Снимок за день
│       └── ...
└── .github/workflows/
    └── collect.yml            # Cron-задание (00:00 UTC)
```

## Локальный запуск скрипта

```bash
pip install requests
export ETHERSCAN_API_KEY=ваш_ключ
export TRONGRID_API_KEY=ваш_ключ   # опционально
python scripts/collect.py
```

## Добавление/удаление кошельков

Просто отредактируйте `wallets.json` и сделайте коммит. Следующий запуск автоматически подхватит изменения.
