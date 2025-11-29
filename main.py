#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import subprocess
import os
import shutil
import webbrowser
import threading
import time
import sys
import logging
import json
import re
import platform

# ================= 0. 环境锚定与配置 =================
# 锁定当前脚本所在目录为工作根目录
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_ROOT)

LOG_FILE = "debug.log"
CONFIG_FILE = "config.json"

IS_WIN = (platform.system() == "Windows")

# Windows 高清屏适配
if IS_WIN:
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass

# 字体适配
FONT_UI = ("Microsoft YaHei", 10) if IS_WIN else ("Arial", 12)
FONT_CODE = ("Consolas", 11) if IS_WIN else ("Menlo", 13)

# 日志配置
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s', 
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class HexoBlogManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Hexo 博客助手 V23.0 (逻辑重制版)")
        self.root.geometry("1100x850")
        
        # 1. 核心环境检查
        if not os.path.exists("_config.yml"):
            messagebox.showerror("环境错误", "未找到 _config.yml 文件！\n\n请将本程序放在 Hexo 博客的根目录下运行。")
            sys.exit(1)
        
        # 2. 目录定义
        self.POST_DIR = os.path.join(APP_ROOT, "source", "_posts")
        self.IMG_DIR = os.path.join(APP_ROOT, "source", "images")
        self.THEME_DIR = os.path.join(APP_ROOT, "themes")
        self.PUBLIC_DIR = os.path.join(APP_ROOT, "public")
        
        # 3. 命令适配
        bin_dir = os.path.join(APP_ROOT, "node_modules", ".bin")
        if IS_WIN:
            self.hexo_cmd = os.path.join(bin_dir, "hexo.cmd")
            if not os.path.exists(self.hexo_cmd): self.hexo_cmd = "hexo"
        else:
            self.hexo_cmd = os.path.join(bin_dir, "hexo")
            if not os.path.exists(self.hexo_cmd): self.hexo_cmd = "hexo"

        self.server_process = None
        self.is_server_running = False
        self.current_editing_file = None

        self._init_security()
        self._init_ui()
        self.load_config()

        # 退出时清理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        if self.is_server_running:
            self.stop_server()
        self.root.destroy()

    def _init_security(self):
        """初始化 gitignore，防止配置文件泄露"""
        ignore_txt = "\nconfig.json\ndebug.log\nnode_modules/\npublic/\n.DS_Store\n.deploy_git/\n"
        
        # 写法修正：标准多行写法
        if not os.path.exists(".gitignore"):
            try:
                with open(".gitignore", "w") as f:
                    f.write(ignore_txt.strip())
            except: pass
        else:
            try:
                with open(".gitignore", "r") as f:
                    content = f.read()
                if "config.json" not in content:
                    with open(".gitignore", "a") as f:
                        f.write("\nconfig.json\n")
            except: pass

    def run_subprocess(self, cmd, cwd=None):
        """统一命令执行器"""
        target_cwd = cwd if cwd else APP_ROOT
        logging.info(f"CMD: {cmd} | CWD: {target_cwd}")
        
        env = os.environ.copy()
        if not IS_WIN:
            # 补全 Mac 环境变量
            path = env.get("PATH", "")
            env["PATH"] = f"/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:{path}"

        kw = {
            "shell": True, 
            "text": True, 
            "stdout": subprocess.PIPE, 
            "stderr": subprocess.STDOUT, 
            "env": env, 
            "cwd": target_cwd,
            "encoding": "utf-8",
            "errors": "replace"
        }
        
        if IS_WIN:
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            kw["preexec_fn"] = os.setsid

        return subprocess.Popen(cmd, **kw)

    def open_sys_file(self, path):
        """调用系统打开文件/目录"""
        if not os.path.exists(path):
            return messagebox.showerror("错误", f"文件不存在: {path}")
        
        if IS_WIN:
            os.startfile(path)
        else:
            subprocess.call(["open", path])

    def _init_ui(self):
        style = ttk.Style()
        style.configure("Big.TButton", font=("微软雅黑", 11, "bold"), padding=8)
        style.configure("Green.TButton", font=("微软雅黑", 11, "bold"), foreground="#006400")
        style.configure("Orange.TButton", font=("微软雅黑", 11, "bold"), foreground="#FF8C00")

        self.notebook = ttk.Notebook(self.root)
        self.tab_write = ttk.Frame(self.notebook)
        self.tab_deploy = ttk.Frame(self.notebook)
        self.tab_theme = ttk.Frame(self.notebook)
        self.tab_preview = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_write, text='✍️ 撰写文章')
        self.notebook.add(self.tab_deploy, text='🚀 发布与备份')
        self.notebook.add(self.tab_theme, text='🎨 主题管理')
        self.notebook.add(self.tab_preview, text='👁️ 本地预览')
        self.notebook.add(self.tab_settings, text='⚙️ 设置 & 修复')
        self.notebook.pack(expand=True, fill="both")

        self._build_write_tab()
        self._build_deploy_tab()
        self._build_theme_tab()
        self._build_preview_tab()
        self._build_settings_tab()

    # ================== 1. 撰写模块 ==================
    def _build_write_tab(self):
        paned = ttk.PanedWindow(self.tab_write, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧列表
        left = ttk.Frame(paned, width=250)
        paned.add(left, weight=1)
        
        ttk.Button(left, text="🔄 刷新列表", command=self.load_article_list).pack(fill="x", pady=2)
        self.article_listbox = tk.Listbox(left, font=FONT_UI, selectmode=tk.SINGLE)
        self.article_listbox.pack(fill="both", expand=True)
        self.article_listbox.bind("<<ListboxSelect>>", self.on_article_select)
        
        # 绑定右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="❌ 删除此文章", command=self.delete_current_article)
        self.context_menu.add_command(label="📂 打开文件位置", command=self.reveal_in_finder)
        
        btn = "<Button-3>" if IS_WIN else "<Button-2>"
        self.article_listbox.bind(btn, lambda e: self.context_menu.post(e.x_root, e.y_root))
        if not IS_WIN:
            self.article_listbox.bind("<Button-3>", lambda e: self.context_menu.post(e.x_root, e.y_root))

        ttk.Button(left, text="✨ 新建文章", command=self.new_article).pack(fill="x", pady=5)

        # 右侧编辑区
        right = ttk.Frame(paned)
        paned.add(right, weight=4)
        
        r1 = ttk.Frame(right)
        r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="文章标题:").pack(side="left")
        self.title_entry = ttk.Entry(r1)
        self.title_entry.pack(side="left", fill="x", expand=True)

        # 工具栏
        tb = ttk.Frame(right)
        tb.pack(fill="x", pady=2)
        tools = [("H1", "# "), ("H2", "## "), ("B", "**"), ("I", "*"), ("引用", "\n> "), ("代码", "\n```\n"), ("链接", "[")]
        for label, code in tools:
            ttk.Button(tb, text=label, width=4, command=lambda c=code: self.insert_md(c)).pack(side="left")
        ttk.Button(tb, text="🖼️ 图片", command=self.handle_image_insert).pack(side="left", padx=5)
        
        self.content_text = scrolledtext.ScrolledText(right, height=20, font=FONT_CODE, undo=True, wrap="word")
        self.content_text.pack(fill="both", expand=True)
        
        ttk.Button(right, text="💾 保存文章", style="Big.TButton", command=self.save_article).pack(fill="x", pady=5)
        self.load_article_list()

    def load_article_list(self):
        self.article_listbox.delete(0, tk.END)
        if not os.path.exists(self.POST_DIR):
            os.makedirs(self.POST_DIR)
        
        files = [f for f in os.listdir(self.POST_DIR) if f.endswith(".md")]
        # 按修改时间倒序
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.POST_DIR, x)), reverse=True)
        
        for f in files:
            self.article_listbox.insert(tk.END, f)

    def on_article_select(self, event):
        sel = self.article_listbox.curselection()
        if not sel: return
        fname = self.article_listbox.get(sel[0])
        self.current_editing_file = fname
        path = os.path.join(self.POST_DIR, fname)
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 从文件名提取标题显示在输入框，方便修改
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, fname.replace(".md", ""))
            
            self.content_text.delete("1.0", tk.END)
            self.content_text.insert("1.0", content)
        except Exception as e:
            logging.error(f"Load error: {e}")

    def new_article(self):
        self.current_editing_file = None
        self.title_entry.delete(0, tk.END)
        self.content_text.delete("1.0", tk.END)

    def delete_current_article(self):
        sel = self.article_listbox.curselection()
        if not sel: return
        fname = self.article_listbox.get(sel[0])
        
        if messagebox.askyesno("确认删除", f"确定要永久删除：\n{fname}\n此操作不可恢复！", icon='warning'):
            try:
                os.remove(os.path.join(self.POST_DIR, fname))
                if self.current_editing_file == fname:
                    self.new_article()
                self.load_article_list()
                messagebox.showinfo("提示", "已删除")
            except Exception as e:
                messagebox.showerror("错误", str(e))

    def reveal_in_finder(self):
        self.open_sys_file(self.POST_DIR)

    def insert_md(self, code):
        try:
            self.content_text.insert(tk.INSERT, code)
        except: pass

    def handle_image_insert(self):
        fp = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")])
        if not fp: return
        
        if not os.path.exists(self.IMG_DIR):
            os.makedirs(self.IMG_DIR)
            
        filename = os.path.basename(fp)
        dest = os.path.join(self.IMG_DIR, filename)
        shutil.copy(fp, dest)
        
        self.content_text.insert(tk.INSERT, f"\n![{filename}](/images/{filename})\n")

    def save_article(self):
        title = self.title_entry.get().strip()
        content = self.content_text.get("1.0", "end-1c").strip()
        
        if not title:
            return messagebox.showwarning("提示", "文章标题不能为空")
        
        # 决定文件名 (如果是新建，则用标题；如果是编辑，则覆盖原文件)
        filename = self.current_editing_file if self.current_editing_file else f"{title}.md"
        
        # 智能头部检测：使用正则严格判断
        # 只有当文章开头没有 YAML 块时，才自动添加
        if not re.search(r'^\s*---\s*\n', content):
            safe_title = json.dumps(title, ensure_ascii=False) # 自动处理引号转义
            header = f"---\ntitle: {safe_title}\ndate: {time.strftime('%Y-%m-%d %H:%M:%S')}\ntags: []\n---\n\n"
            content = header + content
        
        try:
            with open(os.path.join(self.POST_DIR, filename), "w", encoding="utf-8") as f:
                f.write(content)
            
            # 回填：确保界面显示的内容包含刚才自动添加的头部
            self.content_text.delete("1.0", tk.END)
            self.content_text.insert("1.0", content)
            self.current_editing_file = filename
            
            messagebox.showinfo("成功", "文章已保存！")
            self.load_article_list()
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    # ================== 2. 发布与备份模块 ==================
    def _build_deploy_tab(self):
        frame = ttk.Frame(self.tab_deploy, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="💡 流程：先 [发布网站] 更新网页，再 [备份源码] 防止丢数据。", foreground="#666").pack(pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(btn_frame, text="🚀 1. 发布网站 (Deploy)", style="Huge.TButton", command=self.deploy_site).pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(btn_frame, text="☁️ 2. 备份源码 (Backup)", style="Big.TButton", command=self.backup_code).pack(side="left", fill="x", expand=True, padx=10)
        
        self.deploy_log = scrolledtext.ScrolledText(frame, height=20, bg="#1e1e1e", fg="#00ff00", font=FONT_CODE)
        self.deploy_log.pack(fill="both", expand=True, pady=10)

    def log(self, msg):
        self.root.after(0, lambda: [self.deploy_log.insert(tk.END, str(msg)), self.deploy_log.see(tk.END)])

    def get_auth_url(self):
        repo = self.repo_entry.get().strip().replace("https://", "")
        token = self.token_entry.get().strip()
        if not repo or not token: return None
        return f"https://{token}@{repo.split('@')[-1]}"

    def deploy_site(self):
        url = self.get_auth_url()
        if not url: return messagebox.showerror("错误", "请先在 [设置] 页填入 Token 和 仓库地址")
        self.save_config(silent=True)
        
        def worker():
            self.log("\n========== 🚀 开始发布网站 ==========\n")
            self.log(">> 执行 hexo clean...\n")
            self.run_subprocess(f"{self.hexo_cmd} clean").wait()
            
            self.log(">> 执行 hexo g (生成网页)...\n")
            p_gen = self.run_subprocess(f"{self.hexo_cmd} g")
            
            # 捕获输出用于检测报错
            gen_output = ""
            while True:
                line = p_gen.stdout.readline()
                if not line: break
                self.log(line)
                gen_output += line
            
            if p_gen.wait() != 0:
                if "ERR_REQUIRE_ESM" in gen_output:
                    self.root.after(0, lambda: messagebox.showerror("错误", "检测到依赖冲突！\n请去 [设置] 页面点击 [修复 Hexo 依赖] 按钮。"))
                else:
                    self.log("❌ 生成失败！请检查文章内容格式。\n")
                return

            if not os.path.exists(self.PUBLIC_DIR):
                return self.log("❌ 错误：public 文件夹未生成。\n")

            self.log(">> 正在推送到 main 分支...\n")
            # 在 public 目录内操作 git
            self.run_subprocess("git init", cwd=self.PUBLIC_DIR).wait()
            self.run_subprocess("git add .", cwd=self.PUBLIC_DIR).wait()
            self.run_subprocess('git commit -m "Site Update"', cwd=self.PUBLIC_DIR).wait()
            
            p_push = self.run_subprocess(f"git push -f {url} master:main", cwd=self.PUBLIC_DIR)
            while True:
                line = p_push.stdout.readline()
                if not line: break
                self.log(line)
            
            if p_push.wait() == 0:
                self.log("\n✅ 发布成功！网站稍后更新。\n")
                # 清理临时 git
                shutil.rmtree(os.path.join(self.PUBLIC_DIR, ".git"), ignore_errors=True)
            else:
                self.log("\n❌ 推送失败，请检查网络或 Token。\n")

        threading.Thread(target=worker, daemon=True).start()

    def backup_code(self):
        url = self.get_auth_url()
        if not url: return messagebox.showerror("错误", "请配置 Token")
        self.save_config(silent=True)
        
        def worker():
            self.log("\n========== ☁️ 开始备份源码 ==========\n")
            
            # 防止泄露：从暂存区移除敏感文件
            self.run_subprocess("git rm --cached config.json").wait()
            self.run_subprocess("git rm --cached debug.log").wait()
            
            if not os.path.exists(os.path.join(APP_ROOT, ".git")):
                self.run_subprocess("git init").wait()
            
            self.run_subprocess("git add .").wait()
            self.run_subprocess('git commit -m "Backup Source"').wait()
            
            p_push = self.run_subprocess(f"git push -f {url} main:backup")
            while True:
                line = p_push.stdout.readline()
                if not line: break
                self.log(line)
                
            if p_push.wait() == 0:
                self.log("\n✅ 源码备份成功！\n")
            else:
                # 尝试兼容 master 分支名
                if self.run_subprocess(f"git push -f {url} master:backup").wait() == 0:
                    self.log("\n✅ 源码备份成功！\n")
                else:
                    self.log("\n❌ 备份失败。\n")

        threading.Thread(target=worker, daemon=True).start()

    # ================== 3. 主题模块 ==================
    def _build_theme_tab(self):
        frame = ttk.Frame(self.tab_theme, padding=20)
        frame.pack(fill="both", expand=True)

        gf = ttk.LabelFrame(frame, text="安装新主题", padding=10)
        gf.pack(fill="x", pady=5)
        self.theme_url = ttk.Entry(gf)
        self.theme_url.pack(side="left", fill="x", expand=True)
        self.theme_url.insert(0, "[https://github.com/theme-next/hexo-theme-next](https://github.com/theme-next/hexo-theme-next)")
        ttk.Button(gf, text="⬇️ 下载", command=self.install_theme).pack(side="left", padx=5)

        lf = ttk.LabelFrame(frame, text="本地主题", padding=10)
        lf.pack(fill="both", expand=True, pady=5)
        ttk.Button(lf, text="🔄 刷新列表", command=self.load_themes).pack(fill="x")
        self.theme_list = tk.Listbox(lf, height=8, font=FONT_UI)
        self.theme_list.pack(fill="both", expand=True, pady=5)
        
        bf = ttk.Frame(lf)
        bf.pack(fill="x")
        ttk.Button(bf, text="✅ 切换到选中主题", command=self.apply_theme).pack(side="left", fill="x", expand=True)
        ttk.Button(bf, text="📝 编辑主题配置", command=self.edit_theme_cfg).pack(side="left", fill="x", expand=True)
        
        self.load_themes()

    def load_themes(self):
        self.theme_list.delete(0, tk.END)
        if not os.path.exists(self.THEME_DIR): os.makedirs(self.THEME_DIR)
        for t in os.listdir(self.THEME_DIR):
            if os.path.isdir(os.path.join(self.THEME_DIR, t)):
                self.theme_list.insert(tk.END, t)

    def apply_theme(self):
        s = self.theme_list.curselection()
        if not s: return
        t = self.theme_list.get(s[0])
        try:
            cfg = os.path.join(APP_ROOT, "_config.yml")
            with open(cfg, "r", encoding="utf-8") as f: c = f.read()
            # 正则替换 theme: xxx
            c = re.sub(r"^theme:\s*\S+", f"theme: {t}", c, flags=re.MULTILINE)
            with open(cfg, "w", encoding="utf-8") as f: f.write(c)
            messagebox.showinfo("成功", f"主题已切换为: {t}")
        except Exception as e: messagebox.showerror("错误", str(e))

    def install_theme(self):
        url = self.theme_url.get().strip()
        if not url: return
        name = url.split("/")[-1].replace(".git", "")
        tgt = os.path.join(self.THEME_DIR, name)
        
        if os.path.exists(tgt): return messagebox.showerror("错误", "主题已存在")
        
        def worker():
            if self.run_subprocess(f"git clone {url} {tgt}").wait() == 0:
                if not os.path.exists(os.path.join(tgt, "_config.yml")):
                    shutil.rmtree(tgt, ignore_errors=True)
                    self.root.after(0, lambda: messagebox.showerror("失败", "这不是合法的 Hexo 主题"))
                else:
                    shutil.rmtree(os.path.join(tgt, ".git"), ignore_errors=True)
                    self.root.after(0, lambda: [messagebox.showinfo("成功", "安装完成"), self.load_themes()])
            else:
                self.root.after(0, lambda: messagebox.showerror("失败", "下载失败"))
        threading.Thread(target=worker, daemon=True).start()

    def edit_theme_cfg(self):
        s = self.theme_list.curselection()
        if not s: return
        t = self.theme_list.get(s[0])
        self.open_sys_file(os.path.join(self.THEME_DIR, t, "_config.yml"))

    # ================== 4. 预览模块 ==================
    def _build_preview_tab(self):
        frame = ttk.Frame(self.tab_preview, padding=20)
        frame.pack(fill="both", expand=True)
        ctl = ttk.Frame(frame); ctl.pack(fill="x", pady=10)
        ttk.Button(ctl, text="▶️ 启动预览", command=self.start_srv).pack(side="left", padx=5)
        ttk.Button(ctl, text="🌍 打开浏览器", command=lambda: webbrowser.open("http://localhost:4000")).pack(side="left", padx=5)
        ttk.Button(ctl, text="⏹️ 停止服务", command=self.stop_server).pack(side="left", padx=5)
        self.preview_log = scrolledtext.ScrolledText(frame, height=15)
        self.preview_log.pack(fill="both", expand=True)

    def start_srv(self):
        if self.is_server_running: return
        self.is_server_running = True
        threading.Thread(target=self._srv_worker, daemon=True).start()

    def _srv_worker(self):
        self.root.after(0, lambda: self.preview_log.insert(tk.END, "启动中...\n"))
        try:
            self.server_process = self.run_subprocess(f"{self.hexo_cmd} s")
            while self.is_server_running and self.server_process:
                l = self.server_process.stdout.readline()
                if not l: break
                self.root.after(0, lambda t=l: [self.preview_log.insert(tk.END, t), self.preview_log.see(tk.END)])
        except: self.stop_server()

    def stop_server(self):
        self.is_server_running = False
        if self.server_process:
            if IS_WIN: subprocess.run(f"taskkill /F /T /PID {self.server_process.pid}", shell=True)
            else: os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
            self.server_process = None
        self.preview_log.insert(tk.END, "已停止\n")

    # ================== 5. 设置 & 修复模块 ==================
    def _build_settings_tab(self):
        frame = ttk.Frame(self.tab_settings, padding=20)
        frame.pack(fill="both", expand=True)
        
        cf = ttk.LabelFrame(frame, text="全局设置", padding=10); cf.pack(fill="x", pady=5)
        ttk.Button(cf, text="📝 编辑站点配置 (_config.yml)", command=lambda: self.open_sys_file("_config.yml")).pack(fill="x")

        l1 = ttk.LabelFrame(frame, text="身份 & 远程", padding=10); l1.pack(fill="x", pady=5)
        ttk.Label(l1, text="User:").pack(side="left"); self.git_n = ttk.Entry(l1, width=10); self.git_n.pack(side="left")
        ttk.Label(l1, text="Email:").pack(side="left"); self.git_e = ttk.Entry(l1, width=15); self.git_e.pack(side="left")
        ttk.Label(l1, text="Repo:").pack(side="left"); self.repo_entry = ttk.Entry(l1, width=15); self.repo_entry.pack(side="left")
        ttk.Label(l1, text="Token:").pack(side="left"); self.token_entry = ttk.Entry(l1, show="*", width=15); self.token_entry.pack(side="left")
        ttk.Button(l1, text="保存全部", command=self.save_sys).pack(side="left", padx=5)
        
        # 修复专区
        fix = ttk.LabelFrame(frame, text="🛠️ 故障修复", padding=10); fix.pack(fill="x", pady=20)
        ttk.Button(fix, text="🛠️ 修复 Hexo 依赖冲突 (解决 ERR_REQUIRE_ESM)", 
                   style="Orange.TButton", command=self.fix_dependency).pack(fill="x", pady=5)
        ttk.Button(fix, text="🛡️ 重置 Git 历史 (解决提交冲突)", style="Green.TButton", command=self.reset_git).pack(fill="x", pady=5)
        
        ttk.Button(frame, text="📂 打开错误日志", command=lambda: self.open_sys_file(LOG_FILE)).pack(pady=5)

    def fix_dependency(self):
        if not messagebox.askyesno("修复", "这将重新安装依赖并清理冲突文件，确定吗？"): return
        def worker():
            self.root.after(0, lambda: messagebox.showinfo("请稍候", "正在修复..."))
            try:
                # 1. 暴力删除冲突文件
                bad_path = os.path.join("node_modules", "hexo", "node_modules", "strip-ansi")
                if os.path.exists(bad_path): shutil.rmtree(bad_path, ignore_errors=True)
                
                # 2. 强制安装旧版
                logging.info("Fixing: installing strip-ansi@6.0.1")
                self.run_subprocess("npm install strip-ansi@6.0.1 --save").wait()
                
                self.root.after(0, lambda: messagebox.showinfo("成功", "依赖已修复！请重试发布。"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("失败", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def save_sys(self):
        if self.git_n.get():
            self.run_subprocess(f'git config user.name "{self.git_n.get()}"')
            self.run_subprocess(f'git config user.email "{self.git_e.get()}"')
            messagebox.showinfo("成功", "配置已保存"); self.save_config(True)
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                d=json.load(open(CONFIG_FILE))
                self.git_n.insert(0, d.get("name","")); self.git_e.insert(0, d.get("email",""))
                self.repo_entry.insert(0, d.get("repo","")); self.token_entry.insert(0, d.get("token",""))
            except: pass
    def save_config(self, silent=False):
        d={"name":self.git_n.get(),"email":self.git_e.get(),"repo":self.repo_entry.get(),"token":self.token_entry.get()}
        with open(CONFIG_FILE,"w") as f: json.dump(d, f)
        if not silent: messagebox.showinfo("成功", "配置已保存")
    def reset_git(self):
        if messagebox.askyesno("Warn", "重置 Git?"):
            shutil.rmtree(".git", ignore_errors=True); self.run_subprocess("git init")
            messagebox.showinfo("成功", "Git 已重置")

if __name__ == "__main__":
    root = tk.Tk()
    app = HexoBlogManager(root)
    root.mainloop()