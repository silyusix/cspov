# CS2 POV 自动化录制工具 (cspov)

这是一个基于 Python + HLAE + GSI 的 CS2 高清 POV 自动录制解决方案。

### 1. 环境准备
- 安装 [Python 3.10+](https://www.python.org/)。
- 安装依赖库：
  ```bash
  pip install demoparser2
  ```
- 下载并安装 [HLAE](https://www.advancedfx.org/)。
- hlae的命令行输入-insecure -allow_third_party_software +sv_lan 1 -netconport 2121 -noborder 

### 2. 配置游戏状态集成 (GSI)
将本仓库中的 `gamestate_integration_pov.cfg` 复制到你的 CS2 游戏目录：
`...\game\csgo\cfg\gamestate_integration_pov.cfg`

### 3. 修改脚本路径
用记事本打开 `pov.py` 和 `merge.py`，修改顶部的 `GAME_DIR` 和 `VIDEO_DIR` 为你自己的路径。

### 4. 使用流程
1. **启动脚本**：运行 `python pov.py`，选择你要录制的玩家序号。
2. **启动游戏**：通过 HLAE 启动 CS2，启动参数确保包含 `-port 2121`（开启 Telnet）。
3. **加载配置**：进入游戏控制台，输入 `exec pov`。
4. **一键开始**：按 **F5**。
5. **挂机等待**：脚本会自动完成所有回合的录制并重命名。
6. **最终合成**：录制完成后运行 `python merge.py` 得到完整视频。


感谢 HLAE 和 demoparser2 项目提供的技术支持。
