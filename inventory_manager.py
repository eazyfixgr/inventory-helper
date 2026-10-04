#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inventory Manager Pro - Διαχείριση Αποθέματος
Δυναμικό σύστημα με παραμετροποιήσιμα πεδία
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


class ToolTip:
    """Κλάση για δημιουργία tooltips"""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#2c3e50", foreground="white",
                        relief=tk.SOLID, borderwidth=1,
                        font=("Segoe UI", 9), padx=8, pady=4)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class InventoryManager:
    def __init__(self, root):
        self.root = root
        self.root.title("📦 Inventory Manager Pro - Διαχείριση Αποθέματος")

        # Settings file
        self.settings_file = "app_settings.json"

        # Load window state
        self.load_window_state()

        self.root.configure(bg='#f0f0f0')

        # Database
        self.db_file = "inventory.db"
        self.init_database()

        # Load configuration
        self.load_config()

        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 50

        # Create UI
        self.create_ui()
        self.refresh_table()

        # Save window state on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Keyboard shortcuts for undo/redo
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-Z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        self.root.bind('<Control-Y>', lambda e: self.redo())
        
    def load_window_state(self):
        """Φόρτωση κατάστασης παραθύρου από settings"""
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                geometry = settings.get('window_geometry', '1400x800+100+50')
                self.root.geometry(geometry)
        except (FileNotFoundError, json.JSONDecodeError):
            # Default geometry
            self.root.geometry("1400x800")
            # Center window
            self.root.update_idletasks()
            x = (self.root.winfo_screenwidth() // 2) - (1400 // 2)
            y = (self.root.winfo_screenheight() // 2) - (800 // 2)
            self.root.geometry(f"1400x800+{x}+{y}")

    def save_window_state(self):
        """Αποθήκευση κατάστασης παραθύρου"""
        try:
            settings = {}
            # Load existing settings
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            # Save window geometry
            settings['window_geometry'] = self.root.geometry()

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass  # Silent fail

    def on_closing(self):
        """Κλείσιμο εφαρμογής"""
        self.save_window_state()
        self.conn.close()
        self.root.destroy()

    def init_database(self):
        """Αρχικοποίηση βάσης δεδομένων"""
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        
        # Πίνακας ρυθμίσεων πεδίων
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS field_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field_name TEXT UNIQUE,
                field_label TEXT,
                field_type TEXT,
                field_options TEXT,
                field_order INTEGER,
                is_required INTEGER,
                is_searchable INTEGER
            )
        ''')
        
        # Πίνακας δεδομένων (δυναμική δομή)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Έλεγχος αν υπάρχουν προεπιλεγμένα πεδία
        self.cursor.execute("SELECT COUNT(*) FROM field_config")
        if self.cursor.fetchone()[0] == 0:
            self.create_default_fields()
        
        self.conn.commit()
    
    def create_default_fields(self):
        """Δημιουργία προεπιλεγμένων πεδίων"""
        default_fields = [
            ("code", "Κωδικός", "text", "", 1, 1, 1),
            ("name", "Όνομα Προϊόντος", "text", "", 2, 1, 1),
            ("category", "Κατηγορία", "dropdown", json.dumps(["Ηλεκτρονικά", "Εργαλεία", "Είδη Γραφείου", "Ανταλλακτικά", "Λοιπά"]), 3, 0, 1),
            ("quantity", "Τεμάχια", "number", "", 4, 1, 1),
            ("min_stock", "Ελάχ. Απόθεμα", "number", "", 5, 0, 0),
            ("price", "Τιμή Μονάδας (€)", "number", "", 6, 0, 0),
            ("warehouse", "Αποθήκη", "dropdown", json.dumps(["Κεντρική Αποθήκη", "Δευτερεύουσα", "Εκθεσιακός Χώρος"]), 7, 1, 1),
            ("location", "Θέση Ραφιού", "text", "", 8, 0, 1),
            ("supplier", "Προμηθευτής", "text", "", 9, 0, 1),
            ("notes", "Σημειώσεις", "textarea", "", 10, 0, 1),
        ]
        
        for field in default_fields:
            self.cursor.execute('''
                INSERT INTO field_config 
                (field_name, field_label, field_type, field_options, field_order, is_required, is_searchable)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', field)
        
        self.conn.commit()
    
    def load_config(self):
        """Φόρτωση ρυθμίσεων πεδίων"""
        self.cursor.execute('''
            SELECT field_name, field_label, field_type, field_options, is_required, is_searchable
            FROM field_config
            ORDER BY field_order
        ''')
        
        self.fields = []
        for row in self.cursor.fetchall():
            field = {
                'name': row[0],
                'label': row[1],
                'type': row[2],
                'options': json.loads(row[3]) if row[3] else [],
                'required': bool(row[4]),
                'searchable': bool(row[5])
            }
            self.fields.append(field)
    
    def create_ui(self):
        """Δημιουργία γραφικού περιβάλλοντος"""
        
        # === TOP TOOLBAR ===
        toolbar = tk.Frame(self.root, bg='#2c3e50', height=60)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        
        # Τίτλος
        title = tk.Label(toolbar, text="📦 Inventory Manager Pro",
                        font=('Segoe UI', 16, 'bold'),
                        bg='#2c3e50', fg='white')
        title.pack(side=tk.LEFT, padx=20, pady=10)

        # Keyboard shortcuts hint
        shortcuts_hint = tk.Label(toolbar, text="💡 Ctrl+N: Νέο | Ctrl+E: Επεξεργασία | Delete: Διαγραφή | Ctrl+F: Αναζήτηση | Ctrl+R: Reset Φίλτρα",
                                 font=('Segoe UI', 8), bg='#2c3e50', fg='#95a5a6')
        shortcuts_hint.pack(side=tk.BOTTOM, anchor='w', padx=20, pady=(0, 5))
        
        # Κουμπιά
        btn_style = {'font': ('Segoe UI', 10), 'bg': '#3498db', 'fg': 'white',
                     'relief': tk.FLAT, 'padx': 15, 'pady': 8, 'cursor': 'hand2'}

        btn_new = tk.Button(toolbar, text="➕ Νέο Προϊόν", command=self.add_item, **btn_style)
        btn_new.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_new, "Προσθήκη νέου προϊόντος (Ctrl+N)")

        btn_edit = tk.Button(toolbar, text="✏️ Επεξεργασία", command=self.edit_item, **btn_style)
        btn_edit.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_edit, "Επεξεργασία επιλεγμένου προϊόντος (Ctrl+E)")

        btn_delete = tk.Button(toolbar, text="🗑️ Διαγραφή", command=self.delete_item,
                 bg='#e74c3c', fg='white', font=('Segoe UI', 10),
                 relief=tk.FLAT, padx=15, pady=8, cursor='hand2')
        btn_delete.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_delete, "Διαγραφή επιλεγμένου προϊόντος (Delete)")
        
        # Export/Import Menu Button
        export_menu_btn = tk.Menubutton(toolbar, text="📊 Εξαγωγή ▼",
                                       bg='#27ae60', fg='white', font=('Segoe UI', 10),
                                       relief=tk.FLAT, padx=15, pady=8, cursor='hand2')
        export_menu_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(export_menu_btn, "Εξαγωγή δεδομένων σε Excel, CSV, JSON")

        export_menu = tk.Menu(export_menu_btn, tearoff=0, font=('Segoe UI', 10))
        export_menu_btn.config(menu=export_menu)
        export_menu.add_command(label="📊 Export σε Excel (.xlsx)", command=self.export_to_excel)
        export_menu.add_command(label="📄 Export σε CSV", command=self.export_to_csv)
        export_menu.add_command(label="💾 Export σε JSON (Backup)", command=self.export_to_json)
        export_menu.add_separator()
        export_menu.add_command(label="📋 Αντιγραφή στο Clipboard", command=self.copy_to_clipboard)

        import_menu_btn = tk.Menubutton(toolbar, text="📥 Εισαγωγή ▼",
                                       bg='#3498db', fg='white', font=('Segoe UI', 10),
                                       relief=tk.FLAT, padx=15, pady=8, cursor='hand2')
        import_menu_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(import_menu_btn, "Εισαγωγή δεδομένων από Excel, CSV, JSON")

        import_menu = tk.Menu(import_menu_btn, tearoff=0, font=('Segoe UI', 10))
        import_menu_btn.config(menu=import_menu)
        import_menu.add_command(label="📊 Import από Excel (.xlsx)", command=self.import_from_excel)
        import_menu.add_command(label="📄 Import από CSV", command=self.import_from_csv)
        import_menu.add_command(label="💾 Import από JSON (Restore)", command=self.import_from_json)
        import_menu.add_separator()
        import_menu.add_command(label="📋 Επικόλληση από Clipboard", command=self.paste_from_clipboard)

        btn_settings = tk.Button(toolbar, text="⚙️ Ρυθμίσεις Πεδίων", command=self.open_field_settings,
                 bg='#f39c12', fg='white', font=('Segoe UI', 10),
                 relief=tk.FLAT, padx=15, pady=8, cursor='hand2')
        btn_settings.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_settings, "Προσθήκη/Επεξεργασία προσαρμοσμένων πεδίων")

        # Bulk Actions Menu
        bulk_menu_btn = tk.Menubutton(toolbar, text="📋 Μαζικές Ενέργειες ▼",
                                      bg='#9b59b6', fg='white', font=('Segoe UI', 10),
                                      relief=tk.FLAT, padx=15, pady=8, cursor='hand2')
        bulk_menu_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(bulk_menu_btn, "Μαζικές ενέργειες σε πολλαπλά προϊόντα")

        bulk_menu = tk.Menu(bulk_menu_btn, tearoff=0, font=('Segoe UI', 10))
        bulk_menu_btn.config(menu=bulk_menu)
        bulk_menu.add_command(label="🗑️ Μαζική Διαγραφή", command=self.bulk_delete)
        bulk_menu.add_separator()
        bulk_menu.add_command(label="📁 Αλλαγή Κατηγορίας", command=lambda: self.bulk_update_field('category'))
        bulk_menu.add_command(label="🏭 Αλλαγή Αποθήκης", command=lambda: self.bulk_update_field('warehouse'))
        bulk_menu.add_separator()
        bulk_menu.add_command(label="✅ Επιλογή Όλων", command=self.select_all)
        bulk_menu.add_command(label="❌ Αποεπιλογή Όλων", command=self.deselect_all)
        
        # === SEARCH PANEL ===
        search_frame = tk.Frame(self.root, bg='white', relief=tk.RIDGE, bd=2)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_frame, text="🔍 Αναζήτηση:", 
                font=('Segoe UI', 11, 'bold'), bg='white').pack(side=tk.LEFT, padx=10, pady=10)
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *args: self.search_items())

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               font=('Segoe UI', 11), width=50,
                               relief=tk.FLAT, bg='#ecf0f1')
        self.search_entry.pack(side=tk.LEFT, padx=5, pady=10, ipady=5)
        
        # Στατιστικά
        self.stats_label = tk.Label(search_frame, text="",
                                    font=('Segoe UI', 10), bg='white', fg='#7f8c8d')
        self.stats_label.pack(side=tk.RIGHT, padx=20, pady=10)

        # === FILTERS PANEL ===
        filters_frame = tk.Frame(self.root, bg='white', relief=tk.RIDGE, bd=2)
        filters_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(filters_frame, text="🔧 Φίλτρα:",
                font=('Segoe UI', 10, 'bold'), bg='white').pack(side=tk.LEFT, padx=10, pady=8)

        # Κατηγορία Filter
        tk.Label(filters_frame, text="Κατηγορία:", font=('Segoe UI', 9), bg='white').pack(side=tk.LEFT, padx=(10, 5))
        self.filter_category_var = tk.StringVar(value="Όλες")
        self.filter_category = ttk.Combobox(filters_frame, textvariable=self.filter_category_var,
                                            font=('Segoe UI', 9), width=18, state='readonly')
        self.filter_category['values'] = ["Όλες"]
        self.filter_category.pack(side=tk.LEFT, padx=5, pady=8)
        self.filter_category.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())

        # Αποθήκη Filter
        tk.Label(filters_frame, text="Αποθήκη:", font=('Segoe UI', 9), bg='white').pack(side=tk.LEFT, padx=(10, 5))
        self.filter_warehouse_var = tk.StringVar(value="Όλες")
        self.filter_warehouse = ttk.Combobox(filters_frame, textvariable=self.filter_warehouse_var,
                                             font=('Segoe UI', 9), width=18, state='readonly')
        self.filter_warehouse['values'] = ["Όλες"]
        self.filter_warehouse.pack(side=tk.LEFT, padx=5, pady=8)
        self.filter_warehouse.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())

        # Χαμηλό Απόθεμα Checkbox
        self.filter_low_stock_var = tk.BooleanVar(value=False)
        low_stock_cb = tk.Checkbutton(filters_frame, text="Μόνο Χαμηλό Απόθεμα",
                                      variable=self.filter_low_stock_var, font=('Segoe UI', 9),
                                      bg='white', command=self.apply_filters)
        low_stock_cb.pack(side=tk.LEFT, padx=10)

        # Price Range Filter
        tk.Label(filters_frame, text="Τιμή:", font=('Segoe UI', 9), bg='white').pack(side=tk.LEFT, padx=(10, 5))
        self.filter_price_min_var = tk.StringVar()
        tk.Entry(filters_frame, textvariable=self.filter_price_min_var, font=('Segoe UI', 9),
                width=8, relief=tk.FLAT, bg='#f9f9f9').pack(side=tk.LEFT, padx=2)
        tk.Label(filters_frame, text="-", font=('Segoe UI', 9), bg='white').pack(side=tk.LEFT)
        self.filter_price_max_var = tk.StringVar()
        tk.Entry(filters_frame, textvariable=self.filter_price_max_var, font=('Segoe UI', 9),
                width=8, relief=tk.FLAT, bg='#f9f9f9').pack(side=tk.LEFT, padx=2)
        tk.Label(filters_frame, text="€", font=('Segoe UI', 9), bg='white').pack(side=tk.LEFT)

        # Apply Price Filter Button
        btn_apply_price = tk.Button(filters_frame, text="🔍", command=self.apply_filters,
                                    font=('Segoe UI', 9), bg='#3498db', fg='white',
                                    relief=tk.FLAT, padx=8, pady=3, cursor='hand2')
        btn_apply_price.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_apply_price, "Εφαρμογή φίλτρου τιμής")

        # Clear Filters Button
        btn_clear_filters = tk.Button(filters_frame, text="🔄 Καθαρισμός Φίλτρων", command=self.clear_filters,
                 font=('Segoe UI', 9), bg='#e67e22', fg='white',
                 relief=tk.FLAT, padx=12, pady=5, cursor='hand2')
        btn_clear_filters.pack(side=tk.LEFT, padx=10)
        ToolTip(btn_clear_filters, "Καθαρισμός όλων των φίλτρων και αναζήτησης (Ctrl+R)")

        # Populate filter options
        self.populate_filter_options()

        # === MAIN TABLE ===
        table_frame = tk.Frame(self.root, bg='white')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        # Treeview (με multi-select)
        columns = [field['label'] for field in self.fields]
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                 yscrollcommand=v_scroll.set,
                                 xscrollcommand=h_scroll.set,
                                 selectmode='extended')
        
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)
        
        # Headings (με sorting)
        for col in columns:
            self.tree.heading(col, text=col, anchor=tk.W,
                            command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=150, minwidth=100)
        
        # Layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Double-click για επεξεργασία
        self.tree.bind('<Double-1>', lambda e: self.edit_item())
        
        # Styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', 
                       background='white',
                       foreground='black',
                       rowheight=30,
                       fieldbackground='white',
                       font=('Segoe UI', 10))
        style.configure('Treeview.Heading',
                       font=('Segoe UI', 10, 'bold'),
                       background='#34495e',
                       foreground='white')
        style.map('Treeview', background=[('selected', '#3498db')])

        # Keyboard Shortcuts
        self.root.bind('<Control-n>', lambda e: self.add_item())
        self.root.bind('<Control-N>', lambda e: self.add_item())
        self.root.bind('<Control-e>', lambda e: self.edit_item())
        self.root.bind('<Control-E>', lambda e: self.edit_item())
        self.root.bind('<Delete>', lambda e: self.delete_item())
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus())
        self.root.bind('<Control-F>', lambda e: self.search_entry.focus())
        self.root.bind('<Control-r>', lambda e: self.clear_filters())
        self.root.bind('<Control-R>', lambda e: self.clear_filters())
    
    def populate_filter_options(self):
        """Γεμίζει τα filter dropdowns με τις διαθέσιμες επιλογές από τα δεδομένα"""
        # Βρες τα πεδία category και warehouse
        category_field = None
        warehouse_field = None

        for field in self.fields:
            if field['name'] == 'category':
                category_field = field
            elif field['name'] == 'warehouse':
                warehouse_field = field

        # Populate category options
        if category_field and category_field.get('options'):
            self.filter_category['values'] = ["Όλες"] + category_field['options']
        else:
            # Fallback: get unique values from data
            self.cursor.execute("SELECT data FROM items")
            categories = set()
            for row in self.cursor.fetchall():
                data = json.loads(row[0])
                if 'category' in data and data['category']:
                    categories.add(data['category'])
            self.filter_category['values'] = ["Όλες"] + sorted(categories)

        # Populate warehouse options
        if warehouse_field and warehouse_field.get('options'):
            self.filter_warehouse['values'] = ["Όλες"] + warehouse_field['options']
        else:
            # Fallback: get unique values from data
            self.cursor.execute("SELECT data FROM items")
            warehouses = set()
            for row in self.cursor.fetchall():
                data = json.loads(row[0])
                if 'warehouse' in data and data['warehouse']:
                    warehouses.add(data['warehouse'])
            self.filter_warehouse['values'] = ["Όλες"] + sorted(warehouses)

    def apply_filters(self):
        """Εφαρμογή φίλτρων στον πίνακα"""
        self.search_items()  # Χρησιμοποιεί το search_items που ήδη υποστηρίζει φίλτρα

    def clear_filters(self):
        """Καθαρισμός όλων των φίλτρων"""
        self.filter_category_var.set("Όλες")
        self.filter_warehouse_var.set("Όλες")
        self.filter_low_stock_var.set(False)
        self.filter_price_min_var.set("")
        self.filter_price_max_var.set("")
        self.search_var.set("")
        self.apply_filters()

    def refresh_columns(self):
        """Ανανέωση στηλών Treeview μετά από αλλαγή πεδίων"""
        # Νέες στήλες
        columns = [field['label'] for field in self.fields]
        self.tree['columns'] = columns

        # Ανανέωση headings
        for col in columns:
            self.tree.heading(col, text=col, anchor=tk.W,
                            command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=150, minwidth=100)

        # Auto-adjust column widths
        self.auto_adjust_columns()

    def auto_adjust_columns(self):
        """Αυτόματη προσαρμογή πλάτους στηλών βάσει περιεχομένου"""
        font = ('Segoe UI', 10)

        for col_idx, field in enumerate(self.fields):
            col_name = field['label']

            # Υπολογισμός μέγιστου πλάτους
            max_width = len(col_name) * 8  # Header width

            # Έλεγχος περιεχομένου
            for item in self.tree.get_children():
                try:
                    cell_value = str(self.tree.set(item, col_name))
                    cell_width = len(cell_value) * 8
                    max_width = max(max_width, cell_width)
                except:
                    pass

            # Όρια: min 100px, max 400px
            adjusted_width = min(max(max_width + 20, 100), 400)
            self.tree.column(col_name, width=adjusted_width)

    def refresh_table(self):
        """Ανανέωση πίνακα"""
        # Ανανέωση filter options (σε περίπτωση που προστέθηκαν νέες κατηγορίες/αποθήκες)
        if hasattr(self, 'filter_category'):
            self.populate_filter_options()

        # Καθαρισμός
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Φόρτωση δεδομένων
        self.cursor.execute("SELECT id, data FROM items ORDER BY updated_at DESC")
        rows = self.cursor.fetchall()

        for row in rows:
            item_id, data_json = row
            data = json.loads(data_json)

            values = []
            for field in self.fields:
                value = data.get(field['name'], '')
                values.append(value)

            # Χρωματισμός χαμηλού αποθέματος
            tag = ''
            if 'quantity' in data and 'min_stock' in data:
                try:
                    qty = float(data.get('quantity', 0))
                    min_stock = float(data.get('min_stock', 0))
                    if qty < min_stock:
                        tag = 'low_stock'
                except ValueError:
                    pass

            self.tree.insert('', tk.END, values=values, iid=item_id, tags=(tag,))

        self.tree.tag_configure('low_stock', background='#ffcccc')

        # Auto-adjust column widths
        self.auto_adjust_columns()

        # Ενημέρωση στατιστικών
        self.update_stats()
    
    def update_stats(self, filtered_count=None):
        """Ενημέρωση στατιστικών"""
        displayed_items = len(self.tree.get_children())

        # Υπολογισμός συνολικών τεμαχίων
        total_quantity = 0
        low_stock_count = 0

        self.cursor.execute("SELECT data FROM items")
        all_items = self.cursor.fetchall()
        total_items = len(all_items)

        for row in all_items:
            data = json.loads(row[0])
            try:
                qty = float(data.get('quantity', 0))
                total_quantity += qty

                min_stock = float(data.get('min_stock', 0))
                if qty < min_stock:
                    low_stock_count += 1
            except (ValueError, TypeError):
                pass

        # Στατιστικά με filtered count
        if filtered_count is not None:
            stats_text = f"🔍 Εμφανίζονται: {filtered_count} από {total_items} | "
        else:
            stats_text = f"📊 Σύνολο Ειδών: {total_items} | "
        stats_text += f"📦 Σύνολο Τεμαχίων: {int(total_quantity)} | "
        stats_text += f"⚠️ Χαμηλό Απόθεμα: {low_stock_count}"

        self.stats_label.config(text=stats_text)

    def sort_by_column(self, col_name):
        """Ταξινόμηση πίνακα με click σε column header"""
        # Εύρεση index της στήλης
        col_idx = None
        for i, field in enumerate(self.fields):
            if field['label'] == col_name:
                col_idx = i
                break

        if col_idx is None:
            return

        # Λήψη όλων των items
        items = [(self.tree.set(item, col_name), item) for item in self.tree.get_children('')]

        # Ταξινόμηση (αριθμητική αν είναι number field, αλλιώς αλφαβητική)
        field_type = self.fields[col_idx]['type']
        if field_type == 'number':
            # Ταξινόμηση ως αριθμός
            items.sort(key=lambda x: float(x[0]) if x[0] and x[0].replace('.', '', 1).replace('-', '', 1).isdigit() else 0)
        else:
            # Αλφαβητική ταξινόμηση
            items.sort(key=lambda x: x[0].lower())

        # Toggle reverse sorting
        if not hasattr(self, '_sort_reverse'):
            self._sort_reverse = {}

        col_key = col_name
        self._sort_reverse[col_key] = not self._sort_reverse.get(col_key, False)

        if self._sort_reverse[col_key]:
            items.reverse()

        # Ανακατανομή items
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)

    def search_items(self):
        """Αναζήτηση και φιλτράρισμα σε πραγματικό χρόνο"""
        search_term = self.search_var.get().lower()

        # Λήψη φίλτρων
        filter_category = self.filter_category_var.get() if hasattr(self, 'filter_category_var') else "Όλες"
        filter_warehouse = self.filter_warehouse_var.get() if hasattr(self, 'filter_warehouse_var') else "Όλες"
        filter_low_stock = self.filter_low_stock_var.get() if hasattr(self, 'filter_low_stock_var') else False

        # Price range filters
        filter_price_min = self.filter_price_min_var.get() if hasattr(self, 'filter_price_min_var') else ""
        filter_price_max = self.filter_price_max_var.get() if hasattr(self, 'filter_price_max_var') else ""

        # Convert price filters to float
        try:
            price_min = float(filter_price_min) if filter_price_min else None
        except ValueError:
            price_min = None

        try:
            price_max = float(filter_price_max) if filter_price_max else None
        except ValueError:
            price_max = None

        # Καθαρισμός
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Φόρτωση όλων των δεδομένων
        self.cursor.execute("SELECT id, data FROM items")
        rows = self.cursor.fetchall()

        matched_count = 0
        total_count = len(rows)

        for row in rows:
            item_id, data_json = row
            data = json.loads(data_json)

            # === Έλεγχος Search Term ===
            search_match = False
            if not search_term:
                search_match = True
            else:
                for field in self.fields:
                    if field['searchable']:
                        value = str(data.get(field['name'], '')).lower()
                        if search_term in value:
                            search_match = True
                            break

            # === Έλεγχος Category Filter ===
            category_match = True
            if filter_category != "Όλες":
                category_match = data.get('category', '') == filter_category

            # === Έλεγχος Warehouse Filter ===
            warehouse_match = True
            if filter_warehouse != "Όλες":
                warehouse_match = data.get('warehouse', '') == filter_warehouse

            # === Έλεγχος Low Stock Filter ===
            low_stock_match = True
            is_low_stock = False
            if 'quantity' in data and 'min_stock' in data:
                try:
                    qty = float(data.get('quantity', 0))
                    min_stock = float(data.get('min_stock', 0))
                    is_low_stock = qty < min_stock
                except (ValueError, TypeError):
                    pass

            if filter_low_stock:
                low_stock_match = is_low_stock

            # === Έλεγχος Price Range Filter ===
            price_match = True
            if price_min is not None or price_max is not None:
                if 'price' in data:
                    try:
                        item_price = float(data.get('price', 0))
                        if price_min is not None and item_price < price_min:
                            price_match = False
                        if price_max is not None and item_price > price_max:
                            price_match = False
                    except (ValueError, TypeError):
                        price_match = False
                else:
                    price_match = False

            # === Εμφάνιση αν ταιριάζει σε όλα τα φίλτρα ===
            if search_match and category_match and warehouse_match and low_stock_match and price_match:
                values = [data.get(field['name'], '') for field in self.fields]

                tag = 'low_stock' if is_low_stock else ''
                self.tree.insert('', tk.END, values=values, iid=item_id, tags=(tag,))
                matched_count += 1

        self.tree.tag_configure('low_stock', background='#ffcccc')

        # Auto-adjust column widths
        self.auto_adjust_columns()

        # Ενημέρωση στατιστικών με filtered count
        filters_active = (search_term or filter_category != "Όλες" or
                         filter_warehouse != "Όλες" or filter_low_stock or
                         price_min is not None or price_max is not None)
        self.update_stats(filtered_count=matched_count if filters_active else None)
    
    def add_item(self):
        """Προσθήκη νέου προϊόντος"""
        ItemDialog(self, None, self.fields, self.refresh_table)
    
    def edit_item(self):
        """Επεξεργασία επιλεγμένου προϊόντος"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Προειδοποίηση", "Επίλεξε ένα προϊόν για επεξεργασία")
            return
        
        item_id = selected[0]
        self.cursor.execute("SELECT data FROM items WHERE id = ?", (item_id,))
        data_json = self.cursor.fetchone()[0]
        data = json.loads(data_json)
        
        ItemDialog(self, item_id, self.fields, self.refresh_table, data)
    
    def delete_item(self):
        """Διαγραφή επιλεγμένου προϊόντος"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Προειδοποίηση", "Επίλεξε ένα προϊόν για διαγραφή")
            return

        count = len(selected)
        msg = f"Είσαι σίγουρος ότι θέλεις να διαγράψεις {count} προϊόν(τα);" if count > 1 else "Είσαι σίγουρος ότι θέλεις να διαγράψεις αυτό το προϊόν;"

        if messagebox.askyesno("Επιβεβαίωση", msg):
            for item_id in selected:
                self.cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            self.conn.commit()
            self.refresh_table()

    def bulk_delete(self):
        """Μαζική διαγραφή επιλεγμένων προϊόντων"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Προειδοποίηση", "Επίλεξε προϊόντα για μαζική διαγραφή")
            return

        count = len(selected)
        if messagebox.askyesno("Επιβεβαίωση Μαζικής Διαγραφής",
                              f"⚠️ ΠΡΟΣΟΧΗ!\n\n"
                              f"Θα διαγραφούν {count} προϊόντα.\n\n"
                              f"Συνέχεια;"):
            for item_id in selected:
                self.cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            self.conn.commit()
            self.refresh_table()
            messagebox.showinfo("Επιτυχία", f"✅ Διαγράφηκαν {count} προϊόντα!")

    def bulk_update_field(self, field_name):
        """Μαζική ενημέρωση πεδίου για επιλεγμένα προϊόντα"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Προειδοποίηση", "Επίλεξε προϊόντα για ενημέρωση")
            return

        # Βρες το πεδίο
        field = None
        for f in self.fields:
            if f['name'] == field_name:
                field = f
                break

        if not field:
            return

        # Δημιουργία dialog για επιλογή νέας τιμής
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Μαζική Αλλαγή - {field['label']}")
        dialog.geometry("400x200")
        dialog.configure(bg='#ecf0f1')
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text=f"Αλλαγή {field['label']} για {len(selected)} προϊόντα",
                font=('Segoe UI', 12, 'bold'), bg='#ecf0f1').pack(pady=20)

        tk.Label(dialog, text=f"Επίλεξε νέο {field['label']}:",
                font=('Segoe UI', 10), bg='#ecf0f1').pack(pady=10)

        if field['type'] == 'dropdown':
            new_value_var = tk.StringVar()
            combo = ttk.Combobox(dialog, textvariable=new_value_var,
                                values=field['options'], font=('Segoe UI', 10),
                                state='readonly', width=30)
            combo.pack(pady=10)
            if field['options']:
                combo.set(field['options'][0])
        else:
            new_value_var = tk.StringVar()
            entry = tk.Entry(dialog, textvariable=new_value_var,
                           font=('Segoe UI', 10), width=30)
            entry.pack(pady=10)

        def apply_update():
            new_value = new_value_var.get()
            if not new_value:
                messagebox.showerror("Σφάλμα", "Εισάγε μια τιμή!")
                return

            # Ενημέρωση όλων των επιλεγμένων
            for item_id in selected:
                self.cursor.execute("SELECT data FROM items WHERE id = ?", (item_id,))
                row = self.cursor.fetchone()
                if row:
                    data = json.loads(row[0])
                    data[field_name] = new_value
                    data_json = json.dumps(data, ensure_ascii=False)
                    self.cursor.execute(
                        "UPDATE items SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (data_json, item_id)
                    )

            self.conn.commit()
            self.refresh_table()
            dialog.destroy()
            messagebox.showinfo("Επιτυχία",
                              f"✅ Ενημερώθηκαν {len(selected)} προϊόντα!")

        btn_frame = tk.Frame(dialog, bg='#ecf0f1')
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="✅ Εφαρμογή", command=apply_update,
                 font=('Segoe UI', 10, 'bold'), bg='#27ae60', fg='white',
                 relief=tk.FLAT, padx=20, pady=8).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="❌ Ακύρωση", command=dialog.destroy,
                 font=('Segoe UI', 10), bg='#95a5a6', fg='white',
                 relief=tk.FLAT, padx=20, pady=8).pack(side=tk.LEFT, padx=5)

    def select_all(self):
        """Επιλογή όλων των items"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)

    def deselect_all(self):
        """Αποεπιλογή όλων"""
        self.tree.selection_remove(self.tree.get_children())
    
    def get_items_to_export(self):
        """Επιστρέφει τα items προς εξαγωγή (όλα ή filtered)"""
        displayed_count = len(self.tree.get_children())

        # Μέτρηση συνολικών items
        self.cursor.execute("SELECT COUNT(*) FROM items")
        total_count = self.cursor.fetchone()[0]

        export_filtered = False

        # Αν υπάρχουν ενεργά φίλτρα, ρώτα τον χρήστη
        if displayed_count < total_count:
            response = messagebox.askyesnocancel(
                "Επιλογή Εξαγωγής",
                f"Έχεις ενεργά φίλτρα.\n\n"
                f"• ΝΑΙ: Εξαγωγή μόνο εμφανιζόμενων ({displayed_count} προϊόντα)\n"
                f"• ΟΧΙ: Εξαγωγή όλων ({total_count} προϊόντα)\n"
                f"• ΑΚΥΡΟ: Ακύρωση"
            )

            if response is None:  # Cancel
                return None

            export_filtered = response  # True = filtered, False = all

        if export_filtered:
            # Εξαγωγή μόνο των εμφανιζόμενων items
            items = []
            for item_id in self.tree.get_children():
                self.cursor.execute("SELECT data FROM items WHERE id = ?", (item_id,))
                row = self.cursor.fetchone()
                if row:
                    items.append(json.loads(row[0]))
            return items
        else:
            # Εξαγωγή όλων των items
            self.cursor.execute("SELECT data FROM items ORDER BY updated_at DESC")
            return [json.loads(row[0]) for row in self.cursor.fetchall()]

    def export_to_excel(self):
        """Export δεδομένων σε Excel με πλήρη υποστήριξη ελληνικών και custom πεδίων"""
        # Λήψη items προς εξαγωγή
        items_data = self.get_items_to_export()
        if items_data is None:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"Inventory_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

        if not filename:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Αποθέματα"
            
            # Headers - Χρήση των custom labels
            headers = [field['label'] for field in self.fields]
            ws.append(headers)
            
            # Styling headers
            header_fill = PatternFill(start_color="0066CC", end_color="0066CC", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            border = Border(left=Side(style='thin'), right=Side(style='thin'),
                           top=Side(style='thin'), bottom=Side(style='thin'))
            
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col)
                cell.fill = header_fill
                cell.font = header_font
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center')

            # Data - Χρήση των items προς εξαγωγή
            for data in items_data:
                values = [data.get(field['name'], '') for field in self.fields]
                ws.append(values)
                
                # Border για κάθε κελί
                row_num = ws.max_row
                for col in range(1, len(headers) + 1):
                    ws.cell(row=row_num, column=col).border = border
            
            # Column widths - Αυτόματο
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except (TypeError, AttributeError):
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column].width = adjusted_width
            
            wb.save(filename)
            messagebox.showinfo("Επιτυχία", f"✅ Τα δεδομένα εξήχθησαν επιτυχώς!\n\n{filename}")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία εξαγωγής:\n{str(e)}")
    
    def export_to_csv(self):
        """Export σε CSV με υποστήριξη ελληνικών"""
        # Λήψη items προς εξαγωγή
        items_data = self.get_items_to_export()
        if items_data is None:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"Inventory_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        if not filename:
            return

        try:
            import csv

            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)

                # Headers
                headers = [field['label'] for field in self.fields]
                writer.writerow(headers)

                # Data
                for data in items_data:
                    values = [data.get(field['name'], '') for field in self.fields]
                    writer.writerow(values)
            
            messagebox.showinfo("Επιτυχία", f"✅ Τα δεδομένα εξήχθησαν σε CSV!\n\n{filename}")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία εξαγωγής:\n{str(e)}")
    
    def export_to_json(self):
        """Export σε JSON (πλήρες backup με configuration)"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"Inventory_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if not filename:
            return
        
        try:
            # Export field configuration
            self.cursor.execute('''
                SELECT field_name, field_label, field_type, field_options, 
                       field_order, is_required, is_searchable
                FROM field_config ORDER BY field_order
            ''')
            field_config = []
            for row in self.cursor.fetchall():
                field_config.append({
                    'name': row[0],
                    'label': row[1],
                    'type': row[2],
                    'options': json.loads(row[3]) if row[3] else [],
                    'order': row[4],
                    'required': bool(row[5]),
                    'searchable': bool(row[6])
                })
            
            # Export items
            self.cursor.execute("SELECT id, data, created_at, updated_at FROM items")
            items = []
            for row in self.cursor.fetchall():
                items.append({
                    'id': row[0],
                    'data': json.loads(row[1]),
                    'created_at': row[2],
                    'updated_at': row[3]
                })
            
            # Create backup
            backup = {
                'version': '1.0',
                'export_date': datetime.now().isoformat(),
                'field_config': field_config,
                'items': items
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(backup, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("Επιτυχία", 
                              f"✅ Πλήρες backup δημιουργήθηκε!\n\n"
                              f"Περιλαμβάνει:\n"
                              f"• {len(field_config)} πεδία\n"
                              f"• {len(items)} προϊόντα\n\n{filename}")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία backup:\n{str(e)}")
    
    def copy_to_clipboard(self):
        """Αντιγραφή δεδομένων στο clipboard (για paste σε Excel)"""
        try:
            # Λήψη items προς εξαγωγή
            items_data = self.get_items_to_export()
            if items_data is None:
                return

            # Headers
            headers = [field['label'] for field in self.fields]
            clipboard_text = '\t'.join(headers) + '\n'

            # Data
            for data in items_data:
                values = [str(data.get(field['name'], '')) for field in self.fields]
                clipboard_text += '\t'.join(values) + '\n'
            
            self.root.clipboard_clear()
            self.root.clipboard_append(clipboard_text)
            self.root.update()
            
            messagebox.showinfo("Επιτυχία", 
                              "✅ Τα δεδομένα αντιγράφηκαν στο clipboard!\n\n"
                              "Μπορείς να κάνεις Paste (Ctrl+V) σε Excel, Google Sheets, κλπ.")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία αντιγραφής:\n{str(e)}")
    
    def import_from_excel(self):
        """Import από Excel με αυτόματη αντιστοίχιση πεδίων"""
        filename = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            wb = openpyxl.load_workbook(filename)
            ws = wb.active
            
            # Διάβασε headers
            excel_headers = [cell.value for cell in ws[1]]
            
            # Αντιστοίχιση με τα πεδία μας
            field_mapping = {}
            for i, header in enumerate(excel_headers):
                if header:
                    # Βρες αντίστοιχο πεδίο (από label)
                    for field in self.fields:
                        if field['label'].lower() == str(header).lower():
                            field_mapping[i] = field['name']
                            break
            
            if not field_mapping:
                messagebox.showerror("Σφάλμα", 
                                   "Δεν βρέθηκαν αντιστοιχίες πεδίων!\n\n"
                                   "Βεβαιώσου ότι τα headers του Excel ταιριάζουν με τις ετικέτες των πεδίων σου.")
                return
            
            # Import data
            imported = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                data = {}
                for col_idx, field_name in field_mapping.items():
                    if col_idx < len(row):
                        value = row[col_idx]
                        data[field_name] = str(value) if value is not None else ''
                
                # Αποθήκευση
                if data:
                    data_json = json.dumps(data, ensure_ascii=False)
                    self.cursor.execute("INSERT INTO items (data) VALUES (?)", (data_json,))
                    imported += 1
            
            self.conn.commit()
            self.refresh_table()
            
            messagebox.showinfo("Επιτυχία", 
                              f"✅ Import ολοκληρώθηκε!\n\n"
                              f"Εισήχθησαν {imported} προϊόντα.")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία import:\n{str(e)}")
    
    def import_from_csv(self):
        """Import από CSV με υποστήριξη ελληνικών"""
        filename = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            import csv
            
            # Δοκιμή διαφορετικών encodings
            encodings = ['utf-8-sig', 'utf-8', 'iso-8859-7', 'cp1253']
            
            for encoding in encodings:
                try:
                    with open(filename, 'r', encoding=encoding) as csvfile:
                        reader = csv.reader(csvfile)
                        rows = list(reader)
                        break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            else:
                raise Exception("Δεν ήταν δυνατή η ανάγνωση του αρχείου")
            
            if len(rows) < 2:
                messagebox.showwarning("Προειδοποίηση", "Το CSV φαίνεται άδειο!")
                return
            
            # Headers
            csv_headers = rows[0]
            
            # Αντιστοίχιση πεδίων
            field_mapping = {}
            for i, header in enumerate(csv_headers):
                if header:
                    for field in self.fields:
                        if field['label'].lower() == header.lower():
                            field_mapping[i] = field['name']
                            break
            
            if not field_mapping:
                messagebox.showerror("Σφάλμα", "Δεν βρέθηκαν αντιστοιχίες πεδίων!")
                return
            
            # Import data
            imported = 0
            for row in rows[1:]:
                data = {}
                for col_idx, field_name in field_mapping.items():
                    if col_idx < len(row):
                        data[field_name] = row[col_idx]
                
                if data:
                    data_json = json.dumps(data, ensure_ascii=False)
                    self.cursor.execute("INSERT INTO items (data) VALUES (?)", (data_json,))
                    imported += 1
            
            self.conn.commit()
            self.refresh_table()
            
            messagebox.showinfo("Επιτυχία", f"✅ Εισήχθησαν {imported} προϊόντα από CSV!")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία import:\n{str(e)}")
    
    def import_from_json(self):
        """Import από JSON (restore backup)"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        response = messagebox.askyesnocancel(
            "Επιλογή Import",
            "Θέλεις να:\n\n"
            "• ΝΑΙ: Αντικατάσταση όλων των δεδομένων (πλήρες restore)\n"
            "• ΟΧΙ: Προσθήκη μόνο των προϊόντων (διατήρηση πεδίων)\n"
            "• ΑΚΥΡΟ: Ακύρωση"
        )
        
        if response is None:  # Cancel
            return
        
        full_restore = response  # True = Yes, False = No
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                backup = json.load(f)
            
            if full_restore:
                # Πλήρες restore - διαγραφή υπαρχόντων
                if not messagebox.askyesno("Επιβεβαίωση", 
                                          "⚠️ ΠΡΟΣΟΧΗ!\n\n"
                                          "Θα διαγραφούν ΟΛΑ τα υπάρχοντα δεδομένα και πεδία!\n\n"
                                          "Συνέχεια;"):
                    return
                
                self.cursor.execute("DELETE FROM field_config")
                self.cursor.execute("DELETE FROM items")
                
                # Restore field configuration
                for field in backup['field_config']:
                    self.cursor.execute('''
                        INSERT INTO field_config 
                        (field_name, field_label, field_type, field_options, 
                         field_order, is_required, is_searchable)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (field['name'], field['label'], field['type'], 
                          json.dumps(field['options'], ensure_ascii=False),
                          field['order'], 1 if field['required'] else 0,
                          1 if field['searchable'] else 0))
                
                # Reload configuration
                self.load_config()
                self.create_ui()
            
            # Restore items
            imported = 0
            for item in backup['items']:
                data_json = json.dumps(item['data'], ensure_ascii=False)
                self.cursor.execute("INSERT INTO items (data) VALUES (?)", (data_json,))
                imported += 1
            
            self.conn.commit()
            self.refresh_table()
            
            restore_type = "Πλήρες restore" if full_restore else "Προσθήκη προϊόντων"
            messagebox.showinfo("Επιτυχία", 
                              f"✅ {restore_type} ολοκληρώθηκε!\n\n"
                              f"Εισήχθησαν {imported} προϊόντα.")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία restore:\n{str(e)}")
    
    def paste_from_clipboard(self):
        """Επικόλληση δεδομένων από clipboard (π.χ. από Excel copy-paste)"""
        try:
            clipboard_text = self.root.clipboard_get()
            
            if not clipboard_text.strip():
                messagebox.showwarning("Προειδοποίηση", "Το clipboard είναι άδειο!")
                return
            
            # Parse clipboard data (tab-separated)
            lines = clipboard_text.strip().split('\n')
            
            if len(lines) < 2:
                messagebox.showwarning("Προειδοποίηση", 
                                     "Χρειάζονται τουλάχιστον 2 γραμμές (header + data)")
                return
            
            # Headers
            headers = lines[0].split('\t')
            
            # Αντιστοίχιση πεδίων
            field_mapping = {}
            for i, header in enumerate(headers):
                header = header.strip()
                if header:
                    for field in self.fields:
                        if field['label'].lower() == header.lower():
                            field_mapping[i] = field['name']
                            break
            
            if not field_mapping:
                messagebox.showerror("Σφάλμα", 
                                   "Δεν βρέθηκαν αντιστοιχίες πεδίων!\n\n"
                                   "Βεβαιώσου ότι η πρώτη γραμμή περιέχει τα headers.")
                return
            
            # Import data
            imported = 0
            for line in lines[1:]:
                values = line.split('\t')
                data = {}
                
                for col_idx, field_name in field_mapping.items():
                    if col_idx < len(values):
                        data[field_name] = values[col_idx].strip()
                
                if data:
                    data_json = json.dumps(data, ensure_ascii=False)
                    self.cursor.execute("INSERT INTO items (data) VALUES (?)", (data_json,))
                    imported += 1
            
            self.conn.commit()
            self.refresh_table()
            
            messagebox.showinfo("Επιτυχία", 
                              f"✅ Επικόλληση ολοκληρώθηκε!\n\n"
                              f"Εισήχθησαν {imported} προϊόντα από το clipboard.")
        except tk.TclError:
            messagebox.showerror("Σφάλμα", "Το clipboard δεν περιέχει κείμενο!")
        except Exception as e:
            messagebox.showerror("Σφάλμα", f"Αποτυχία επικόλλησης:\n{str(e)}")

    
    def open_field_settings(self):
        """Άνοιγμα παραθύρου ρυθμίσεων πεδίων"""
        FieldSettingsDialog(self)


class ItemDialog:
    """Διάλογος προσθήκης/επεξεργασίας προϊόντος"""

    def __init__(self, parent, item_id, fields, callback, data=None):
        self.parent = parent
        self.item_id = item_id
        self.fields = fields
        self.callback = callback
        self.data = data or {}

        self.dialog = tk.Toplevel(parent.root)
        self.dialog.title("Νέο Προϊόν" if item_id is None else "Επεξεργασία Προϊόντος")
        self.dialog.geometry("680x750")
        self.dialog.minsize(650, 600)
        self.dialog.configure(bg='#ecf0f1')
        self.dialog.transient(parent.root)
        self.dialog.grab_set()

        # Register validation command
        self.vcmd_number = (self.dialog.register(self.validate_number), '%P')

        self.create_form()

    def validate_number(self, value):
        """Validation για number fields - επιτρέπει μόνο αριθμούς και δεκαδικά"""
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def create_form(self):
        """Δημιουργία φόρμας"""
        # === HEADER ===
        header = tk.Frame(self.dialog, bg='#3498db')
        header.pack(fill=tk.X)

        title_text = "➕ Νέο Προϊόν" if self.item_id is None else "✏️ Επεξεργασία Προϊόντος"
        tk.Label(header, text=title_text, font=('Segoe UI', 13, 'bold'),
                bg='#3498db', fg='white').pack(pady=12)

        # === FORM CONTAINER με Scrollbar ===
        form_container = tk.Frame(self.dialog, bg='white')
        form_container.pack(fill=tk.BOTH, expand=True)

        # Canvas για scrolling
        canvas = tk.Canvas(form_container, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(form_container, orient=tk.VERTICAL, command=canvas.yview)

        # Scrollable frame μέσα στο canvas
        scrollable_frame = tk.Frame(canvas, bg='white')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas και scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Update canvas window width when canvas resizes
        def _configure_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', _configure_canvas)

        # Bind mouse wheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # === FORM FIELDS ===
        self.widgets = {}

        # Padding για καλύτερη εμφάνιση
        inner_frame = tk.Frame(scrollable_frame, bg='white')
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=15)

        for field in self.fields:
            # Field container
            field_frame = tk.Frame(inner_frame, bg='white')
            field_frame.pack(fill=tk.X, pady=10)

            # Label
            label_text = field['label']
            if field['required']:
                label_text += " *"

            tk.Label(field_frame, text=label_text, font=('Segoe UI', 10, 'bold'),
                    bg='white', fg='#2c3e50', anchor='w').pack(fill=tk.X, pady=(0, 5))

            # Widget
            widget = None
            value = self.data.get(field['name'], '')

            if field['type'] == 'text':
                widget = tk.Entry(field_frame, font=('Segoe UI', 10),
                                relief=tk.SOLID, bd=1, bg='white')
                widget.insert(0, value)
                widget.pack(fill=tk.X, ipady=6)

            elif field['type'] == 'number':
                widget = tk.Entry(field_frame, font=('Segoe UI', 10),
                                relief=tk.SOLID, bd=1, bg='white',
                                validate='key', validatecommand=self.vcmd_number)
                widget.insert(0, value)
                widget.pack(fill=tk.X, ipady=6)

            elif field['type'] == 'dropdown':
                widget = ttk.Combobox(field_frame, values=field['options'],
                                     font=('Segoe UI', 10), state='readonly')
                if value in field['options']:
                    widget.set(value)
                elif field['options']:
                    widget.set(field['options'][0])
                widget.pack(fill=tk.X, ipady=2)

            elif field['type'] == 'textarea':
                widget = tk.Text(field_frame, font=('Segoe UI', 10),
                               relief=tk.SOLID, bd=1, bg='white',
                               height=4, wrap=tk.WORD)
                widget.insert('1.0', value)
                widget.pack(fill=tk.X)

            self.widgets[field['name']] = widget

        # === BOTTOM BUTTONS ===
        separator = tk.Frame(self.dialog, bg='#ddd', height=1)
        separator.pack(fill=tk.X)

        btn_container = tk.Frame(self.dialog, bg='white')
        btn_container.pack(fill=tk.X, pady=15)

        # Button frame για center alignment
        btn_frame = tk.Frame(btn_container, bg='white')
        btn_frame.pack()

        tk.Button(btn_frame, text="💾 Αποθήκευση", command=self.save_item,
                 font=('Segoe UI', 11, 'bold'), bg='#27ae60', fg='white',
                 relief=tk.FLAT, padx=40, pady=12, cursor='hand2',
                 activebackground='#229954').pack(side=tk.LEFT, padx=8)

        tk.Button(btn_frame, text="❌ Ακύρωση", command=self.dialog.destroy,
                 font=('Segoe UI', 11), bg='#95a5a6', fg='white',
                 relief=tk.FLAT, padx=40, pady=12, cursor='hand2',
                 activebackground='#7f8c8d').pack(side=tk.LEFT, padx=8)
    
    def save_item(self):
        """Αποθήκευση προϊόντος"""
        data = {}
        
        # Validation
        for field in self.fields:
            widget = self.widgets[field['name']]
            
            if field['type'] == 'textarea':
                value = widget.get('1.0', tk.END).strip()
            else:
                value = widget.get().strip()
            
            if field['required'] and not value:
                messagebox.showerror("Σφάλμα", f"Το πεδίο '{field['label']}' είναι υποχρεωτικό!")
                return
            
            data[field['name']] = value
        
        data_json = json.dumps(data, ensure_ascii=False)
        
        if self.item_id is None:
            # Insert
            self.parent.cursor.execute(
                "INSERT INTO items (data) VALUES (?)", 
                (data_json,)
            )
        else:
            # Update
            self.parent.cursor.execute(
                "UPDATE items SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (data_json, self.item_id)
            )
        
        self.parent.conn.commit()
        self.callback()
        self.dialog.destroy()


class FieldSettingsDialog:
    """Διάλογος ρυθμίσεων πεδίων"""
    
    def __init__(self, parent):
        self.parent = parent
        
        self.dialog = tk.Toplevel(parent.root)
        self.dialog.title("⚙️ Ρυθμίσεις Πεδίων")
        self.dialog.geometry("950x680")
        self.dialog.minsize(900, 650)
        self.dialog.configure(bg='#ecf0f1')
        self.dialog.transient(parent.root)
        self.dialog.grab_set()
        
        self.create_ui()
        self.load_fields()
    
    def create_ui(self):
        """Δημιουργία UI"""
        # Header
        header = tk.Frame(self.dialog, bg='#f39c12', height=60)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="⚙️ Διαχείριση Πεδίων", 
                font=('Segoe UI', 14, 'bold'),
                bg='#f39c12', fg='white').pack(side=tk.LEFT, padx=20, pady=15)
        
        tk.Button(header, text="➕ Νέο Πεδίο", command=self.add_field,
                 font=('Segoe UI', 10), bg='#27ae60', fg='white',
                 relief=tk.FLAT, padx=15, pady=8).pack(side=tk.RIGHT, padx=20)
        
        # Table
        table_frame = tk.Frame(self.dialog, bg='white')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('Σειρά', 'Όνομα', 'Ετικέτα', 'Τύπος', 'Επιλογές', 'Υποχρεωτικό', 'Αναζητήσιμο')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            width = 80 if col == 'Σειρά' else 150
            self.tree.column(col, width=width)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Separator
        separator = tk.Frame(self.dialog, bg='#bdc3c7', height=1)
        separator.pack(fill=tk.X)

        # Buttons
        btn_frame = tk.Frame(self.dialog, bg='#ecf0f1')
        btn_frame.pack(fill=tk.X, padx=20, pady=15, side=tk.BOTTOM)
        
        tk.Button(btn_frame, text="✏️ Επεξεργασία", command=self.edit_field,
                 font=('Segoe UI', 10), bg='#3498db', fg='white',
                 relief=tk.FLAT, padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="🗑️ Διαγραφή", command=self.delete_field,
                 font=('Segoe UI', 10), bg='#e74c3c', fg='white',
                 relief=tk.FLAT, padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="⬆️ Μετακίνηση Πάνω", command=lambda: self.move_field(-1),
                 font=('Segoe UI', 10), bg='#95a5a6', fg='white',
                 relief=tk.FLAT, padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="⬇️ Μετακίνηση Κάτω", command=lambda: self.move_field(1),
                 font=('Segoe UI', 10), bg='#95a5a6', fg='white',
                 relief=tk.FLAT, padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="✅ Κλείσιμο", command=self.close_dialog,
                 font=('Segoe UI', 10), bg='#27ae60', fg='white',
                 relief=tk.FLAT, padx=30, pady=8, cursor='hand2').pack(side=tk.RIGHT, padx=5)
    
    def load_fields(self):
        """Φόρτωση πεδίων"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.parent.cursor.execute('''
            SELECT id, field_order, field_name, field_label, field_type, 
                   field_options, is_required, is_searchable
            FROM field_config
            ORDER BY field_order
        ''')
        
        for row in self.parent.cursor.fetchall():
            field_id, order, name, label, ftype, options, required, searchable = row
            options_text = ', '.join(json.loads(options)) if options else ''
            req_text = '✓' if required else ''
            search_text = '✓' if searchable else ''
            
            self.tree.insert('', tk.END, iid=field_id,
                           values=(order, name, label, ftype, options_text, req_text, search_text))
    
    def add_field(self):
        """Προσθήκη νέου πεδίου"""
        FieldEditorDialog(self, None)
    
    def edit_field(self):
        """Επεξεργασία πεδίου"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Προειδοποίηση", "Επίλεξε ένα πεδίο για επεξεργασία")
            return
        
        field_id = selected[0]
        FieldEditorDialog(self, field_id)
    
    def delete_field(self):
        """Διαγραφή πεδίου"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Προειδοποίηση", "Επίλεξε ένα πεδίο για διαγραφή")
            return
        
        if messagebox.askyesno("Επιβεβαίωση", 
                              "Η διαγραφή του πεδίου θα διαγράψει και τα δεδομένα του από όλα τα προϊόντα.\n\nΣυνέχεια;"):
            field_id = selected[0]
            self.parent.cursor.execute("DELETE FROM field_config WHERE id = ?", (field_id,))
            self.parent.conn.commit()
            self.load_fields()
    
    def move_field(self, direction):
        """Μετακίνηση πεδίου πάνω/κάτω"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Προειδοποίηση", "Επίλεξε ένα πεδίο για μετακίνηση")
            return
        
        field_id = int(selected[0])
        
        # Φόρτωση όλων των πεδίων
        self.parent.cursor.execute("SELECT id, field_order FROM field_config ORDER BY field_order")
        fields = self.parent.cursor.fetchall()
        
        # Εύρεση index
        current_index = next((i for i, f in enumerate(fields) if f[0] == field_id), None)
        if current_index is None:
            return
        
        new_index = current_index + direction
        if new_index < 0 or new_index >= len(fields):
            return
        
        # Swap
        fields[current_index], fields[new_index] = fields[new_index], fields[current_index]
        
        # Update database
        for i, (fid, _) in enumerate(fields):
            self.parent.cursor.execute("UPDATE field_config SET field_order = ? WHERE id = ?", (i + 1, fid))
        
        self.parent.conn.commit()
        self.load_fields()
    
    def close_dialog(self):
        """Κλείσιμο και ανανέωση"""
        self.parent.load_config()
        self.parent.refresh_columns()
        self.parent.refresh_table()
        self.dialog.destroy()


class FieldEditorDialog:
    """Διάλογος προσθήκης/επεξεργασίας πεδίου"""
    
    def __init__(self, parent, field_id):
        self.parent = parent
        self.field_id = field_id
        
        self.dialog = tk.Toplevel(parent.dialog)
        self.dialog.title("Νέο Πεδίο" if field_id is None else "Επεξεργασία Πεδίου")
        self.dialog.geometry("550x600")
        self.dialog.minsize(520, 550)
        self.dialog.configure(bg='#ecf0f1')
        self.dialog.transient(parent.dialog)
        self.dialog.grab_set()
        
        self.create_form()
        
        if field_id:
            self.load_field_data()
    
    def create_form(self):
        """Δημιουργία φόρμας"""
        # Header
        header = tk.Frame(self.dialog, bg='#f39c12', height=50)
        header.pack(fill=tk.X)
        
        title = "➕ Νέο Πεδίο" if self.field_id is None else "✏️ Επεξεργασία Πεδίου"
        tk.Label(header, text=title, font=('Segoe UI', 12, 'bold'),
                bg='#f39c12', fg='white').pack(pady=12)
        
        # Form
        form = tk.Frame(self.dialog, bg='#ecf0f1')
        form.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Όνομα πεδίου (field_name)
        tk.Label(form, text="Όνομα Πεδίου (χωρίς κενά):", 
                font=('Segoe UI', 10, 'bold'), bg='#ecf0f1').grid(row=0, column=0, sticky='w', pady=5)
        self.name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.name_var, font=('Segoe UI', 10), 
                relief=tk.FLAT, bg='white').grid(row=0, column=1, sticky='ew', pady=5, ipady=5)
        
        # Ετικέτα
        tk.Label(form, text="Ετικέτα (εμφάνιση):", 
                font=('Segoe UI', 10, 'bold'), bg='#ecf0f1').grid(row=1, column=0, sticky='w', pady=5)
        self.label_var = tk.StringVar()
        tk.Entry(form, textvariable=self.label_var, font=('Segoe UI', 10), 
                relief=tk.FLAT, bg='white').grid(row=1, column=1, sticky='ew', pady=5, ipady=5)
        
        # Τύπος
        tk.Label(form, text="Τύπος Πεδίου:", 
                font=('Segoe UI', 10, 'bold'), bg='#ecf0f1').grid(row=2, column=0, sticky='w', pady=5)
        self.type_var = tk.StringVar(value='text')
        type_combo = ttk.Combobox(form, textvariable=self.type_var, 
                                 values=['text', 'number', 'dropdown', 'textarea'],
                                 state='readonly', font=('Segoe UI', 10))
        type_combo.grid(row=2, column=1, sticky='ew', pady=5)
        type_combo.bind('<<ComboboxSelected>>', self.on_type_change)
        
        # Επιλογές (για dropdown)
        tk.Label(form, text="Επιλογές (μια ανά γραμμή):", 
                font=('Segoe UI', 10, 'bold'), bg='#ecf0f1').grid(row=3, column=0, sticky='nw', pady=5)
        self.options_text = tk.Text(form, font=('Segoe UI', 10), 
                                   relief=tk.FLAT, bg='white', height=6, wrap=tk.WORD)
        self.options_text.grid(row=3, column=1, sticky='ew', pady=5)
        self.options_label = form.grid_slaves(row=3, column=0)[0]
        
        # Υποχρεωτικό
        self.required_var = tk.BooleanVar()
        tk.Checkbutton(form, text="Υποχρεωτικό πεδίο", variable=self.required_var,
                      font=('Segoe UI', 10), bg='#ecf0f1').grid(row=4, column=0, columnspan=2, sticky='w', pady=5)
        
        # Αναζητήσιμο
        self.searchable_var = tk.BooleanVar(value=True)
        tk.Checkbutton(form, text="Αναζητήσιμο πεδίο", variable=self.searchable_var,
                      font=('Segoe UI', 10), bg='#ecf0f1').grid(row=5, column=0, columnspan=2, sticky='w', pady=5)
        
        form.columnconfigure(1, weight=1)

        # Separator
        separator = tk.Frame(self.dialog, bg='#bdc3c7', height=1)
        separator.pack(fill=tk.X, pady=(10, 0))

        # Buttons - Σταθερά στο bottom
        btn_frame = tk.Frame(self.dialog, bg='#ecf0f1')
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=15)

        # Center τα buttons
        tk.Button(btn_frame, text="💾 Αποθήκευση", command=self.save_field,
                 font=('Segoe UI', 10, 'bold'), bg='#27ae60', fg='white',
                 relief=tk.FLAT, padx=30, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=10, expand=True)

        tk.Button(btn_frame, text="❌ Ακύρωση", command=self.dialog.destroy,
                 font=('Segoe UI', 10), bg='#95a5a6', fg='white',
                 relief=tk.FLAT, padx=30, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=10, expand=True)
        
        self.on_type_change()
    
    def on_type_change(self, event=None):
        """Εμφάνιση/απόκρυψη επιλογών dropdown"""
        if self.type_var.get() == 'dropdown':
            self.options_text.config(state=tk.NORMAL)
            self.options_label.config(fg='#2c3e50')
        else:
            self.options_text.config(state=tk.DISABLED)
            self.options_label.config(fg='#95a5a6')
    
    def load_field_data(self):
        """Φόρτωση δεδομένων πεδίου"""
        self.parent.parent.cursor.execute('''
            SELECT field_name, field_label, field_type, field_options, is_required, is_searchable
            FROM field_config WHERE id = ?
        ''', (self.field_id,))
        
        row = self.parent.parent.cursor.fetchone()
        if row:
            self.name_var.set(row[0])
            self.label_var.set(row[1])
            self.type_var.set(row[2])
            
            if row[3]:
                options = json.loads(row[3])
                self.options_text.delete('1.0', tk.END)
                self.options_text.insert('1.0', '\n'.join(options))
            
            self.required_var.set(bool(row[4]))
            self.searchable_var.set(bool(row[5]))
            
            self.on_type_change()
    
    def save_field(self):
        """Αποθήκευση πεδίου"""
        name = self.name_var.get().strip().replace(' ', '_')
        label = self.label_var.get().strip()
        ftype = self.type_var.get()
        
        if not name or not label:
            messagebox.showerror("Σφάλμα", "Συμπλήρωσε όνομα και ετικέτα πεδίου!")
            return
        
        options = []
        if ftype == 'dropdown':
            options_text = self.options_text.get('1.0', tk.END).strip()
            if not options_text:
                messagebox.showerror("Σφάλμα", "Συμπλήρωσε τις επιλογές για το dropdown!")
                return
            options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
        
        options_json = json.dumps(options, ensure_ascii=False)
        required = 1 if self.required_var.get() else 0
        searchable = 1 if self.searchable_var.get() else 0
        
        if self.field_id is None:
            # Νέο πεδίο
            self.parent.parent.cursor.execute('''
                SELECT MAX(field_order) FROM field_config
            ''')
            max_order = self.parent.parent.cursor.fetchone()[0] or 0
            
            self.parent.parent.cursor.execute('''
                INSERT INTO field_config 
                (field_name, field_label, field_type, field_options, field_order, is_required, is_searchable)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, label, ftype, options_json, max_order + 1, required, searchable))
        else:
            # Επεξεργασία
            self.parent.parent.cursor.execute('''
                UPDATE field_config 
                SET field_name = ?, field_label = ?, field_type = ?, 
                    field_options = ?, is_required = ?, is_searchable = ?
                WHERE id = ?
            ''', (name, label, ftype, options_json, required, searchable, self.field_id))
        
        self.parent.parent.conn.commit()
        self.parent.load_fields()
        self.dialog.destroy()


def main():
    root = tk.Tk()
    app = InventoryManager(root)
    root.mainloop()

if __name__ == '__main__':
    main()
