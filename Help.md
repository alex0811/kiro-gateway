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