import os
import subprocess
import config

class GitSyncer:
    """Hugo 构建与 GitHub 产物直接部署管理器（不依赖 GitHub Actions）"""

    def __init__(self):
        self.cwd = config.BASE_DIR

    def _run_cmd(self, cmd: list[str], cwd: str = None) -> tuple[int, str, str]:
        """安全执行本地 Shell 命令"""
        target_cwd = cwd or self.cwd
        try:
            res = subprocess.run(
                cmd,
                cwd=target_cwd,
                capture_output=True,
                text=True,
                timeout=90
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return 1, "", str(e)

    def build_hugo(self) -> bool:
        """调用本机 Hugo 执行静态网站构建，并自动生成 .nojekyll"""
        print("[Hugo 构建] 开始编译静态站点 HTML...")
        code, stdout, stderr = self._run_cmd(["hugo"])
        if code == 0:
            print("[Hugo 构建成功] 静态资源编译完成：")
            for line in stdout.split("\n"):
                if "Pages" in line or "Total" in line:
                    print(f"  {line}")

            # 确保 public 目录生成 .nojekyll（防止 GitHub Pages 启用 Jekyll 过滤器）
            public_dir = os.path.join(self.cwd, "public")
            nojekyll_path = os.path.join(public_dir, ".nojekyll")
            if not os.path.exists(nojekyll_path):
                try:
                    open(nojekyll_path, "w").close()
                except Exception:
                    pass

            return True
        else:
            print(f"[Hugo 构建异常] code: {code}\n{stderr}\n{stdout}")
            return False

    def sync_source_to_github(self, commit_msg: str = None) -> bool:
        """提交并同步 Python 采集程序与 Markdown 源码到源码分支 (main)"""
        git_dir = os.path.join(self.cwd, ".git")
        if not os.path.exists(git_dir):
            print("[Git 源码初始化] 本地 hugo-page 尚未建立 git 仓库，执行 git init...")
            self._run_cmd(["git", "init", "-b", config.GITHUB_BRANCH])

        self._run_cmd(["git", "config", "user.name", config.GIT_AUTHOR_NAME])
        self._run_cmd(["git", "config", "user.email", config.GIT_AUTHOR_EMAIL])

        if config.GITHUB_REPO_URL:
            code, remotes, _ = self._run_cmd(["git", "remote"])
            if "origin" in remotes.split():
                self._run_cmd(["git", "remote", "set-url", "origin", config.GITHUB_REPO_URL])
            else:
                self._run_cmd(["git", "remote", "add", "origin", config.GITHUB_REPO_URL])

        # 暂存所有源码与 Markdown 文件（public 已在 .gitignore 中忽略）
        self._run_cmd(["git", "add", "."])

        code, status_out, _ = self._run_cmd(["git", "status", "--porcelain"])
        if not status_out:
            print("[Git 源码] 本地源码工作区无新变动，无需重复 commit。")
        else:
            msg = commit_msg or f"Auto update source: Steam posts updated ({config.SITE_AUTHOR}) [skip ci]"
            code, stdout, stderr = self._run_cmd(["git", "commit", "-m", msg])
            if code == 0:
                print(f"[Git 源码提交成功] {msg}")
            else:
                print(f"[Git 源码提交提示] {stdout or stderr}")

        if config.GITHUB_AUTO_PUSH and config.GITHUB_REPO_URL:
            print(f"[Git 源码推送] 正在推送源码到 GitHub ({config.GITHUB_REPO_URL}) 的 {config.GITHUB_BRANCH} 分支...")
            p_code, p_out, p_err = self._run_cmd(["git", "push", "-u", "origin", config.GITHUB_BRANCH])
            if p_code == 0:
                print(f"[Git 源码推送成功] 源码分支 {config.GITHUB_BRANCH} 同步完成！")
            else:
                print(f"[Git 源码推送异常] {p_err or p_out}")

        return True

    def deploy_build_artifacts(self) -> bool:
        """
        将 public/ 目录下的静态编译产物直接提交并推送到 GitHub Pages 分支 (例如 gh-pages)
        完全绕过 GitHub Actions，由 GitHub Pages 直接原生托管静态 HTML！
        """
        public_dir = os.path.join(self.cwd, "public")
        if not os.path.exists(public_dir):
            print("[静态产物发布错误] public 编译目录不存在，请先执行 hugo 构建！")
            return False

        # 确保 .nojekyll 存在
        nojekyll_path = os.path.join(public_dir, ".nojekyll")
        if not os.path.exists(nojekyll_path):
            open(nojekyll_path, "w").close()

        if not config.GITHUB_REPO_URL:
            print("[静态产物发布提示] 未在 .env 中配置 GITHUB_REPO_URL，仅保留本地编译产物。")
            return True

        # 在 public 目录内建立/复用独立 git 仓库
        pub_git = os.path.join(public_dir, ".git")
        if not os.path.exists(pub_git):
            self._run_cmd(["git", "init", "-b", config.GITHUB_PAGES_BRANCH], cwd=public_dir)

        self._run_cmd(["git", "config", "user.name", config.GIT_AUTHOR_NAME], cwd=public_dir)
        self._run_cmd(["git", "config", "user.email", config.GIT_AUTHOR_EMAIL], cwd=public_dir)

        # 维护 remote origin
        code, remotes, _ = self._run_cmd(["git", "remote"], cwd=public_dir)
        if "origin" in remotes.split():
            self._run_cmd(["git", "remote", "set-url", "origin", config.GITHUB_REPO_URL], cwd=public_dir)
        else:
            self._run_cmd(["git", "remote", "add", "origin", config.GITHUB_REPO_URL], cwd=public_dir)

        # 暂存并提交 public 全部文件
        self._run_cmd(["git", "add", "-A"], cwd=public_dir)

        code, status_out, _ = self._run_cmd(["git", "status", "--porcelain"], cwd=public_dir)
        if not status_out:
            print(f"[静态产物发布] public/ 产物无新变化，无需重复 commit。")
        else:
            msg = f"Deploy static build artifacts ({config.SITE_AUTHOR}) [skip ci]"
            self._run_cmd(["git", "commit", "-m", msg], cwd=public_dir)
            print(f"[静态产物提交] 已生成产物 commit: {msg}")

        # 若开启自动推送，将编译产物推送到目标 Pages 分支
        if config.GITHUB_AUTO_PUSH:
            print(f"[静态产物推送] 正在将 public/ 产物直接推送到 GitHub 仓库的 {config.GITHUB_PAGES_BRANCH} 分支...")
            p_code, p_out, p_err = self._run_cmd(
                ["git", "push", "-f", "origin", f"HEAD:{config.GITHUB_PAGES_BRANCH}"],
                cwd=public_dir
            )
            if p_code == 0:
                print(f"[静态产物推送成功] 🎉 静态产物已成功推送到 {config.GITHUB_PAGES_BRANCH} 分支！GitHub Pages 将直接上线。")
                return True
            else:
                print(f"[静态产物推送失败] {p_err or p_out}")
                return False

        return True

    def sync_to_github(self, commit_msg: str = None) -> bool:
        """全流程同步：同步源码到 main 分支 + 直接推送构建产物到 gh-pages 分支"""
        # 1. 同步源码
        self.sync_source_to_github(commit_msg)
        # 2. 直接部署编译产物到 GitHub Pages
        self.deploy_build_artifacts()
        return True
