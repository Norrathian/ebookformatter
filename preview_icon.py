import tkinter as tk
from PIL import Image, ImageTk

def show_icon():
    # Create the main window
    root = tk.Tk()
    root.title("Icon Preview")
    
    # Load and display the icon
    try:
        # Load the icon
        photo = Image.open('icon.ico')
        
        # Convert to PhotoImage for Tkinter
        photo = ImageTk.PhotoImage(photo)
        
        # Create and pack the label with the icon
        label = tk.Label(root, image=photo)
        label.image = photo  # Keep a reference!
        label.pack(padx=10, pady=10)
        
        # Add size information
        size_label = tk.Label(root, text=f"Size: {photo.width()}x{photo.height()} pixels")
        size_label.pack(pady=5)
        
        # Start the main loop
        root.mainloop()
    except Exception as e:
        print(f"Error loading icon: {e}")

if __name__ == "__main__":
    show_icon() 