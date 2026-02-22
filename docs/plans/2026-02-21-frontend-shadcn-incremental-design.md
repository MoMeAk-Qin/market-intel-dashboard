# 前端 shadcn/ui 增量优化设计（Research 优先）

## 1. 目标与范围

- 目标：在保持现有深色数据中台视觉风格的前提下，基于 shadcn/ui 进行增量优化。
- 本轮范围：
  - 统一基础 token 与核心基础组件风格。
  - 引入 `form/command/chart/tooltip/tabs/sonner` 组件。
  - 首批落地到 `Research` 页面。
- 非目标：
  - 不改后端 API。
  - 不做全站视觉重构。
  - 不一次性重写 `Events/News` 页面。

## 2. Token 规范

### 2.1 语义 token

在 `apps/web/src/app/globals.css` 定义语义变量：

- 布局与文本：`--background --foreground --card --card-foreground --popover --popover-foreground`
- 交互状态：`--primary --primary-foreground --secondary --secondary-foreground --muted --muted-foreground --accent --accent-foreground`
- 风险状态：`--destructive --destructive-foreground`
- 边框与输入：`--border --input --ring`
- 图表：`--chart-1 ... --chart-5`
- 圆角：`--radius`

### 2.2 Tailwind 映射

在 `apps/web/tailwind.config.ts` 扩展：

- `colors` 映射到所有语义变量。
- `borderRadius` 使用 `--radius`。
- `boxShadow.panel` 作为卡片统一阴影。

## 3. 基础组件使用约束

- 禁止在基础组件内部写死 `bg-white/text-slate-900/border-slate-*` 等浅色硬编码。
- 组件优先使用语义类：`bg-card text-card-foreground border-border ring-ring`。
- 统一交互节奏：
  - hover/颜色过渡 `150~250ms`
  - focus 统一 `focus-visible:ring-2 focus-visible:ring-ring`
- 允许页面级覆盖类名，但应基于语义 token 而非固定色值。

## 4. Research 页面交互准则

### 4.1 表单层

- 使用 `react-hook-form + zod` 校验 ticker。
- 输入值统一大写。
- 非法 ticker 阻止提交并显示错误信息。

### 4.2 快速选择层

- 使用 `Command` 提供常用 ticker 快速检索与回车选择。
- 选择后同步更新输入框与查询状态。

### 4.3 信息分区层

- 使用 `Tabs` 拆分：`Earnings / Reports / Fact Check`。
- 避免单页长滚动导致信息检索效率下降。

### 4.4 图表层

- 使用 `ChartContainer + Recharts` 展示核心指标。
- 图表色值通过 `ChartConfig` 与 CSS 变量注入，避免硬编码。
- Tooltip/Legend 样式统一深色语义风格。

### 4.5 状态层

- 保留 `演示数据（非实时）` 提示。
- 对加载失败使用 `toast + 卡片内重试` 双反馈。

## 5. 后续扩展顺序（增量）

1. `Events` 页面
- 将筛选区域迁移到 `Form` 体系。
- 用统一 token 改造表格、抽屉详情、分页控制样式。

2. `News` 页面
- 统一筛选控件与结果卡片语义色。
- 追加 `tooltip` 解释排序与来源标签。

3. `Search` 与 `Daily Summary`
- 复用 `Form + Tabs + Badge` 状态表达。
- 将结果反馈逐步迁移到 `sonner`。

## 6. 验收清单

- [ ] `pnpm lint` 通过。
- [ ] `pnpm -C apps/web build` 通过。
- [ ] `pnpm -C apps/web test:contract` 通过。
- [ ] Research 页面在 375/768/1024/1440 宽度无横向滚动。
- [ ] 键盘可操作 ticker 输入、命令面板、Tabs。
- [ ] `prefers-reduced-motion` 下动画降级仍生效。
