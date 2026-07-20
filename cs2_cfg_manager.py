import os
import shutil
import json
import datetime
import stat
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

CONFIG_FILE = "settings.json"

def get_relative_file_paths(base_dir):
    """获取目录内所有文件的相对路径集合"""
    rel_files = set()
    if not os.path.exists(base_dir):
        return rel_files
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, base_dir)
            rel_files.add(rel_path)
    return rel_files

class CS2ConfigManager:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 配置同步管理器")
        
        # 默认配置
        self.config = {
            "global_path": "",
            "backup_path": "",
            "users": []
        }
        self.load_config()
        
        self.create_widgets()
        self.refresh_ui()
        
        # 自动自适应窗口合适宽高并限制最小尺寸，防止控件被遮挡或过度缩小
        self.adjust_window_size()

    def adjust_window_size(self):
        """动态检测界面所需空间，设置合理的默认尺寸与最小缩放限制"""
        self.root.update_idletasks()
        req_w = self.root.winfo_reqwidth()
        req_h = self.root.winfo_reqheight()
        
        # 为高分辨率或不同 DPI 留出适当的安全余量
        min_w = max(req_w + 30, 820)
        min_h = max(req_h + 30, 720)
        
        self.root.minsize(min_w, min_h)
        self.root.geometry(f"{min_w}x{min_h}")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception as e:
                messagebox.showerror("错误", f"加载配置文件失败: {e}")

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

    def create_widgets(self):
        style = ttk.Style()
        style.configure("TButton", padding=4)
        
        # --- 1. 全局与备份路径设置 ---
        path_frame = ttk.LabelFrame(self.root, text="基础路径设置 (全局配置与备份目录)", padding=10)
        path_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(path_frame, text="全局配置路径 (如 csgo/cfg):").grid(row=0, column=0, sticky="w", pady=3)
        self.global_path_var = tk.StringVar(value=self.config.get("global_path", ""))
        ttk.Entry(path_frame, textvariable=self.global_path_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(path_frame, text="浏览", command=lambda: self.browse_path("global_path", self.global_path_var)).grid(row=0, column=2, padx=2)
        ttk.Button(path_frame, text="备份全局配置", command=self.backup_global).grid(row=0, column=3, padx=5)

        ttk.Label(path_frame, text="备份存放路径:").grid(row=1, column=0, sticky="w", pady=3)
        self.backup_path_var = tk.StringVar(value=self.config.get("backup_path", ""))
        ttk.Entry(path_frame, textvariable=self.backup_path_var, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(path_frame, text="浏览", command=lambda: self.browse_path("backup_path", self.backup_path_var)).grid(row=1, column=2, padx=2)

        # --- 2. 用户管理 ---
        user_frame = ttk.LabelFrame(self.root, text="用户配置管理", padding=10)
        user_frame.pack(fill="both", expand=True, padx=10, pady=5)

        add_frame = ttk.Frame(user_frame)
        add_frame.pack(fill="x", pady=5)
        ttk.Label(add_frame, text="新增用户名:").pack(side="left")
        self.new_user_name = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.new_user_name, width=15).pack(side="left", padx=5)
        
        ttk.Label(add_frame, text="目录路径:").pack(side="left")
        self.new_user_path = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.new_user_path, width=35).pack(side="left", padx=5)
        ttk.Button(add_frame, text="浏览", command=self.browse_new_user_path).pack(side="left", padx=2)
        ttk.Button(add_frame, text="添加用户", command=self.add_user).pack(side="left", padx=5)

        # 明确的表头提示
        header_frame = ttk.Frame(user_frame)
        header_frame.pack(fill="x", pady=(8, 2))
        ttk.Label(header_frame, text="用户名", width=15, font=("SimSun", 9, "bold")).pack(side="left")
        ttk.Label(header_frame, text="对应账号的 CFG 配置文件夹路径", font=("SimSun", 9, "bold")).pack(side="left", padx=5)

        # 用于动态显示用户列表的容器
        self.users_container = ttk.Frame(user_frame)
        self.users_container.pack(fill="both", expand=True, pady=2)

        # --- 3. 历史备份列表（全局与用户分开显示） ---
        backup_frame = ttk.LabelFrame(self.root, text="历史备份管理 (全局与各用户分别最多保留10个版本)", padding=10)
        backup_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 左右划分容器
        lists_frame = ttk.Frame(backup_frame)
        lists_frame.pack(side="left", fill="both", expand=True)

        # 全局备份历史
        g_box_frame = ttk.LabelFrame(lists_frame, text="全局备份历史", padding=5)
        g_box_frame.pack(side="left", fill="both", expand=True, padx=3)
        self.global_listbox = tk.Listbox(g_box_frame, height=7, selectmode=tk.SINGLE, exportselection=False)
        self.global_listbox.pack(fill="both", expand=True)
        self.global_listbox.bind("<<ListboxSelect>>", lambda e: self.on_listbox_select("global"))

        # 用户备份历史
        u_box_frame = ttk.LabelFrame(lists_frame, text="用户备份历史", padding=5)
        u_box_frame.pack(side="left", fill="both", expand=True, padx=3)
        self.user_listbox = tk.Listbox(u_box_frame, height=7, selectmode=tk.SINGLE, exportselection=False)
        self.user_listbox.pack(fill="both", expand=True)
        self.user_listbox.bind("<<ListboxSelect>>", lambda e: self.on_listbox_select("user"))

        # 右侧操作按钮区
        btn_frame = ttk.Frame(backup_frame)
        btn_frame.pack(side="right", fill="y", padx=(5, 0))
        ttk.Button(btn_frame, text="刷新列表", command=self.refresh_backups).pack(fill="x", pady=4)
        ttk.Button(btn_frame, text="还原选中备份", command=self.restore_backup).pack(fill="x", pady=4)
        ttk.Button(btn_frame, text="删除选中备份", command=self.delete_selected_backup).pack(fill="x", pady=4)

    # --- 辅助方法 ---
    def on_listbox_select(self, source):
        """保持全局备份和用户备份列表之间单选关联"""
        if source == "global" and self.global_listbox.curselection():
            self.user_listbox.selection_clear(0, tk.END)
        elif source == "user" and self.user_listbox.curselection():
            self.global_listbox.selection_clear(0, tk.END)

    def get_selected_backup(self):
        """获取当前被选中的备份名称"""
        g_sel = self.global_listbox.curselection()
        if g_sel:
            return self.global_listbox.get(g_sel[0])
        u_sel = self.user_listbox.curselection()
        if u_sel:
            return self.user_listbox.get(u_sel[0])
        return None

    def browse_path(self, config_key, var):
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)
            self.config[config_key] = folder
            self.save_config()

    def browse_new_user_path(self):
        folder = filedialog.askdirectory()
        if folder:
            self.new_user_path.set(folder)

    def add_user(self):
        name = self.new_user_name.get().strip()
        path = self.new_user_path.get().strip()
        if not name or not path:
            messagebox.showwarning("警告", "用户名和路径不能为空！")
            return
        
        self.config["users"].append({"name": name, "path": path})
        self.save_config()
        self.new_user_name.set("")
        self.new_user_path.set("")
        self.refresh_ui()

    def delete_user(self, index):
        if messagebox.askyesno("确认", "确定要删除该用户配置吗？"):
            del self.config["users"][index]
            self.save_config()
            self.refresh_ui()

    def refresh_ui(self):
        for widget in self.users_container.winfo_children():
            widget.destroy()

        for i, user in enumerate(self.config.get("users", [])):
            frame = ttk.Frame(self.users_container)
            frame.pack(fill="x", pady=2)
            
            ttk.Label(frame, text=f"[{user['name']}]", width=15).pack(side="left")
            
            # 显示账号路径，使用只读展示框
            path_entry = ttk.Entry(frame, width=38)
            path_entry.insert(0, user['path'])
            path_entry.config(state="readonly")
            path_entry.pack(side="left", padx=5)
            
            ttk.Button(frame, text="备份", command=lambda u=user: self.backup_user(u)).pack(side="left", padx=2)
            ttk.Button(frame, text="备份并同步", command=lambda u=user: self.do_backup_and_sync(u)).pack(side="left", padx=2)
            ttk.Button(frame, text="删除", command=lambda idx=i: self.delete_user(idx)).pack(side="left", padx=2)
            
        self.refresh_backups()

    def copy_dir(self, src, dst, check_extra=True):
        """强力覆盖式复制目录内容，并检测/删除目标目录中源目录没有的多余文件"""
        if not os.path.exists(dst):
            os.makedirs(dst)

        # 检查多余文件
        if check_extra and os.path.exists(dst):
            src_files = get_relative_file_paths(src)
            dst_files = get_relative_file_paths(dst)
            extra_files = dst_files - src_files

            if extra_files:
                extra_list = sorted(list(extra_files))
                shown_files = extra_list[:10]
                file_text = "\n".join([f" • {f}" for f in shown_files])
                if len(extra_list) > 10:
                    file_text += f"\n... 等共 {len(extra_list)} 个文件"

                dst_name = os.path.basename(dst.rstrip("\\/")) or dst
                confirm = messagebox.askyesno(
                    "多余文件删除提示",
                    f"在还原/同步至目标目录 [{dst_name}] 时，发现目标目录中包含源目录不存在的以下文件：\n\n"
                    f"{file_text}\n\n"
                    f"是否要将这些多余文件删除，以确保配置文件彻底一致？"
                )
                if confirm:
                    for rel_f in extra_files:
                        full_f = os.path.join(dst, rel_f)
                        try:
                            if os.path.exists(full_f):
                                os.chmod(full_f, stat.S_IWRITE)
                                os.remove(full_f)
                        except Exception as e:
                            print(f"删除多余文件失败 {full_f}: {e}")
                    
                    # 清除可能产生的空文件夹
                    for root, dirs, files in os.walk(dst, topdown=False):
                        for d in dirs:
                            d_path = os.path.join(root, d)
                            if os.path.exists(d_path) and not os.listdir(d_path):
                                try:
                                    os.rmdir(d_path)
                                except Exception:
                                    pass

        # 复制/覆盖文件
        for root, dirs, files in os.walk(src):
            rel_root = os.path.relpath(root, src)
            target_root = os.path.join(dst, rel_root) if rel_root != "." else dst
            if not os.path.exists(target_root):
                os.makedirs(target_root)
            for f in files:
                s_file = os.path.join(root, f)
                d_file = os.path.join(target_root, f)
                if os.path.exists(d_file):
                    os.chmod(d_file, stat.S_IWRITE)
                shutil.copy2(s_file, d_file)

    def prune_backups(self, backup_path, prefix):
        """按前缀清理备份，全局备份和每个用户备份分别最多保留 10 个"""
        dirs = []
        for d in os.listdir(backup_path):
            p = os.path.join(backup_path, d)
            if os.path.isdir(p) and d.startswith(prefix):
                dirs.append((os.path.getctime(p), p))
        
        dirs.sort() # 按创建时间由旧到新排序
        while len(dirs) > 10:
            oldest = dirs.pop(0)
            try:
                shutil.rmtree(oldest[1])
            except Exception as e:
                print(f"删除旧备份失败: {e}")

    def refresh_backups(self):
        self.global_listbox.delete(0, tk.END)
        self.user_listbox.delete(0, tk.END)
        
        backup_path = self.config.get("backup_path")
        if not backup_path or not os.path.exists(backup_path):
            return
            
        global_dirs = []
        user_dirs = []
        for d in os.listdir(backup_path):
            p = os.path.join(backup_path, d)
            if os.path.isdir(p):
                if d.startswith("全局备份-"):
                    global_dirs.append((os.path.getctime(p), d))
                elif d.startswith("用户备份-"):
                    user_dirs.append((os.path.getctime(p), d))
                
        # 最新排在最上面
        global_dirs.sort(reverse=True)
        for _, d in global_dirs:
            self.global_listbox.insert(tk.END, d)

        user_dirs.sort(reverse=True)
        for _, d in user_dirs:
            self.user_listbox.insert(tk.END, d)

    # --- 核心业务逻辑 ---

    def backup_global(self):
        """单独备份全局配置"""
        global_path = self.config.get("global_path")
        backup_path = self.config.get("backup_path")
        
        if not global_path or not os.path.exists(global_path):
            messagebox.showerror("错误", "请先设置有效的全局配置路径！")
            return
        if not backup_path or not os.path.exists(backup_path):
            messagebox.showerror("错误", "请先设置有效的备份存放路径！")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"全局备份-{timestamp}"
        target_dir = os.path.join(backup_path, folder_name)
        
        try:
            self.copy_dir(global_path, target_dir, check_extra=False)
            self.prune_backups(backup_path, "全局备份-")
            self.refresh_backups()
            messagebox.showinfo("成功", f"全局配置备份完成！\n备份版本: {folder_name}")
        except Exception as e:
            messagebox.showerror("备份失败", str(e))

    def backup_user(self, user, silent=False):
        """单独备份用户配置"""
        backup_path = self.config.get("backup_path")
        if not backup_path or not os.path.exists(backup_path):
            if not silent: messagebox.showerror("错误", "请先设置有效的备份存放路径！")
            return False

        if not os.path.exists(user["path"]):
            if not silent: messagebox.showerror("错误", f"用户目录不存在: {user['path']}")
            return False

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"用户备份-{user['name']}-{timestamp}"
        target_dir = os.path.join(backup_path, folder_name)
        
        try:
            self.copy_dir(user["path"], target_dir, check_extra=False)
            self.prune_backups(backup_path, f"用户备份-{user['name']}-")
            self.refresh_backups()
            if not silent: messagebox.showinfo("成功", f"【{user['name']}】 配置备份完成！\n备份版本: {folder_name}")
            return True
        except Exception as e:
            if not silent: messagebox.showerror("备份失败", str(e))
            return False

    def do_backup_and_sync(self, source_user):
        """备份源用户，并将其配置直接同步覆盖给所有其他账号"""
        # 1. 备份当前源账号
        success = self.backup_user(source_user, silent=True)
        if not success:
            return

        users = self.config.get("users", [])
        if len(users) <= 1:
            messagebox.showinfo("提示", "当前只有一个用户配置，已备份，无需同步。")
            return

        # 2. 从源账号直接复制到其他目标账号（开启多余文件检测）
        sync_count = 0
        try:
            for u in users:
                if u["name"] != source_user["name"]:
                    if os.path.exists(u["path"]):
                        self.copy_dir(source_user["path"], u["path"], check_extra=True)
                        sync_count += 1
            
            messagebox.showinfo("成功", f"【{source_user['name']}】的配置已备份，并成功同步覆盖给其他 {sync_count} 个账号！")
        except Exception as e:
            messagebox.showerror("同步失败", f"同步过程中出现错误:\n{str(e)}")

    def restore_backup(self):
        """智能还原：根据选中的备份名称判断是还原全局还是还原所有用户"""
        selected_folder_name = self.get_selected_backup()
        if not selected_folder_name:
            messagebox.showwarning("提示", "请先在列表中选择一个备份版本！")
            return
            
        backup_path = self.config.get("backup_path")
        full_backup_dir = os.path.join(backup_path, selected_folder_name)
        
        if not os.path.exists(full_backup_dir):
            messagebox.showerror("错误", "找不到对应的备份文件夹！")
            return

        try:
            # 全局备份还原
            if selected_folder_name.startswith("全局备份-"):
                global_target = self.config.get("global_path")
                if not global_target or not os.path.exists(global_target):
                    messagebox.showerror("错误", "未设置全局路径或路径不存在，无法还原！")
                    return
                self.copy_dir(full_backup_dir, global_target, check_extra=True)
                messagebox.showinfo("成功", f"已成功将【{selected_folder_name}】还原至全局配置目录！")
            
            # 用户备份还原
            elif selected_folder_name.startswith("用户备份-"):
                users = self.config.get("users", [])
                if not users:
                    messagebox.showerror("错误", "当前没有添加任何用户配置目录！")
                    return
                
                success_count = 0
                for u in users:
                    if os.path.exists(u["path"]):
                        self.copy_dir(full_backup_dir, u["path"], check_extra=True)
                        success_count += 1
                        
                messagebox.showinfo("成功", f"已成功将【{selected_folder_name}】覆盖还原至 {success_count} 个用户的配置目录！")
                
        except Exception as e:
            messagebox.showerror("还原失败", f"文件复制时出错: {str(e)}")

    def delete_selected_backup(self):
        """删除选中的备份文件夹"""
        selected_folder_name = self.get_selected_backup()
        if not selected_folder_name:
            messagebox.showwarning("提示", "请先在列表中选择一个备份版本！")
            return

        backup_path = self.config.get("backup_path")
        full_backup_dir = os.path.join(backup_path, selected_folder_name)

        if messagebox.askyesno("确认删除", f"确定要永久删除以下备份吗？\n\n{selected_folder_name}"):
            try:
                if os.path.exists(full_backup_dir):
                    shutil.rmtree(full_backup_dir)
                self.refresh_backups()
                messagebox.showinfo("成功", f"已成功删除备份: {selected_folder_name}")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CS2ConfigManager(root)
    root.mainloop()