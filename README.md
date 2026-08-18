# 主板周线三浪检查表

这是一个零依赖的手机网页/PWA，用于收盘后逐项核对沪深主板交易条件，并展示自动扫描结果。

## 本机试用

在此目录运行：

```powershell
python -m http.server 8765
```

然后打开 `http://localhost:8765`。手机添加到主屏幕后可以像应用一样使用；检查状态保存在当前浏览器本地。

## GitHub Pages

将本目录内容推送到 GitHub 仓库的 `main` 分支，在仓库 Settings > Pages 中选择 `GitHub Actions`。`.github/workflows/pages.yml` 会自动部署。

## 自动筛选

GitHub Actions 在工作日 15:01（北京时间）运行 `.github/workflows/auto-screen.yml`，也可以在 Actions 页面手动运行。结果写入 `data/latest.json`，Pages 会自动刷新。

自动筛选先扫描全沪深主板报价池，再逐只获取完整日线数据并评分；ST 股票不进入候选推荐，PB 不高于 22 是其中一个软条件。共有 12 个软条件：5 星为全部通过，4 星至少 90%，3 星至少 80%（最多 2 个软缺口）。大盘闸门、主板范围、数据完整性不可容错。板块强度目前采用个股相对大盘强度和 MA20 的代理，最终下单前仍要人工确认行业强度。
