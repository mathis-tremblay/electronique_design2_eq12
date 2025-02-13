import os
import serial
import csv
import time
import tkinter as tk
from tkinter import scrolledtext
from utils import lire_donnees, envoyer_commande

class ArduinoInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("Arduino Interface")

        self.port = "COM4"
        self.baudrate = 115200
        self.ser = None

        self.t_actu = tk.StringVar()
        self.t_milieu = tk.StringVar()
        self.t_laser = tk.StringVar()

        self.create_widgets()
        self.setup_serial()

    def create_widgets(self):
        self.command_label = tk.Label(self.root, text="Commande:")
        self.command_label.grid(row=0, column=0, padx=10, pady=10)

        self.command_entry = tk.Entry(self.root, width=30)
        self.command_entry.grid(row=0, column=1, padx=10, pady=10)

        self.send_button = tk.Button(self.root, text="Envoyer", command=self.send_command)
        self.send_button.grid(row=0, column=2, padx=10, pady=10)

        self.output_text = scrolledtext.ScrolledText(self.root, width=50, height=20)
        self.output_text.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

        self.temp_actu_label = tk.Label(self.root, text="Température ACTU:")
        self.temp_actu_label.grid(row=2, column=0, padx=10, pady=10)
        self.temp_actu_entry = tk.Entry(self.root, textvariable=self.t_actu, state='readonly')
        self.temp_actu_entry.grid(row=2, column=1, padx=10, pady=10)

        self.temp_milieu_label = tk.Label(self.root, text="Température MILIEU:")
        self.temp_milieu_label.grid(row=3, column=0, padx=10, pady=10)
        self.temp_milieu_entry = tk.Entry(self.root, textvariable=self.t_milieu, state='readonly')
        self.temp_milieu_entry.grid(row=3, column=1, padx=10, pady=10)

        self.temp_laser_label = tk.Label(self.root, text="Température LASER:")
        self.temp_laser_label.grid(row=4, column=0, padx=10, pady=10)
        self.temp_laser_entry = tk.Entry(self.root, textvariable=self.t_laser, state='readonly')
        self.temp_laser_entry.grid(row=4, column=1, padx=10, pady=10)

        self.mode_label = tk.Label(self.root, text="Mode:")
        self.mode_label.grid(row=5, column=0, padx=10, pady=10)
        self.mode_var = tk.StringVar(self.root)
        self.mode_var.set("manuel")
        self.mode_menu = tk.OptionMenu(self.root, self.mode_var, "manuel", "automatique", command=self.set_mode)
        self.mode_menu.grid(row=5, column=1, padx=10, pady=10)

        self.voltage_label = tk.Label(self.root, text="Voltage:")
        self.voltage_label.grid(row=6, column=0, padx=10, pady=10)
        self.voltage_entry = tk.Entry(self.root, width=10)
        self.voltage_entry.grid(row=6, column=1, padx=10, pady=10)

        self.set_voltage_button = tk.Button(self.root, text="Set Voltage", command=self.set_voltage)
        self.set_voltage_button.grid(row=6, column=2, padx=10, pady=10)

    def setup_serial(self):
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=1)
            time.sleep(1)
            self.output_text.insert(tk.END, f"Port série {self.port} ouvert.\n")
        except serial.SerialException:
            self.output_text.insert(tk.END, "Erreur d'ouverture du port série.\n")

    def send_command(self):
        command = self.command_entry.get()
        if command and self.ser:
            response = envoyer_commande(command, self.ser)
            self.output_text.insert(tk.END, f"Envoyé: {command}\nRéponse: {response}\n")
            self.command_entry.delete(0, tk.END)

    def set_mode(self, mode):
        if self.ser:
            mode_value = "1" if mode == "manuel" else "2"
            command = f"set_mode {mode_value}"
            response = envoyer_commande(command, self.ser)
            self.output_text.insert(tk.END, f"Envoyé: {command}\nRéponse: {response}\n")

    def set_voltage(self):
        voltage = self.voltage_entry.get()
        if voltage and self.ser:
            command = f"set_voltage {voltage}"
            response = envoyer_commande(command, self.ser)
            self.output_text.insert(tk.END, f"Envoyé: {command}\nRéponse: {response}\n")


    def read_data(self):
        if self.ser:
            try:
                ligne = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if ligne.startswith("DATA:"):
                    _, t_actu, t_milieu, t_laser = map(float, ligne[5:].split(","))
                    self.output_text.insert(tk.END, f"Données: {ligne[5:]}\n")
                    self.t_actu.set(str(t_actu))
                    self.t_milieu.set(str(t_milieu))
                    self.t_laser.set(str(t_laser))
            except Exception as e:
                self.output_text.insert(tk.END, f"Erreur de lecture: {e}\n")
        self.root.after(1000, self.read_data)

    def on_closing(self):
        if self.ser:
            self.ser.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArduinoInterface(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.read_data()
    root.mainloop()