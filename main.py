"""
Camera Photo Tools — Windows helper for post-import photo cleanup.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cleanup_orphan_jpg import delete_files, find_orphan_jpgs, find_orphan_raws
from jpg_rename import apply_jpg_renames, plan_jpg_renames


def browse_dir(var: tk.StringVar) -> None:
    path = filedialog.askdirectory()
    if path:
        var.set(path)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Camera Photo Tools")
        self.minsize(680, 460)
        self.geometry("820x540")

        self.raw_dir_var = tk.StringVar()
        self.jpg_dir_var = tk.StringVar()
        self.rename_target_var = tk.StringVar()
        self.rename_find_var = tk.StringVar()
        self.rename_replace_var = tk.StringVar()

        self.feature_var = tk.StringVar(value="orphan_jpg")
        self.hint_var = tk.StringVar()
        self._orphans: list[Path] = []
        self._preview_raw: Path | None = None
        self._preview_jpg: Path | None = None
        self._preview_feature: str | None = None

        self._rename_plan: list[tuple[Path, str]] = []
        self._preview_rename_target: Path | None = None
        self._preview_rename_pattern: str | None = None
        self._preview_rename_repl: str | None = None

        self._build_ui()
        self._update_hint()
        self._sync_feature_panels()
        self.feature_var.trace_add("write", self._on_feature_change)

    def _on_feature_change(self, *_args: object) -> None:
        self._orphans = []
        self._preview_raw = None
        self._preview_jpg = None
        self._preview_feature = None
        self._rename_plan = []
        self._preview_rename_target = None
        self._preview_rename_pattern = None
        self._preview_rename_repl = None
        self.text.delete("1.0", tk.END)
        self._update_hint()
        self._sync_feature_panels()
        self.status_var.set("就绪")

    def _sync_pair_row_order(self) -> None:
        """RAW-first for orphan_jpg; JPG-first for orphan_raw (reference above, scan target below)."""
        pad = {"padx": 10, "pady": 6}
        if self.feature_var.get() == "orphan_raw":
            self._jpg_pair_label.grid(row=0, column=0, sticky=tk.NW, **pad)
            self._jpg_pair_row.grid(row=0, column=1, sticky=tk.EW, **pad)
            self._raw_pair_label.grid(row=1, column=0, sticky=tk.NW, **pad)
            self._raw_pair_row.grid(row=1, column=1, sticky=tk.EW, **pad)
        else:
            self._raw_pair_label.grid(row=0, column=0, sticky=tk.NW, **pad)
            self._raw_pair_row.grid(row=0, column=1, sticky=tk.EW, **pad)
            self._jpg_pair_label.grid(row=1, column=0, sticky=tk.NW, **pad)
            self._jpg_pair_row.grid(row=1, column=1, sticky=tk.EW, **pad)

    def _sync_feature_panels(self) -> None:
        f = self.feature_var.get()
        if f == "jpg_rename":
            self.pair_panel.pack_forget()
            self.rename_panel.pack(fill=tk.X)
            self.btn_preview.configure(text="预览重命名")
            self.btn_action.configure(text="执行重命名")
        else:
            self.rename_panel.pack_forget()
            self._sync_pair_row_order()
            self.pair_panel.pack(fill=tk.X)
            self.btn_preview.configure(text="预览待删除列表")
            self.btn_action.configure(text="执行删除")

    def _update_hint(self) -> None:
        f = self.feature_var.get()
        if f == "orphan_jpg":
            self.hint_var.set(
                "提示：上方为 RAW 参考目录，下方为待扫描的 JPG 根目录；若未填写 JPG 目录，将默认与 RAW 目录相同。\n"
                "配对规则：在每一级子目录内，若某 JPG 的基名与同目录（或并行 RAW 目录下对应子文件夹）内\n"
                "任一 RAW 的基名相同（忽略大小写），则保留；否则视为可删除的孤立 JPG。\n"
                "删除的文件将移入回收站。"
            )
        elif f == "orphan_raw":
            self.hint_var.set(
                "提示：上方为 JPG 参考目录，下方为待扫描的 RAW 根目录；若未填写 JPG 目录，将默认与 RAW 目录相同。\n"
                "配对规则：在每一级子目录内，若某 RAW 的基名与并行 JPG 目录下对应子文件夹内\n"
                "任一 JPG/JPEG 的基名相同（忽略大小写），则保留；否则视为可删除的孤立 RAW。\n"
                "删除的文件将移入回收站。"
            )
        else:
            self.hint_var.set(
                "仅处理目标文件夹下的一层 JPG/JPEG（不扫描子文件夹），与在资源管理器中对该文件夹执行\n"
                "Get-ChildItem *.jpg 相同。\n"
                "查找词按正则表达式解析（与 PowerShell -replace 一致）；替换为空即删除该段字符。\n"
                "捕获组替换请用 \\1、\\2（Python 正则），不是 PowerShell 的 $1。"
            )

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}
        outer = ttk.Frame(self, padding=8)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        sidebar = ttk.LabelFrame(outer, text="功能", padding=10)
        sidebar.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 8))
        ttk.Radiobutton(
            sidebar,
            text="删除无对应 RAW 的 JPG",
            variable=self.feature_var,
            value="orphan_jpg",
        ).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(
            sidebar,
            text="同目录（或并行树）下按文件基名与 RAW 配对",
            wraplength=168,
            justify=tk.LEFT,
            font=("", 8),
        ).pack(anchor=tk.W, pady=(0, 12))
        ttk.Radiobutton(
            sidebar,
            text="删除无对应 JPG 的 RAW",
            variable=self.feature_var,
            value="orphan_raw",
        ).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(
            sidebar,
            text="同目录（或并行树）下按文件基名与 JPG 配对",
            wraplength=168,
            justify=tk.LEFT,
            font=("", 8),
        ).pack(anchor=tk.W, pady=(0, 12))
        ttk.Radiobutton(
            sidebar,
            text="JPG 文件名查找替换",
            variable=self.feature_var,
            value="jpg_rename",
        ).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(
            sidebar,
            text="当前文件夹内 JPG 文件名正则替换（不递归）",
            wraplength=168,
            justify=tk.LEFT,
            font=("", 8),
        ).pack(anchor=tk.W)

        frm = ttk.Frame(outer, padding=(0, 4))
        frm.grid(row=0, column=1, sticky=tk.NSEW)
        frm.columnconfigure(0, weight=1)

        self.options_container = ttk.Frame(frm)
        self.options_container.grid(row=0, column=0, columnspan=2, sticky=tk.EW, **pad)
        self.options_container.columnconfigure(0, weight=1)

        self.pair_panel = ttk.Frame(self.options_container)
        self._raw_pair_label = ttk.Label(self.pair_panel, text="RAW 所在目录")
        self._raw_pair_row = ttk.Frame(self.pair_panel)
        self._raw_pair_row.columnconfigure(0, weight=1)
        ttk.Entry(self._raw_pair_row, textvariable=self.raw_dir_var, width=50).grid(
            row=0, column=0, sticky=tk.EW, padx=(0, 8)
        )
        ttk.Button(
            self._raw_pair_row,
            text="浏览…",
            command=lambda: browse_dir(self.raw_dir_var),
        ).grid(row=0, column=1)

        self._jpg_pair_label = ttk.Label(self.pair_panel, text="JPG 所在目录")
        self._jpg_pair_row = ttk.Frame(self.pair_panel)
        self._jpg_pair_row.columnconfigure(0, weight=1)
        ttk.Entry(self._jpg_pair_row, textvariable=self.jpg_dir_var, width=50).grid(
            row=0, column=0, sticky=tk.EW, padx=(0, 8)
        )
        ttk.Button(
            self._jpg_pair_row,
            text="浏览…",
            command=lambda: browse_dir(self.jpg_dir_var),
        ).grid(row=0, column=1)
        self.pair_panel.columnconfigure(1, weight=1)
        self._sync_pair_row_order()

        self.rename_panel = ttk.Frame(self.options_container)
        ttk.Label(self.rename_panel, text="目标目录").grid(row=0, column=0, sticky=tk.NW, **pad)
        tgt_row = ttk.Frame(self.rename_panel)
        tgt_row.grid(row=0, column=1, sticky=tk.EW, **pad)
        tgt_row.columnconfigure(0, weight=1)
        ttk.Entry(tgt_row, textvariable=self.rename_target_var, width=50).grid(
            row=0, column=0, sticky=tk.EW, padx=(0, 8)
        )
        ttk.Button(tgt_row, text="浏览…", command=lambda: browse_dir(self.rename_target_var)).grid(
            row=0, column=1
        )

        ttk.Label(self.rename_panel, text="查找词（正则）").grid(row=1, column=0, sticky=tk.NW, **pad)
        ttk.Entry(self.rename_panel, textvariable=self.rename_find_var, width=52).grid(
            row=1, column=1, sticky=tk.EW, **pad
        )

        ttk.Label(self.rename_panel, text="替换为").grid(row=2, column=0, sticky=tk.NW, **pad)
        ttk.Entry(self.rename_panel, textvariable=self.rename_replace_var, width=52).grid(
            row=2, column=1, sticky=tk.EW, **pad
        )
        self.rename_panel.columnconfigure(1, weight=1)

        hint_lbl = ttk.Label(frm, textvariable=self.hint_var, wraplength=520, justify=tk.LEFT)
        hint_lbl.grid(row=1, column=0, columnspan=2, sticky=tk.W, **pad)

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=2, column=0, columnspan=2, sticky=tk.NW, **pad)
        self.btn_preview = ttk.Button(btn_row, text="预览待删除列表", command=self._on_preview)
        self.btn_preview.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_action = ttk.Button(btn_row, text="执行删除", command=self._on_action)
        self.btn_action.pack(side=tk.LEFT)

        ttk.Label(frm, text="预览").grid(row=3, column=0, sticky=tk.NW, **pad)
        self.list_frame = ttk.Frame(frm)
        self.list_frame.grid(row=3, column=1, rowspan=2, sticky=tk.NSEW, **pad)
        self.list_frame.columnconfigure(0, weight=1)
        self.list_frame.rowconfigure(0, weight=1)

        scroll = ttk.Scrollbar(self.list_frame)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.text = tk.Text(self.list_frame, height=14, wrap=tk.NONE, yscrollcommand=scroll.set)
        self.text.grid(row=0, column=0, sticky=tk.NSEW)
        scroll.config(command=self.text.yview)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(frm, textvariable=self.status_var).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, **pad
        )

        frm.rowconfigure(3, weight=1)

    def _resolved_roots(self) -> tuple[Path, Path] | None:
        raw_s = self.raw_dir_var.get().strip()
        if not raw_s:
            messagebox.showwarning("缺少目录", "请先填写 RAW 所在目录。")
            return None
        raw_path = Path(raw_s)
        if not raw_path.is_dir():
            messagebox.showerror("路径无效", f"RAW 目录不存在或不是文件夹：\n{raw_path}")
            return None

        jpg_s = self.jpg_dir_var.get().strip()
        if not jpg_s:
            jpg_path = raw_path
        else:
            jpg_path = Path(jpg_s)
            if not jpg_path.is_dir():
                messagebox.showerror("路径无效", f"JPG 目录不存在或不是文件夹：\n{jpg_path}")
                return None
        return raw_path, jpg_path

    def _resolved_rename_target(self) -> Path | None:
        s = self.rename_target_var.get().strip()
        if not s:
            messagebox.showwarning("缺少目录", "请先填写目标目录。")
            return None
        p = Path(s)
        if not p.is_dir():
            messagebox.showerror("路径无效", f"目标目录不存在或不是文件夹：\n{p}")
            return None
        return p

    def _on_preview(self) -> None:
        feat = self.feature_var.get()
        self.text.delete("1.0", tk.END)

        if feat == "jpg_rename":
            self._preview_rename()
            return

        roots = self._resolved_roots()
        if not roots:
            return
        raw_root, jpg_root = roots

        self.status_var.set("正在扫描…")
        self.update_idletasks()
        try:
            if feat == "orphan_jpg":
                self._orphans = find_orphan_jpgs(raw_root, jpg_root)
            else:
                self._orphans = find_orphan_raws(raw_root, jpg_root)
        except OSError as e:
            self.status_var.set("扫描失败")
            self._preview_raw = None
            self._preview_jpg = None
            self._preview_feature = None
            messagebox.showerror("错误", str(e))
            return

        self._preview_raw = raw_root.resolve()
        self._preview_jpg = jpg_root.resolve()
        self._preview_feature = feat
        for p in self._orphans:
            self.text.insert(tk.END, str(p) + "\n")

        if feat == "orphan_jpg":
            self.status_var.set(
                f"共 {len(self._orphans)} 个 JPG 无同目录同名 RAW，执行删除时将移入回收站。"
            )
        else:
            self.status_var.set(
                f"共 {len(self._orphans)} 个 RAW 无同目录同名 JPG，执行删除时将移入回收站。"
            )

    def _preview_rename(self) -> None:
        target = self._resolved_rename_target()
        if not target:
            self._rename_plan = []
            self._preview_rename_target = None
            self._preview_rename_pattern = None
            self._preview_rename_repl = None
            self._preview_feature = None
            return

        pat = self.rename_find_var.get()
        repl = self.rename_replace_var.get()
        self.status_var.set("正在生成重命名预览…")
        self.update_idletasks()

        plans, errs = plan_jpg_renames(target, pat, repl)
        self._rename_plan = plans
        self._preview_rename_target = target.resolve()
        self._preview_rename_pattern = pat
        self._preview_rename_repl = repl
        self._preview_feature = "jpg_rename"

        if errs:
            self.text.insert(tk.END, "【提示】\n")
            for e in errs:
                self.text.insert(tk.END, e + "\n")
            self.text.insert(tk.END, "\n")

        if not plans:
            self.status_var.set("没有可重命名的 JPG，或存在错误。")
            if errs:
                messagebox.showwarning("预览", "\n".join(errs[:12]))
            else:
                messagebox.showinfo("预览", "当前目录下没有会因本次规则而改名的 JPG/JPEG。")
            return

        self.text.insert(tk.END, "原文件名 → 新文件名\n")
        for p, new in plans:
            self.text.insert(tk.END, f"{p.name} → {new}\n")

        msg = f"将重命名 {len(plans)} 个文件。"
        if errs:
            msg += f" 另有 {len(errs)} 条提示见预览区。"
        self.status_var.set(msg)
        if errs:
            messagebox.showwarning("预览", "部分文件已跳过，详见预览区开头。")

    def _on_action(self) -> None:
        feat = self.feature_var.get()
        if feat == "jpg_rename":
            self._apply_rename()
        else:
            self._on_delete()

    def _apply_rename(self) -> None:
        target = self._resolved_rename_target()
        if not target:
            return
        pat = self.rename_find_var.get()
        repl = self.rename_replace_var.get()

        if self._preview_rename_target is None or self._preview_feature != "jpg_rename":
            messagebox.showinfo("提示", "请先点击「预览重命名」后再执行。")
            return
        if pat != self._preview_rename_pattern or repl != self._preview_rename_repl:
            messagebox.showwarning(
                "参数已变更",
                "查找词或替换词与预览时不一致。请重新预览后再执行。",
            )
            return
        if target.resolve() != self._preview_rename_target:
            messagebox.showwarning(
                "目录已变更",
                "目标目录与预览时不一致。请重新预览后再执行。",
            )
            return
        if not self._rename_plan:
            messagebox.showinfo("提示", "预览列表为空，无需重命名。")
            return

        n = len(self._rename_plan)
        if not messagebox.askyesno(
            "确认重命名",
            f"将把 {n} 个 JPG/JPEG 按预览结果重命名。\n是否继续？",
            icon=messagebox.WARNING,
        ):
            return

        ok, errors = apply_jpg_renames(self._rename_plan)
        self._rename_plan = []
        self.text.delete("1.0", tk.END)
        self._preview_rename_target = None
        self._preview_rename_pattern = None
        self._preview_rename_repl = None
        self._preview_feature = None

        if errors:
            self.status_var.set(f"已重命名 {ok} 个，{len(errors)} 个失败。")
            messagebox.showerror("部分失败", "\n".join(errors[:20]))
        else:
            self.status_var.set(f"已成功重命名 {ok} 个文件。")
            messagebox.showinfo("完成", f"已成功重命名 {ok} 个文件。")

    def _on_delete(self) -> None:
        roots = self._resolved_roots()
        if not roots:
            return
        raw_now, jpg_now = roots
        feat = self.feature_var.get()

        if self._preview_raw is None or self._preview_jpg is None or self._preview_feature is None:
            messagebox.showinfo(
                "提示",
                "请先点击「预览待删除列表」生成列表后再删除。",
            )
            return
        if feat != self._preview_feature:
            messagebox.showwarning(
                "功能已切换",
                "当前选择与预览时的功能不一致。请重新预览后再删除。",
            )
            return
        if raw_now.resolve() != self._preview_raw or jpg_now.resolve() != self._preview_jpg:
            messagebox.showwarning(
                "目录已变更",
                "RAW 或 JPG 目录与预览时不一致。请重新预览后再删除。",
            )
            return
        if not self._orphans:
            messagebox.showinfo(
                "提示",
                "预览列表为空。请先点击「预览待删除列表」，确认列表无误后再删除。",
            )
            return

        n = len(self._orphans)
        if feat == "orphan_jpg":
            kind = "JPG"
            msg = (
                f"将把 {n} 个 JPG 移入回收站，可从回收站恢复或彻底清空。\n是否继续？"
            )
        else:
            kind = "RAW"
            msg = (
                f"将把 {n} 个 RAW 移入回收站，可从回收站恢复或彻底清空。\n是否继续？"
            )

        if not messagebox.askyesno("确认删除", msg, icon=messagebox.WARNING):
            return

        ok, errors = delete_files(self._orphans)
        self._orphans = []
        self.text.delete("1.0", tk.END)
        self._preview_raw = None
        self._preview_jpg = None
        self._preview_feature = None

        if errors:
            self.status_var.set(f"已移入回收站 {ok} 个，{len(errors)} 个失败。")
            messagebox.showerror("部分失败", "\n".join(errors[:20]))
        else:
            self.status_var.set(f"已将 {ok} 个 {kind} 移入回收站。")
            messagebox.showinfo("完成", f"已将 {ok} 个 {kind} 移入回收站。")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
