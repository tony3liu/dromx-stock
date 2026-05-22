# DromX 前端启动手册

## 环境要求

| 工具 | 推荐版本 | 说明 |
|------|----------|------|
| Node.js | ≥ 20.x | JavaScript 运行时 |
| npm | ≥ 10.x | 随 Node.js 一起安装的包管理器 |

验证安装：

```bash
node --version   # 应输出 v20.x.x 或更高
npm --version    # 应输出 10.x.x 或更高
```

## 项目结构概览

```
DromX/
├── SETUP.md                 # 本手册
└── frontend/                # 前端项目根目录
    ├── index.html           # HTML 入口
    ├── package.json         # 项目配置 & 依赖声明
    ├── tsconfig.json        # TypeScript 配置
    ├── vite.config.ts       # Vite 构建 & Vitest 测试配置
    ├── public/
    │   └── logo.svg         # 网站图标
    └── src/
        ├── main.tsx         # 应用入口
        ├── App.tsx          # 根组件（路由 & 全局状态）
        ├── App.test.tsx     # 集成测试
        ├── styles.css       # 全局样式
        ├── components/      # 通用组件
        ├── pages/           # 页面组件
        ├── data/            # 数据模型 & 默认数据
        ├── i18n/            # 国际化文本
        └── test/            # 测试配置
```

## 技术栈

- **React 19** — UI 框架
- **TypeScript** — 类型检查
- **Vite** — 开发服务器 & 生产构建
- **Vitest** — 单元测试 & 集成测试
- **Testing Library** — 组件测试工具
- **Lucide React** — 图标库

## 快速启动

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

启动后终端会输出访问地址，通常是：

```
VITE vX.X.X  ready in xxx ms
➜  Local:   http://localhost:5173/
➜  Network: http://<your-ip>:5173/
```

在浏览器中打开 `http://localhost:5173/` 即可查看应用。

> **注意**：`dev` 脚本使用了 `--host 0.0.0.0`，允许同一局域网内的其他设备通过你的 IP 地址访问开发服务器。

### 3. 生产构建

```bash
npm run build
```

构建产物输出到 `frontend/dist/` 目录。部署时将该目录下的所有文件上传到静态服务器（Nginx、CDN 等）即可。

> **说明**：这是一个纯前端 SPA 应用，无后端服务依赖。所有数据均为前端 mock 数据，保存在 React 组件状态中。

### 4. 运行测试

```bash
# 单次运行所有测试
npm test

# 持续监听模式（开发时使用）
npm run test:watch
```

## 项目功能页面

| 路由路径 | 页面 | 说明 |
|----------|------|------|
| `/` | Landing Page | 产品首页 |
| `/console` | Agent Console | 控制台（Agent、Swarm、技能工作台、工作流、算力中心） |
| `/agents` | Role Agent Store | Agent 应用商店 |
| `/agents/:index/edit` | Agent Builder | Agent 编辑器 |
| `/swarms` | Swarm Center | Swarm 中心，查看所有已组装的团体 |
| `/skills` | Skills Center | 技能中心 |
| `/skills/new` | Skill Builder | 技能编辑器 |
| `/workflows/new` | Workflow Editor (New) | 新建工作流 |
| `/workflows/:index/edit` | Workflow Editor | 编辑工作流 |

## 开发注意事项

1. **无路由库**：项目未使用 React Router，路由通过 `window.location.pathname` 手动解析，配合 `window.history.pushState` 和 `popstate` 事件实现 SPA 导航。

2. **无状态管理库**：所有状态通过 React 的 `useState` / `useMemo` 管理，在 `App.tsx` 中集中，通过 props 向下传递。

3. **国际化**：所有文本定义在 `src/i18n/content.ts` 中，支持中英文切换，默认语言为中文。

4. **样式**：所有样式写在 `src/styles.css` 单文件中，使用原生 CSS + CSS 变量实现深色主题。

5. **无环境变量**：项目当前不需要 `.env` 文件，所有配置均为硬编码的 mock 数据。

## 常见问题

**Q: 启动后页面空白？**
检查浏览器控制台是否有错误。确认已执行 `npm install` 且没有报错。

**Q: `npm install` 报错？**
尝试删除 `node_modules` 和 `package-lock.json` 后重新安装：

```bash
rm -rf node_modules package-lock.json
npm install
```

**Q: TypeScript 类型检查报错？**
运行类型检查：

```bash
npx tsc --noEmit
```

部分错误来源于测试文件缺少 jest/vitest 全局类型声明，属于正常现象，不影响运行。

**Q: 如何切换语言？**
点击页面右上角的语言切换按钮（中文/English）。

**Q: 数据是否会持久化？**
不会。当前所有数据（Agent、Swarm、工作流、技能等）仅保存在 React 组件状态中，刷新页面后会重置为默认数据。
