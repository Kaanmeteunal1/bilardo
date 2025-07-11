import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import time
import os
from datetime import datetime, timedelta
from threading import Thread
import locale


class BilliardsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Olbia Bilardo")

        # Get screen width and height
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight() - 40  # Leave space for taskbar

        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        self.root.configure(bg='#f0f0f0')

        # Maximize window but don't use fullscreen mode to keep taskbar visible
        self.root.state('zoomed')

        # Data file path
        self.data_file = "billiards_data.json"

        # Global categories for items
        self.categories = {
            'İçecekler': {'Çay': 15, 'Su': 15, 'Nescafe': 20, 'Soda': 35},
            'Yiyecekler': {'Tost': 100,}
        }

        # Individual table data - each table has its own order and billiard charges
        self.table_orders = {}  # table_id: {'Yiyecekler': [...], 'İçecekler': [...], 'billiard_charges': [...]}
        self.tables = {}
        self.running_timers = {}
        self.table_counter = 0

        # Current selected table for ordering
        self.current_table_id = None
        self.selected_items = []
        self.current_category = None

        # Track whether quick add categories are shown
        self.table_quickadd_shown = {}

        # Notification variables
        self.notification_showing = False
        self.notification_text = ""
        self.notification_label = None

        # Load saved data or initialize defaults
        self.load_data()

        # Setup UI FIRST - this creates all the widgets
        self.setup_ui()

        # THEN select the first table (after UI is created)
        if self.tables:
            first_table_id = min(self.tables.keys())
            self.select_table(first_table_id)

        self.start_timer_thread()

        # Save data when window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start the date/time update thread
        self.update_datetime()

    def show_notification(self, message):
        """Show a temporary notification at the top center of the interface"""
        if self.notification_showing:
            # If a notification is already showing, clear it first
            if self.notification_label:
                self.notification_label.destroy()

        # Create notification frame and label
        self.notification_text = message
        self.notification_label = tk.Label(
            self.root,
            text=message,
            font=('Arial', 14, 'bold'),
            bg='#2196F3',
            fg='white',
            padx=20,
            pady=10,
            relief='raised',
            bd=2
        )

        # Position at top center of screen
        self.notification_label.place(relx=0.5, rely=0.1, anchor='center')
        self.notification_showing = True

        # Schedule removal after 3 seconds
        self.root.after(3000, self.clear_notification)

    def clear_notification(self):
        """Clear the notification after timeout"""
        if self.notification_label:
            self.notification_label.destroy()
            self.notification_label = None
        self.notification_showing = False

    def update_datetime(self):
        """Update the date and time display with proper Turkish characters"""
        # Get current date and time
        now = datetime.now()

        # Format day and month
        day = now.day

        # Manual mapping for Turkish month names
        turkish_months = {
            1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs",
            6: "Haziran", 7: "Temmuz", 8: "Ağustos",
            9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
        }
        month = turkish_months[now.month]

        # Manual mapping for Turkish day names
        turkish_days = {
            0: "Pazartesi", 1: "Salı", 2: "Çarşamba",
            3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"
        }
        weekday = turkish_days[now.weekday()]

        # Format time: HH:MM (24-hour format)
        time_format = now.strftime("%H:%M")

        # Combine all parts
        date_string = f"{day} {month} {weekday} {time_format}"

        # Update label
        if hasattr(self, 'datetime_label'):
            self.datetime_label.config(text=date_string)

        # Schedule next update in 1 second
        self.root.after(1000, self.update_datetime)

    def save_data(self):
        """Save all data to JSON file"""
        try:
            data = {
                'categories': self.categories,
                'tables': {},
                'table_orders': {},
                'table_counter': self.table_counter,
                'save_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Save table data (excluding runtime data like timers)
            for table_id, table_info in self.tables.items():
                data['tables'][str(table_id)] = {
                    'name': table_info['name'],
                    'rate': table_info['rate'],
                    'type': table_info['type'],
                    'color': table_info['color']
                }

            # Save table orders
            for table_id, orders in self.table_orders.items():
                data['table_orders'][str(table_id)] = orders

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"Data saved successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            print(f"Error saving data: {e}")
            messagebox.showerror("Kaydetme Hatası", f"Veriler kaydedilirken hata oluştu: {e}")

    def load_data(self):
        """Load data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                print(f"Loading saved data from {data.get('save_date', 'unknown date')}")

                # Load categories
                if 'categories' in data:
                    self.categories = data['categories']

                # Load table counter
                if 'table_counter' in data:
                    self.table_counter = data['table_counter']

                # Load tables
                if 'tables' in data and data['tables']:
                    for table_id_str, table_info in data['tables'].items():
                        table_id = int(table_id_str)
                        self.tables[table_id] = {
                            'name': table_info['name'],
                            'active': False,
                            'paused': False,
                            'start_time': None,
                            'pause_time': None,
                            'total_pause_duration': 0,
                            'rate': table_info['rate'],
                            'type': table_info['type'],
                            'color': table_info['color'],
                            'total_cost': 0,
                            'timer_type': None,
                            'preset_duration': None,
                            'remaining_time': None
                        }
                        self.table_quickadd_shown[table_id] = False
                else:
                    self.initialize_default_tables()

                # Initialize empty orders for all tables (don't load previous orders)
                self.initialize_table_orders()
            else:
                self.initialize_default_tables()
                self.initialize_table_orders()

        except Exception as e:
            print(f"Error loading data: {e}")
            messagebox.showerror("Yükleme Hatası", f"Veriler yüklenirken hata oluştu: {e}")
            self.initialize_default_tables()
            self.initialize_table_orders()

    def initialize_default_tables(self):
        """Initialize default tables with updated prices"""
        # 4 Normal Bilardo tables
        for i in range(1, 5):
            self.table_counter += 1
            # Set prices: Masa 1, 2, 4 = 150, Masa 3 = 120
            price = 120 if i == 3 else 150

            self.tables[self.table_counter] = {
                'name': f'Masa {i}',
                'active': False,
                'paused': False,
                'start_time': None,
                'pause_time': None,
                'total_pause_duration': 0,
                'rate': price,  # Updated prices here
                'type': 'Normal Bilardo',
                'color': '#4CAF50',
                'total_cost': 0,
                'timer_type': None,
                'preset_duration': None,
                'remaining_time': None
            }
            self.table_quickadd_shown[self.table_counter] = False

        # 1 American Bilardo table (120 TL)
        self.table_counter += 1
        self.tables[self.table_counter] = {
            'name': 'Amerikan Masa',
            'active': False,
            'paused': False,
            'start_time': None,
            'pause_time': None,
            'total_pause_duration': 0,
            'rate': 120,  # Updated price for Amerikan
            'type': 'Amerikan Bilardo',
            'color': '#2196F3',
            'total_cost': 0,
            'timer_type': None,
            'preset_duration': None,
            'remaining_time': None
        }
        self.table_quickadd_shown[self.table_counter] = False

    def initialize_table_orders(self):
        """Initialize empty orders for all tables"""
        for table_id in self.tables.keys():
            self.table_orders[table_id] = {
                'Yiyecekler': [],
                'İçecekler': [],
                'billiard_charges': []
            }

    def on_closing(self):
        """Handle window closing event"""
        try:
            self.save_data()
            print("Application closing, data saved")
        except Exception as e:
            print(f"Error during closing: {e}")
        finally:
            self.root.destroy()

    def setup_ui(self):
        # Main container - with a bit more bottom padding for small screens
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=10, pady=(10, 15))  # Added more padding at bottom

        # Header with title - smaller height
        self.setup_header(main_frame)

        # Table selection buttons - more compact
        self.setup_table_selection(main_frame)

        # Main content area
        content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        content_frame.pack(fill='both', expand=True, pady=5)  # Reduced padding

        # Left Section - Categories and Items
        self.setup_left_section(content_frame)

        # Middle Section - Current Table's Order
        self.setup_middle_section(content_frame)

        # Right Section - Table Management
        self.setup_right_section(content_frame)

        # Setup right-click menus
        self.root.after(200, self.setup_right_click_menus)

    def setup_header(self, parent):
        """Setup the main header with more compact styling"""
        # Smaller header height for compact screens
        header_frame = tk.Frame(parent, bg='#2196F3', height=45)  # Reduced from 60 to 45
        header_frame.pack(fill='x', pady=(0, 5))  # Reduced padding
        header_frame.pack_propagate(False)

        # Title label with smaller font
        title_label = tk.Label(header_frame, text="Bilardo Cafe Yönetim Sistemi",
                               font=('Segoe UI', 18, 'bold'), bg='#2196F3', fg='white')
        title_label.pack(pady=(10, 0))  # Less padding

        # Date and time display - smaller font
        self.datetime_label = tk.Label(header_frame, text="",
                                       font=('Segoe UI', 12),
                                       bg='#2196F3', fg='white')
        self.datetime_label.place(relx=0.95, rely=0.5, anchor="e")

    def setup_table_selection(self, parent):
        """Setup table selection buttons"""
        selection_frame = tk.Frame(parent, bg='#f0f0f0')
        selection_frame.pack(fill='x', pady=(0, 10))

        tk.Label(selection_frame, text="Masa Seçimi:", font=('Arial', 14, 'bold'),
                 bg='#f0f0f0').pack(side='left', padx=(0, 20))

        self.table_buttons = {}
        for table_id in sorted(self.tables.keys()):
            table_name = self.tables[table_id]['name']
            table_color = self.tables[table_id]['color']

            btn = tk.Button(selection_frame, text=table_name,
                            font=('Arial', 12, 'bold'),
                            bg=table_color, fg='white',
                            width=12, height=2,
                            command=lambda tid=table_id: self.select_table(tid))
            btn.pack(side='left', padx=5)
            self.table_buttons[table_id] = btn

    def select_table(self, table_id):
        """Select a table for ordering with improved refresh"""
        previous_table_id = self.current_table_id
        self.current_table_id = table_id

        # Update button states
        for tid, btn in self.table_buttons.items():
            if tid == table_id:
                btn.configure(relief='sunken', bd=3)
            else:
                btn.configure(relief='raised', bd=2)

        # Update selected table label
        if hasattr(self, 'current_table_label'):
            self.current_table_label.config(text=f"Seçili Masa: {self.tables[table_id]['name']}")

        # Update table widgets order - move selected table to top
        self.update_table_widgets_order()

        # Force a complete refresh of the middle section display
        if hasattr(self, 'order_scrollable_frame'):
            # Clear current display first
            for widget in self.order_scrollable_frame.winfo_children():
                widget.destroy()

            # Create the display anew
            table_orders = self.table_orders[self.current_table_id]
            has_items = (table_orders['Yiyecekler'] or table_orders['İçecekler'] or table_orders['billiard_charges'])

            if not has_items:
                # Show placeholder
                self.no_items_label = tk.Label(self.order_scrollable_frame,
                                               text="Henüz ürün eklenmedi",
                                               font=('Arial', 14, 'italic'), bg='white', fg='#888888')
                self.no_items_label.pack(expand=True, pady=50)
            else:
                # Display items as usual
                if table_orders['Yiyecekler']:
                    self.create_order_section("Yiyecekler", table_orders['Yiyecekler'], '#4CAF50')

                if table_orders['İçecekler']:
                    self.create_order_section("İçecekler", table_orders['İçecekler'], '#2196F3')

                if table_orders['billiard_charges']:
                    self.create_billiard_section(table_orders['billiard_charges'])

            # Update totals display
            self.update_table_totals()

            # Update scroll region
            self.root.after(10, self.update_order_scroll_region)

    def create_change_calculator_for_table(self, table_id):
        """Create a change calculator for a specific table"""
        if not hasattr(self, 'change_frames'):
            self.change_frames = {}
            self.payment_entries = {}
            self.change_labels = {}

        # First, hide all existing change calculators
        for tid, frame in self.change_frames.items():
            if frame.winfo_exists():
                frame.pack_forget()

        # If we already have a calculator for this table, just show it
        if table_id in self.change_frames and self.change_frames[table_id].winfo_exists():
            self.change_frames[table_id].pack(fill='x', pady=10)
            return

        # Get the totals_frame we stored in setup_total_and_actions
        if hasattr(self, 'totals_frame') and self.totals_frame.winfo_exists():
            totals_frame = self.totals_frame
        else:
            # Fallback - look for it
            totals_frame = None
            for child in self.root.winfo_children():
                if isinstance(child, tk.Frame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, tk.Frame):
                            for great_grandchild in grandchild.winfo_children():
                                if isinstance(great_grandchild, tk.Frame):
                                    for widget in great_grandchild.winfo_children():
                                        if isinstance(widget, tk.Label) and widget.cget("text").startswith(
                                                "GENEL TOPLAM"):
                                            totals_frame = great_grandchild
                                            break

            if not totals_frame:
                print("Could not find totals frame")
                return

        # Create change frame
        change_frame = tk.Frame(totals_frame, bg='white', relief='groove', bd=1)
        change_frame.pack(fill='x', pady=10)

        # Customer payment entry
        payment_frame = tk.Frame(change_frame, bg='white')
        payment_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(payment_frame, text="Ödenen Tutar:", font=('Arial', 12, 'bold'),
                 bg='white', fg='#333').pack(side='left', padx=(0, 10))

        payment_entry = tk.Entry(payment_frame, font=('Arial', 12), width=10)
        payment_entry.pack(side='left')

        tk.Label(payment_frame, text="TL", font=('Arial', 12),
                 bg='white', fg='#333').pack(side='left', padx=5)

        calculate_btn = tk.Button(payment_frame, text="Hesapla", bg='#4CAF50', fg='white',
                                  font=('Arial', 10), command=self.calculate_change)
        calculate_btn.pack(side='left', padx=10)

        # Change display
        change_label = tk.Label(change_frame, text="Para Üstü: 0 TL",
                                font=('Arial', 14, 'bold'), bg='white', fg='#2196F3')
        change_label.pack(pady=5)

        # Store references
        self.change_frames[table_id] = change_frame
        self.payment_entries[table_id] = payment_entry
        self.change_labels[table_id] = change_label

    def update_table_widgets_order(self):
        """Update the order of table widgets to show selected table at the top"""
        if not hasattr(self, 'tables_scrollable_frame') or self.current_table_id is None:
            return

        # First, remove all table frames from the scrollable frame
        for table_id, widget_data in self.table_widgets.items():
            widget_data['frame'].pack_forget()

        # Then add the selected table frame first
        if self.current_table_id in self.table_widgets:
            selected_widget = self.table_widgets[self.current_table_id]
            selected_widget['frame'].pack(fill='x', padx=0, pady=5)

            # Add "Seçili Masa" indicator to the selected table
            selected_widget['table_label'].config(text=f"{self.tables[self.current_table_id]['name']} (Seçili)")

        # Then add all other table frames
        for table_id in sorted(self.tables.keys()):
            if table_id != self.current_table_id and table_id in self.table_widgets:
                # Reset the label to original name without "Seçili" indicator
                self.table_widgets[table_id]['table_label'].config(text=self.tables[table_id]['name'])
                self.table_widgets[table_id]['frame'].pack(fill='x', padx=0, pady=5)

    def setup_left_section(self, parent):
        """Setup categories and items section"""
        left_frame = tk.Frame(parent, bg='white', relief='raised', bd=2)
        left_frame.pack(side='left', fill='both', padx=(0, 5), pady=5)
        left_frame.configure(width=350)

        # Header
        header = tk.Label(left_frame, text="Ürün Kategorileri", font=('Arial', 16, 'bold'),
                          bg='white', fg='#333')
        header.pack(pady=10)

        # Category tabs
        tab_frame = tk.Frame(left_frame, bg='white')
        tab_frame.pack(fill='x', padx=10, pady=5)

        self.category_buttons = {}
        for i, category in enumerate(self.categories.keys()):
            btn = tk.Button(tab_frame, text=category, font=('Arial', 12, 'bold'),
                            command=lambda c=category: self.show_category(c),
                            bg='#e0e0e0', activebackground='#d0d0d0',
                            height=2)
            btn.pack(fill='x', pady=2)
            self.category_buttons[category] = btn

        # Items container with scrollbar
        items_frame = tk.Frame(left_frame, bg='white')
        items_frame.pack(fill='both', expand=True, padx=5, pady=10)

        self.left_canvas = tk.Canvas(items_frame, bg='white', highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(items_frame, orient="vertical", command=self.left_canvas.yview)
        self.scrollable_frame = tk.Frame(self.left_canvas, bg='white')

        def configure_scroll_region():
            self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))

        self.scrollable_frame.bind("<Configure>", lambda e: configure_scroll_region())

        self.canvas_frame = self.left_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.left_canvas.configure(yscrollcommand=left_scrollbar.set)

        def configure_canvas(event):
            canvas_width = event.width
            self.left_canvas.itemconfig(self.canvas_frame, width=canvas_width)

        self.left_canvas.bind('<Configure>', configure_canvas)

        self.left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")

        # Fix scrolling to prevent blank space at top
        def on_mousewheel(event):
            # Get the current position
            current_pos = self.left_canvas.yview()[0]

            # If at the top, don't allow scrolling up further
            if current_pos == 0 and event.delta > 0:
                return "break"

            self.left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.left_canvas.bind("<MouseWheel>", on_mousewheel)
        self.bind_mousewheel_recursively(self.scrollable_frame, on_mousewheel)

        # Management buttons
        mgmt_frame = tk.Frame(left_frame, bg='white')
        mgmt_frame.pack(fill='x', padx=10, pady=10)

        tk.Button(mgmt_frame, text="Yeni Ürün Ekle", command=self.add_item,
                  bg='#4CAF50', fg='white', font=('Arial', 10)).pack(side='left', padx=2)

        self.edit_btn = tk.Button(mgmt_frame, text="Düzenle", command=self.edit_item,
                                  bg='#2196F3', fg='white', font=('Arial', 10))
        self.edit_btn.pack(side='left', padx=2)

        tk.Button(mgmt_frame, text="Sil", command=self.delete_items,
                  bg='#f44336', fg='white', font=('Arial', 10)).pack(side='left', padx=2)

        # Show first category
        self.current_category = list(self.categories.keys())[0] if self.categories else 'Yiyecekler'
        self.show_category(self.current_category)

    def setup_middle_section(self, parent):
        """Setup current table's order display"""
        middle_frame = tk.Frame(parent, bg='white', relief='raised', bd=2)
        middle_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        # Header with selected table name
        header_frame = tk.Frame(middle_frame, bg='#2196F3')
        header_frame.pack(fill='x')

        self.current_table_label = tk.Label(header_frame, text="Seçili Masa: -",
                                            font=('Arial', 14, 'bold'), bg='#2196F3', fg='white')
        self.current_table_label.pack(pady=10)

        # Order sections for Yiyecekler, İçecekler, and Billiard charges
        self.setup_order_sections(middle_frame)

        # Total and action buttons
        self.setup_total_and_actions(middle_frame)

    def setup_order_sections(self, parent):
        """Setup order sections for different categories"""
        # Scrollable container for all orders
        order_container = tk.Frame(parent, bg='white')
        order_container.pack(fill='both', expand=True, padx=10, pady=10)

        self.order_canvas = tk.Canvas(order_container, bg='white', highlightthickness=0)
        order_scrollbar = ttk.Scrollbar(order_container, orient="vertical", command=self.order_canvas.yview)
        self.order_scrollable_frame = tk.Frame(self.order_canvas, bg='white')

        def configure_order_scroll():
            self.order_canvas.configure(scrollregion=self.order_canvas.bbox("all"))

        self.order_scrollable_frame.bind("<Configure>", lambda e: configure_order_scroll())

        self.order_canvas_frame = self.order_canvas.create_window((0, 0), window=self.order_scrollable_frame,
                                                                  anchor="nw")
        self.order_canvas.configure(yscrollcommand=order_scrollbar.set)

        def configure_order_canvas(event):
            canvas_width = event.width
            self.order_canvas.itemconfig(self.order_canvas_frame, width=canvas_width)

        self.order_canvas.bind('<Configure>', configure_order_canvas)

        self.order_canvas.pack(side="left", fill="both", expand=True)
        order_scrollbar.pack(side="right", fill="y")

        # Fix scrolling to prevent blank space at top
        def on_order_mousewheel(event):
            # Get the current position
            current_pos = self.order_canvas.yview()[0]

            # If at the top, don't allow scrolling up further
            if current_pos == 0 and event.delta > 0:
                return "break"

            self.order_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.order_canvas.bind("<MouseWheel>", on_order_mousewheel)
        self.bind_mousewheel_recursively(self.order_scrollable_frame, on_order_mousewheel)

    def setup_total_and_actions(self, parent):
        """Setup total display and action buttons - without change calculator and with better layout"""
        # Totals frame
        totals_frame = tk.Frame(parent, bg='white')
        totals_frame.pack(fill='x', padx=10, pady=5)  # Reduced padding

        # Individual totals - smaller fonts and padding
        self.yiyecek_total_label = tk.Label(totals_frame, text="Yiyecek Toplamı: 0 TL",
                                            font=('Segoe UI', 11), bg='white', fg='#4CAF50')
        self.yiyecek_total_label.pack(anchor='w', pady=2)  # Reduced padding

        self.icecek_total_label = tk.Label(totals_frame, text="İçecek Toplamı: 0 TL",
                                           font=('Segoe UI', 11), bg='white', fg='#2196F3')
        self.icecek_total_label.pack(anchor='w', pady=2)  # Reduced padding

        self.billiard_total_label = tk.Label(totals_frame, text="Bilardo Toplamı: 0 TL",
                                             font=('Segoe UI', 11), bg='white', fg='#FF9800')
        self.billiard_total_label.pack(anchor='w', pady=2)  # Reduced padding

        # Grand total
        self.grand_total_label = tk.Label(totals_frame, text="GENEL TOPLAM: 0 TL",
                                          font=('Segoe UI', 14, 'bold'), bg='white', fg='#f44336')
        self.grand_total_label.pack(pady=(5, 5))  # Reduced padding

        # Store reference for later use but don't create change calculator
        self.totals_frame = totals_frame

        # Action buttons frame - moved up since we removed the change calculator
        action_frame = tk.Frame(parent, bg='white')
        action_frame.pack(fill='x', padx=10, pady=5)  # Reduced padding

        # Button layout - single centered button for Hesabı Sıfırla
        # Removed the Hesabı Yazdır button as requested
        reset_btn = tk.Button(action_frame, text="Hesabı Sıfırla", command=self.clear_table_order,
                              bg='#f44336', fg='white', font=('Segoe UI', 11),
                              width=15, height=1)  # Adjusted size
        reset_btn.pack(side='top', pady=5)

        # Create no-items placeholder for middle section
        self.no_items_label = tk.Label(self.order_scrollable_frame, text="Henüz ürün eklenmedi",
                                       font=('Arial', 14, 'italic'), bg='white', fg='#888888')
        self.no_items_label.pack(expand=True, pady=50)

    def setup_right_section(self, parent):
        """Setup table management section"""
        right_frame = tk.Frame(parent, bg='white', relief='raised', bd=2)
        right_frame.pack(side='right', fill='both', padx=(5, 0), pady=5)
        right_frame.configure(width=400)

        # Header
        header = tk.Label(right_frame, text="Masa Yönetimi", font=('Arial', 16, 'bold'),
                          bg='white', fg='#333')
        header.pack(pady=10)

        # Tables container with scrollbar
        tables_frame = tk.Frame(right_frame, bg='white')
        tables_frame.pack(fill='both', expand=True, padx=5, pady=10)

        self.tables_canvas = tk.Canvas(tables_frame, bg='white', highlightthickness=0)
        tables_scrollbar = ttk.Scrollbar(tables_frame, orient="vertical", command=self.tables_canvas.yview)
        self.tables_scrollable_frame = tk.Frame(self.tables_canvas, bg='white')

        def configure_tables_scroll():
            self.tables_canvas.configure(scrollregion=self.tables_canvas.bbox("all"))

        self.tables_scrollable_frame.bind("<Configure>", lambda e: configure_tables_scroll())

        self.tables_canvas_frame = self.tables_canvas.create_window((0, 0), window=self.tables_scrollable_frame,
                                                                    anchor="nw")
        self.tables_canvas.configure(yscrollcommand=tables_scrollbar.set)

        def configure_tables_canvas(event):
            canvas_width = event.width
            self.tables_canvas.itemconfig(self.tables_canvas_frame, width=canvas_width)

        self.tables_canvas.bind('<Configure>', configure_tables_canvas)

        self.tables_canvas.pack(side="left", fill="both", expand=True)
        tables_scrollbar.pack(side="right", fill="y")

        # Create table widgets
        self.table_widgets = {}
        self.create_all_table_widgets()

        # Fix scrolling to prevent blank space at top
        def on_tables_mousewheel(event):
            # Get the current position
            current_pos = self.tables_canvas.yview()[0]

            # If at the top, don't allow scrolling up further
            if current_pos == 0 and event.delta > 0:
                return "break"

            self.tables_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.tables_canvas.bind("<MouseWheel>", on_tables_mousewheel)
        self.bind_mousewheel_recursively(self.tables_scrollable_frame, on_tables_mousewheel)

        # Add table button
        add_table_frame = tk.Frame(right_frame, bg='white')
        add_table_frame.pack(fill='x', padx=10, pady=10)

        tk.Button(add_table_frame, text="Yeni Masa Ekle", command=self.add_new_table,
                  bg='#4CAF50', fg='white', font=('Arial', 12)).pack()

    def bind_mousewheel_recursively(self, widget, callback):
        """Bind mousewheel event to widget and all its children recursively"""
        try:
            widget.bind("<MouseWheel>", callback)
            for child in widget.winfo_children():
                self.bind_mousewheel_recursively(child, callback)
        except:
            pass

    def show_category(self, category):
        """Show items for selected category"""
        # Clear current items
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Reset selection
        self.selected_items = []
        self.update_edit_button_state()

        # Update button states
        for cat, btn in self.category_buttons.items():
            if cat == category:
                btn.configure(bg='#2196F3', fg='white')
            else:
                btn.configure(bg='#e0e0e0', fg='black')

        self.current_category = category

        # Show items for selected category
        for item_name, price in self.categories[category].items():
            self.create_item_widget(item_name, price)

        # Update scroll region
        self.root.after(10, self.update_left_scroll_region)

    def update_left_scroll_region(self):
        """Update left scroll region"""
        self.scrollable_frame.update_idletasks()
        self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))

    def create_item_widget(self, item_name, price):
        """Create an item widget with add button"""
        item_frame = tk.Frame(self.scrollable_frame, bg='#f0f0f0', relief='raised', bd=1)
        item_frame.pack(fill='x', padx=0, pady=2)

        # Bind right-click event directly
        item_frame.bind("<Button-3>", lambda e, n=item_name: self.show_item_right_click_menu(e, n))

        # Bind selection events
        item_frame.bind("<Button-1>", lambda e, n=item_name: self.select_item(n, e))

        # Item info
        info_frame = tk.Frame(item_frame, bg='#f0f0f0')
        info_frame.pack(fill='x', padx=10, pady=8)

        # Format price display
        if price == int(price):
            price_display = f"{int(price)} TL"
        else:
            price_display = f"{price} TL"

        item_label = tk.Label(info_frame, text=f"{item_name} - {price_display}",
                              bg='#f0f0f0', font=('Arial', 12), anchor='w')
        item_label.pack(side='left', fill='x', expand=True)

        # Bind events to the label too
        item_label.bind("<Button-1>", lambda e, n=item_name: self.select_item(n, e))
        item_label.bind("<Button-3>", lambda e, n=item_name: self.show_item_right_click_menu(e, n))

        # Add button
        add_btn = tk.Button(info_frame, text="Ekle", bg='#4CAF50', fg='white', font=('Arial', 10),
                            command=lambda n=item_name, p=price: self.add_to_current_table_order(n, p))
        add_btn.pack(side='right', padx=5)

        # Multiple quantity buttons
        qty_frame = tk.Frame(info_frame, bg='#f0f0f0')
        qty_frame.pack(side='right')

        for qty in [2, 3, 5]:
            qty_btn = tk.Button(qty_frame, text=str(qty), font=('Arial', 9),
                                command=lambda n=item_name, p=price, q=qty: self.add_multiple_to_table(n, p, q),
                                width=2)
            qty_btn.pack(side='left', padx=1)

    def add_multiple_to_table(self, item_name, price, quantity):
        """Add multiple quantities of an item to current table"""
        if self.current_table_id is None:
            messagebox.showwarning("Uyarı", "Lütfen önce bir masa seçin!")
            return

        # Check if item already exists in table's category order
        category_orders = self.table_orders[self.current_table_id][self.current_category]

        for order_item in category_orders:
            if order_item['name'] == item_name:
                order_item['quantity'] += quantity
                break
        else:
            # Add new item with specified quantity
            category_orders.append({
                'name': item_name,
                'price': price,
                'quantity': quantity
            })

        # Show notification
        table_name = self.tables[self.current_table_id]['name']
        self.show_notification(f"{table_name}'e {quantity} {item_name} eklendi!")

        self.update_current_table_display()
        self.save_data()

    def select_item(self, item_name, event):
        """Select item for editing/deleting"""
        # Multiple selection with Ctrl+Click
        if event.state & 0x4:  # Ctrl key pressed
            if item_name in self.selected_items:
                self.selected_items.remove(item_name)
            else:
                self.selected_items.append(item_name)
        else:
            # Single selection
            self.selected_items = [item_name]

        self.update_item_visual_feedback()
        self.update_edit_button_state()

    def update_item_visual_feedback(self):
        """Update visual feedback for selected items"""
        for widget in self.scrollable_frame.winfo_children():
            widget.configure(bg='#f0f0f0')
            for child in widget.winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg='#f0f0f0')
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, tk.Label):
                            grandchild.configure(bg='#f0f0f0')

        # Highlight selected items
        for widget in self.scrollable_frame.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Frame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, tk.Label):
                            for selected_item in self.selected_items:
                                if selected_item in grandchild.cget('text'):
                                    widget.configure(bg='#e3f2fd')
                                    child.configure(bg='#e3f2fd')
                                    grandchild.configure(bg='#e3f2fd')

    def update_edit_button_state(self):
        """Update edit button state based on selection"""
        if len(self.selected_items) > 1:
            self.edit_btn.configure(state='disabled', bg='#9E9E9E')
        else:
            self.edit_btn.configure(state='normal', bg='#2196F3')

    def add_to_current_table_order(self, item_name, price):
        """Add item to current selected table's order"""
        if self.current_table_id is None:
            messagebox.showwarning("Uyarı", "Lütfen önce bir masa seçin!")
            return

        # Check if item already exists in table's category order
        category_orders = self.table_orders[self.current_table_id][self.current_category]

        for order_item in category_orders:
            if order_item['name'] == item_name:
                order_item['quantity'] += 1
                break
        else:
            # Add new item
            category_orders.append({
                'name': item_name,
                'price': price,
                'quantity': 1
            })

        # Show notification
        table_name = self.tables[self.current_table_id]['name']
        self.show_notification(f"{table_name}'e 1 {item_name} eklendi!")

        self.update_current_table_display()
        self.save_data()

    def update_current_table_display(self):
        """Update the current table's order display"""
        if self.current_table_id is None:
            return

        # Clear current display
        for widget in self.order_scrollable_frame.winfo_children():
            widget.destroy()

        table_orders = self.table_orders[self.current_table_id]

        # Check if there are any items
        has_items = (table_orders['Yiyecekler'] or table_orders['İçecekler'] or table_orders['billiard_charges'])

        if not has_items:
            # Show placeholder
            self.no_items_label = tk.Label(self.order_scrollable_frame,
                                           text="Henüz ürün eklenmedi",
                                           font=('Arial', 14, 'italic'), bg='white', fg='#888888')
            self.no_items_label.pack(expand=True, pady=50)
        else:
            # Display items as usual
            # Display Yiyecekler section
            if table_orders['Yiyecekler']:
                self.create_order_section("Yiyecekler", table_orders['Yiyecekler'], '#4CAF50')

            # Display İçecekler section
            if table_orders['İçecekler']:
                self.create_order_section("İçecekler", table_orders['İçecekler'], '#2196F3')

            # Display Billiard charges section
            if table_orders['billiard_charges']:
                self.create_billiard_section(table_orders['billiard_charges'])

        # Update totals
        self.update_table_totals()

        # Update total cost display in table widget
        if self.current_table_id in self.table_widgets:
            self.update_table_total_display(self.current_table_id)

        # Update scroll region
        self.root.after(10, self.update_order_scroll_region)

    def create_order_section(self, category_name, orders, color):
        """Create a section for a category of orders - more compact version"""
        # Section header
        section_frame = tk.Frame(self.order_scrollable_frame, bg='white')
        section_frame.pack(fill='x', pady=(6, 2))  # Reduced padding

        header_frame = tk.Frame(section_frame, bg=color)
        header_frame.pack(fill='x')

        tk.Label(header_frame, text=category_name, font=('Arial', 12, 'bold'),  # Smaller font
                 bg=color, fg='white').pack(pady=4)  # Reduced padding

        # Order items
        for i, item in enumerate(orders):
            self.create_order_item_widget(section_frame, item, category_name, i)

    def create_order_item_widget(self, parent, item, category, index):
        """Create widget for individual order item - more compact version"""
        item_frame = tk.Frame(parent, bg='white', relief='raised', bd=1)
        item_frame.pack(fill='x', padx=0, pady=1)  # Reduced padding

        # Grid layout for alignment
        grid_frame = tk.Frame(item_frame, bg='white')
        grid_frame.pack(fill='x', padx=8, pady=4)  # Reduced padding

        # Item name and price - smaller font
        name_text = f"{item['name']} ({item['price']} TL)"
        name_label = tk.Label(grid_frame, text=name_text, bg='white',
                              font=('Arial', 9), width=20, anchor='w')  # Smaller font
        name_label.grid(row=0, column=0, sticky='w')

        # Quantity controls - more compact
        qty_frame = tk.Frame(grid_frame, bg='white')
        qty_frame.grid(row=0, column=1, padx=5)  # Reduced padding

        minus_btn = tk.Button(qty_frame, text="-", width=1,  # Smaller button
                              command=lambda: self.decrease_item_quantity(category, index))
        minus_btn.pack(side='left')

        qty_label = tk.Label(qty_frame, text=str(item['quantity']), width=2,  # Smaller width
                             bg='white', font=('Arial', 9))  # Smaller font
        qty_label.pack(side='left', padx=2)  # Reduced padding

        plus_btn = tk.Button(qty_frame, text="+", width=1,  # Smaller button
                             command=lambda: self.increase_item_quantity(category, index))
        plus_btn.pack(side='left')

        # Total price - smaller font
        item_total = item['price'] * item['quantity']
        if item_total == int(item_total):
            total_text = f"{int(item_total)} TL"
        else:
            total_text = f"{item_total} TL"

        price_label = tk.Label(grid_frame, text=total_text, bg='white',
                               font=('Arial', 9, 'bold'), width=8, anchor='w')  # Smaller font and width
        price_label.grid(row=0, column=2, sticky='w', padx=5)  # Reduced padding

        # Remove button - smaller
        remove_btn = tk.Button(grid_frame, text="X", bg='#f44336', fg='white',
                               font=('Arial', 10, 'bold'), relief='raised', bd=1,  # Smaller button
                               width=1, height=1,  # Fixed smaller size
                               command=lambda: self.remove_order_item(category, index))
        remove_btn.grid(row=0, column=3, padx=5)  # Reduced padding

    def create_billiard_section(self, billiard_charges):
        """Create billiard charges section with fixed indices"""
        # Section header
        section_frame = tk.Frame(self.order_scrollable_frame, bg='white')
        section_frame.pack(fill='x', pady=(6, 2))  # Reduced padding

        header_frame = tk.Frame(section_frame, bg='#FF9800')
        header_frame.pack(fill='x')

        tk.Label(header_frame, text="Bilardo Ücreti", font=('Arial', 12, 'bold'),
                 bg='#FF9800', fg='white').pack(pady=4)

        # Billiard charges - store the index in a variable that won't change
        for i, charge in enumerate(billiard_charges):
            self.create_billiard_item_widget(section_frame, charge, i)

    def create_billiard_item_widget(self, parent, charge, index):
        """Create widget for billiard charge with fixed index handling"""
        charge_frame = tk.Frame(parent, bg='#fff3e0', relief='raised', bd=1)
        charge_frame.pack(fill='x', pady=1)  # Reduced padding

        grid_frame = tk.Frame(charge_frame, bg='#fff3e0')
        grid_frame.pack(fill='x', padx=8, pady=4)  # Reduced padding

        # Charge description - smaller font
        charge_text = f"{charge['table_name']} - {charge['duration']}"
        charge_label = tk.Label(grid_frame, text=charge_text, bg='#fff3e0',
                                font=('Arial', 9), width=25, anchor='w')  # Smaller font
        charge_label.grid(row=0, column=0, sticky='w')

        # Price - smaller font
        if charge['cost'] == int(charge['cost']):
            cost_text = f"{int(charge['cost'])} TL"
        else:
            cost_text = f"{charge['cost']} TL"

        price_label = tk.Label(grid_frame, text=cost_text, bg='#fff3e0',
                               font=('Arial', 9, 'bold'), width=8, anchor='w')  # Smaller font and width
        price_label.grid(row=0, column=2, sticky='w', padx=5)  # Reduced padding

        # Create a closure to capture the current index value
        def create_remove_command(idx):
            return lambda: self.remove_billiard_charge(idx)

        # Remove button with fixed index
        remove_btn = tk.Button(grid_frame, text="X", bg='#f44336', fg='white',
                               font=('Arial', 10, 'bold'), relief='raised', bd=1,
                               width=1, height=1,
                               command=create_remove_command(index))
        remove_btn.grid(row=0, column=3, padx=5)
    def increase_item_quantity(self, category, index):
        """Increase quantity of an order item"""
        if self.current_table_id is None:
            return

        item_name = self.table_orders[self.current_table_id][category][index]['name']
        self.table_orders[self.current_table_id][category][index]['quantity'] += 1

        # Show notification
        table_name = self.tables[self.current_table_id]['name']
        self.show_notification(f"{table_name}'e {item_name} eklendi!")

        self.update_current_table_display()
        self.save_data()

    def decrease_item_quantity(self, category, index):
        """Decrease quantity of an order item"""
        if self.current_table_id is None:
            return

        orders = self.table_orders[self.current_table_id][category]
        item_name = orders[index]['name']

        if orders[index]['quantity'] > 1:
            orders[index]['quantity'] -= 1
            # Show notification
            table_name = self.tables[self.current_table_id]['name']
            self.show_notification(f"{table_name}'den {item_name} azaltıldı!")
        else:
            orders.pop(index)
            # Show notification
            table_name = self.tables[self.current_table_id]['name']
            self.show_notification(f"{table_name}'den {item_name} silindi!")

        self.update_current_table_display()
        self.save_data()

    def remove_order_item(self, category, index):
        """Remove an order item completely"""
        if self.current_table_id is None:
            return

        item_name = self.table_orders[self.current_table_id][category][index]['name']
        self.table_orders[self.current_table_id][category].pop(index)

        # Show notification
        table_name = self.tables[self.current_table_id]['name']
        self.show_notification(f"{table_name}'den {item_name} silindi!")

        self.update_current_table_display()
        self.save_data()

    def remove_billiard_charge(self, index):
        """Remove a billiard charge with index checking"""
        if self.current_table_id is None:
            return

        # Add safety check for index
        billiard_charges = self.table_orders[self.current_table_id]['billiard_charges']
        if index < 0 or index >= len(billiard_charges):
            # Index is out of range, print debug info and return
            print(f"Error: Index {index} is out of range for billiard charges (length: {len(billiard_charges)})")
            return

        charge_info = billiard_charges[index]
        billiard_charges.pop(index)

        # Show notification
        table_name = self.tables[self.current_table_id]['name']
        self.show_notification(f"{table_name}'den bilardo ücreti silindi!")

        self.update_current_table_display()
        self.save_data()

    def update_table_totals(self):
        """Update all totals for current table"""
        if self.current_table_id is None:
            return

        table_orders = self.table_orders[self.current_table_id]

        # Calculate Yiyecekler total
        yiyecek_total = sum(item['price'] * item['quantity'] for item in table_orders['Yiyecekler'])

        # Calculate İçecekler total
        icecek_total = sum(item['price'] * item['quantity'] for item in table_orders['İçecekler'])

        # Calculate Billiard total
        billiard_total = sum(charge['cost'] for charge in table_orders['billiard_charges'])

        # Grand total
        grand_total = yiyecek_total + icecek_total + billiard_total

        # Update labels
        self.yiyecek_total_label.config(text=f"Yiyecek Toplamı: {yiyecek_total} TL")
        self.icecek_total_label.config(text=f"İçecek Toplamı: {icecek_total} TL")
        self.billiard_total_label.config(text=f"Bilardo Toplamı: {billiard_total} TL")
        self.grand_total_label.config(text=f"GENEL TOPLAM: {grand_total} TL")

    def update_order_scroll_region(self):
        """Update order scroll region"""
        self.order_scrollable_frame.update_idletasks()
        self.order_canvas.configure(scrollregion=self.order_canvas.bbox("all"))

    def clear_table_order(self):
        """Clear current table's order and reset timer without charging"""
        if self.current_table_id is None:
            messagebox.showwarning("Uyarı", "Lütfen önce bir masa seçin!")
            return

        table_name = self.tables[self.current_table_id]['name']
        result = messagebox.askyesno("Hesabı Sıfırla",
                                     f"{table_name} hesabını tamamen sıfırlamak istediğinizden emin misiniz?")
        if result:
            # If table is active, end the timer without calculating any cost
            if self.tables[self.current_table_id]['active']:
                # Reset table without calculating costs
                self.reset_table(self.current_table_id)

            # Clear all orders for this table
            self.table_orders[self.current_table_id] = {
                'Yiyecekler': [],
                'İçecekler': [],
                'billiard_charges': []
            }

            # Remove references to payment_entries and change_labels which no longer exist
            # since we removed the money change system

            # Immediately update the display
            self.update_current_table_display()

            # Force refresh the middle section
            if hasattr(self, 'order_scrollable_frame'):
                # Clear current display first
                for widget in self.order_scrollable_frame.winfo_children():
                    widget.destroy()

                # Show the no items label
                self.no_items_label = tk.Label(self.order_scrollable_frame,
                                               text="Henüz ürün eklenmedi",
                                               font=('Arial', 14, 'italic'), bg='white', fg='#888888')
                self.no_items_label.pack(expand=True, pady=50)

            # Update totals to zero
            self.yiyecek_total_label.config(text="Yiyecek Toplamı: 0 TL")
            self.icecek_total_label.config(text="İçecek Toplamı: 0 TL")
            self.billiard_total_label.config(text="Bilardo Toplamı: 0 TL")
            self.grand_total_label.config(text="GENEL TOPLAM: 0 TL")

            # Reset current billiard cost
            if self.current_table_id in self.table_widgets:
                self.table_widgets[self.current_table_id]['current_billiard_cost'] = 0.0
                # Update the table display as well
                self.update_table_total_display(self.current_table_id)

            self.save_data()

            # Show notification
            self.show_notification(f"{table_name} hesabı sıfırlandı!")

    def calculate_change(self):
        """Calculate change based on payment amount"""
        if self.current_table_id is None:
            messagebox.showwarning("Uyarı", "Lütfen önce bir masa seçin!")
            return

        # Make sure we're using the correct entry widget
        if self.current_table_id not in self.payment_entries:
            messagebox.showwarning("Uyarı", "Para üstü hesaplanamıyor!")
            return

        payment_entry = self.payment_entries[self.current_table_id]
        change_label = self.change_labels[self.current_table_id]

        # Get current total
        grand_total = 0
        table_orders = self.table_orders[self.current_table_id]

        # Calculate totals from orders
        yiyecek_total = sum(item['price'] * item['quantity'] for item in table_orders['Yiyecekler'])
        icecek_total = sum(item['price'] * item['quantity'] for item in table_orders['İçecekler'])
        billiard_total = sum(charge['cost'] for charge in table_orders['billiard_charges'])
        grand_total = yiyecek_total + icecek_total + billiard_total

        # Add current billiard cost if table is active
        if self.tables[self.current_table_id]['active'] and not self.tables[self.current_table_id]['paused']:
            if hasattr(self.table_widgets[self.current_table_id], 'current_billiard_cost'):
                current_billiard_cost = getattr(self.table_widgets[self.current_table_id], 'current_billiard_cost', 0)
                grand_total += current_billiard_cost

        try:
            # Get payment amount
            payment = float(payment_entry.get().replace(',', '.').strip())

            # Calculate change
            change = payment - grand_total

            # Update change label
            if change >= 0:
                change_label.config(text=f"Para Üstü: {change:.2f} TL", fg='#2196F3')
            else:
                change_label.config(text=f"Eksik Ödeme: {abs(change):.2f} TL", fg='#f44336')

        except ValueError:
            # Invalid input
            change_label.config(text="Geçerli bir tutar girin!", fg='#f44336')

    def print_table_bill(self):
        """Print/show bill for current table"""
        if self.current_table_id is None:
            messagebox.showwarning("Uyarı", "Lütfen önce bir masa seçin!")
            return

        table_name = self.tables[self.current_table_id]['name']
        table_orders = self.table_orders[self.current_table_id]

        # Create bill text
        bill_text = f"{'=' * 50}\n"
        bill_text += f"OLBIA BİLARDO CAFE\n"
        bill_text += f"{'=' * 50}\n"
        bill_text += f"Masa: {table_name}\n"
        bill_text += f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        bill_text += f"{'=' * 50}\n\n"

        yiyecek_total = 0
        icecek_total = 0
        billiard_total = 0
        current_billiard_cost = 0

        # Yiyecekler
        if table_orders['Yiyecekler']:
            bill_text += "YİYECEKLER:\n"
            bill_text += "-" * 30 + "\n"
            for item in table_orders['Yiyecekler']:
                item_total = item['price'] * item['quantity']
                yiyecek_total += item_total
                bill_text += f"{item['name']} x{item['quantity']} = {item_total} TL\n"
            bill_text += f"Yiyecek Toplamı: {yiyecek_total} TL\n\n"

        # İçecekler - FIX: This was incorrectly nested inside the Yiyecekler block
        if table_orders['İçecekler']:
            bill_text += "İÇECEKLER:\n"
            bill_text += "-" * 30 + "\n"
            for item in table_orders['İçecekler']:
                item_total = item['price'] * item['quantity']
                icecek_total += item_total
                bill_text += f"{item['name']} x{item['quantity']} = {item_total} TL\n"
            bill_text += f"İçecek Toplamı: {icecek_total} TL\n\n"

        # Billiard charges
        if table_orders['billiard_charges']:
            bill_text += "BİLARDO ÜCRETİ:\n"
            bill_text += "-" * 30 + "\n"
            for charge in table_orders['billiard_charges']:
                billiard_total += charge['cost']
                bill_text += f"{charge['table_name']} - {charge['duration']} = {charge['cost']} TL\n"
            bill_text += f"Bilardo Toplamı: {billiard_total} TL\n\n"

        # Add current billiard cost if table is active
        if self.tables[self.current_table_id]['active'] and not self.tables[self.current_table_id]['paused']:
            if self.current_table_id in self.table_widgets:
                current_billiard_cost = self.table_widgets[self.current_table_id]['current_billiard_cost']

                if current_billiard_cost > 0:
                    bill_text += "DEVAM EDEN BİLARDO:\n"
                    bill_text += "-" * 30 + "\n"
                    bill_text += f"Anlık Ücret = {current_billiard_cost:.2f} TL\n"
                    bill_text += f"Devam Eden Bilardo: {current_billiard_cost:.2f} TL\n\n"

        # Grand total
        grand_total = yiyecek_total + icecek_total + billiard_total + current_billiard_cost
        bill_text += "=" * 50 + "\n"
        bill_text += f"GENEL TOPLAM: {grand_total} TL\n"

        # Add payment and change information if available
        try:
            if self.current_table_id in self.payment_entries:
                payment_entry = self.payment_entries[self.current_table_id]
                payment = float(payment_entry.get().replace(',', '.').strip())
                change = payment - grand_total
                bill_text += f"Ödenen Tutar: {payment:.2f} TL\n"
                if change >= 0:
                    bill_text += f"Para Üstü: {change:.2f} TL\n"
                else:
                    bill_text += f"Eksik Ödeme: {abs(change):.2f} TL\n"
        except:
            pass  # Don't add payment info if not available

        bill_text += "=" * 50 + "\n"
        bill_text += "Teşekkür ederiz!\n"

        # Show bill in a dialog
        self.show_bill_dialog(bill_text, table_name)

    def show_bill_dialog(self, bill_text, table_name):
        """Show bill in a dialog window"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{table_name} - Hesap")
        dialog.geometry("600x700")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 300
        y = (dialog.winfo_screenheight() // 2) - 350
        dialog.geometry(f"600x700+{x}+{y}")

        # Bill text area
        text_frame = tk.Frame(dialog)
        text_frame.pack(fill='both', expand=True, padx=20, pady=20)

        text_area = tk.Text(text_frame, font=('Courier', 11), wrap='word')
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_area.yview)
        text_area.configure(yscrollcommand=scrollbar.set)

        text_area.insert('1.0', bill_text)
        text_area.config(state='disabled')

        text_area.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill='x', padx=20, pady=10)

        tk.Button(btn_frame, text="Yazdır", command=lambda: self.save_bill_to_file(bill_text, table_name),
                  bg='#4CAF50', fg='white', font=('Arial', 12)).pack(side='left', padx=10)
        tk.Button(btn_frame, text="Kapat", command=dialog.destroy,
                  bg='#f44336', fg='white', font=('Arial', 12)).pack(side='right', padx=10)

    def save_bill_to_file(self, bill_text, table_name):
        """Save bill to a text file"""
        try:
            filename = f"{table_name}_hesap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(bill_text)
            messagebox.showinfo("Başarılı", f"Hesap '{filename}' dosyasına kaydedildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya kaydedilirken hata oluştu: {e}")

    def create_all_table_widgets(self):
        """Create widgets for all tables"""
        for table_id in sorted(self.tables.keys()):
            self.create_table_widget(table_id)

    def create_table_widget(self, table_id):
        """Create a single table widget with uniform button heights"""
        table_frame = tk.Frame(self.tables_scrollable_frame, bg='#f5f5f5',
                               relief='solid', bd=1)
        table_frame.pack(fill='x', padx=0, pady=5)

        # Add double-click binding to navigate to this table
        table_frame.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        # Table header with status
        header_frame = tk.Frame(table_frame, bg=self.tables[table_id]['color'])
        header_frame.pack(fill='x')
        header_frame.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        table_label = tk.Label(header_frame, text=self.tables[table_id]['name'],
                               bg=self.tables[table_id]['color'], fg='white', font=('Segoe UI', 12, 'bold'))
        table_label.pack(side='left', padx=10, pady=5)
        table_label.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        status_label = tk.Label(header_frame, text="Masa Boş",
                                bg=self.tables[table_id]['color'], fg='white', font=('Segoe UI', 10))
        status_label.pack(side='right', padx=10, pady=5)
        status_label.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        # Table info
        info_frame = tk.Frame(table_frame, bg='#f5f5f5')
        info_frame.pack(fill='x', padx=10, pady=5)
        info_frame.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        # Left side table info
        info_left_frame = tk.Frame(info_frame, bg='#f5f5f5')
        info_left_frame.pack(side='left', fill='y')
        info_left_frame.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        type_label = tk.Label(info_left_frame, text=f"Masa Türü: {self.tables[table_id]['type']}",
                              bg='#f5f5f5', font=('Segoe UI', 10))
        type_label.pack(anchor='w')
        type_label.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        rate_label = tk.Label(info_left_frame, text=f"Saatlik Ücret: {self.tables[table_id]['rate']} TL",
                              bg='#f5f5f5', font=('Segoe UI', 10))
        rate_label.pack(anchor='w')
        rate_label.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        time_label = tk.Label(info_left_frame, text="Süre: 00:00:00",
                              bg='#f5f5f5', font=('Segoe UI', 10))
        time_label.pack(anchor='w')
        time_label.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        # Current cost label
        cost_label = tk.Label(info_left_frame, text="",
                              bg='#f5f5f5', font=('Segoe UI', 10, 'bold'), fg='#d32f2f')
        cost_label.pack(anchor='w')
        cost_label.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        # Total cost label (billiard + food/drinks)
        total_label = tk.Label(info_left_frame, text="",
                               bg='#f5f5f5', font=('Segoe UI', 10, 'bold'), fg='#d32f2f')
        # Only show if there are costs
        if self.calculate_table_total(table_id) > 0:
            total_label.pack(anchor='w')
        total_label.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        # Food and drink icons to the right of the info
        quick_add_frame = tk.Frame(info_frame, bg='#f5f5f5')
        quick_add_frame.pack(side='right', fill='y', padx=5)

        # Food icon button - smaller size
        food_btn = tk.Button(quick_add_frame, text="🍔", font=('Segoe UI', 14, 'bold'),
                             bg='#4CAF50', fg='white', relief='flat', bd=0,
                             width=2, height=1,
                             command=lambda t=table_id: self.toggle_table_quickadd('Yiyecekler', t))
        food_btn.pack(side='top', pady=2)

        # Drink icon button - smaller size
        drink_btn = tk.Button(quick_add_frame, text="🥤", font=('Segoe UI', 14, 'bold'),
                              bg='#2196F3', fg='white', relief='flat', bd=0,
                              width=2, height=1,
                              command=lambda t=table_id: self.toggle_table_quickadd('İçecekler', t))
        drink_btn.pack(side='top', pady=2)

        # Quick add items container - initially hidden
        quick_items_frame = tk.Frame(info_frame, bg='#f5f5f5')
        # Not packed initially - will be shown when category button is clicked

        # Control buttons
        btn_frame = tk.Frame(table_frame, bg='#f5f5f5')
        btn_frame.pack(fill='x', padx=10, pady=5)
        btn_frame.bind("<Double-1>", lambda e, tid=table_id: self.select_table(tid))

        # Define consistent button height and width
        button_height = 1
        std_button_width = 8
        icon_button_width = 2

        start_btn = tk.Button(btn_frame, text="Başlat", bg='#4CAF50', fg='white',
                              font=('Segoe UI', 10), height=button_height, width=std_button_width,
                              command=lambda tid=table_id: self.start_table(tid))
        start_btn.pack(side='left', padx=2)

        stop_btn = tk.Button(btn_frame, text="Bitir", bg='#9E9E9E', fg='white',
                             font=('Segoe UI', 10), height=button_height, width=std_button_width,
                             command=lambda tid=table_id: self.stop_table(tid),
                             state='disabled')
        stop_btn.pack(side='left', padx=2)

        # Add time button (green + button) - initially hidden
        add_time_btn = tk.Button(btn_frame, text="+", bg='#4CAF50', fg='white',
                                 font=('Segoe UI', 12, 'bold'), height=button_height, width=icon_button_width,
                                 command=lambda tid=table_id: self.add_time_to_table(tid))
        # Don't pack initially - will be packed when table is active with preset timer

        edit_btn = tk.Button(btn_frame, text="Düzenle", bg='#2196F3', fg='white',
                             font=('Segoe UI', 10), height=button_height, width=std_button_width,
                             command=lambda tid=table_id: self.edit_table(tid))
        edit_btn.pack(side='left', padx=2)

        # Use X icon for delete button
        delete_btn = tk.Button(btn_frame, text="X", bg='#f44336', fg='white',
                               font=('Segoe UI', 12, 'bold'), height=button_height, width=icon_button_width,
                               relief='flat', bd=0,
                               command=lambda tid=table_id: self.delete_table(tid))
        delete_btn.pack(side='right', padx=2)

        self.table_widgets[table_id] = {
            'frame': table_frame,
            'header': header_frame,
            'table_label': table_label,
            'status': status_label,
            'type': type_label,
            'rate': rate_label,
            'time': time_label,
            'cost': cost_label,
            'total_label': total_label,
            'start_btn': start_btn,
            'stop_btn': stop_btn,
            'add_time_btn': add_time_btn,  # New add time button
            'delete_btn': delete_btn,
            'food_btn': food_btn,
            'drink_btn': drink_btn,
            'quick_items_frame': quick_items_frame,
            'current_billiard_cost': 0.0  # Store current billiard cost for total calculation
        }

        # Set initial quickadd state
        self.table_quickadd_shown[table_id] = False

    def calculate_table_total(self, table_id):
        """Calculate total cost for a table (orders + billiard)"""
        table_orders = self.table_orders[table_id]

        # Calculate food/drink costs
        yiyecek_total = sum(item['price'] * item['quantity'] for item in table_orders['Yiyecekler'])
        icecek_total = sum(item['price'] * item['quantity'] for item in table_orders['İçecekler'])

        # Calculate billiard charges
        billiard_total = sum(charge['cost'] for charge in table_orders['billiard_charges'])

        # Include current billiard cost if table is active
        current_billiard_cost = 0
        if self.tables[table_id]['active'] and not self.tables[table_id]['paused']:
            if table_id in self.table_widgets:
                # FIX: Access the dictionary item instead of using hasattr
                current_billiard_cost = self.table_widgets[table_id]['current_billiard_cost']

        # Return grand total
        return yiyecek_total + icecek_total + billiard_total + current_billiard_cost

    def update_table_total_display(self, table_id):
        """Update the total display for a table"""
        if table_id not in self.table_widgets:
            return

        # Calculate total cost for this table (items + billiard)
        table_orders = self.table_orders[table_id]

        # Calculate items cost
        yiyecek_total = sum(item['price'] * item['quantity'] for item in table_orders['Yiyecekler'])
        icecek_total = sum(item['price'] * item['quantity'] for item in table_orders['İçecekler'])
        items_total = yiyecek_total + icecek_total

        # Billiard charges from completed sessions
        billiard_total = sum(charge['cost'] for charge in table_orders['billiard_charges'])

        # Current billiard cost (if active) - directly use the value we calculated in the timer thread
        current_billiard_cost = 0
        if self.tables[table_id]['active'] and not self.tables[table_id]['paused']:
            current_billiard_cost = self.table_widgets[table_id]['current_billiard_cost']

        # Grand total
        grand_total = items_total + billiard_total + current_billiard_cost

        # Only show total if we have items or billiard charges or active billiard
        if grand_total > 0:
            self.table_widgets[table_id]['total_label'].config(text=f"Toplam: {grand_total:.2f} TL")
            self.table_widgets[table_id]['total_label'].pack(anchor='w')  # Make sure it's visible
        else:
            # Hide if no costs
            self.table_widgets[table_id]['total_label'].pack_forget()

    def toggle_table_quickadd(self, category, table_id):
        """Toggle the display of quick add items for a table"""
        if self.table_quickadd_shown.get(table_id, False) and self.table_quickadd_shown[table_id] == category:
            # Hide if already showing this category
            self.table_widgets[table_id]['quick_items_frame'].pack_forget()
            self.table_quickadd_shown[table_id] = False

            # Reset button reliefs
            self.table_widgets[table_id]['food_btn'].config(relief='raised')
            self.table_widgets[table_id]['drink_btn'].config(relief='raised')
        else:
            # Show if hidden or different category
            self.table_quickadd_shown[table_id] = category

            # Update button states
            self.table_widgets[table_id]['food_btn'].config(relief='raised')
            self.table_widgets[table_id]['drink_btn'].config(relief='raised')

            if category == 'Yiyecekler':
                self.table_widgets[table_id]['food_btn'].config(relief='sunken')
            else:
                self.table_widgets[table_id]['drink_btn'].config(relief='sunken')

            # Show and update items
            self.update_table_quickadd_items(table_id, category)

            # Make sure it's packed
            quick_items_frame = self.table_widgets[table_id]['quick_items_frame']
            if quick_items_frame.winfo_manager() != 'pack':
                quick_items_frame.pack(side='right', fill='y', padx=5)

    def update_table_quickadd_items(self, table_id, category):
        """Update quick add items for a table with fixed scrolling"""
        if table_id not in self.table_widgets or 'quick_items_frame' not in self.table_widgets[table_id]:
            return  # Skip if the widget doesn't exist yet

        # Get the frame
        quick_items_frame = self.table_widgets[table_id]['quick_items_frame']

        # Clear current items
        for widget in quick_items_frame.winfo_children():
            widget.destroy()

        # Create new quick add buttons for the selected category
        if category in self.categories:
            # Create a small, scrollable area for quick add items
            canvas_height = 150
            items_canvas = tk.Canvas(quick_items_frame, bg='#f5f5f5', width=120, height=canvas_height,
                                     highlightthickness=0)
            items_scrollbar = ttk.Scrollbar(quick_items_frame, orient="vertical",
                                            command=items_canvas.yview)
            items_inner_frame = tk.Frame(items_canvas, bg='#f5f5f5')

            # Configure scrolling
            def configure_scroll_region():
                items_canvas.configure(scrollregion=items_canvas.bbox("all"))

            items_inner_frame.bind("<Configure>", lambda e: configure_scroll_region())

            items_canvas_frame = items_canvas.create_window((0, 0), window=items_inner_frame, anchor="nw")
            items_canvas.configure(yscrollcommand=items_scrollbar.set)

            # Add mousewheel binding for scrolling
            def on_mousewheel(event):
                # Scroll 2 units for every mouse wheel click
                items_canvas.yview_scroll(int(-1 * (event.delta / 60)), "units")

            # Bind mousewheel to canvas and all child widgets
            items_canvas.bind("<MouseWheel>", on_mousewheel)
            self.bind_mousewheel_recursively(items_inner_frame, on_mousewheel)

            items_canvas.pack(side="left", fill="both", expand=True)
            items_scrollbar.pack(side="right", fill="y")

            # Add items as buttons
            for item_name, price in self.categories[category].items():
                btn_frame = tk.Frame(items_inner_frame, bg='#f5f5f5')
                btn_frame.pack(fill='x', pady=1)

                btn = tk.Button(btn_frame, text=f"{item_name}", font=('Arial', 8),
                                bg='#e0e0e0', width=12,
                                command=lambda t=table_id, n=item_name, p=price,
                                               c=category: self.add_to_table_from_quickadd(t, n, p, c))
                btn.pack(side='left', fill='x', expand=True)

                # Also bind mousewheel to button
                btn.bind("<MouseWheel>", on_mousewheel)

            # Make the frame visible and show items
            quick_items_frame.pack(side='right', fill='y', padx=5)

    def add_to_table_from_quickadd(self, table_id, item_name, price, category):
        """Add item to a specific table from quick add buttons"""
        # Check if item already exists in table's category order
        category_orders = self.table_orders[table_id][category]

        for order_item in category_orders:
            if order_item['name'] == item_name:
                order_item['quantity'] += 1
                break
        else:
            # Add new item
            category_orders.append({
                'name': item_name,
                'price': price,
                'quantity': 1
            })

        # Show notification
        table_name = self.tables[table_id]['name']
        self.show_notification(f"{table_name}'e 1 {item_name} eklendi!")

        # Update current display if this is the selected table
        if self.current_table_id == table_id:
            self.update_current_table_display()

        # Always update total display for this table
        self.update_table_total_display(table_id)

        self.save_data()

    def setup_right_click_menus(self):
        """Set up right-click context menus for different elements"""
        # Create context menus
        self.item_menu = tk.Menu(self.root, tearoff=0)
        self.item_menu.add_command(label="Ekle", command=self.context_add_item)
        self.item_menu.add_command(label="Düzenle", command=self.edit_item)
        self.item_menu.add_command(label="Sil", command=self.delete_items)

        # Add "Şu masaya ekle" submenu
        self.table_submenu = tk.Menu(self.item_menu, tearoff=0)
        self.item_menu.add_cascade(label="Şu masaya ekle", menu=self.table_submenu)

        self.category_menu = tk.Menu(self.root, tearoff=0)
        self.category_menu.add_command(label="Yeni Ürün Ekle", command=self.add_item)

        self.table_menu = tk.Menu(self.root, tearoff=0)
        self.table_menu.add_command(label="Seç", command=self.context_select_table)
        self.table_menu.add_command(label="Başlat/Duraklat", command=self.context_start_table)
        self.table_menu.add_command(label="Bitir", command=self.context_stop_table)
        self.table_menu.add_separator()
        self.table_menu.add_command(label="Düzenle", command=self.context_edit_table)
        self.table_menu.add_command(label="Sil", command=self.context_delete_table)

        # Populate the table submenu with all tables
        self.update_table_submenu()

        # Bind right-click events for items in Ürün kategorileri
        def bind_item_menu_recursively(widget):
            widget.bind("<Button-3>", lambda e: self.show_item_right_click_menu(e))
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    bind_item_menu_recursively(child)

        # Bind right-click events for tables
        def show_table_menu(event):
            widget = event.widget
            # Find the table ID
            table_id = None

            # Check if widget is part of a table
            for tid, table_widget in self.table_widgets.items():
                for key, value in table_widget.items():
                    # Check if value is a widget before calling winfo_children
                    if isinstance(value, (tk.Widget, tk.BaseWidget)):
                        if widget == value:
                            table_id = tid
                            break
                        try:
                            if hasattr(value, 'winfo_children') and widget in value.winfo_children():
                                table_id = tid
                                break
                        except:
                            pass
                if table_id:
                    break

            # If still not found, look at parent
            if not table_id and hasattr(widget, 'winfo_parent'):
                try:
                    parent = self.root.nametowidget(widget.winfo_parent())
                    for tid, table_widget in self.table_widgets.items():
                        for key, value in table_widget.items():
                            # Check if value is a widget before checking children
                            if isinstance(value, (tk.Widget, tk.BaseWidget)):
                                if parent == value:
                                    table_id = tid
                                    break
                                try:
                                    if hasattr(value, 'winfo_children') and parent in value.winfo_children():
                                        table_id = tid
                                        break
                                except:
                                    pass
                        if table_id:
                            break
                except:
                    pass

            if table_id:
                self.context_table_id = table_id
                self.table_menu.post(event.x_root, event.y_root)

        # Bind menu to all item frames recursively
        bind_item_menu_recursively(self.scrollable_frame)

        # Bind right-click events for categories
        def show_category_menu(event):
            self.category_menu.post(event.x_root, event.y_root)

        # Bind menu to table frames recursively
        def bind_table_menu_recursively(widget):
            widget.bind("<Button-3>", show_table_menu)
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    bind_table_menu_recursively(child)

        # Bind menu to category buttons
        for btn in self.category_buttons.values():
            btn.bind("<Button-3>", show_category_menu)

        # Bind menu to table widgets and all their children
        for table_id, table_widget in self.table_widgets.items():
            for key, value in table_widget.items():
                # Only bind to actual widgets, not numeric values
                if isinstance(value, (tk.Widget, tk.BaseWidget)):
                    try:
                        bind_table_menu_recursively(value)
                    except:
                        pass

    def update_table_submenu(self):
        """Update the table submenu with all current tables"""
        # Clear current entries
        self.table_submenu.delete(0, 'end')

        # Add all tables
        for table_id in sorted(self.tables.keys()):
            table_name = self.tables[table_id]['name']
            self.table_submenu.add_command(
                label=table_name,
                command=lambda tid=table_id: self.add_selected_item_to_table(tid)
            )

    def add_selected_item_to_table(self, table_id):
        """Add the selected item to the specified table"""
        if self.selected_items:
            item_name = self.selected_items[0]
            price = self.categories[self.current_category][item_name]

            # Check if item already exists in table's category order
            category_orders = self.table_orders[table_id][self.current_category]

            for order_item in category_orders:
                if order_item['name'] == item_name:
                    order_item['quantity'] += 1
                    break
            else:
                # Add new item
                category_orders.append({
                    'name': item_name,
                    'price': price,
                    'quantity': 1
                })

            # Show notification
            table_name = self.tables[table_id]['name']
            self.show_notification(f"{table_name}'e {item_name} eklendi!")

            # Update display if this is the current table
            if self.current_table_id == table_id:
                self.update_current_table_display()

            # Update table total display
            self.update_table_total_display(table_id)

            self.save_data()

    def context_add_item(self):
        """Add selected item to current table from context menu"""
        if self.selected_items and self.current_table_id:
            item_name = self.selected_items[0]
            price = self.categories[self.current_category][item_name]
            self.add_to_current_table_order(item_name, price)

    def context_select_table(self):
        """Select table from context menu"""
        if hasattr(self, 'context_table_id'):
            self.select_table(self.context_table_id)

    def context_start_table(self):
        """Start/pause table from context menu"""
        if hasattr(self, 'context_table_id'):
            self.start_table(self.context_table_id)

    def context_stop_table(self):
        """Stop table from context menu"""
        if hasattr(self, 'context_table_id'):
            self.stop_table(self.context_table_id)

    def context_edit_table(self):
        """Edit table from context menu"""
        if hasattr(self, 'context_table_id'):
            self.edit_table(self.context_table_id)

    def context_delete_table(self):
        """Delete table from context menu"""
        if hasattr(self, 'context_table_id'):
            self.delete_table(self.context_table_id)

    def add_item(self):
        """Add new item dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Yeni Ürün")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 175
        dialog.geometry(f"500x350+{x}+{y}")

        # Main container with padding
        main_container = tk.Frame(dialog, bg='white')
        main_container.pack(fill='both', expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(main_container, text="Yeni Ürün Ekle",
                               font=('Arial', 16, 'bold'), bg='white')
        title_label.pack(pady=(0, 20))

        # Input section
        input_frame = tk.Frame(main_container, bg='white')
        input_frame.pack(fill='x', pady=20)

        # Name input
        tk.Label(input_frame, text="Ürün adı:", font=('Arial', 12), bg='white').pack(pady=(0, 5))
        name_entry = tk.Entry(input_frame, font=('Arial', 12), width=35, relief='solid', bd=1)
        name_entry.pack(pady=(0, 15))
        name_entry.focus()

        # Price input
        tk.Label(input_frame, text="Fiyat (TL):", font=('Arial', 12), bg='white').pack(pady=(0, 5))
        price_entry = tk.Entry(input_frame, font=('Arial', 12), width=35, relief='solid', bd=1)
        price_entry.pack(pady=(0, 15))

        # Spacer
        spacer = tk.Frame(main_container, bg='white', height=30)
        spacer.pack(fill='x')

        # Button frame at bottom
        btn_frame = tk.Frame(main_container, bg='white')
        btn_frame.pack(side='bottom', fill='x', pady=(20, 0))

        def save_item():
            name = name_entry.get().strip()
            try:
                price = float(price_entry.get())
                if name and price > 0:
                    # Format price to remove unnecessary decimals
                    if price == int(price):
                        formatted_price = int(price)
                    else:
                        formatted_price = price

                    self.categories[self.current_category][name] = formatted_price
                    self.show_category(self.current_category)

                    # Update quick add items for all tables
                    for table_id in self.tables:
                        if hasattr(self, 'table_widgets') and table_id in self.table_widgets:
                            try:
                                if self.table_quickadd_shown.get(table_id) == self.current_category:
                                    self.update_table_quickadd_items(table_id, self.current_category)
                            except:
                                pass

                    self.save_data()
                    dialog.destroy()

                    # Show notification
                    self.show_notification(f"Yeni ürün eklendi: {name} - {formatted_price} TL")
                else:
                    messagebox.showerror("Hata", "Lütfen geçerli bir ad ve fiyat girin!")
            except ValueError:
                messagebox.showerror("Hata", "Lütfen geçerli bir fiyat girin!")

        tk.Button(btn_frame, text="Kaydet", command=save_item,
                  bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'),
                  width=12, height=2, relief='flat', cursor='hand2').pack(side='left', padx=(0, 10))
        tk.Button(btn_frame, text="İptal", command=dialog.destroy,
                  bg='#f44336', fg='white', font=('Arial', 12, 'bold'),
                  width=12, height=2, relief='flat', cursor='hand2').pack(side='left')

    def edit_item(self):
        """Edit selected item"""
        if len(self.selected_items) != 1:
            messagebox.showwarning("Uyarı", "Lütfen düzenlemek istediğiniz tek bir ürünü seçin!")
            return

        item_name = self.selected_items[0]
        current_price = self.categories[self.current_category][item_name]

        dialog = tk.Toplevel(self.root)
        dialog.title("Ürün Düzenle")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 175
        dialog.geometry(f"500x350+{x}+{y}")

        # Main container with padding
        main_container = tk.Frame(dialog, bg='white')
        main_container.pack(fill='both', expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(main_container, text="Ürün Düzenle",
                               font=('Arial', 16, 'bold'), bg='white')
        title_label.pack(pady=(0, 20))

        # Input section
        input_frame = tk.Frame(main_container, bg='white')
        input_frame.pack(fill='x', pady=20)

        # Name input
        tk.Label(input_frame, text="Ürün adı:", font=('Arial', 12), bg='white').pack(pady=(0, 5))
        name_entry = tk.Entry(input_frame, font=('Arial', 12), width=35, relief='solid', bd=1)
        name_entry.pack(pady=(0, 15))
        name_entry.insert(0, item_name)
        name_entry.focus()

        # Price input
        tk.Label(input_frame, text="Fiyat (TL):", font=('Arial', 12), bg='white').pack(pady=(0, 5))
        price_entry = tk.Entry(input_frame, font=('Arial', 12), width=35, relief='solid', bd=1)
        price_entry.pack(pady=(0, 15))

        # Format price display in entry field
        if current_price == int(current_price):
            price_entry.insert(0, str(int(current_price)))
        else:
            price_entry.insert(0, str(current_price))

        # Spacer
        spacer = tk.Frame(main_container, bg='white', height=30)
        spacer.pack(fill='x')

        # Button frame at bottom
        btn_frame = tk.Frame(main_container, bg='white')
        btn_frame.pack(side='bottom', fill='x', pady=(20, 0))

        def save_changes():
            new_name = name_entry.get().strip()
            try:
                new_price = float(price_entry.get())
                if new_name and new_price > 0:
                    # Format price to remove unnecessary decimals
                    if new_price == int(new_price):
                        formatted_price = int(new_price)
                    else:
                        formatted_price = new_price

                    del self.categories[self.current_category][item_name]
                    self.categories[self.current_category][new_name] = formatted_price
                    self.selected_items = []
                    self.show_category(self.current_category)

                    # Update quick add items for all tables
                    for table_id in self.tables:
                        if hasattr(self, 'table_widgets') and table_id in self.table_widgets:
                            try:
                                if self.table_quickadd_shown.get(table_id) == self.current_category:
                                    self.update_table_quickadd_items(table_id, self.current_category)
                            except:
                                pass

                    self.save_data()
                    dialog.destroy()

                    # Show notification
                    self.show_notification(f"Ürün düzenlendi: {new_name} - {formatted_price} TL")
                else:
                    messagebox.showerror("Hata", "Lütfen geçerli bir ad ve fiyat girin!")
            except ValueError:
                messagebox.showerror("Hata", "Lütfen geçerli bir fiyat girin!")

        tk.Button(btn_frame, text="Kaydet", command=save_changes,
                  bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'),
                  width=12, height=2, relief='flat', cursor='hand2').pack(side='left', padx=(0, 10))
        tk.Button(btn_frame, text="İptal", command=dialog.destroy,
                  bg='#f44336', fg='white', font=('Arial', 12, 'bold'),
                  width=12, height=2, relief='flat', cursor='hand2').pack(side='left')

    def delete_items(self):
        """Delete selected items with fixed right-click menu handling"""
        if not self.selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz ürün(ler)i seçin!")
            return

        item_names = ", ".join(self.selected_items)
        result = messagebox.askyesno("Ürün Sil",
                                     f"Seçili ürün(ler)i silmek istediğinizden emin misiniz?\n\n{item_names}")
        if result:
            # Save deleted items to check if we need to recreate bindings
            deleted_items = []
            for item_name in self.selected_items:
                if item_name in self.categories[self.current_category]:
                    deleted_items.append(item_name)
                    del self.categories[self.current_category][item_name]

            self.selected_items = []

            # First clear the frame
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            # Then recreate all items with proper bindings
            self.show_category(self.current_category)

            # Re-bind the right-click menus for the newly created items
            def rebind_item_menu_recursively(widget):
                widget.bind("<Button-3>", lambda e: self.show_item_right_click_menu(e))
                for child in widget.winfo_children():
                    rebind_item_menu_recursively(child)

            rebind_item_menu_recursively(self.scrollable_frame)

            # Update quick add items for all tables
            for table_id in self.tables:
                if hasattr(self, 'table_widgets') and table_id in self.table_widgets:
                    try:
                        if self.table_quickadd_shown.get(table_id) == self.current_category:
                            self.update_table_quickadd_items(table_id, self.current_category)
                    except:
                        pass

            self.save_data()

            # Show notification
            self.show_notification(f"Ürün(ler) silindi: {item_names}")

    def show_item_right_click_menu(self, event, item_name=None):
        """Handler for right-click on items"""
        if item_name is None:
            widget = event.widget
            # Find the item name
            item_name = None

            # Try to get text directly from widget if it's a label
            if isinstance(widget, tk.Label) and hasattr(widget, 'cget'):
                try:
                    text = widget.cget('text')
                    if ' - ' in text:
                        item_name = text.split(' - ')[0]
                except:
                    pass

            # If not found, look at parent's children
            if not item_name and hasattr(widget, 'winfo_parent'):
                try:
                    parent = self.root.nametowidget(widget.winfo_parent())
                    for child in parent.winfo_children():
                        if isinstance(child, tk.Label) and hasattr(child, 'cget'):
                            try:
                                text = child.cget('text')
                                if ' - ' in text:
                                    item_name = text.split(' - ')[0]
                                    break
                            except:
                                pass
                except:
                    pass

        # Print debug info
        print(f"Right-click menu: item_name={item_name}, current_category={self.current_category}")

        # Make sure current category exists
        if self.current_category not in self.categories:
            print(f"Warning: current category {self.current_category} not found in categories")
            return

        # Check if item exists in current category
        if item_name and item_name in self.categories.get(self.current_category, {}):
            self.selected_items = [item_name]
            self.update_item_visual_feedback()
            self.update_edit_button_state()
            # Update table submenu before showing
            self.update_table_submenu()
            self.item_menu.post(event.x_root, event.y_root)

    def add_new_table(self):
        """Add a new table"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Yeni Masa Ekle")
        dialog.geometry("500x650")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 325
        dialog.geometry(f"500x650+{x}+{y}")

        # Name input
        tk.Label(dialog, text="Masa Adı:", font=('Arial', 12)).pack(pady=10)
        name_entry = tk.Entry(dialog, font=('Arial', 12), width=30)
        name_entry.pack(pady=5)
        name_entry.focus()

        # Rate input
        tk.Label(dialog, text="Saatlik Ücret (TL):", font=('Arial', 12)).pack(pady=10)
        rate_entry = tk.Entry(dialog, font=('Arial', 12), width=30)
        rate_entry.pack(pady=5)
        rate_entry.insert(0, "50")

        # Table type selection
        tk.Label(dialog, text="Masa Türü:", font=('Arial', 12)).pack(pady=10)
        type_var = tk.StringVar(value="Normal Bilardo")
        type_frame = tk.Frame(dialog)
        type_frame.pack(pady=5)

        tk.Radiobutton(type_frame, text="Normal Bilardo", variable=type_var,
                       value="Normal Bilardo", font=('Arial', 10)).pack(anchor='w')
        tk.Radiobutton(type_frame, text="Amerikan Bilardo", variable=type_var,
                       value="Amerikan Bilardo", font=('Arial', 10)).pack(anchor='w')

        # Custom type option
        custom_frame = tk.Frame(type_frame)
        custom_frame.pack(anchor='w')

        custom_radio = tk.Radiobutton(custom_frame, text="Özel:", variable=type_var,
                                      value="custom", font=('Arial', 10))
        custom_radio.pack(side='left')

        custom_entry = tk.Entry(custom_frame, font=('Arial', 10), width=20)
        custom_entry.pack(side='left', padx=5)

        # Color selection
        tk.Label(dialog, text="Renk:", font=('Arial', 12)).pack(pady=10)
        color_var = tk.StringVar(value='#4CAF50')
        color_frame = tk.Frame(dialog)
        color_frame.pack(pady=5)

        colors = [('#4CAF50', 'Yeşil'), ('#2196F3', 'Mavi'), ('#FF9800', 'Turuncu'),
                  ('#9C27B0', 'Mor'), ('#F44336', 'Kırmızı'), ('#795548', 'Kahverengi')]

        for color_code, color_name in colors:
            tk.Radiobutton(color_frame, text=color_name, variable=color_var,
                           value=color_code, font=('Arial', 10)).pack(anchor='w')

        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(side='bottom', pady=20)

        def create_table():
            name = name_entry.get().strip()
            try:
                rate = float(rate_entry.get())
                selected_type = type_var.get()

                if selected_type == "custom":
                    table_type = custom_entry.get().strip()
                    if not table_type:
                        messagebox.showerror("Hata", "Lütfen özel masa türünü girin!")
                        return
                else:
                    table_type = selected_type

                color = color_var.get()

                if name and rate > 0:
                    self.table_counter += 1
                    new_table_id = self.table_counter

                    self.tables[new_table_id] = {
                        'name': name,
                        'active': False,
                        'paused': False,
                        'start_time': None,
                        'pause_time': None,
                        'total_pause_duration': 0,
                        'rate': rate,
                        'type': table_type,
                        'color': color,
                        'total_cost': 0,
                        'timer_type': None,
                        'preset_duration': None,
                        'remaining_time': None
                    }

                    # Initialize quick add state
                    self.table_quickadd_shown[new_table_id] = False

                    # Initialize empty orders for new table
                    self.table_orders[new_table_id] = {
                        'Yiyecekler': [],
                        'İçecekler': [],
                        'billiard_charges': []
                    }

                    # Add table selection button
                    table_color = color
                    btn = tk.Button(self.root.children[list(self.root.children.keys())[0]].children[
                                        list(self.root.children[list(self.root.children.keys())[0]].children.keys())[
                                            1]],
                                    text=name, font=('Arial', 12, 'bold'),
                                    bg=table_color, fg='white', width=12, height=2,
                                    command=lambda tid=new_table_id: self.select_table(tid))
                    btn.pack(side='left', padx=5)
                    self.table_buttons[new_table_id] = btn

                    self.create_table_widget(new_table_id)
                    self.save_data()
                    dialog.destroy()

                    # Show notification
                    self.show_notification(f"Yeni masa eklendi: {name}")
                else:
                    messagebox.showerror("Hata", "Lütfen geçerli bir ad ve ücret girin!")
            except ValueError:
                messagebox.showerror("Hata", "Lütfen geçerli bir ücret girin!")

        tk.Button(btn_frame, text="Oluştur", command=create_table,
                  bg='#4CAF50', fg='white', font=('Arial', 12), width=10).pack(side='left', padx=10)
        tk.Button(btn_frame, text="İptal", command=dialog.destroy,
                  bg='#f44336', fg='white', font=('Arial', 12), width=10).pack(side='left', padx=10)

    def edit_table(self, table_id):
        """Edit table properties"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Masa Düzenle")
        dialog.geometry("500x650")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 325
        dialog.geometry(f"500x650+{x}+{y}")

        # Name input
        tk.Label(dialog, text="Masa Adı:", font=('Arial', 12)).pack(pady=10)
        name_entry = tk.Entry(dialog, font=('Arial', 12), width=30)
        name_entry.pack(pady=5)
        name_entry.insert(0, self.tables[table_id]['name'])
        name_entry.focus()

        # Rate input
        tk.Label(dialog, text="Saatlik Ücret (TL):", font=('Arial', 12)).pack(pady=10)
        rate_entry = tk.Entry(dialog, font=('Arial', 12), width=30)
        rate_entry.pack(pady=5)
        rate_entry.insert(0, str(self.tables[table_id]['rate']))

        # Table type selection
        tk.Label(dialog, text="Masa Türü:", font=('Arial', 12)).pack(pady=10)
        type_var = tk.StringVar(value=self.tables[table_id]['type'])
        type_frame = tk.Frame(dialog)
        type_frame.pack(pady=5)

        tk.Radiobutton(type_frame, text="Normal Bilardo", variable=type_var,
                       value="Normal Bilardo", font=('Arial', 10)).pack(anchor='w')
        tk.Radiobutton(type_frame, text="Amerikan Bilardo", variable=type_var,
                       value="Amerikan Bilardo", font=('Arial', 10)).pack(anchor='w')

        # Custom type option
        custom_frame = tk.Frame(type_frame)
        custom_frame.pack(anchor='w')

        custom_radio = tk.Radiobutton(custom_frame, text="Özel:", variable=type_var,
                                      value="custom", font=('Arial', 10))
        custom_radio.pack(side='left')

        custom_entry = tk.Entry(custom_frame, font=('Arial', 10), width=20)
        custom_entry.pack(side='left', padx=5)
        if self.tables[table_id]['type'] not in ["Normal Bilardo", "Amerikan Bilardo"]:
            type_var.set("custom")
            custom_entry.insert(0, self.tables[table_id]['type'])

        # Color selection
        tk.Label(dialog, text="Renk:", font=('Arial', 12)).pack(pady=10)
        color_var = tk.StringVar(value=self.tables[table_id]['color'])
        color_frame = tk.Frame(dialog)
        color_frame.pack(pady=5)

        colors = [('#4CAF50', 'Yeşil'), ('#2196F3', 'Mavi'), ('#FF9800', 'Turuncu'),
                  ('#9C27B0', 'Mor'), ('#F44336', 'Kırmızı'), ('#795548', 'Kahverengi')]

        for color_code, color_name in colors:
            tk.Radiobutton(color_frame, text=color_name, variable=color_var,
                           value=color_code, font=('Arial', 10)).pack(anchor='w')

        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(side='bottom', pady=20)

        def save_changes():
            new_name = name_entry.get().strip()
            try:
                new_rate = float(rate_entry.get())
                selected_type = type_var.get()

                if selected_type == "custom":
                    new_type = custom_entry.get().strip()
                    if not new_type:
                        messagebox.showerror("Hata", "Lütfen özel masa türünü girin!")
                        return
                else:
                    new_type = selected_type

                new_color = color_var.get()

                if new_name and new_rate > 0:
                    old_name = self.tables[table_id]['name']
                    self.tables[table_id]['name'] = new_name
                    self.tables[table_id]['rate'] = new_rate
                    self.tables[table_id]['type'] = new_type
                    self.tables[table_id]['color'] = new_color

                    # Update UI
                    self.table_widgets[table_id]['table_label'].config(
                        text=f"{new_name} {'(Seçili)' if table_id == self.current_table_id else ''}")
                    self.table_widgets[table_id]['rate'].config(text=f"Saatlik Ücret: {new_rate} TL")
                    self.table_widgets[table_id]['type'].config(text=f"Masa Türü: {new_type}")

                    # Update header color if not active
                    if not self.tables[table_id]['active']:
                        self.table_widgets[table_id]['header'].config(bg=new_color)
                        self.table_widgets[table_id]['status'].config(bg=new_color)
                        self.table_widgets[table_id]['table_label'].config(bg=new_color)

                    # Update table selection button
                    if table_id in self.table_buttons:
                        self.table_buttons[table_id].config(text=new_name, bg=new_color)

                    # Update current table display if this is the selected table
                    if self.current_table_id == table_id:
                        self.current_table_label.config(text=f"Seçili Masa: {new_name}")

                    self.save_data()
                    dialog.destroy()

                    # Show notification
                    self.show_notification(f"Masa düzenlendi: {old_name} -> {new_name}")
                else:
                    messagebox.showerror("Hata", "Lütfen geçerli bir ad ve ücret girin!")
            except ValueError:
                messagebox.showerror("Hata", "Lütfen geçerli bir ücret girin!")

        tk.Button(btn_frame, text="Kaydet", command=save_changes,
                  bg='#4CAF50', fg='white', font=('Arial', 12), width=10).pack(side='left', padx=10)
        tk.Button(btn_frame, text="İptal", command=dialog.destroy,
                  bg='#f44336', fg='white', font=('Arial', 12), width=10).pack(side='left', padx=10)

    def delete_table(self, table_id):
        """Delete a table"""
        if table_id in self.tables:
            result = messagebox.askyesno("Masa Sil",
                                         f"'{self.tables[table_id]['name']}' masasını silmek istediğinizden emin misiniz?")
            if result:
                table_name = self.tables[table_id]['name']

                # Stop timer if active
                if table_id in self.running_timers:
                    del self.running_timers[table_id]

                # Remove from tables and orders
                del self.tables[table_id]
                if table_id in self.table_orders:
                    del self.table_orders[table_id]

                # Remove from quickadd tracking
                if table_id in self.table_quickadd_shown:
                    del self.table_quickadd_shown[table_id]

                # Remove from change calculator
                if table_id in self.change_frames:
                    self.change_frames[table_id].destroy()
                    del self.change_frames[table_id]
                if table_id in self.payment_entries:
                    del self.payment_entries[table_id]
                if table_id in self.change_labels:
                    del self.change_labels[table_id]

                # Remove widgets
                self.table_widgets[table_id]['frame'].destroy()
                del self.table_widgets[table_id]

                # Remove table selection button
                if table_id in self.table_buttons:
                    self.table_buttons[table_id].destroy()
                    del self.table_buttons[table_id]

                # Select another table if current was deleted
                if self.current_table_id == table_id:
                    if self.tables:
                        new_table_id = min(self.tables.keys())
                        self.select_table(new_table_id)
                    else:
                        self.current_table_id = None

                self.save_data()

                # Show notification
                self.show_notification(f"Masa silindi: {table_name}")

    def show_timer_selection_dialog(self, table_id):
        """Show timer selection dialog with editable and clickable custom start time"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Zamanlayıcı Seçimi")
        dialog.geometry("400x450")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 200
        y = (dialog.winfo_screenheight() // 2) - 225
        dialog.geometry(f"400x450+{x}+{y}")

        tk.Label(dialog, text="Zamanlayıcı Türü Seçin",
                 font=('Segoe UI', 14, 'bold')).pack(pady=15)

        # Timer type selection
        timer_var = tk.StringVar(value="unlimited")

        # Simplified timer options
        tk.Radiobutton(dialog, text="Sınırsız", variable=timer_var, value="unlimited",
                       font=('Segoe UI', 12)).pack(pady=5)

        # Only 3 preset times as requested
        presets_frame = tk.Frame(dialog)
        presets_frame.pack(pady=5, fill='x')

        for minutes, text in [(30, "30 Dakika"), (60, "1 Saat"), (120, "2 Saat")]:
            tk.Radiobutton(presets_frame, text=text, variable=timer_var,
                           value=str(minutes), font=('Segoe UI', 12)).pack(pady=3)

        # Add custom start time option
        custom_time_frame = tk.Frame(dialog, pady=15)
        custom_time_frame.pack(pady=10, fill='x')

        tk.Label(custom_time_frame, text="Başlangıç Zamanı:",
                 font=('Segoe UI', 12, 'bold')).pack(pady=5)

        time_frame = tk.Frame(custom_time_frame)
        time_frame.pack()

        # Current time as default
        now = datetime.now()
        hour_var = tk.StringVar(value=now.strftime('%H'))
        minute_var = tk.StringVar(value=now.strftime('%M'))

        # Create a custom hybrid widget for hours - both editable and with spinbox arrows
        tk.Label(time_frame, text="Saat:").pack(side='left')

        hour_frame = tk.Frame(time_frame)
        hour_frame.pack(side='left', padx=5)

        # Custom spinbox with editable field for hours
        hour_spinbox = tk.Spinbox(hour_frame, from_=0, to=23, width=3,
                                  textvariable=hour_var, wrap=True)
        hour_spinbox.pack(side='left')

        # Allow direct editing of the spinbox text
        hour_spinbox.config(state='normal')

        # Create a custom hybrid widget for minutes - both editable and with spinbox arrows
        tk.Label(time_frame, text="Dakika:").pack(side='left')

        minute_frame = tk.Frame(time_frame)
        minute_frame.pack(side='left', padx=5)

        # Custom spinbox with editable field for minutes
        minute_spinbox = tk.Spinbox(minute_frame, from_=0, to=59, width=3,
                                    textvariable=minute_var, wrap=True)
        minute_spinbox.pack(side='left')

        # Allow direct editing of the spinbox text
        minute_spinbox.config(state='normal')

        # Add validation for hour and minute inputs
        def validate_hour(text):
            if text == "":
                return True
            try:
                val = int(text)
                return 0 <= val <= 23
            except ValueError:
                return False

        def validate_minute(text):
            if text == "":
                return True
            try:
                val = int(text)
                return 0 <= val <= 59
            except ValueError:
                return False

        # Register validation commands
        vcmd_hour = dialog.register(validate_hour)
        vcmd_minute = dialog.register(validate_minute)

        # Apply validation to spinboxes
        hour_spinbox.config(validate="key", validatecommand=(vcmd_hour, '%P'))
        minute_spinbox.config(validate="key", validatecommand=(vcmd_minute, '%P'))

        use_custom_time = tk.BooleanVar(value=False)
        custom_time_check = tk.Checkbutton(custom_time_frame, text="Özel başlangıç zamanı kullan",
                                           variable=use_custom_time)
        custom_time_check.pack(pady=5)

        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=15)

        def start_timer():
            selection = timer_var.get()
            custom_start_time = None

            if use_custom_time.get():
                # Parse custom time
                try:
                    custom_hour = int(hour_spinbox.get())
                    custom_minute = int(minute_spinbox.get())

                    # Validate input
                    if not (0 <= custom_hour <= 23 and 0 <= custom_minute <= 59):
                        messagebox.showerror("Hata", "Geçersiz saat veya dakika değeri!")
                        return

                    # Create a datetime object with today's date but custom time
                    custom_start_time = datetime.now().replace(hour=custom_hour, minute=custom_minute, second=0,
                                                               microsecond=0)

                    # If custom time is in the future, assume it's from yesterday
                    if custom_start_time > datetime.now():
                        custom_start_time = custom_start_time - timedelta(days=1)
                except ValueError:
                    messagebox.showerror("Hata", "Geçersiz saat veya dakika!")
                    return

            if selection == "unlimited":
                self.start_unlimited_timer(table_id, custom_start_time)
            else:
                self.start_preset_timer(table_id, int(selection), custom_start_time)
            dialog.destroy()

        tk.Button(btn_frame, text="Başlat", command=start_timer,
                  bg='#4CAF50', fg='white', font=('Segoe UI', 12),
                  width=8).pack(side='left', padx=10)
        tk.Button(btn_frame, text="İptal", command=dialog.destroy,
                  bg='#f44336', fg='white', font=('Segoe UI', 12),
                  width=8).pack(side='left', padx=10)

    def start_unlimited_timer(self, table_id, custom_start_time=None):
        """Start unlimited timer for table with proper custom start time handling"""
        self.tables[table_id]['active'] = True
        self.tables[table_id]['paused'] = False

        # Handle custom start time properly to avoid double counting
        if custom_start_time:
            # Calculate initial elapsed time
            initial_elapsed = datetime.now() - custom_start_time
            initial_elapsed_seconds = initial_elapsed.total_seconds()

            # Store this for display purposes
            self.tables[table_id]['initial_elapsed_seconds'] = initial_elapsed_seconds

            # But for timing purposes, we adjust the start time to be "now"
            # This way, we don't double count the elapsed time in calculations
            self.tables[table_id]['start_time'] = datetime.now()

            # Calculate initial cost - this will be the only place we calculate it
            if initial_elapsed_seconds > 60:  # More than a minute
                initial_hours = initial_elapsed_seconds / 3600
                initial_cost = initial_hours * self.tables[table_id]['rate']
                self.tables[table_id]['initial_cost'] = initial_cost
            else:
                self.tables[table_id]['initial_cost'] = 0
        else:
            # Standard start with current time
            self.tables[table_id]['start_time'] = datetime.now()
            self.tables[table_id]['initial_elapsed_seconds'] = 0
            self.tables[table_id]['initial_cost'] = 0

        self.tables[table_id]['total_pause_duration'] = 0
        self.tables[table_id]['timer_type'] = 'unlimited'
        self.running_timers[table_id] = True

        # Update UI
        self.table_widgets[table_id]['status'].config(text="Masa Aktif")
        self.table_widgets[table_id]['header'].config(bg='#f44336')
        self.table_widgets[table_id]['status'].config(bg='#f44336')
        self.table_widgets[table_id]['table_label'].config(bg='#f44336')
        self.table_widgets[table_id]['start_btn'].config(text="Duraklat", bg='#ff9800')
        self.table_widgets[table_id]['stop_btn'].config(state='normal', bg='#f44336')

        # DON'T show the add time button for unlimited timer
        self.table_widgets[table_id]['add_time_btn'].pack_forget()

        # Update table selection button color
        if table_id in self.table_buttons:
            relief = 'sunken' if table_id == self.current_table_id else 'raised'
            self.table_buttons[table_id].config(bg='#f44336', relief=relief)

        # Show notification
        if custom_start_time:
            elapsed_str = str(timedelta(seconds=int(initial_elapsed_seconds)))
            self.show_notification(f"{self.tables[table_id]['name']} başlatıldı (Sınırsız, Geçen süre: {elapsed_str})")
        else:
            self.show_notification(f"{self.tables[table_id]['name']} başlatıldı (Sınırsız)")

    def start_preset_timer(self, table_id, minutes, custom_start_time=None):
        """Start preset timer for table with proper custom start time handling"""
        self.tables[table_id]['active'] = True
        self.tables[table_id]['paused'] = False

        # Use custom start time if provided, otherwise use current time
        if custom_start_time:
            # For custom start time, we calculate how much time has already elapsed
            initial_elapsed = datetime.now() - custom_start_time
            initial_elapsed_seconds = initial_elapsed.total_seconds()

            # Store this elapsed time to display correctly
            self.tables[table_id]['initial_elapsed_seconds'] = initial_elapsed_seconds

            # But for timing purposes, we adjust the start time to be "now - initial_elapsed"
            # This way, we don't double count the elapsed time
            self.tables[table_id]['start_time'] = datetime.now()

            # Calculate initial cost - this will be the only place we calculate it
            if initial_elapsed_seconds > 60:  # More than a minute
                initial_hours = initial_elapsed_seconds / 3600
                initial_cost = initial_hours * self.tables[table_id]['rate']
                self.tables[table_id]['initial_cost'] = initial_cost
            else:
                self.tables[table_id]['initial_cost'] = 0

            # Adjust remaining time for the preset timer
            remaining_seconds = max(0, minutes * 60 - initial_elapsed_seconds)
            self.tables[table_id]['remaining_time'] = remaining_seconds
        else:
            # Standard timer, no custom start time
            self.tables[table_id]['start_time'] = datetime.now()
            self.tables[table_id]['initial_elapsed_seconds'] = 0
            self.tables[table_id]['initial_cost'] = 0
            self.tables[table_id]['remaining_time'] = minutes * 60

        self.tables[table_id]['total_pause_duration'] = 0
        self.tables[table_id]['timer_type'] = 'preset'
        self.tables[table_id]['preset_duration'] = minutes
        self.tables[table_id]['bonus_seconds'] = 0  # Track added time
        self.running_timers[table_id] = True

        # Update UI
        self.table_widgets[table_id]['status'].config(text="Masa Aktif")
        self.table_widgets[table_id]['header'].config(bg='#f44336')
        self.table_widgets[table_id]['status'].config(bg='#f44336')
        self.table_widgets[table_id]['table_label'].config(bg='#f44336')
        self.table_widgets[table_id]['start_btn'].config(text="Duraklat", bg='#ff9800')
        self.table_widgets[table_id]['stop_btn'].config(state='normal', bg='#f44336')

        # Show add time button for preset timers only
        self.table_widgets[table_id]['add_time_btn'].pack(side='left', padx=2)

        # Update table selection button color
        if table_id in self.table_buttons:
            relief = 'sunken' if table_id == self.current_table_id else 'raised'
            self.table_buttons[table_id].config(bg='#f44336', relief=relief)

        # Show notification
        time_text = f"{minutes} Dakika" if minutes < 60 else f"{minutes // 60} Saat {minutes % 60} Dakika" if minutes % 60 else f"{minutes // 60} Saat"

        if custom_start_time:
            elapsed_str = str(timedelta(seconds=int(initial_elapsed_seconds)))
            self.show_notification(
                f"{self.tables[table_id]['name']} başlatıldı ({time_text}, Geçen süre: {elapsed_str})")
        else:
            self.show_notification(f"{self.tables[table_id]['name']} başlatıldı ({time_text})")

    def add_time_to_table(self, table_id):
        """Show dialog to add time to a table"""
        if not self.tables[table_id]['active']:
            messagebox.showwarning("Uyarı", "Masa aktif değil!")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Ek Süre Ekle")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 150
        y = (dialog.winfo_screenheight() // 2) - 100
        dialog.geometry(f"300x200+{x}+{y}")

        tk.Label(dialog, text="Eklenecek Süre",
                 font=('Segoe UI', 12, 'bold')).pack(pady=10)

        # Create buttons for adding time
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)

        time_options = [
            (15, "15 Dakika"),
            (30, "30 Dakika"),
            (60, "1 Saat")
        ]

        for minutes, label in time_options:
            tk.Button(
                btn_frame,
                text=label,
                command=lambda m=minutes: self.extend_table_time(table_id, m, dialog),
                width=10,
                height=2,
                bg='#4CAF50',
                fg='white'
            ).pack(side='left', padx=5, pady=10)

        # Cancel button
        tk.Button(
            dialog,
            text="İptal",
            command=dialog.destroy,
            width=10,
            bg='#f44336',
            fg='white'
        ).pack(pady=10)

    def extend_table_time(self, table_id, minutes_to_add, dialog=None):
        """Add time to a table"""
        if not self.tables[table_id]['active']:
            return

        seconds_to_add = minutes_to_add * 60
        table = self.tables[table_id]

        # For preset timers, add to the remaining time
        if table['timer_type'] == 'preset':
            # Add to remaining time
            if 'remaining_time' in table:
                table['remaining_time'] += seconds_to_add

            # Track bonus time for cost calculation
            if 'bonus_seconds' not in table:
                table['bonus_seconds'] = 0
            table['bonus_seconds'] += seconds_to_add

            # Calculate additional cost
            hours_added = minutes_to_add / 60
            additional_cost = hours_added * table['rate']

            # Show notification with cost
            self.show_notification(
                f"{table['name']} masasına {minutes_to_add} dakika ({additional_cost:.2f} TL) eklendi!"
            )
        else:
            # For unlimited timers, just track bonus time for informational purposes
            if 'bonus_seconds' not in table:
                table['bonus_seconds'] = 0
            table['bonus_seconds'] += seconds_to_add

            # Calculate additional cost
            hours_added = minutes_to_add / 60
            additional_cost = hours_added * table['rate']

            # Show notification with cost
            self.show_notification(
                f"{table['name']} masasına {minutes_to_add} dakika ({additional_cost:.2f} TL) eklendi!"
            )

        # Close the dialog if provided
        if dialog:
            dialog.destroy()

    def start_table(self, table_id):
        """Start or pause/resume table"""
        if not self.tables[table_id]['active']:
            # Show timer selection dialog
            self.show_timer_selection_dialog(table_id)
        else:
            # Pause or resume
            if self.tables[table_id]['paused']:
                # Resume
                self.tables[table_id]['paused'] = False
                # Calculate total pause duration
                pause_duration = datetime.now() - self.tables[table_id]['pause_time']
                self.tables[table_id]['total_pause_duration'] += pause_duration.total_seconds()

                self.table_widgets[table_id]['start_btn'].config(text="Duraklat", bg='#ff9800')
                self.table_widgets[table_id]['header'].config(bg='#f44336')
                self.table_widgets[table_id]['status'].config(bg='#f44336')
                self.table_widgets[table_id]['table_label'].config(bg='#f44336')

                # Update table selection button color to active (red)
                if table_id in self.table_buttons:
                    # Preserve the selected state (sunken relief) if this is the current table
                    relief = 'sunken' if table_id == self.current_table_id else 'raised'
                    self.table_buttons[table_id].config(bg='#f44336', relief=relief)

                self.running_timers[table_id] = True

                # Show notification
                self.show_notification(f"{self.tables[table_id]['name']} devam ediyor")
            else:
                # Pause
                self.tables[table_id]['paused'] = True
                self.tables[table_id]['pause_time'] = datetime.now()
                self.table_widgets[table_id]['start_btn'].config(text="Devam Et", bg='#4CAF50')
                # Change header color to orange when paused
                self.table_widgets[table_id]['header'].config(bg='#ff9800')
                self.table_widgets[table_id]['status'].config(bg='#ff9800')
                self.table_widgets[table_id]['table_label'].config(bg='#ff9800')

                # Update table selection button color to paused (orange)
                if table_id in self.table_buttons:
                    # Preserve the selected state (sunken relief) if this is the current table
                    relief = 'sunken' if table_id == self.current_table_id else 'raised'
                    self.table_buttons[table_id].config(bg='#ff9800', relief=relief)

                if table_id in self.running_timers:
                    del self.running_timers[table_id]

                # Show notification
                self.show_notification(f"{self.tables[table_id]['name']} duraklatıldı")

    def stop_table(self, table_id):
        """Stop table and calculate cost with minimum play time check"""
        if self.tables[table_id]['active']:
            # Calculate duration and cost
            start_time = self.tables[table_id]['start_time']
            if start_time:
                # Calculate actual duration including any initial time
                current_time = datetime.now()
                elapsed = current_time - start_time
                actual_elapsed_seconds = elapsed.total_seconds() - self.tables[table_id]['total_pause_duration']

                # Include initial elapsed time if using custom start time
                total_elapsed_seconds = actual_elapsed_seconds
                if 'initial_elapsed_seconds' in self.tables[table_id]:
                    total_elapsed_seconds += self.tables[table_id]['initial_elapsed_seconds']

                # Create duration string for display
                total_elapsed = timedelta(seconds=int(total_elapsed_seconds))
                duration_str = str(total_elapsed)

                # Check if total duration is less than 1 minute (60 seconds)
                if total_elapsed_seconds < 60:
                    # Reset table first to stop timer updates
                    self.reset_table(table_id)

                    # Update display if this is the current table
                    if self.current_table_id == table_id:
                        self.update_current_table_display()

                    # Show notification about minimum time requirement
                    table_name = self.tables[table_id]['name']
                    messagebox.showinfo("Bilgi",
                                        f"{table_name} - Bilardo oynama süresi 1 dakikanın altında olduğu için ücret eklenmedi.\n"
                                        f"Süre: {duration_str}")
                    self.show_notification(f"{table_name} - Süre 1 dakikadan az, ücret eklenmedi.")

                    # Update UI
                    self.update_table_total_display(table_id)
                    return

                # For play times over 1 minute, continue with normal process
                # Get current cost from the table widget
                cost = self.table_widgets[table_id]['current_billiard_cost']

                # Add to table's billiard charges
                self.table_orders[table_id]['billiard_charges'].append({
                    'table_name': self.tables[table_id]['name'],
                    'duration': duration_str,
                    'cost': round(cost, 2)
                })

                # Get current total for the dialog
                yiyecek_total = sum(
                    item['price'] * item['quantity'] for item in self.table_orders[table_id]['Yiyecekler'])
                icecek_total = sum(
                    item['price'] * item['quantity'] for item in self.table_orders[table_id]['İçecekler'])

                # Calculate current total (all previous billiard + current billiard + items)
                previous_billiard = sum(c['cost'] for c in self.table_orders[table_id]['billiard_charges'][:-1])
                total = yiyecek_total + icecek_total + previous_billiard + cost

                # Reset table BEFORE showing dialog to stop timer updates
                self.reset_table(table_id)

                # Update display if this is the current table
                if self.current_table_id == table_id:
                    self.update_current_table_display()

                # Show completion message with total
                messagebox.showinfo("Hesap",
                                    f"{self.tables[table_id]['name']}\nSüre: {duration_str}\n"
                                    f"Bilardo Ücreti: {cost:.2f} TL\n"
                                    f"Toplam Tutar: {total:.2f} TL")

                self.save_data()

                # Show notification
                self.show_notification(f"{self.tables[table_id]['name']} hesabı: {cost:.2f} TL")
            else:
                # Reset table if no start time
                self.reset_table(table_id)

            # Explicitly reset the table selection button color
            original_color = self.tables[table_id]['color']
            if table_id in self.table_buttons:
                relief = 'sunken' if table_id == self.current_table_id else 'raised'
                self.table_buttons[table_id].config(bg=original_color, relief=relief)

            # Update total cost display
            self.update_table_total_display(table_id)

    def reset_table(self, table_id):
        """Reset table to initial state"""
        if table_id in self.tables:
            self.tables[table_id]['active'] = False
            self.tables[table_id]['paused'] = False
            self.tables[table_id]['start_time'] = None
            self.tables[table_id]['pause_time'] = None
            self.tables[table_id]['total_pause_duration'] = 0
            self.tables[table_id]['total_cost'] = 0
            self.tables[table_id]['timer_type'] = None
            self.tables[table_id]['preset_duration'] = None
            self.tables[table_id]['remaining_time'] = None

            # Clear any custom time data
            if 'initial_elapsed_seconds' in self.tables[table_id]:
                del self.tables[table_id]['initial_elapsed_seconds']
            if 'initial_cost' in self.tables[table_id]:
                del self.tables[table_id]['initial_cost']
            if 'bonus_seconds' in self.tables[table_id]:
                del self.tables[table_id]['bonus_seconds']

            if table_id in self.running_timers:
                del self.running_timers[table_id]

            # Update UI
            original_color = self.tables[table_id]['color']
            self.table_widgets[table_id]['status'].config(text="Masa Boş", bg=original_color)
            self.table_widgets[table_id]['header'].config(bg=original_color)
            self.table_widgets[table_id]['table_label'].config(bg=original_color)
            self.table_widgets[table_id]['time'].config(text="Süre: 00:00:00")
            self.table_widgets[table_id]['cost'].config(text="")
            self.table_widgets[table_id]['start_btn'].config(text="Başlat", bg='#4CAF50')
            self.table_widgets[table_id]['stop_btn'].config(state='disabled', bg='#9E9E9E')

            # Hide the add time button when table is reset
            self.table_widgets[table_id]['add_time_btn'].pack_forget()

            # Reset current billiard cost
            self.table_widgets[table_id]['current_billiard_cost'] = 0.0

            # Reset table selection button color
            if table_id in self.table_buttons:
                # Preserve the selected state (sunken relief) if this is the current table
                relief = 'sunken' if table_id == self.current_table_id else 'raised'
                self.table_buttons[table_id].config(bg=original_color, relief=relief)

    def start_timer_thread(self):
        """Start the timer update thread with correct pricing for custom start times"""

        def update_timers():
            while True:
                for table_id in list(self.running_timers.keys()):
                    if table_id in self.tables and self.tables[table_id]['active'] and not self.tables[table_id][
                        'paused']:
                        table = self.tables[table_id]
                        start_time = table['start_time']

                        if start_time:
                            current_time = datetime.now()
                            # Get the time elapsed since we started the timer (not since custom start time)
                            elapsed = current_time - start_time
                            actual_elapsed_seconds = elapsed.total_seconds() - table['total_pause_duration']

                            # For display purposes, we add initial_elapsed_seconds
                            display_elapsed_seconds = actual_elapsed_seconds
                            if 'initial_elapsed_seconds' in table:
                                display_elapsed_seconds += table['initial_elapsed_seconds']

                            # Format for display
                            display_elapsed = timedelta(seconds=int(display_elapsed_seconds))

                            if table['timer_type'] == 'unlimited':
                                # Count up - show total elapsed time including initial time
                                duration_str = str(display_elapsed)
                                self.table_widgets[table_id]['time'].config(text=f"Süre: {duration_str}")

                                # For cost calculation, only count the current timer's elapsed time
                                hours = actual_elapsed_seconds / 3600
                                timer_cost = hours * table['rate']

                                # Add initial cost, which was calculated once when starting the timer
                                initial_cost = table.get('initial_cost', 0)
                                current_cost = timer_cost + initial_cost

                                self.table_widgets[table_id]['cost'].config(text=f"Anlık Ücret: {current_cost:.2f} TL")
                                self.table_widgets[table_id]['current_billiard_cost'] = current_cost

                            elif table['timer_type'] == 'preset':
                                # For preset timers, calculate remaining time based on preset duration minus display_elapsed
                                preset_duration = table['preset_duration'] * 60  # convert to seconds

                                # Add any bonus seconds from extensions
                                if 'bonus_seconds' in table:
                                    preset_duration += table['bonus_seconds']

                                # Calculate remaining seconds for display
                                remaining_seconds = preset_duration - display_elapsed_seconds

                                # Handle timer completion
                                if remaining_seconds <= 0:
                                    # Timer finished
                                    self.handle_preset_timer_finish(table_id)
                                else:
                                    # Show remaining time
                                    remaining_time = timedelta(seconds=int(remaining_seconds))
                                    self.table_widgets[table_id]['time'].config(text=f"Kalan: {str(remaining_time)}")

                                    # For cost calculation, only count the current timer's elapsed time
                                    hours = actual_elapsed_seconds / 3600
                                    timer_cost = hours * table['rate']

                                    # Add initial cost from custom start time
                                    initial_cost = table.get('initial_cost', 0)
                                    current_cost = timer_cost + initial_cost

                                    self.table_widgets[table_id]['cost'].config(
                                        text=f"Anlık Ücret: {current_cost:.2f} TL")
                                    self.table_widgets[table_id]['current_billiard_cost'] = current_cost

                            # Update the total display with the correct cost
                            self.update_table_total_display(table_id)

                # Update all tables even when not active
                for table_id in self.tables:
                    if table_id in self.table_widgets:
                        self.update_table_total_display(table_id)

                time.sleep(1)

        timer_thread = Thread(target=update_timers, daemon=True)
        timer_thread.start()

    def handle_preset_timer_finish(self, table_id):
        """Handle when preset timer finishes with minimum play time check"""
        if table_id in self.tables:
            table = self.tables[table_id]

            # Calculate actual duration including any initial time
            initial_elapsed_seconds = table.get('initial_elapsed_seconds', 0)
            preset_duration = table['preset_duration'] * 60  # convert minutes to seconds

            # If there are bonus seconds from time extension, add them
            if 'bonus_seconds' in table:
                preset_duration += table['bonus_seconds']

            # For preset timers that finish, the total elapsed time equals the preset duration
            total_elapsed_seconds = preset_duration

            # Check if total duration is less than 1 minute
            if total_elapsed_seconds < 60:
                # Reset table first to stop timer updates
                self.reset_table(table_id)

                # Update display if this is the current table
                if self.current_table_id == table_id:
                    self.update_current_table_display()

                # Show notification about minimum time requirement
                table_name = table['name']
                messagebox.showinfo("Bilgi",
                                    f"{table_name} - Bilardo oynama süresi 1 dakikanın altında olduğu için ücret eklenmedi.")
                self.show_notification(f"{table_name} - Süre 1 dakikadan az, ücret eklenmedi.")

                # Update UI
                self.update_table_total_display(table_id)
                return

            # For timers over 1 minute, calculate cost
            hours = preset_duration / 3600
            cost = hours * table['rate']

            # Add initial cost if there was a custom start time
            if 'initial_cost' in table and table['initial_cost'] > 0:
                cost += table['initial_cost']

            # Add to table's billiard charges
            duration_str = f"{int(preset_duration // 60)} dakika"  # Format as minutes
            self.table_orders[table_id]['billiard_charges'].append({
                'table_name': table['name'],
                'duration': duration_str,
                'cost': round(cost, 2)
            })

            # Get current total for the dialog
            yiyecek_total = sum(item['price'] * item['quantity'] for item in self.table_orders[table_id]['Yiyecekler'])
            icecek_total = sum(item['price'] * item['quantity'] for item in self.table_orders[table_id]['İçecekler'])

            # Calculate current total (all previous billiard + current billiard + items)
            previous_billiard = sum(c['cost'] for c in self.table_orders[table_id]['billiard_charges'][:-1])
            total = yiyecek_total + icecek_total + previous_billiard + cost

            # Reset table BEFORE showing dialog to stop timer updates
            self.reset_table(table_id)

            # Update display if this is the current table
            if self.current_table_id == table_id:
                self.update_current_table_display()

            # Show completion message with total
            messagebox.showinfo("Süre Bitti",
                                f"{table['name']}\nSüre: {duration_str}\n"
                                f"Bilardo Ücreti: {cost:.2f} TL\n"
                                f"Toplam Tutar: {total:.2f} TL\n\nSüre tamamlandı!")

            # Show notification
            self.show_notification(f"{table['name']} süresi bitti! Tutar: {cost:.2f} TL")

            self.save_data()

            # Update total cost display
            self.update_table_total_display(table_id)

            # Explicitly reset the table selection button color
            original_color = table['color']
            if table_id in self.table_buttons:
                relief = 'sunken' if table_id == self.current_table_id else 'raised'
                self.table_buttons[table_id].config(bg=original_color, relief=relief)

def main():
    root = tk.Tk()
    app = BilliardsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()