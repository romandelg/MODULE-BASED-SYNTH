import tkinter as tk
from tkinter import ttk

def create_knob(parent, label_text):
    frame = tk.Frame(parent, bg="gray20")
    frame.pack(side=tk.LEFT, padx=10, pady=5)

    label = tk.Label(frame, text=label_text, fg="orange", bg="gray20", font=("Helvetica", 10))
    label.pack()

    knob = tk.Canvas(frame, width=50, height=50, bg="gray30", highlightthickness=0)
    knob.create_oval(5, 5, 45, 45, outline="orange", width=2)
    knob.create_line(25, 25, 25, 10, fill="orange", width=2)
    knob.pack()
    return frame

def create_switch(parent, label_text, options):
    frame = tk.Frame(parent, bg="gray20")
    frame.pack(side=tk.LEFT, padx=10, pady=5)

    label = tk.Label(frame, text=label_text, fg="orange", bg="gray20", font=("Helvetica", 10))
    label.pack()

    for option in options:
        button = tk.Radiobutton(frame, text=option, bg="gray20", fg="orange", selectcolor="gray30", indicatoron=0, font=("Helvetica", 10))
        button.pack(fill="x", pady=2)
    return frame

root = tk.Tk()
root.title("Synth GUI")
root.configure(bg="gray20")

# ADSR Section
adsr_frame = tk.Frame(root, bg="gray20")
adsr_frame.pack(padx=10, pady=10, fill="x")
create_knob(adsr_frame, "Attack")
create_knob(adsr_frame, "Decay")
create_knob(adsr_frame, "Sustain")
create_knob(adsr_frame, "Release")

# Oscillator Section
osc_frame = tk.Frame(root, bg="gray20")
osc_frame.pack(padx=10, pady=10, fill="x")
create_knob(osc_frame, "Sin")
create_knob(osc_frame, "Saw")
create_knob(osc_frame, "Tri")
create_knob(osc_frame, "Pulse")

# Filter Section
filter_frame = tk.Frame(root, bg="gray20")
filter_frame.pack(padx=10, pady=10, fill="x")
create_knob(filter_frame, "P Cutoff")
create_knob(filter_frame, "Resonance")
create_switch(filter_frame, "Switch", ["HP", "LP", "Bypass"])

# Noise Section
noise_frame = tk.Frame(root, bg="gray20")
noise_frame.pack(padx=10, pady=10, fill="x")
create_knob(noise_frame, "Noise")

# FX Section
fx_frame = tk.Frame(root, bg="gray20")
fx_frame.pack(padx=10, pady=10, fill="x")
create_switch(fx_frame, "FX Switch", ["Clipper", "Bypass"])

root.mainloop()