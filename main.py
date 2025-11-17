import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import webbrowser

class DanbooruTagger:
    def __init__(self, root):
        self.root = root
        self.root.title("TKtagger (Danbooru Tagger)")
        self.root.geometry("1400x900")

        self.root_folder = None
        self.current_folder = None
        self.images = []
        self.selected_images = set()
        self.image_widgets = {}
        self.tag_entries = {}
        self.tag_filters = {}
        self.images_per_row = 3

        self.setup_ui()

        # cross-platform mousewheel binding
        # note: widgets already exist after setup_ui
        for widget in (self.canvas, self.tags_canvas):
            widget.bind_all("<MouseWheel>", self._on_mousewheel)
            widget.bind_all("<Button-4>", self._on_mousewheel)
            widget.bind_all("<Button-5>", self._on_mousewheel)

        self.root.bind('<Control-a>', lambda e: self.select_all_images())
        self.root.bind('<Control-A>', lambda e: self.select_all_images())
        self.root.bind('<Control-i>', lambda e: self.invert_selection())
        self.root.bind('<Control-I>', lambda e: self.invert_selection())
        self.root.bind('<Control-d>', lambda e: self.deselect_all_images())
        self.root.bind('<Control-D>', lambda e: self.deselect_all_images())

    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open folder", command=self.select_root_folder)
        file_menu.add_command(label="Save", command=self.save_all)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.quit)

        tool_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tool", menu=tool_menu)
        tool_menu.add_command(label="Remove duplicate tags", command=self.remove_duplicate_tags)
        tool_menu.add_command(label="Sort tags", command=self.sort_tags)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Main container
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Left panel - Directory tree
        left_frame = tk.Frame(main_container, width=250, bg='#2b2b2b')
        main_container.add(left_frame, minsize=200)

        tk.Label(left_frame, text="Folder directory", bg='#2b2b2b', fg='white',
                 font=('Arial', 12, 'bold')).pack(pady=5)

        tree_frame = tk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tree_scroll = tk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.dir_tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set)
        self.dir_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.dir_tree.yview)
        self.dir_tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # Right panel - Tag search & list
        right_frame = tk.Frame(main_container, width=300, bg='#2b2b2b')
        main_container.add(right_frame, minsize=250)

        tk.Label(right_frame, text="Search tags", bg='#2b2b2b', fg='white',
                 font=('Arial', 12, 'bold')).pack(pady=5)

        search_frame = tk.Frame(right_frame, bg='#2b2b2b')
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        entry_row = tk.Frame(search_frame, bg='#2b2b2b')
        entry_row.pack(fill=tk.X, pady=(0, 4))

        tk.Label(entry_row, text="Search", bg='#2b2b2b', fg='white',
                 font=('Arial', 12)).pack(side=tk.LEFT)

        self.folder_tag_search = tk.Entry(entry_row, font=('Arial', 10))
        self.folder_tag_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        btn_row = tk.Frame(search_frame)
        btn_row.pack(fill=tk.X)

        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)
        btn_row.grid_columnconfigure(2, weight=1)
        btn_row.grid_columnconfigure(3, weight=1)

        clear_search_btn = tk.Button(btn_row, text="Clear Input", bg='#666', fg='white',
                                     font=('Arial', 10, 'bold'), width=10,
                                     command=lambda: [self.folder_tag_search.delete(0, tk.END),
                                                      self.filter_folder_tags()])
        clear_search_btn.pack(side=tk.LEFT, padx=(0, 3))

        deselect_tags_btn = tk.Button(btn_row, text="Deselect", bg='#9C27B0', fg='white',
                                      font=('Arial', 10, 'bold'), width=10,
                                      command=self.deselect_all_tag_filters,
                                      cursor='hand2')
        deselect_tags_btn.pack(side=tk.LEFT, padx=(0, 3))

        delete_btn = tk.Button(btn_row, text="Delete Tags", bg='#f44336', fg='white',
                               font=('Arial', 10, 'bold'), width=12,
                               command=self.open_delete_tag_window)
        delete_btn.pack(side=tk.LEFT, padx=(0, 3))

        replace_btn = tk.Button(btn_row, text="Replace Tags", bg='#FF9800', fg='white',
                                font=('Arial', 10, 'bold'), width=12,
                                command=self.open_replace_tag_window)
        replace_btn.pack(side=tk.LEFT)

        self.folder_tag_search.bind('<KeyRelease>', self.filter_folder_tags)

        folder_tags_frame = tk.Frame(right_frame, bg='#2b2b2b')
        folder_tags_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        folder_tags_scroll = tk.Scrollbar(folder_tags_frame)
        folder_tags_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tags_canvas = tk.Canvas(folder_tags_frame, bg='#1e1e1e',
                                     highlightthickness=0,
                                     yscrollcommand=folder_tags_scroll.set)
        self.tags_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        folder_tags_scroll.config(command=self.tags_canvas.yview)

        self.tags_list_frame = tk.Frame(self.tags_canvas, bg='#1e1e1e')
        self.tags_canvas_window = self.tags_canvas.create_window((0, 0),
                                                                 window=self.tags_list_frame,
                                                                 anchor='nw')

        self.tags_list_frame.bind('<Configure>',
                                 lambda e: self.tags_canvas.configure(
                                     scrollregion=self.tags_canvas.bbox("all")))
        self.tags_canvas.bind('<Configure>', self.on_tags_canvas_configure)

        self.all_folder_tags = []
        self.folder_tag_counts = {}

        # Center panel - Image grid
        center_frame = tk.Frame(main_container, bg='#1e1e1e')
        main_container.add(center_frame, minsize=600)

        canvas_frame = tk.Frame(center_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        top_bar = tk.Frame(center_frame, bg='#3c3c3c', height=40)
        top_bar.pack(fill=tk.X, padx=10, pady=(10, 0))

        select_all_btn = tk.Button(top_bar, text="✔️ Select All (Ctrl+A)", bg='#4CAF50', fg='white',
                                   font=('Arial', 9), command=self.select_all_images)
        select_all_btn.pack(side=tk.LEFT, padx=5)

        invert_select_btn = tk.Button(top_bar, text="🔁 Invert Select (Ctrl+I)", bg='#FF9800', fg='white',
                                      font=('Arial', 9), command=self.invert_selection)
        invert_select_btn.pack(side=tk.LEFT, padx=5)

        deselect_all_btn = tk.Button(top_bar, text="❌ Deselect All (Ctrl+D)", bg='#f44336', fg='white',
                                     font=('Arial', 9), command=self.deselect_all_images)
        deselect_all_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(top_bar, text="💾 Save", bg='#2196F3', fg='white',
                  command=self.save_all, font=('Arial', 9),
                  cursor='hand2').pack(side=tk.LEFT, padx=5)

        columns_control_bar = tk.Frame(center_frame, bg='#2b2b2b', height=35)
        columns_control_bar.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(columns_control_bar, text="Visible columns:", bg='#2b2b2b', fg='white',
                 font=('Arial', 9)).pack(side=tk.LEFT, padx=(10, 5))

        for num in [1, 2, 3, 4, 5, 6, 8]:
            btn = tk.Button(columns_control_bar, text=str(num),
                            bg='#555',
                            fg='white', font=('Arial', 9, 'bold'), width=3,
                            command=lambda n=num: self.set_columns(n))
            btn.pack(side=tk.LEFT, padx=2)
            if num == 4:
                self.active_col_btn = btn

        self.canvas = tk.Canvas(canvas_frame, bg='#1e1e1e', highlightthickness=0)
        v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scroll = tk.Scrollbar(center_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.grid_frame = tk.Frame(self.canvas, bg='#1e1e1e')
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor='nw')

        self.grid_frame.bind('<Configure>', self.on_frame_configure)
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        bottom_bar = tk.Frame(center_frame, bg='#3c3c3c', height=60)
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        tk.Label(bottom_bar, text="Tag:", bg='#3c3c3c', fg='white',
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)

        self.global_tag_entry = tk.Entry(bottom_bar, font=('Arial', 11), width=40)
        self.global_tag_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        tk.Button(bottom_bar, text="Add Tag", bg='#4CAF50', fg='white',
                  command=self.add_tag_to_selected, font=('Arial', 10, 'bold'),
                  cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(bottom_bar, text="Remove Tag (must be same name of tag)", bg='#f44336', fg='white',
                  command=self.remove_tag_from_selected, font=('Arial', 10, 'bold'),
                  cursor='hand2').pack(side=tk.LEFT, padx=5)

    def remove_duplicate_tags(self):
        if not self.current_folder:
            messagebox.showinfo("Info", "No folder selected")
            return
        answer = messagebox.askyesno("Confirm", "Are you sure you want to remove duplicate tags?")
        if answer:
            for idx, img_data in enumerate(self.images):
                img_data['tags'] = list(dict.fromkeys(img_data['tags']))
                img_data['modified'] = True
                self.refresh_image_tags(idx)
            messagebox.showinfo("Done", "Duplicate tags removed.")

    def sort_tags(self):
            if not self.images:
                messagebox.showinfo("Info", "No images in current folder")
                return

            window = tk.Toplevel(self.root)
            window.title("Choose tags (global)")
            window.geometry("380x620")
            
            window.resizable(False, True)
            window.transient(self.root)
            window.grab_set()
            window.focus_force()

            # --- Search bar ---
            self.search_var = tk.StringVar()
            self.search_var.trace_add("write", lambda name, index, mode: self.filter_tags(self.search_var.get()))
            
            tk.Label(window, text="Choose tags (global)", font=("Arial", 14, "bold")).pack(pady=(10, 5))

            search_entry = tk.Entry(window, textvariable=self.search_var, font=("Arial", 10))
            search_entry.pack(fill="x", padx=20, pady=(0, 10))
            # ----------------------

            canvas_frame = tk.Frame(window)
            canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

            canvas = tk.Canvas(canvas_frame, highlightthickness=0)
            scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)

            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill=tk.BOTH, expand=True)

            # Save tags_frame to self so it can be updated later
            self.tags_frame = tags_frame = tk.Frame(canvas)
            canvas.create_window((0, 0), window=tags_frame, anchor="nw")
            tags_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

            # Store check_vars and tags_widgets for filtering functionality
            self.check_vars = check_vars = {}
            self.tags_widgets = {} # {tag: (row, chk, label)}

            for tag in self.all_folder_tags:
                var = tk.BooleanVar(value=False)
                check_vars[tag] = var

                row = tk.Frame(tags_frame)
                row.pack(fill="x", pady=1)

                chk = tk.Checkbutton(row, variable=var, bd=0, highlightthickness=0) 
                # Delete selectcolor
                chk.pack(side="left")
                
                label = tk.Label(row, text=tag, font=("Arial", 11), anchor="w")
                label.pack(side="left", fill="x", expand=True)
                
                self.tags_widgets[tag] = row # Save only parent widget to hide/show

            pos_frame = tk.Frame(window)
            pos_frame.pack(fill="x", pady=15)

            tk.Label(pos_frame, text="re-sort at:", font=("Arial", 11)).pack(side="left", padx=20)

            pos_var = tk.StringVar(value="beginning")

            rb_begin = tk.Radiobutton(pos_frame, text="beginning", variable=pos_var, value="beginning", bd=0, highlightthickness=0)
            rb_begin.pack(side="left", padx=(40, 80))

            rb_end = tk.Radiobutton(pos_frame, text="ending", variable=pos_var, value="ending", bd=0, highlightthickness=0)
            rb_end.pack(side="left", padx=0)

            btn_frame = tk.Frame(window)
            btn_frame.pack(pady=20)

            tk.Button(btn_frame, text="Deselect", width=12,
                      command=lambda: [v.set(False) for v in check_vars.values()]).pack(side="left", padx=30)

            tk.Button(btn_frame, text="Confirm", width=12,
                      font=("Arial", 10, "bold"), command=lambda: self.apply_sort_tags(check_vars, pos_var, window)).pack(side="right", padx=30)
    def filter_tags(self, search_term):
            search_term = search_term.lower().strip()
            
            # Hide all previous tags widgets
            for widget in self.tags_widgets.values():
                widget.pack_forget()

            # Display matching tags
            if not search_term:
                # If the search bar is empty, show all again
                for tag in self.all_folder_tags:
                    self.tags_widgets[tag].pack(fill="x", pady=1)
            else:
                # Lặp qua tất cả các tags
                for tag in self.all_folder_tags:
                    if search_term in tag.lower():
                        self.tags_widgets[tag].pack(fill="x", pady=1)

            # Update canvas scrollregion
            self.tags_frame.update_idletasks() # Ensure layout is recalculated
            canvas = self.tags_frame.master # Assume tags_frame is in Canvas
    
            canvas.configure(scrollregion=canvas.bbox("all"))
        
    def apply_sort_tags(self, check_vars, pos_var, window):
        chosen_tags = [tag for tag, var in check_vars.items() if var.get()]
        if not chosen_tags:
            messagebox.showinfo("Info", "No tags selected")
            window.destroy()
            return

        chosen_set = set(chosen_tags)
        affected = 0

        for idx, img_data in enumerate(self.images):
            present = [t for t in img_data['tags'] if t in chosen_set]
            if not present:
                continue

            remaining = [t for t in img_data['tags'] if t not in chosen_set]

            if pos_var.get() == "beginning":
                img_data['tags'] = present + remaining
            else:
                img_data['tags'] = remaining + present

            img_data['modified'] = True
            self.refresh_image_tags(idx)
            affected += 1

        self.load_all_folder_tags()
        messagebox.showinfo("Done", f"Re-sorted tags in {affected} images")
        window.destroy()

    def on_tags_canvas_configure(self, event):
        try:
            self.tags_canvas.itemconfig(self.tags_canvas_window, width=event.width)
        except Exception:
            pass

    def on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        try:
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        except Exception:
            pass
        if self.images:
            self.display_images()

    def set_columns(self, num):
        self.images_per_row = num
        self.display_images()

    def select_root_folder(self):
        folder = filedialog.askdirectory(title="Open folder")
        if folder:
            self.root_folder = folder
            self.current_folder = folder

            self.dir_tree.delete(*self.dir_tree.get_children())
            self.populate_tree(folder, '')

            self.load_folder_images(folder)

    def deselect_all_tag_filters(self):
        self.tag_filters.clear()
        self.update_folder_tags_listbox(self.folder_tag_search.get().strip())
        self.display_images()

    def load_folder_images(self, folder):
        if self.images and self.has_unsaved_changes():
            response = messagebox.askyesnocancel(
                "Save the change?",
                "Do you want to save the changes before transferring the folder?"
            )
            if response is True:
                self.save_all()
            elif response is None:
                return

        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self.images = []
        self.selected_images.clear()
        self.image_widgets.clear()
        self.tag_entries.clear()
        self.tag_filters.clear()

        self.current_folder = folder

        supported_formats = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
        try:
            for file in sorted(os.listdir(folder)):
                if file.lower().endswith(supported_formats):
                    img_path = os.path.join(folder, file)
                    txt_path = os.path.splitext(img_path)[0] + '.txt'
                    tags = self.load_tags(txt_path)
                    self.images.append({
                        'path': img_path,
                        'txt_path': txt_path,
                        'tags': tags,
                        'filename': file,
                        'modified': False
                    })
        except PermissionError:
            messagebox.showerror("Error", f"No permission access: {folder}")
            return

        self.display_images()
        self.load_all_folder_tags()

    def has_unsaved_changes(self):
        for img_data in self.images:
            if img_data.get('modified', False):
                return True
        return False

    def update_folder_tags_listbox(self, filter_text=''):
        for widget in self.tags_list_frame.winfo_children():
            widget.destroy()

        filtered_tags = [tag for tag in self.all_folder_tags if filter_text.lower() in tag.lower()]

        for tag in filtered_tags:
            tag_frame = tk.Frame(self.tags_list_frame, bg='#1e1e1e')
            tag_frame.pack(fill=tk.X, padx=5, pady=1)

            tag_frame.grid_columnconfigure(1, weight=1)

            var = tk.BooleanVar(value=self.tag_filters.get(tag, False))

            chk = tk.Checkbutton(tag_frame, variable=var, bg='#1e1e1e',
                                fg='white', selectcolor='#2b2b2b', bd=0, highlightthickness=0,
                                command=lambda t=tag, v=var: self.toggle_tag_filter(t, v))
            chk.grid(row=0, column=0, sticky='w', padx=(12, 8), pady=2)

            count = self.folder_tag_counts.get(tag, 0)
            display_text = f"{tag} ({count})"

            label = tk.Label(tag_frame, text=display_text, bg='#1e1e1e', fg='white',
                             font=('Arial', 10), anchor='w', cursor='hand2')
            label.grid(row=0, column=1, sticky='ew', padx=(0, 10), pady=2)
            label.bind('<Button-1>', lambda e, t=tag: self.insert_tag_to_global(t))

            insert_btn = tk.Button(tag_frame, text="Insert", bg='#2196F3', fg='white',
                                   font=('Arial', 9, 'bold'), width=7, relief='flat',
                                   cursor='hand2', command=lambda t=tag: self.insert_tag_to_global(t))
            insert_btn.grid(row=0, column=2, sticky='e', padx=(0, 15), pady=2)

        self.tags_canvas.yview_moveto(0)

    def filter_folder_tags(self, event=None):
        search_term = self.folder_tag_search.get().strip()
        self.update_folder_tags_listbox(search_term)

    def toggle_tag_filter(self, tag, var):
        self.tag_filters[tag] = var.get()
        self.display_images()

    def insert_tag_to_global(self, tag):
        self.global_tag_entry.insert(0, tag)
        self.global_tag_entry.focus_set()

    def load_all_folder_tags(self):
        all_tags = {}
        if not self.current_folder:
            return

        for img_data in self.images:
            for tag in img_data['tags']:
                all_tags[tag] = all_tags.get(tag, 0) + 1

        self.folder_tag_counts = all_tags
        self.all_folder_tags = sorted(all_tags.keys())
        self.tag_filters = {}
        self.update_folder_tags_listbox()
        self.display_images()

    def populate_tree(self, path, parent):
        node_text = os.path.basename(path) or path
        node = self.dir_tree.insert(parent, 'end', text=node_text,
                                    values=[path], open=True)

        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    self.populate_tree(item_path, node)
        except PermissionError:
            pass

    def on_tree_select(self, event):
        selection = self.dir_tree.selection()
        if selection:
            item = selection[0]
            values = self.dir_tree.item(item, 'values')
            if values:
                folder = values[0]
                if os.path.isdir(folder):
                    self.load_folder_images(folder)

    def load_tags(self, txt_path):
        if os.path.exists(txt_path):
            try:
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    return [tag.strip() for tag in content.split(',') if tag.strip()]
            except Exception:
                return []
        return []

    def open_delete_tag_window(self):
        selected_tags = [tag for tag, enabled in self.tag_filters.items() if enabled]

        if not selected_tags:
            messagebox.showwarning("Warning", "Please select at least one tag to replace!")
            return

        tag_list = "\n- " + "\n- ".join(selected_tags)

        confirm = messagebox.askyesno(
            "Delete Tags",
            f"Are you sure you want to remove the following tags from all images?\n{tag_list}"
        )

        if not confirm:
            return

        count = 0
        for idx, img_data in enumerate(self.images):
            modified = False
            for tag in selected_tags:
                if tag in img_data['tags']:
                    img_data['tags'].remove(tag)
                    modified = True
            if modified:
                img_data['modified'] = True
                self.refresh_image_tags(idx)
                count += 1

        self.load_all_folder_tags()
        messagebox.showinfo("Done", f"Removed {len(selected_tags)} tag from {count} images.")

    def select_all_images(self):
        for idx in range(len(self.images)):
            if idx not in self.selected_images:
                self.selected_images.add(idx)
                container = self.image_widgets.get(idx, {}).get('container')
                var = self.image_widgets.get(idx, {}).get('checkbox_var')
                if container and var:
                    container.config(highlightbackground='#4CAF50', highlightthickness=3)
                    var.set(True)

    def invert_selection(self):
        for idx in range(len(self.images)):
            container = self.image_widgets.get(idx, {}).get('container')
            var = self.image_widgets.get(idx, {}).get('checkbox_var')
            if container and var:
                if idx in self.selected_images:
                    self.selected_images.discard(idx)
                    container.config(highlightbackground='#3c3c3c', highlightthickness=2)
                    var.set(False)
                else:
                    self.selected_images.add(idx)
                    container.config(highlightbackground='#4CAF50', highlightthickness=3)
                    var.set(True)

    def deselect_all_images(self):
        for idx in list(self.selected_images):
            container = self.image_widgets.get(idx, {}).get('container')
            var = self.image_widgets.get(idx, {}).get('checkbox_var')
            if container and var:
                container.config(highlightbackground='#3c3c3c', highlightthickness=2)
                var.set(False)
        self.selected_images.clear()

    def open_replace_tag_window(self):
        selected_tags = [tag for tag, enabled in self.tag_filters.items() if enabled]

        if not selected_tags:
            messagebox.showwarning("Warning", "Please select at least one tag to replace!")
            return

        window = tk.Toplevel(self.root)
        window.title("Thay thế Tag")
        window.geometry("500x" + str(120 + 40 * len(selected_tags)))
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()

        tk.Label(window, text="Enter the new tag that corresponds to each old tag:",
                 font=('Arial', 11), wraplength=360, justify="left").pack(pady=(15, 5), anchor='w', padx=10)

        entry_dict = {}
        for tag in selected_tags:
            frame = tk.Frame(window)
            frame.pack(fill=tk.X, padx=15, pady=5)

            tk.Label(frame, text=tag, font=('Arial', 10), width=15, anchor='w').pack(side=tk.LEFT)
            entry = tk.Entry(frame, font=('Arial', 10))
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry_dict[tag] = entry

        def confirm_replace():
            replace_map = {}
            for old_tag, entry in entry_dict.items():
                new_tag = entry.get().strip()
                if new_tag and new_tag != old_tag:
                    replace_map[old_tag] = new_tag

            if not replace_map:
                messagebox.showinfo("No changes", "No tags replaced.")
                return

            affected = 0
            for idx, img_data in enumerate(self.images):
                modified = False
                for old_tag, new_tag in replace_map.items():
                    if old_tag in img_data['tags']:
                        img_data['tags'].remove(old_tag)
                        if new_tag not in img_data['tags']:
                            img_data['tags'].append(new_tag)
                        modified = True
                if modified:
                    img_data['modified'] = True
                    self.refresh_image_tags(idx)
                    affected += 1

            self.load_all_folder_tags()
            messagebox.showinfo("Successful", f"Tag replaced on {affected} images.")
            window.destroy()
            self.load_all_folder_tags()

        tk.Button(window, text="Confirm", bg='#FF9800', fg='white',
                  font=('Arial', 10, 'bold'), command=confirm_replace).pack(pady=(10, 15))

    def display_images(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self.image_widgets.clear()
        self.tag_entries.clear()

        canvas_width = self.canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 800

        img_width = 200
        spacing = 15
        cols = self.images_per_row

        active_filters = [tag for tag, enabled in self.tag_filters.items() if enabled]

        images_with_tags = []
        images_without_tags = []

        for idx, img_data in enumerate(self.images):
            if active_filters:
                has_any_tag = any(tag in img_data['tags'] for tag in active_filters)
                if has_any_tag:
                    images_with_tags.append((idx, img_data))
                else:
                    images_without_tags.append((idx, img_data))
            else:
                images_with_tags.append((idx, img_data))

        current_grid_pos = 0

        if images_with_tags and active_filters:
            header_frame = tk.Frame(self.grid_frame, bg='#4CAF50', height=40)
            header_frame.grid(row=current_grid_pos, column=0, columnspan=cols,
                              sticky='ew', padx=5, pady=10)

            filter_text = ', '.join(active_filters)
            tk.Label(header_frame, text=f"📁 Images WITH tags: {filter_text}",
                     bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'),
                     anchor='w', padx=10).pack(fill=tk.BOTH, expand=True)

            current_grid_pos += 1

        for grid_idx, (idx, img_data) in enumerate(images_with_tags):
            row = current_grid_pos + (grid_idx // cols)
            col = grid_idx % cols
            self.create_image_widget(idx, img_data, row, col, img_width, spacing)

        if images_with_tags:
            current_grid_pos += ((len(images_with_tags) - 1) // cols) + 1

        if images_without_tags and active_filters:
            separator_frame = tk.Frame(self.grid_frame, bg='#1e1e1e', height=20)
            separator_frame.grid(row=current_grid_pos, column=0, columnspan=cols,
                                 sticky='ew', padx=5, pady=5)
            current_grid_pos += 1

            header_frame = tk.Frame(self.grid_frame, bg='#f44336', height=40)
            header_frame.grid(row=current_grid_pos, column=0, columnspan=cols,
                              sticky='ew', padx=5, pady=10)

            filter_text = ', '.join(active_filters)
            tk.Label(header_frame, text=f"📁 Images WITHOUT tags: {filter_text}",
                     bg='#f44336', fg='white', font=('Arial', 11, 'bold'),
                     anchor='w', padx=10).pack(fill=tk.BOTH, expand=True)

            current_grid_pos += 1

            for grid_idx, (idx, img_data) in enumerate(images_without_tags):
                row = current_grid_pos + (grid_idx // cols)
                col = grid_idx % cols
                self.create_image_widget(idx, img_data, row, col, img_width, spacing)

        self.grid_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def create_image_widget(self, idx, img_data, row, col, img_width, spacing):
        container = tk.Frame(self.grid_frame, bg='#2b2b2b',
                             highlightthickness=2, highlightbackground='#3c3c3c')
        container.grid(row=row, column=col, padx=spacing//2, pady=spacing//2, sticky='n')

        # create basic widget entry in case image load fails (so other code can reference)
        self.image_widgets[idx] = {'container': container}

        try:
            # robust resampling selection for different Pillow versions
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = getattr(Image, 'LANCZOS', Image.ANTIALIAS)

            with Image.open(img_data['path']) as img:
                img.thumbnail((img_width, img_width), resample)
                photo = ImageTk.PhotoImage(img.copy())

            img_label = tk.Label(container, image=photo, bg='#2b2b2b', cursor='hand2')
            img_label.image = photo
            img_label.pack()
            img_label.bind('<Button-1>', lambda e, i=idx: self.toggle_select(i))

            self.image_widgets[idx].update({'label': img_label})
        except Exception:
            tk.Label(container, text="❌ Error", bg='#2b2b2b', fg='red').pack()

        var = tk.BooleanVar(value=(idx in self.selected_images))
        chk = tk.Checkbutton(container, text="Select", variable=var, bg='#2b2b2b',
                             fg='white', selectcolor='#1e1e1e',
                             command=lambda i=idx, v=var: self.checkbox_changed(i, v))
        chk.pack()
        self.image_widgets[idx]['checkbox_var'] = var

        if idx in self.selected_images:
            container.config(highlightbackground='#4CAF50', highlightthickness=3)

        tag_frame_display = tk.Frame(container, bg='#2b2b2b')
        tag_frame_display.pack(pady=(5, 0), fill=tk.X)
        self.image_widgets[idx]['tag_display_frame'] = tag_frame_display

        if img_data['tags']:
            max_per_row = 3
            for i, tag in enumerate(img_data['tags']):
                is_active = tag in self.tag_filters and self.tag_filters[tag]
                tag_color = '#80ff80' if is_active else 'white'

                tag_label = tk.Label(tag_frame_display, text=tag,
                                     bg='#3c3c3c', fg=tag_color,
                                     font=('Arial', 10, 'bold'),
                                     padx=5, pady=2, relief='flat',
                                     wraplength=130, justify='left')
                tag_label.grid(row=i // max_per_row, column=i % max_per_row, padx=2, pady=2, sticky='w')
        else:
            tag_label = tk.Label(tag_frame_display, text="*No tags*",
                                 bg='#3c3c3c', fg='#888', font=('Arial', 9, 'italic'))
            tag_label.grid(row=0, column=0, padx=2, pady=2, sticky='w')

        tag_frame = tk.Frame(container, bg='#2b2b2b')
        tag_frame.pack(fill=tk.X, padx=5, pady=5)

        tag_entry = tk.Entry(tag_frame, font=('Arial', 9), width=15)
        tag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tag_entries[idx] = tag_entry

        add_btn = tk.Button(tag_frame, text="+", bg='#4CAF50', fg='white',
                            command=lambda i=idx: self.add_tag_individual(i),
                            font=('Arial', 8, 'bold'), width=2, cursor='hand2')
        add_btn.pack(side=tk.LEFT, padx=(2, 0))

    def toggle_select(self, idx):
        if idx not in self.image_widgets or 'checkbox_var' not in self.image_widgets[idx]:
            return
        var = self.image_widgets[idx]['checkbox_var']
        var.set(not var.get())
        self.checkbox_changed(idx, var)

    def checkbox_changed(self, idx, var):
        container = self.image_widgets.get(idx, {}).get('container')
        if not container:
            return
        if var.get():
            self.selected_images.add(idx)
            container.config(highlightbackground='#4CAF50', highlightthickness=3)
        else:
            self.selected_images.discard(idx)
            container.config(highlightbackground='#3c3c3c', highlightthickness=2)

    def add_tag_individual(self, idx):
        if idx not in self.tag_entries:
            return
        tag = self.tag_entries[idx].get().strip()
        if tag and tag not in self.images[idx]['tags']:
            self.images[idx]['tags'].append(tag)
            self.images[idx]['modified'] = True
            self.tag_entries[idx].delete(0, tk.END)
            self.refresh_image_tags(idx)

    def _on_mousewheel(self, event):
        # cross-platform scrolling
        if event.delta:
            # Windows / macOS
            delta = int(-1 * (event.delta / 120))
            self.canvas.yview_scroll(delta, "units")
        else:
            # X11, event.num = 4 (up) or 5 (down)
            if event.num == 5:
                self.canvas.yview_scroll(1, "units")
            elif event.num == 4:
                self.canvas.yview_scroll(-1, "units")

    def add_tag_to_selected(self):
        tag = self.global_tag_entry.get().strip()
        if not tag:
            messagebox.showwarning("Warning", "Please enter the tag!")
            return

        if not self.selected_images:
            messagebox.showwarning("Warning", "Please select at least one image!")
            return

        for idx in list(self.selected_images):
            if tag not in self.images[idx]['tags']:
                self.images[idx]['tags'].append(tag)
                self.images[idx]['modified'] = True
                self.refresh_image_tags(idx)

        self.global_tag_entry.delete(0, tk.END)
        messagebox.showinfo("Success", f"Added '{tag}' tag to {len(self.selected_images)} image!")
        self.deselect_all_images()
        self.load_all_folder_tags()

    def remove_tag_from_selected(self):
        tag = self.global_tag_entry.get().strip()
        if not tag:
            messagebox.showwarning("Warning", "Please enter the tag to be removed!")
            return

        if not self.selected_images:
            messagebox.showwarning("Warning", "Please select at least one image!")
            return

        count = 0
        for idx in list(self.selected_images):
            if tag in self.images[idx]['tags']:
                self.images[idx]['tags'].remove(tag)
                self.images[idx]['modified'] = True
                self.refresh_image_tags(idx)
                count += 1

        self.global_tag_entry.delete(0, tk.END)
        messagebox.showinfo("Success", f"Removed the tag '{tag}' from {count} images!")
        self.deselect_all_images()
        self.load_all_folder_tags()

    def refresh_image_tags(self, idx):
        if idx not in self.image_widgets or 'tag_display_frame' not in self.image_widgets[idx]:
            return

        frame = self.image_widgets[idx]['tag_display_frame']
        for child in frame.winfo_children():
            child.destroy()

        tags = self.images[idx]['tags']

        if tags:
            max_per_row = 3
            for i, tag in enumerate(tags):
                is_active = self.tag_filters.get(tag, False)
                color = '#80ff80' if is_active else 'white'
                lbl = tk.Label(frame, text=tag, bg='#3c3c3c', fg=color,
                               font=('Arial', 10, 'bold'), padx=5, pady=2)
                lbl.grid(row=i // max_per_row, column=i % max_per_row, padx=2, pady=2, sticky='w')
        else:
            lbl = tk.Label(frame, text="*No tags*", bg='#3c3c3c', fg='#888',
                           font=('Arial', 9, 'italic'))
            lbl.grid(row=0, column=0, padx=2, pady=2, sticky='w')

    def save_all(self):
        saved_count = 0
        for img_data in self.images:
            if img_data.get('modified', False):
                try:
                    with open(img_data['txt_path'], 'w', encoding='utf-8') as f:
                        f.write(', '.join(img_data['tags']))
                    img_data['modified'] = False
                    saved_count += 1
                except Exception:
                    pass

        if saved_count > 0:
            messagebox.showinfo("Success", f"Saved {saved_count} file tags!")
        else:
            messagebox.showinfo("Notifications", "No changes to save!")

    def show_about(self):

        link_url = "https://github.com/Quocraft1436/TKtagger"

        def open_github(event=None):
            webbrowser.open(link_url)
        
        about = tk.Toplevel(root)
        about.title("About")
        about.geometry("360x220")
        about.resizable(False, False)

        tk.Label(about, text="TK-tagger", font=("Arial", 16, "bold")).pack(pady=(12, 4))

        tk.Label(about, text="Quocraft_AI / Quocraft 1436", font=("Arial", 10)).pack(pady=(8, 2))

        github = tk.Label(about, text=link_url, font=("Arial", 10), fg="blue", cursor="hand2")
        github.pack()
        github.bind("<Button-1>", open_github)

        tk.Label(about, text="Version 1.0 (Demo)", font=("Arial", 10)).pack(pady=(8, 2))

        tk.Label(about, text="License: MIT", font=("Arial", 9, "italic")).pack(pady=(0, 10))

        tk.Label(
            about,
            text="© 2025 — Open-source. Danbrou Tagger (reference).",
            font=("Arial", 9),
            wraplength=320,
            justify="center"
        ).pack(pady=(2, 4))


        tk.Button(about, text="Close", command=about.destroy).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = DanbooruTagger(root)
    root.mainloop()
