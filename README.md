# CFD Particle Figures

可复用的 CFD/DPM 科研绘图技能，用于冶金精炼、镀锌槽、钢包、RH、中间包等过程设备的仿真后处理。

A reusable skill and Python renderer for publication figures from saved CFD fields and particle-tracking results.

## 支持的图形

- 颗粒真实生成区域、初始位置及同一批颗粒的多时刻运动轨迹。
- 三维半透明浓度等值面，独立的物理量色带和颗粒时间色带。
- 实际壁面上的沉积质量、沉积通量或其他已导出的壁面量。
- 多时刻、多物理量对比及总览；PNG、LZW TIFF、SVG 和 PDF 导出。

通用样式与具体物理场景分开配置。镀锌槽预设记录了连续灰色半透明钢带、180°相机视角以及 Fe/Al/Fe₂Al₅ 绘图方式；其他设备须使用自己的几何、源位置和物理量定义。

## 使用

技能入口为 [SKILL.md](SKILL.md)。将完整仓库目录放入个人技能目录，保留文件结构；技能名称为 `cfd-particle-figures`。

示例请求：

```text
用 $cfd-particle-figures 绘制这组精炼结果，展示颗粒生成区域、
同一批颗粒的运动过程，以及三维半透明浓度场。标签使用英文。
```

也可以直接运行脚本。环境依赖：Python、NumPy、Matplotlib、SciPy、scikit-image、Pillow。

```bash
python -m pip install numpy matplotlib scipy scikit-image pillow
python scripts/render_scene.py /path/to/project/scene.json --validate-only
python scripts/render_scene.py /path/to/project/scene.json --preview
python scripts/render_scene.py /path/to/project/scene.json
```

从 [scene.example.json](assets/scene.example.json) 创建项目配置，按 [数据契约](references/data-contract.md) 提供 NPZ 数据。脚本读取已适配的数据，不直接读取原生 Fluent CAS/DAT；字段提取、网格关联和粒子身份匹配需要按实际求解器导出格式处理。

## 文件

| 路径 | 用途 |
| --- | --- |
| `SKILL.md` | 技能触发范围、绘图流程及验证要求 |
| `scripts/render_scene.py` | 场景配置驱动的通用渲染器 |
| `scripts/figure_tools.py` | 体积加权聚合、保留缺失段的轨迹、受限补点、连续带面 |
| `assets/scene.example.json` | 通用场景配置示例 |
| `assets/galvanizing.style.json` | 镀锌槽样式配置片段 |
| `references/data-contract.md` | 输入数组、配置、单位及数据关联规范 |
| `references/scenarios.md` | 钢包、RH、中间包、析出和壁面沉积适配说明 |
| `references/galvanizing-style.md` | 已确认的镀锌槽绘图预设 |

## 数据与可复现性

颗粒缺失段不连线，不生成虚构轨迹；浓度云团不能代替源位置。区分欧拉析出物浓度、计算包数量、物理粒子数密度和壁面沉积量。对比图固定视角及标尺，保留原始有符号数值；补点、参考浓度、颜色归一化和显示几何均须记录。

渲染器生成 `figure_manifest.json` 和 `figure_caption.md`，记录输入 SHA256、配置、颜色范围和显示处理。默认论文导出为 600 dpi，但目标期刊要求仍需另行核对。Matplotlib 透明多边形遮挡排序具有近似性，需要检查实际输出。

代码已通过真实 CFD 数据试画及零场、单侧变化、缺失轨迹和壁面数据等功能检查。仓库包含绘图方法、样式和通用脚本；研究数据由各项目自行提供。
