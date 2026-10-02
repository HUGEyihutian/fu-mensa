# FU Mensa 通关手册

柏林自由大学六个食堂（Mensa FU II、Shokudō、Pharmazie、Koserstraße、Herrenhaus Düppel、Lankwitz）的本周与下周菜单、搭配推荐和个人用餐计划。

## 数据从哪来

`scripts/scrape.py` 请求 studierendenWERK BERLIN 官网自己用来切换日期标签的接口
`POST https://www.stw.berlin/xhr/speiseplan-wochentag.html`（参数 `resources_id`、`date`），
解析出每道菜的分组、名称、三档价格（学生/员工/访客）、过敏原编号、素食/纯素标记、交通灯评级和 CO₂、用水量，
写入 `docs/data/menus.json`。只用 Python 标准库。

GitHub Actions（`.github/workflows/update-menus.yml`）每天清晨跑一次，周五到周日下午各加跑一次，以便尽早拿到下周菜单。菜单有变化才提交。

## 页面

`docs/index.html` 通过 GitHub Pages 发布（Settings → Pages → Source: Deploy from a branch → `main` / `docs`）。
打开时读取 `docs/data/` 下的三个文件，所以每次打开都是最近一次抓取的结果。

## 让模型变得更懂你

- `docs/data/model.json`：饱腹估计、搭配规则、打分权重、长期偏好。改这里就是改模型。
- `docs/data/feedback.json`：提交到仓库的口味反馈（整道菜和关键词的 ±1）。
- 页面上的 👍/👎 和计划先存在浏览器本地；在“模型与反馈”里导出，可以粘贴进 `feedback.json`，或发给 Claude，让它一并调整 `model.json`。

## 手动刷新

Actions → Update menus → Run workflow。本地：`python3 scripts/scrape.py`。
