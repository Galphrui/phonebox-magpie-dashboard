# PhoneBox + magpie

把本机 magpie 的用量与网关路由状态显示在 PhoneBox 安卓面板上。当前部署针对 macOS 桌面端和已配对的 Android 手机。

## 当前页面

- **第 2 页：magpie**：今日调用和 Tokens、缓存命中、首字延迟、生成速度、余额、近期请求与调用趋势。
- **第 3 页：路由**：请求 Agent、magpie 网关、实际命中的供应商和账户、候选顺序、最近路由结果。
- 路由请求进行中时，小喜鹊沿连线飞动；请求结束后停止。
- 桥接每 2 秒读取一次本机 magpie API。页面保持手动选择状态，不自动返回主页。

## 安装或更新

先确认 PhoneBox 和 magpie 正在本机运行，magpie 的 **设置 → 网络与共享 → 浏览器访问** 已开启。然后从仓库目录运行：

```sh
./install.sh
```

安装脚本会把桥接程序复制到 PhoneBox 支持目录、更新 PhoneBox 第 2/3 页并启用登录启动。它只替换这两个页面和“无操作返回主页”设置，其他 PhoneBox 设置会保留。

以后更新：

```sh
git pull
./install.sh
```

卸载自动同步任务：

```sh
./uninstall.sh
```

卸载会保留 PhoneBox 页面和桥接文件。若要恢复页面布局，可在 PhoneBox 设置中还原对应页面，或重新运行 `./install.sh`。

## 项目文件

- `bridge/magpie-bridge.py`：读取 magpie 的本机用量、余额和网关路由 API，并推送到 PhoneBox `/api/push/magpie`。
- `widgets/ai-dashboard.html`：AI 用量面板。
- `widgets/route-dashboard.html`：路由面板和飞行状态指示。
- `pages.json`：PhoneBox 页面名称、图标及 widget 映射。
- `scripts/apply-dashboard.py`：通过本机 PhoneBox 设置 API 更新页面，保留其余设置。
- `install.sh` / `uninstall.sh`：安装、更新和停止 launchd 同步任务。

## 自定义与维护

修改 `widgets/ai-dashboard.html` 或 `widgets/route-dashboard.html` 后，运行 `./install.sh` 把改动应用到 PhoneBox。修改 `bridge/magpie-bridge.py` 后也需重新安装。

桥接密钥从 `~/.config/magpie/web-page.json` 读取，不保存在仓库中。用量和请求记录只在本机 magpie API 与 PhoneBox 之间传递；仓库不包含个人配置、密钥、日志或请求历史。

遇到同步问题时检查：

```sh
launchctl list | grep phonebox-magpie
tail -f "$HOME/Library/Logs/phonebox-magpie.log"
curl -s http://127.0.0.1:8765/api/info
```

若 magpie 关闭或“浏览器访问”停用，PhoneBox 页面会显示离线状态；恢复服务后自动继续同步。
