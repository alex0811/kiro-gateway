最常用的同步命令：

  git fetch upstream
  git checkout main
  git merge upstream/main
  git push origin main

  这 4 步的意思是：

  - fetch upstream 拉取源仓库最新提交
  - 切回你本地主分支 main
  - 把源仓库的 main 合并到你本地
  - 再推回你自己的 fork origin

  如果你希望历史更干净，也可以用 rebase：

  git fetch upstream
  git checkout main
  git rebase upstream/main
  git push --force-with-lease origin main

  建议你平时这样做：

  1. 开始开发前先同步一次

  git fetch upstream
  git checkout main
  git merge upstream/main
  git push origin main

  2. 新功能分支从最新 main 拉出来

  git checkout -b feature/xxx

  3. 源仓库有更新时，先更新本地 main

  git checkout main
  git fetch upstream
  git merge upstream/main
  git push origin main

  4. 再把更新带到你的功能分支

  git checkout feature/xxx
  git merge main

  如果你想尽量省事，可以给自己配个 Git alias，比如：

  git config --global alias.sync-up "!git fetch upstream && git checkout main && git merge upstream/main && git push origin main"

  之后直接运行：

  git sync-up

  额外建议：

  - 如果你经常跟源仓库同步，main 尽量不要直接写自己的开发提交
  - 自己的改动放功能分支，main 只负责跟 upstream/main 保持同步
  - 如果同步时出现冲突，优先在本地解决后再 push origin main

  如果你愿意，我可以直接帮你把这个 git sync-up alias 配上。

使用 `claude-kiro` 启动 Claude Code：

  现在已经安装了全局命令：

  claude-kiro

  它会自动做这些事：

  - 检查本地 Kiro Gateway 是否已经在跑
  - 如果没跑，就自动启动网关
  - 把 `ANTHROPIC_BASE_URL` 和 `ANTHROPIC_AUTH_TOKEN` 注入给 Claude Code
  - 再启动 `claude`

  最常用的方式：

  claude-kiro

  也可以直接把参数传给 Claude Code：

  claude-kiro --help
  claude-kiro "fix this bug"

  如果你想改端口或代理密钥：

  export KIRO_GATEWAY_PORT=8011
  export KIRO_GATEWAY_PROXY_API_KEY=your-secret-key
  claude-kiro

  默认凭据来源优先级：

  - `KIRO_GATEWAY_CREDS_FILE`
  - `KIRO_GATEWAY_CLI_DB_FILE`
  - `KIRO_GATEWAY_REFRESH_TOKEN`

  默认情况下，它会优先使用：

  `~/.aws/sso/cache/kiro-auth-token.json`

管理后台运行的 Kiro Gateway：

  现在也有两个全局命令：

  kiro-gateway-start
  kiro-gateway-stop

  最常用的方式：

  kiro-gateway-start
  curl http://127.0.0.1:8000/health
  kiro-gateway-stop

  `kiro-gateway-start` 会：

  - 如果网关已经在跑，直接告诉你 PID 和 health 地址
  - 如果网关没跑，就在后台启动它
  - 启动成功后打印 PID、health 地址和日志文件路径

  `kiro-gateway-stop` 会：

  - 优先按 PID 文件找到当前网关进程
  - 发送 SIGTERM 正常关闭
  - 如果进程没退出，再补 SIGKILL

  默认日志文件和 PID 文件在：

  - `${TMPDIR:-/tmp}/kiro-gateway-8000.log`
  - `${TMPDIR:-/tmp}/kiro-gateway-8000.pid`

  如果你想改端口：

  export KIRO_GATEWAY_PORT=8011
  kiro-gateway-start
