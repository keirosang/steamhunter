import os
import subprocess
import config

class GitSyncer:
    """Hugo 构建与 GitHub 自动提交/同步推送管理器"""

    def __init__(self):
        self.cwd = config.BASE_DIR

    def _run_cmd(self, cmd: list[str]) -> tuple[int, str, str]:
        """安全执行本地 Shell 命令"""
        try:
            res = subprocess.run(
                cmd,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=90
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return 1, "", str(e)

    def build_hugo(self) -> bool:
        """调用本机 Hugo 执行静态网站构建"""
        print("[Hugo 构建] 开始编译静态站点 HTML...")
        code, stdout, stderr = self._run_cmd(["hugo"])
        if code == 0:
            print("[Hugo 构建成功] 静态资源编译完成：")
            for line in stdout.split("\n"):
                if "Pages" in line or "Total" in line:
                    print(f"  {line}")
            return True
        else:
            print(f"[Hugo 构建异常] code: {code}\n{stderr}\n{stdout}")
            return False

    def sync_to_github(self, commit_msg: str = None) -> bool:
        """Git 自动提交流程，并按配置推送到 GitHub 远程仓库"""
        # 1. 检查或初始化本地 Git 仓库
        git_dir = os.path.join(self.cwd, ".git")
        if not os.path.exists(git_dir):
            print("[Git 初始化] 本地 hugo-page 尚未建立 git 仓库，正在执行 git init...")
            self._run_cmd(["git", "init", "-b", config.GITHUB_BRANCH])

        # 2. 配置提交者身份
        self._run_cmd(["git", "config", "user.name", config.GIT_AUTHOR_NAME])
        self._run_cmd(["git", "config", "user.email", config.GIT_AUTHOR_EMAIL])

        # 3. 检查远程仓库配置
        if config.GITHUB_REPO_URL:
            code, remotes, _ = self._run_cmd(["git", "remote"])
            if "origin" in remotes.split():
                self._run_cmd(["git", "remote", "set-url", "origin", config.GITHUB_REPO_URL])
            else:
                self._run_cmd(["git", "remote", "add", "origin", config.GITHUB_REPO_URL])

        # 4. 暂存所有必要源码与静态文件
        self._run_cmd(["git", "add", "."])

        # 5. 检查是否有变动需要提交
        code, status_out, _ = self._run_cmd(["git", "status", "--porcelain"])
        if not status_out:
            print("[Git 提交] 本地工作区无新变动，无需重复 commit。")
            return True

        msg = commit_msg or f"Auto update: Steam posts updated ({config.SITE_AUTHOR}) [skip ci]"
        code, stdout, stderr = self._run_cmd(["git", "commit", "-m", msg])
        if code == 0:
            print(f"[Git 提交成功] 已提交变动: {msg}")
        else:
            print(f"[Git 提交提示] {stdout or stderr}")

        # 6. 若开启 GITHUB_AUTO_PUSH 且配置了仓库，执行远程推送
        if config.GITHUB_AUTO_PUSH:
            if not config.GITHUB_REPO_URL:
                print("[Git 推送跳过] 未在 .env 中配置 GITHUB_REPO_URL，跳过推送。")
                return True

            print(f"[Git 推送] 正在推送到远程仓库 ({config.GITHUB_REPO_URL}) 分支 {config.GITHUB_BRANCH}...")
            p_code, p_out, p_err = self._run_cmd(["git", "push", "-u", "origin", config.GITHUB_BRANCH])
            if p_code == 0:
                print("[Git 推送成功] GitHub Pages 仓库同步完成！")
                return True
            else:
                print(f"[Git 推送失败] {p_err or p_out}")
                return False

        return True
