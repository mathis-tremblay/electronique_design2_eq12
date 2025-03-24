import serial
import time
import tkinter as tk
from tkinter import scrolledtext
from tkinter import simpledialog
from tooltip import ToolTip
from utils import lire_donnees, envoyer_commande, creer_fichier
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# Dialogue pour selectionner le port série avant d'ouvrir la page principale
class PortSelectionDialog(simpledialog.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Sélection du port")

    def body(self, master):
        self.geometry("300x70")
        tk.Label(master, text="Entrez le port de l'Arduino : ").grid(row=0)
        self.port_entry = tk.Entry(master)
        self.port_entry.grid(row=0, column=1)
        return self.port_entry

    def apply(self):
        self.result = self.port_entry.get()

'''' Page principale '''
class ArduinoInterface:
    def __init__(self, root, port="COM9"):
        self.root = root
        self.root.title("Arduino Interface")
        self.root.minsize(500, 690)

        self.port = port
        self.baudrate = 115200
        self.ser = None

        self.t_actu = tk.StringVar()
        self.t_milieu = tk.StringVar()
        self.t_laser = tk.StringVar()
        self.t_laser_estime = tk.StringVar()

        self.temp_cible = tk.StringVar()
        self.temp_piece = tk.StringVar()

        self.temps_data = []
        self.t_actu_data = []
        self.t_milieu_data = []
        self.t_laser_data = []
        self.t_laser_estime_data = []
        self.commande_data = []
        self.fig, (self.ax, self.ax_commande) = plt.subplots(2, 1, sharex=True)
        self.ax.set_title("Températures")
        self.ax.set_xlabel("Temps (s)")
        self.ax.set_ylabel("Température (°C)")
        self.ax_commande.set_title("Commande")
        self.ax_commande.set_xlabel("Temps (s)")
        self.ax_commande.set_ylabel("OCR1A")

        self.v_actu = tk.StringVar()
        self.v_milieu = tk.StringVar()
        self.v_laser = tk.StringVar()
        self.ocr1a = tk.StringVar()

        self.stable = tk.IntVar()

        self.create_widgets()
        self.setup_serial()

        self.fichier, self.writer = creer_fichier()

        self.pause = False

    # Éléments dans la page
    def create_widgets(self):
        # Grid
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=3)
        self.root.columnconfigure(3, weight=1)
        self.root.columnconfigure(4, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=4)
        self.root.rowconfigure(3, weight=1)
        self.root.rowconfigure(4, weight=1)
        self.root.rowconfigure(5, weight=1)
        self.root.rowconfigure(6, weight=1)
        self.root.rowconfigure(7, weight=1)
        self.root.rowconfigure(8, weight=1)

        # Envoyer commandes manuellement
        self.command_label = tk.Label(self.root, text="Commande : ")
        self.command_label.grid(row=0, column=1, padx=10, pady=10, sticky=tk.E)
        ToolTip(self.command_label, msg="Liste de commandes : \n- set_mode {0 pour manuel, 1 pour auto}\n- set_voltage {-1 à 1}\n- set_temp {20 à 30}\n- get_mode\n get_temp_cible\n get_temp_piece")
        self.command_entry = tk.Entry(self.root, width=30)
        self.command_entry.grid(row=0, column=2, padx=10, pady=10)
        self.command_entry.bind("<Return>", lambda event: self.send_command())
        self.send_button = tk.Button(self.root, text="Envoyer", command=self.send_command)
        self.send_button.grid(row=0, column=3, padx=10, pady=10, sticky=tk.W)

        self.pause_bouton = tk.Button(self.root, text="\u23F8", command=self.toggle_pause)
        self.pause_bouton.grid(row=0, column=3, padx=(40,10), pady=10)
        ToolTip(self.pause_bouton, msg="Mettre en pause ou reprendre l'asservissement. Mettre sur pause envoie la dernière valeur de puissance déterminé par le régulateur dans le système.")

        self.stop_bouton = tk.Button(self.root, text="Reset", command=self.stop)
        self.stop_bouton.grid(row=0, column=3, padx=(120,10), pady=10)
        ToolTip(self.stop_bouton, msg="Met la plaque à la température ambiante. Pour arrêter, choisir une autre température cible.")

        # Champ de texte pour afficher les données (lis le port série)
        self.output_text = scrolledtext.ScrolledText(self.root, width=60, height=8)
        self.output_text.grid(row=1, column=1, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)
        
        # Graphique
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().grid(row=2, column=1, columnspan=3, rowspan=1, padx=10, pady=10, sticky=tk.NSEW)

        # Labels pour les températures
        self.temp_piece_label = tk.Label(self.root, text="Pièce (°C)")
        self.temp_piece_label.grid(row=3, column=1, padx=10, pady=(10, 0), sticky=tk.S)
        self.temp_piece_entry = tk.Entry(self.root, textvariable=self.temp_piece, state='readonly', justify="center")
        self.temp_piece_entry.grid(row=4, column=1, padx=10, pady=(0, 10), sticky=tk.N)

        self.temp_actu_label = tk.Label(self.root, text="Actuateur (°C)")
        self.temp_actu_label.grid(row=3, column=2, padx=10, pady=(10,0), sticky=tk.SW)
        self.temp_actu_entry = tk.Entry(self.root, textvariable=self.t_actu, state='readonly', justify="center")
        self.temp_actu_entry.grid(row=4, column=2, padx=10, pady=(0,10), sticky=tk.W)

        self.temp_milieu_label = tk.Label(self.root, text="Milieu (°C)")
        self.temp_milieu_label.grid(row=3, column=2, padx=10, pady=(10,0), sticky=tk.SE)
        self.temp_milieu_entry = tk.Entry(self.root, textvariable=self.t_milieu, state='readonly', justify="center")
        self.temp_milieu_entry.grid(row=4, column=2, padx=10, pady=(0,10), sticky=tk.NE)

        self.temp_laser_label = tk.Label(self.root, text="Estimation laser (°C)")
        self.temp_laser_label.grid(row=3, column=3, padx=10, pady=(10,0), sticky=tk.S)
        self.temp_laser_entry = tk.Entry(self.root, textvariable=self.t_laser_estime, state='readonly', justify="center")
        self.temp_laser_entry.grid(row=4, column=3, padx=10, pady=(0,10), sticky=tk.N)

        # Voyant de stabilité
        self.stabilite_label = tk.Label(self.root, text="Non stable à partir de 0s")
        self.stabilite_label.grid(row=5, column=3, padx=10, pady=0, sticky=tk.N)
        self.red_light_canvas = tk.Canvas(self.root, width=20, height=20, highlightthickness=0)
        self.red_light_canvas.grid(row=5, column=3, padx=10, pady=(10,0))
        ToolTip(self.red_light_canvas, msg="Vert : stable\nJaune : semi-stable\nRouge : non stable")
        self.red_light = self.red_light_canvas.create_oval(2, 2, 18, 18, fill="red")

        # Modes automatique ou manuel
        self.mode_label = tk.Label(self.root, text="Mode : ")
        self.mode_label.grid(row=5, column=1, padx=10, pady=10, sticky=tk.E)
        self.mode_var = tk.StringVar(self.root)
        self.mode_var.set("Manuel")
        self.mode_button = tk.Button(self.root, textvariable=self.mode_var, command=self.show_mode_menu)
        self.mode_button.grid(row=5, column=2, padx=10, pady=10)
        self.mode_menu = tk.Menu(self.root, tearoff=0)
        self.mode_menu.add_command(label="Manuel", command=lambda: self.set_mode("Manuel"))
        self.mode_menu.add_command(label="Automatique", command=lambda: self.set_mode("Automatique"))

        # Choisir manuellement tension appliquée (entre -1 et 1), doit etre en mode manuel
        self.voltage_label = tk.Label(self.root, text="Voltage : ")
        self.voltage_label.grid(row=6, column=1, padx=10, pady=10, sticky=tk.E)
        self.voltage_entry = tk.Entry(self.root, width=10)
        self.voltage_entry.grid(row=6, column=2, padx=10, pady=10)
        self.voltage_entry.bind("<Return>", lambda event: self.set_voltage())
        self.set_voltage_button = tk.Button(self.root, text="Fixer la tension", command=self.set_voltage)
        self.set_voltage_button.grid(row=6, column=3, padx=10, pady=10)

        # Choisir manuellement la température (entre 20 et 30), doit etre en mode automatique
        self.temp_label = tk.Label(self.root, text="Température : ")
        self.temp_label.grid(row=7, column=1, padx=10, pady=10, sticky=tk.E)
        self.temp_entry = tk.Entry(self.root, width=10)
        self.temp_entry.grid(row=7, column=2, padx=(10,100), pady=10)
        self.temp_entry.bind("<Return>", lambda event: self.set_temperature())
        self.temp_cible_mtn = tk.Entry(self.root, width=10, textvariable=self.temp_cible, state='readonly', justify="center")
        self.temp_cible_mtn.grid(row=7, column=2, padx=(100,10), pady=10)
        self.set_temp_button = tk.Button(self.root, text="Fixer la température", command=self.set_temperature)
        self.set_temp_button.grid(row=7, column=3, padx=10, pady=10)

    # Setup communication serie avec arduino
    def setup_serial(self):
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=1)
            time.sleep(2)
            self.output_text.insert(tk.END, f"Port série {self.port} ouvert.\n")
            self.output_text.see(tk.END)
            # Bon mode au début
            self.root.after(1000, self.sync)
        except serial.SerialException:
            self.output_text.insert(tk.END, "Erreur d'ouverture du port série.\n")
            self.output_text.see(tk.END)

    # Pour synchroniser le mode et la temperature cible avec le Arduino au debut
    def sync(self):
        if self.ser:
            rep = envoyer_commande("get_mode", self.ser)
            self.mode_var.set("Manuel" if rep == "1" else "Automatique")
            self.pause = (rep == "1")
            if self.pause:
                self.pause_bouton.config(text="\u25B6")
            else:
                self.pause_bouton.config(text="\u23F8")
            rep = envoyer_commande("get_temp_cible", self.ser)
            self.temp_cible.set(rep)
            if float(rep) < 20. or float(rep) > 30.:
                self.output_text.insert(tk.END, f"Attention, la température cible {rep} n'est pas entre 20 et 30°C.\n")
            rep = envoyer_commande("get_temp_piece", self.ser)
            self.temp_piece.set(rep)
            if float(rep) < 20. or float(rep) > 30.:
                self.output_text.insert(tk.END, f"Attention, la température pièce {rep} n'est pas entre 20 et 30°C.\n")

    def toggle_pause(self):
        if self.pause:
            self.set_mode("Automatique")
            self.pause_bouton.config(text="\u23F8")
        else:
            self.set_mode("Manuel")
            self.pause_bouton.config(text="\u25B6")
        self.pause = not self.pause

    def stop(self):
        self.set_mode("Automatique")
        self.set_temperature(temp_piece=True)

    # Envoyer une commande
    def send_command(self, command=""):
        if command == "":
            command = self.command_entry.get()
        if command and self.ser:
            reponse = envoyer_commande(command, self.ser)
            self.output_text.insert(tk.END, f"Envoyé : {command}\nRéponse : {reponse}\n")
            self.output_text.see(tk.END)
            self.command_entry.delete(0, tk.END)

    # Afficher le menu pour choisir le mode
    def show_mode_menu(self):
        self.mode_menu.post(self.mode_button.winfo_rootx(), self.mode_button.winfo_rooty() + self.mode_button.winfo_height())

    # Changer le mode
    def set_mode(self, mode):
        if self.ser:
            mode_value = "1" if mode == "Manuel" else "0"
            command = f"set_mode {mode_value}"
            reponse = envoyer_commande(command, self.ser)
            self.output_text.insert(tk.END, f"Envoyé : {command}\nRéponse : {reponse}\n")
            self.output_text.see(tk.END)
            self.mode_var.set("Manuel" if mode == "Manuel" else "Automatique")

    # Changer la tension
    def set_voltage(self):
        voltage = self.voltage_entry.get()
        if voltage and self.ser:
            command = f"set_voltage {voltage}"
            reponse = envoyer_commande(command, self.ser)
            self.output_text.insert(tk.END, f"Envoyé : {command}\nRéponse : {reponse}\n")
            self.output_text.see(tk.END)
            self.voltage_entry.delete(0, tk.END)

    # Changer la température
    def set_temperature(self, temp_piece=False):
        temperature = self.temp_entry.get()
        if temp_piece:
            temperature = self.temp_piece.get()
        if temperature and self.ser:
            command = f"set_temp {temperature}"
            reponse = envoyer_commande(command, self.ser)
            self.output_text.insert(tk.END, f"Envoyé : {command}\nRéponse : {reponse}\n")
            self.output_text.see(tk.END)
            self.temp_entry.delete(0, tk.END)
            if reponse != "Aucune réponse, veuillez réessayer." and reponse != "La température n'est pas entre 20°C et 30°C.":
                self.temp_cible.set(temperature)

    # Mettre à jour le voyant de stabilité
    def set_stable(self, stable, temps):
        if self.stable.get() != stable:
            self.stable.set(stable)
            if stable == 1:
                self.stabilite_label.config(text=f"Est stable à partir de {temps}s")
                self.red_light_canvas.itemconfig(self.red_light, fill="green")
            elif stable == 2:
                self.stabilite_label.config(text=f"Semi-stable à partir de {temps}s")
                self.red_light_canvas.itemconfig(self.red_light, fill="yellow")
            else:
                self.stabilite_label.config(text=f"Non stable à partir de {temps}s")
                self.red_light_canvas.itemconfig(self.red_light, fill="red")


    # Lire les données en continu
    def read_data(self):
        if self.ser:
            try:
                ligne = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if ligne.startswith("DATA:"):
                    temps, t_actu, t_milieu, t_laser, t_laser_estime, v_actu, v_milieu, v_laser, ocr1a, stable  = map(float, ligne[5:].split(","))
                    self.output_text.insert(tk.END, f"Données: {ligne[5:]}\n")
                    self.t_actu.set(str(t_actu))
                    self.t_milieu.set(str(t_milieu))
                    self.t_laser.set(str(t_laser))
                    self.t_laser_estime.set(str(t_laser_estime))
                    self.v_actu.set(str(v_actu))
                    self.v_milieu.set(str(v_milieu))
                    self.v_laser.set(str(v_laser))
                    self.ocr1a.set(str(ocr1a))
                    self.set_stable(stable, temps)

                    self.writer.writerow([temps, t_actu, t_milieu, t_laser, t_laser_estime, v_actu, v_milieu, v_laser, ocr1a, stable])

                    self.temps_data.append(temps)
                    self.t_actu_data.append(t_actu)
                    self.t_milieu_data.append(t_milieu)
                    self.t_laser_data.append(t_laser)
                    self.t_laser_estime_data.append(t_laser_estime)
                    self.commande_data.append(ocr1a)
                    self.update_plot()
            except Exception as e:
                self.output_text.insert(tk.END, f"Erreur de lecture: {e}\n")
        self.root.after(1000, self.read_data)
        self.output_text.see(tk.END)

    def update_plot(self):
        self.ax.clear()
        self.ax.plot(self.temps_data, self.t_actu_data, label="Actuateur")
        self.ax.plot(self.temps_data, self.t_milieu_data, label="Milieu")
        self.ax.plot(self.temps_data, self.t_laser_data, label="Laser")
        self.ax.plot(self.temps_data, self.t_laser_estime_data, label="Laser estimé ")

        # Réappliquer les titres et labels
        self.ax.set_title("Températures")
        self.ax.set_ylabel("Température (°C)")
        self.ax.legend()

        self.ax_commande.clear()
        self.ax_commande.plot(self.temps_data, self.commande_data, label="Commande", color='tab:orange')
        self.ax_commande.set_title("Commande")
        self.ax_commande.set_xlabel("Temps (s)")
        self.ax_commande.set_ylabel("OCR1A")
        self.ax_commande.legend()

        self.canvas.draw()

    # Gerer la fermeture
    def on_closing(self):
        if self.ser:
            self.ser.close()
        if not self.fichier.closed:
            self.fichier.close()
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    # Ouvrir fenetre pour selectionner le port
    root = tk.Tk()
    root.withdraw()
    #dialog = PortSelectionDialog(root)
    port = "com9"#dialog.result
    if port:
        # Ouvre la fenêtre principale
        root.deiconify()
        app = ArduinoInterface(root, port)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.read_data()
        root.mainloop()