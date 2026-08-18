# 主板周线三浪检查表

这是一个零依赖的手机网页/PWA，用于收盘后逐项核对沪深主板交易条件。

## 本机试用

在此目录运行：

```powershell
python -m http.server 8765
```

然后打开 `http://localhost:8765`。手机添加到主屏幕后可以像应用一样使用；检查状态保存在当前浏览器本地。

## GitHub Pages

将本目录内容推送到 GitHub 仓库的 `main` 分支，在仓库 Settings > Pages 中选择 `GitHub Actions`。`.github/workflows/pages.yml` 会自动部署。

第一版不自动抓取行情，必须手动使用最近完整交易日数据。这样行情源失效或返回旧数据时不会误给出买入结论。
