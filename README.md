# 豆包 Linux 桌面客户端（非官方）

> **免责声明**：本项目是**非官方**的豆包（Doubao）Linux 桌面客户端，由个人出于学习目的开发，与北京抖音信息服务有限公司（ByteDance）无任何关联，未获得其授权或认可。「豆包」「Doubao」及相关商标权利归其所有者所有。本客户端仅作为网页版的桌面封装，不修改、不存储、不分发任何官方服务端内容。如官方推出 Linux 版本，请以官方版本为准。

## 项目背景

官方目前仅提供 Windows / macOS 客户端。经分析，官方 Windows 客户端
（`doubao_client_..._ext.exe`）本质上是基于 Rust + Win32 的桌面壳，
承载豆包网页服务。由于 Windows 二进制无法直接在 Linux 上复用，本项目按其
产品形态用 GTK3 + WebKit2GTK 重新实现了一个 Linux 原生客户端，
提供与官方桌面客户端一致的核心体验。

## 功能特性

- 原生桌面窗口（GTK3 + WebKit2GTK），承载豆包网页版全部功能
- 登录态与本地数据持久化（Cookie / LocalStorage / IndexedDB）
- 文件下载（保存对话框，支持自定义路径）
- 外链跳转：站内链接同窗打开，站外链接交给系统默认浏览器
- 麦克风权限仅对 `www.doubao.com` 放行（语音输入可用）
- 自定义 User-Agent（携带 `DoubaoDesktop` 标识）
- 加载失败时显示内置重试页
- 单实例运行，桌面菜单集成（图标 / 分类 / 关键词）

### 快捷键

| 快捷键 | 功能 |
| --- | --- |
| `Ctrl + R` / `Ctrl + F5` | 刷新页面 |
| `Alt + Home` | 回到首页 |
| `Ctrl + +` / `Ctrl + -` / `Ctrl + 0` | 放大 / 缩小 / 重置缩放 |
| `Ctrl + Q` | 退出 |

## 安装

系统要求：Debian / Ubuntu / Deepin / UOS 等 amd64 桌面系统。

```bash
sudo dpkg -i doubao_1.0.2_amd64.deb
sudo apt -f install   # 自动补齐依赖
```

依赖：`python3 (>= 3.7)`、`python3-gi`、`gir1.2-gtk-3.0`、
`gir1.2-webkit2-4.0`、`libwebkit2gtk-4.0-37`。

安装后可从应用菜单启动「豆包」，或终端执行：

```bash
doubao
```

卸载：

```bash
sudo apt remove doubao
```

## 从源码构建

打包源目录为 `build/doubao-deb/`（Debian 包标准目录结构）：

```bash
dpkg-deb --build --root-owner-group build/doubao-deb doubao_1.0.2_amd64.deb
```

## 项目结构

```
.
├── .gitignore                  # 忽略官方 exe 参考样本（专有二进制，不入库）
├── README.md                   # 本说明
├── doubao_1.0.2_amd64.deb      # 构建产物：Linux 安装包
└── build/doubao-deb/           # deb 打包源目录
    ├── DEBIAN/                 # control / postinst / postrm
    ├── opt/doubao/doubao.py    # 客户端主体（约 200 行 Python）
    ├── opt/doubao/doubao.png   # 应用图标
    ├── usr/bin/doubao          # 启动器
    └── usr/share/              # desktop 入口与 hicolor 图标
```

## 技术说明

- 运行时：Python 3 + PyGObject + GTK3 + WebKit2GTK（WebKitGTK 2.38 实测通过）
- 窗口：`Gtk.ApplicationWindow` 内嵌 `WebKit2.WebView`，默认 1280×820
- 数据目录：遵循 XDG 规范，存储于 `~/.local/share/webkitgtk/` 等默认位置
- 已在 UOS Desktop 20 Professional（x11）上实测：页面渲染、断网重试页、
  窗口类名（`StartupWMClass=doubao`）与菜单图标均正常

## 故障排查

### 启动后显示「暂时无法加载豆包 · Peer failed to perform TLS handshake」

这是**网络层 TLS 握手被拒绝**，与客户端界面无关。实测结论：

- 豆包 CDN 对 **TLS 1.3** 握手与 **GnuTLS 3.6**（Debian 10 / UOS 20 自带的
  `glib-networking` 底层库）组合不兼容，服务端会中断握手；同一环境下
  OpenSSL（curl / Chrome）以及 GnuTLS 走 **TLS 1.2** 均正常
- 1.0.1 起客户端已在进程内固定 `G_TLS_GNUTLS_PRIORITY=NORMAL:-VERS-TLS1.3`，
  只影响本应用，不修改系统配置，无需额外设置

若仍偶发，可手动确认环境变量是否生效：

```bash
G_TLS_GNUTLS_PRIORITY="NORMAL:-VERS-TLS1.3" doubao
```

同时检查是否启用了代理 / VPN（其证书或 TLS 策略也可能导致握手失败）。

### 点击某些功能后异常卡顿

1.0.2 已开启 WebKit 的 2D canvas 硬件加速与 DNS 预取。若仍卡顿，用调试模式启动
定位具体原因（卡顿时把终端里 `[perf]` 开头的行记录下来）：

```bash
DOUBAO_DEBUG=1 doubao
```

- `[perf] block 1200ms ...` —— 页面主线程被阻塞的时长（前端自身 JS 重计算）
- `[perf] slowres 3500ms <url>` —— 超过 1 秒的慢请求（网络/接口问题）

两者区别很重要：`block` 多说明卡在页面脚本运算（WebKit 引擎侧），`slowres` 多
说明卡在等待网络响应。

## 已知限制

- 依赖网络访问 `www.doubao.com`，离线不可用
- 网页版内的「下载电脑版」推广弹窗为站点行为，客户端不做屏蔽
- 不具备 Windows 客户端的本地任务执行能力（那是官方客户端的私有扩展）
