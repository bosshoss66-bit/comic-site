#!/usr/bin/env python3
"""Desktop GUI for comic add/delete operations.

Run directly (or via Comic Manager.command) to manage comics without terminal commands.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import comic_admin


class ComicManagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Comic Manager")
        self.geometry("1020x650")
        self.minsize(900, 560)

        self.comics: list[dict] = []

        self.slug_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.source_dir_var = tk.StringVar()
        self.cover_var = tk.StringVar()
        self.replace_var = tk.BooleanVar(value=False)
        self.delete_files_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready.")

        self._build_ui()
        self.refresh_list(select_slug=None)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(root, text="Existing Comics", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        ttk.Button(left, text="Refresh", command=lambda: self.refresh_list(None)).grid(
            row=0, column=0, sticky="w"
        )

        self.listbox = tk.Listbox(left, exportselection=False)
        self.listbox.grid(row=1, column=0, sticky="nsew", pady=(8, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self.detail_label = ttk.Label(
            left,
            text="Select a comic to see details.",
            anchor="w",
            justify="left",
            wraplength=320,
        )
        self.detail_label.grid(row=2, column=0, sticky="ew")

        delete_frame = ttk.Frame(left)
        delete_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        delete_frame.columnconfigure(0, weight=1)

        ttk.Checkbutton(
            delete_frame,
            text="Also delete image files from uploads",
            variable=self.delete_files_var,
        ).grid(row=0, column=0, sticky="w")

        ttk.Button(delete_frame, text="Delete Selected Comic", command=self.delete_selected).grid(
            row=1, column=0, sticky="ew", pady=(8, 0)
        )

        right = ttk.LabelFrame(root, text="Add or Replace Comic", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)

        self._add_labeled_entry(right, "Slug", self.slug_var, 0)
        self._add_labeled_entry(right, "Title", self.title_var, 1)
        self._add_labeled_entry(right, "Description", self.description_var, 2)

        ttk.Label(right, text="Source Folder").grid(row=3, column=0, sticky="w", pady=(8, 0))
        source_frame = ttk.Frame(right)
        source_frame.grid(row=3, column=1, sticky="ew", pady=(8, 0))
        source_frame.columnconfigure(0, weight=1)
        ttk.Entry(source_frame, textvariable=self.source_dir_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(source_frame, text="Browse", command=self.pick_source_dir).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(right, text="Optional Cover Image").grid(row=4, column=0, sticky="w", pady=(8, 0))
        cover_frame = ttk.Frame(right)
        cover_frame.grid(row=4, column=1, sticky="ew", pady=(8, 0))
        cover_frame.columnconfigure(0, weight=1)
        ttk.Entry(cover_frame, textvariable=self.cover_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(cover_frame, text="Browse", command=self.pick_cover_file).grid(row=0, column=1, padx=(8, 0))

        ttk.Checkbutton(
            right,
            text="Replace existing comic if slug already exists",
            variable=self.replace_var,
        ).grid(row=5, column=1, sticky="w", pady=(10, 0))

        ttk.Button(right, text="Add / Replace Comic", command=self.add_or_replace).grid(
            row=6, column=1, sticky="ew", pady=(12, 0)
        )

        instructions = (
            "Workflow: choose source folder with page images -> fill slug/title -> Add/Replace.\n"
            "Images are optimized and copied into uploads/<slug>/ as .opt.jpg files."
        )
        ttk.Label(right, text=instructions, anchor="w", justify="left", wraplength=560).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(16, 0)
        )

        status_bar = ttk.Label(root, textvariable=self.status_var, anchor="w")
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _add_labeled_entry(self, parent: ttk.LabelFrame, label: str, variable: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=(8, 0))

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def refresh_list(self, select_slug: str | None) -> None:
        try:
            self.comics = comic_admin.get_comics()
        except Exception as error:
            messagebox.showerror("Load Error", str(error))
            self.set_status("Failed to load comic data.")
            return

        self.comics.sort(key=lambda c: (c.get("title", "").lower(), c.get("slug", "").lower()))

        self.listbox.delete(0, tk.END)
        selected_index = None
        for idx, comic in enumerate(self.comics):
            title = comic.get("title", "(untitled)")
            slug = comic.get("slug", "")
            pages = len(comic.get("pages", []))
            self.listbox.insert(tk.END, f"{title} ({slug}) - {pages} pages")
            if select_slug and slug == select_slug:
                selected_index = idx

        if selected_index is not None:
            self.listbox.selection_set(selected_index)
            self.listbox.activate(selected_index)
            self.listbox.see(selected_index)
            self._on_select(None)
        else:
            self.detail_label.configure(text="Select a comic to see details.")

        self.set_status(f"Loaded {len(self.comics)} comics.")

    def _on_select(self, _: object) -> None:
        idxs = self.listbox.curselection()
        if not idxs:
            self.detail_label.configure(text="Select a comic to see details.")
            return

        comic = self.comics[idxs[0]]
        title = comic.get("title", "")
        slug = comic.get("slug", "")
        description = comic.get("description", "")
        pages = len(comic.get("pages", []))
        cover = comic.get("cover", "")

        details = (
            f"Title: {title}\n"
            f"Slug: {slug}\n"
            f"Pages: {pages}\n"
            f"Cover: {cover}\n"
            f"Description: {description}"
        )
        self.detail_label.configure(text=details)

    def pick_source_dir(self) -> None:
        folder = filedialog.askdirectory(title="Choose folder containing comic pages")
        if folder:
            self.source_dir_var.set(folder)

    def pick_cover_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose optional cover image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.heic"), ("All Files", "*.*")],
        )
        if path:
            self.cover_var.set(path)

    def add_or_replace(self) -> None:
        slug = self.slug_var.get().strip()
        title = self.title_var.get().strip()
        description = self.description_var.get().strip()
        source_dir = self.source_dir_var.get().strip()
        cover = self.cover_var.get().strip()
        replace = self.replace_var.get()

        if not slug or not title or not source_dir:
            messagebox.showwarning("Missing Fields", "Slug, Title, and Source Folder are required.")
            return

        try:
            comic = comic_admin.add_comic(
                slug=slug,
                title=title,
                description=description,
                source_dir=Path(source_dir),
                cover=Path(cover) if cover else None,
                replace=replace,
            )
        except Exception as error:
            messagebox.showerror("Add Comic Failed", str(error))
            self.set_status("Add/replace failed.")
            return

        self.refresh_list(select_slug=comic.get("slug"))
        messagebox.showinfo(
            "Comic Added",
            f"Saved '{comic.get('title')}' with {len(comic.get('pages', []))} pages.",
        )
        self.set_status(f"Added/updated comic: {comic.get('slug')}")

    def delete_selected(self) -> None:
        idxs = self.listbox.curselection()
        if not idxs:
            messagebox.showwarning("No Selection", "Select a comic to delete.")
            return

        comic = self.comics[idxs[0]]
        slug = comic.get("slug", "")
        title = comic.get("title", slug)
        delete_files = self.delete_files_var.get()

        prompt = f"Delete '{title}' ({slug}) from the site catalog?"
        if delete_files:
            prompt += "\n\nImage files in uploads/<slug> will also be removed."

        if not messagebox.askyesno("Confirm Delete", prompt):
            return

        try:
            comic_admin.delete_comic(slug=slug, delete_files=delete_files)
        except Exception as error:
            messagebox.showerror("Delete Failed", str(error))
            self.set_status("Delete failed.")
            return

        self.refresh_list(select_slug=None)
        messagebox.showinfo("Comic Deleted", f"Deleted '{title}'.")
        self.set_status(f"Deleted comic: {slug}")


def main() -> int:
    app = ComicManagerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
