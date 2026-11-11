# Model Comparison Video

从一段 prompt 和可选模型名单生成 Offloop 风格的多模型同屏评测视频。支持通过 OpenRouter 生成 HTML / Three.js / Canvas 场景，验证运行、录制动画，并展示真实 API 耗时与费用。

## 安装到 Codex

将仓库克隆到技能目录：

```sh
git clone https://github.com/Velcro007/model-comparison-video.git ~/.codex/skills/model-comparison-video
```

如果该目录已经存在，请先检查现有内容，勿直接覆盖。重新开启聊天以加载技能。

## 使用

```text
使用 $model-comparison-video
Prompt：你的视觉场景提示词
对比模型：可选，不填则查询当前模型后选择
```

需配置可用的 `OPENROUTER_API_KEY`，或运行时通过隐藏输入提供。仓库不包含凭据。API 调用产生费用；本地渲染不需要额外模型订阅。

## 能力

- 2–3 模型横排，4 模型四宫格。
- 默认 64,000 token 输出预算，按模型实际能力调整；检测截断，有限重试。
- 保存各次请求、原始响应、计费和运行状态；浏览器验证后才录制。
- 输出 H.264/AAC MP4，1080px/格、30 fps，含配乐和 TIME/COST 动画条。
- 单模型重跑、备份并替换原视频，区分成功尝试费用与累计费用。

## 依赖与文档

Python 3.10+：`python3 -m pip install -r requirements.txt`。浏览器操作使用 ego-browser 技能及 CLI；模型调用需联网访问 OpenRouter，场景的 CDN 依赖也可能需要网络。

- [技能入口](SKILL.md)
- [运行与配置说明](references/workflow.md)
- [模型调用脚本](scripts/run_models.py)
- [视频渲染器](scripts/render.py)
- [录制脚本模板](scripts/record.js)

录制脚本是供代理填写参数后执行的模板，不是独立的一键启动程序。对于 DOM 页面或多个 canvas，应按运行说明录制完整视口。

## 范围与素材

这是单次视觉编程效果对比流程，不是综合模型能力排名，也不调用视频生成模型。各模型预算或推理默认值不同时会记录差异。

品牌标志与字体的来源及使用说明见 [assets/NOTICE.md](assets/NOTICE.md) 和 [字体许可证](assets/Inter-OFL.txt)。第三方标志不代表授权背书；本仓库未授予这些商标的权利。
