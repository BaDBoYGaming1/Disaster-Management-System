import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import socket
import json
import threading
import webbrowser
import requests
from PIL import Image, ImageTk
import io
import base64
import os

class DisasterManagementClient:
    def __init__(self, root):
        self.root = root
        self.root.title("🚨 Disaster Management System")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1a1a2e')
        
        # Server configuration
        self.HOST = '127.0.0.1'
        self.PORT = 8080
        self.socket = None
        self.is_logged_in = False
        self.current_user_role = ""
        
        # Create GUI
        self.create_widgets()
        
    def create_widgets(self):
        # Title
        title_label = tk.Label(self.root, text="🚨 DISASTER MANAGEMENT SYSTEM", 
                              font=('Arial', 24, 'bold'), fg='#ff6b35', bg='#1a1a2e')
        title_label.pack(pady=10)
        
        # Login Frame
        self.login_frame = tk.Frame(self.root, bg='#16213e', relief='raised', bd=2)
        self.login_frame.pack(pady=20, padx=20, fill='x')
        
        tk.Label(self.login_frame, text="Login", font=('Arial', 16, 'bold'), 
                fg='white', bg='#16213e').pack(pady=10)
        
        tk.Label(self.login_frame, text="Username:", fg='white', bg='#16213e').pack()
        self.username_entry = tk.Entry(self.login_frame, font=('Arial', 12), width=20)
        self.username_entry.pack(pady=5)
        self.username_entry.insert(0, "admin")
        
        tk.Label(self.login_frame, text="Password:", fg='white', bg='#16213e').pack()
        self.password_entry = tk.Entry(self.login_frame, font=('Arial', 12), width=20, show="*")
        self.password_entry.pack(pady=5)
        self.password_entry.insert(0, "admin123")
        
        self.login_btn = tk.Button(self.login_frame, text="Login", command=self.login,
                                  bg='#ff6b35', fg='white', font=('Arial', 12, 'bold'),
                                  relief='flat', padx=20, pady=5, cursor='hand2')
        self.login_btn.pack(pady=20)
        
        # Main content frame (initially hidden)
        self.main_frame = tk.Frame(self.root, bg='#1a1a2e')
        
        # Sidebar
        self.sidebar = tk.Frame(self.main_frame, bg='#16213e', width=250)
        self.sidebar.pack(side='left', fill='y', padx=(0,10), pady=10)
        self.sidebar.pack_propagate(False)
        
        # User info
        self.user_info = tk.Label(self.sidebar, text="", font=('Arial', 12, 'bold'),
                                 fg='#ff6b35', bg='#16213e')
        self.user_info.pack(pady=20)
        
        self.logout_btn = tk.Button(self.sidebar, text="Logout", command=self.logout,
                                   bg='#e94560', fg='white', font=('Arial', 10, 'bold'),
                                   relief='flat', padx=20, pady=5, cursor='hand2')
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.setup_disasters_tab()
        self.setup_resources_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief='sunken',
                             anchor='w', bg='#0f3460', fg='white')
        status_bar.pack(side='bottom', fill='x')
        
    def setup_disasters_tab(self):
        self.disasters_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.disasters_frame, text="🌪️ Disasters")
        
        # Add disaster form
        form_frame = tk.LabelFrame(self.disasters_frame, text="Add New Disaster", 
                                  font=('Arial', 10, 'bold'), bg='#1a1a2e', fg='white')
        form_frame.pack(fill='x', padx=10, pady=10)
        
        # Form fields
        tk.Label(form_frame, text="Type:", bg='#1a1a2e', fg='white').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.disaster_type = ttk.Combobox(form_frame, values=["Earthquake", "Flood", "Fire", "Hurricane", "Other"], width=15)
        self.disaster_type.grid(row=0, column=1, padx=5, pady=5)
        self.disaster_type.set("Earthquake")
        
        tk.Label(form_frame, text="Name:", bg='#1a1a2e', fg='white').grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.disaster_name = tk.Entry(form_frame, width=20)
        self.disaster_name.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Label(form_frame, text="Location:", bg='#1a1a2e', fg='white').grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.disaster_location = tk.Entry(form_frame, width=25)
        self.disaster_location.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='ew')
        
        tk.Label(form_frame, text="Image:", bg='#1a1a2e', fg='white').grid(row=1, column=3, sticky='w', padx=5, pady=5)
        self.image_path = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.image_path, width=20, state='readonly').grid(row=1, column=4, padx=5, pady=5)
        tk.Button(form_frame, text="Browse", command=self.browse_image, 
                 bg='#ff6b35', fg='white', relief='flat').grid(row=1, column=5, padx=5, pady=5)
        
        tk.Button(form_frame, text="Add Disaster", command=self.add_disaster,
                 bg='#00d4aa', fg='white', font=('Arial', 10, 'bold'), relief='flat',
                 padx=20).grid(row=2, column=0, columnspan=6, pady=10)
        
        form_frame.columnconfigure(1, weight=1)
        
        # Disasters list
        list_frame = tk.LabelFrame(self.disasters_frame, text="Active Disasters", 
                                  font=('Arial', 10, 'bold'), bg='#1a1a2e', fg='white')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Treeview for disasters
        columns = ('ID', 'Type', 'Name', 'Location', 'Time')
        self.disasters_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.disasters_tree.heading(col, text=col)
            self.disasters_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.disasters_tree.yview)
        self.disasters_tree.configure(yscrollcommand=scrollbar.set)
        
        self.disasters_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Buttons frame
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(fill='x', pady=5)
        
        self.refresh_disasters_btn = tk.Button(btn_frame, text="🔄 Refresh", command=self.refresh_disasters,
                                             bg='#4ecdc4', fg='white', relief='flat', padx=10)
        self.refresh_disasters_btn.pack(side='left', padx=5)
        
        self.get_route_btn = tk.Button(btn_frame, text="🗺️ Get Route", command=self.get_route,
                                      bg='#45b7d1', fg='white', relief='flat', padx=10)
        self.get_route_btn.pack(side='left', padx=5)
        
        # Bind selection for route
        self.disasters_tree.bind('<<TreeviewSelect>>', self.on_disaster_select)
        
    def setup_resources_tab(self):
        self.resources_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.resources_frame, text="📦 Resources")
        
        # Disaster selection
        disaster_frame = tk.LabelFrame(self.resources_frame, text="Select Disaster", 
                                      font=('Arial', 10, 'bold'), bg='#1a1a2e', fg='white')
        disaster_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(disaster_frame, text="Disaster:", bg='#1a1a2e', fg='white').pack(side='left', padx=5)
        self.disaster_combo = ttk.Combobox(disaster_frame, width=30)
        self.disaster_combo.pack(side='left', padx=5, fill='x', expand=True)
        self.disaster_combo.bind('<<ComboboxSelected>>', self.on_disaster_select_resources)
        
        self.refresh_combo_btn = tk.Button(disaster_frame, text="🔄 Refresh", 
                                          command=self.refresh_disaster_combo,
                                          bg='#ff6b35', fg='white', relief='flat', padx=10)
        self.refresh_combo_btn.pack(side='right', padx=5)
        
        # Add resource form
        add_frame = tk.LabelFrame(self.resources_frame, text="Add Resource", 
                                 font=('Arial', 10, 'bold'), bg='#1a1a2e', fg='white')
        add_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(add_frame, text="Resource Name:", bg='#1a1a2e', fg='white').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.resource_name = tk.Entry(add_frame, width=20)
        self.resource_name.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(add_frame, text="Quantity:", bg='#1a1a2e', fg='white').grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.resource_quantity = tk.Entry(add_frame, width=10)
        self.resource_quantity.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Button(add_frame, text="➕ Add Resource", command=self.add_resource,
                 bg='#00d4aa', fg='white', font=('Arial', 10, 'bold'), relief='flat',
                 padx=20).grid(row=0, column=4, padx=10, pady=5)
        
        # Resources list
        list_frame = tk.LabelFrame(self.resources_frame, text="Resources", 
                                  font=('Arial', 10, 'bold'), bg='#1a1a2e', fg='white')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('ID', 'Name', 'Quantity', 'Action')
        self.resources_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.resources_tree.heading(col, text=col)
            self.resources_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.resources_tree.yview)
        self.resources_tree.configure(yscrollcommand=scrollbar.set)
        
        self.resources_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind double-click for delete
        self.resources_tree.bind('<Double-1>', self.delete_resource)
        
    def connect_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.HOST, self.PORT))
            self.status_var.set("Connected to server")
            return True
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to server:\n{str(e)}")
            self.status_var.set("Connection failed")
            return False
    
    def send_request(self, action, data=None):
        if not self.socket:
            return None
        
        try:
            request_data = {
                "action": action
            }
            if data:
                request_data.update(data)
            
            request_json = json.dumps(request_data)
            self.socket.send(request_json.encode('utf-8'))
            
            response = self.socket.recv(4096).decode('utf-8')
            return json.loads(response)
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if self.connect_socket():
            response = self.send_request("login", {
                "username": username,
                "password": password
            })
            
            if response and response.get("status") == "success":
                self.is_logged_in = True
                self.current_user_role = response["data"]["role"]
                
                self.login_frame.pack_forget()
                self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
                
                self.user_info.config(text=f"👤 {username} ({self.current_user_role})")
                self.logout_btn.pack(pady=10)
                
                self.status_var.set(f"Logged in as {username}")
                self.refresh_disasters()
                self.refresh_disaster_combo()
            else:
                messagebox.showerror("Login Failed", "Invalid credentials!")
    
    def logout(self):
        self.is_logged_in = False
        self.main_frame.pack_forget()
        self.login_frame.pack(pady=20, padx=20, fill='x')
        self.socket.close()
        self.socket = None
        self.status_var.set("Logged out")
    
    def add_disaster(self):
        type_ = self.disaster_type.get()
        name = self.disaster_name.get()
        location = self.disaster_location.get()
        image = self.image_path.get()
        
        if not all([type_, name, location]):
            messagebox.showwarning("Missing Data", "Please fill all required fields!")
            return
        
        response = self.send_request("add_disaster", {
            "type": type_,
            "name": name,
            "location": location,
            "image": image
        })
        
        if response and response.get("status") == "success":
            messagebox.showinfo("Success", "Disaster added successfully!")
            self.clear_disaster_form()
            self.refresh_disasters()
            self.refresh_disaster_combo()
        else:
            messagebox.showerror("Error", response.get("message", "Failed to add disaster"))
    
    def clear_disaster_form(self):
        self.disaster_type.set("Earthquake")
        self.disaster_name.delete(0, tk.END)
        self.disaster_location.delete(0, tk.END)
        self.image_path.set("")
    
    def refresh_disasters(self):
        response = self.send_request("get_disasters")
        if response and response.get("status") == "success":
            self.disasters_tree.delete(*self.disasters_tree.get_children())
            disasters = response["data"]
            for disaster in disasters:
                self.disasters_tree.insert('', 'end', values=(
                    disaster['id'],
                    disaster['type'],
                    disaster['name'],
                    disaster['location'],
                    self.format_timestamp(disaster['timestamp'])
                ))
    
    def format_timestamp(self, timestamp):
        try:
            from datetime import datetime
            dt = datetime.fromtimestamp(int(timestamp))
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return "Unknown"
    
    def on_disaster_select(self, event):
        selection = self.disasters_tree.selection()
        if selection:
            item = self.disasters_tree.item(selection[0])
            location = item['values'][3]
            self.disaster_location.delete(0, tk.END)
            self.disaster_location.insert(0, location)
    
    def get_route(self):
        selection = self.disasters_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a disaster first!")
            return
        
        item = self.disasters_tree.item(selection[0])
        disaster_location = item['values'][3]
        
        # Get user's current location (you can modify this)
        user_location = "Current Location"
        
        response = self.send_request("get_route", {
            "from": user_location,
            "to": disaster_location
        })
        
        if response and response.get("status") == "success":
            webbrowser.open(response["data"]["url"])
        else:
            messagebox.showerror("Error", "Failed to generate route")
    
    def browse_image(self):
        filename = filedialog.askopenfilename(
            title="Select Disaster Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        if filename:
            self.image_path.set(filename)

    
    
    def refresh_disaster_combo(self):
        self.refresh_disasters()
        response = self.send_request("get_disasters")
        if response and response.get("status") == "success":
            disasters = response["data"]
            disaster_names = [f"{d['id']}: {d['name']} ({d['location']})" for d in disasters]
            self.disaster_combo['values'] = disaster_names
    
    def on_disaster_select_resources(self, event):
        selected = self.disaster_combo.get()
        if selected:
            try:
                disaster_id = int(selected.split(':')[0])
                self.refresh_resources(disaster_id)
            except:
                pass
    
    def refresh_resources(self, disaster_id):
        response = self.send_request("get_resources", {"disaster_id": str(disaster_id)})
        if response and response.get("status") == "success":
            self.resources_tree.delete(*self.resources_tree.get_children())
            resources = response["data"]
            for resource in resources:
                self.resources_tree.insert('', 'end', values=(
                    resource['id'],
                    resource['name'],
                    resource['quantity'],
                    "🗑️"
                ))
                
    
    def add_resource(self):
        selected = self.disaster_combo.get()
        if not selected:
            messagebox.showwarning("No Disaster", "Please select a disaster first!")
            return
        
        name = self.resource_name.get()
        quantity = self.resource_quantity.get()
        
        if not all([name, quantity]):
            messagebox.showwarning("Missing Data", "Please fill resource name and quantity!")
            return
        
        try:
            disaster_id = int(selected.split(':')[0])
            response = self.send_request("add_resource", {
                "disaster_id": str(disaster_id),
                "name": name,
                "quantity": quantity
            })
            
            if response and response.get("status") == "success":
                messagebox.showinfo("Success", "Resource added successfully!")
                self.resource_name.delete(0, tk.END)
                self.resource_quantity.delete(0, tk.END)
                self.refresh_resources(disaster_id)
            else:
                messagebox.showerror("Error", response.get("message", "Failed to add resource"))
        except ValueError:
            messagebox.showerror("Error", "Invalid disaster selection")
    
    def delete_resource(self, event):
        selection = self.resources_tree.selection()
        if not selection:
            return
        
        item = self.resources_tree.item(selection[0])
        resource_id = int(item['values'][0])
        
        if messagebox.askyesno("Confirm Delete", f"Delete resource '{item['values'][1]}'?"):
            response = self.send_request("delete_resource", {"resource_id": str(resource_id)})
            
            if response and response.get("status") == "success":
                messagebox.showinfo("Success", "Resource deleted successfully!")
                # Refresh resources for current disaster
                selected = self.disaster_combo.get()
                if selected:
                    try:
                        disaster_id = int(selected.split(':')[0])
                        self.refresh_resources(disaster_id)
                    except:
                        pass
            else:
                messagebox.showerror("Error", response.get("message", "Failed to delete resource"))

def main():
    root = tk.Tk()
    app = DisasterManagementClient(root)
    
    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # Handle window close
    def on_closing():
        if app.socket:
            app.socket.close()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()