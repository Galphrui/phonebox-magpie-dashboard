# 项目整理摘要

## 目标

将本机 magpie 的 AI 使用数据和模型路由过程，集成到 PhoneBox 手机桌面面板，并保留可更新的源码与安装流程。

## 已实现

1. PhoneBox 第 2 页显示 magpie 用量概览、模型请求、TokenFuture 余额与趋势。
2. PhoneBox 第 3 页显示路由来源、候选账户、实际命中账户、HTTP 结果和近期路由。
3. 活跃路由期间显示飞行中的小喜鹊；请求结束后动画停止。
4. macOS launchd 每 2 秒同步本机 magpie API 至 PhoneBox。
5. 关闭无操作自动返回主页，手机停留在用户手动滑到的页面。
6. UI 为 Android 横屏状态栏留白，并把近期路由改成单列，避免文字相互遮挡。

## 数据流程

`magpie 本机 API → bridge/magpie-bridge.py → PhoneBox /api/push/magpie → 手机 widget`

桥接认证密钥从本机配置文件读取，不纳入项目版本管理。页面应用脚本只更改 AI 与路由页面以及全局无操作返回时间，保留其他 PhoneBox 配置。

## 维护

- 页面样式与渲染逻辑在 `widgets/`。
- 数据采集与字段适配在 `bridge/magpie-bridge.py`。
- 页面映射在 `pages.json`。
- 修改后执行 `./install.sh` 更新本机部署。
