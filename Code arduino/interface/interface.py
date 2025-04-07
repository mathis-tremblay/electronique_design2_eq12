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

        self.fichier, self.writer = creer_fichier()

        self.kp = tk.StringVar()
        self.ti = tk.StringVar()
        self.td = tk.StringVar()
        self.tf = tk.StringVar()
        self.b_un = tk.StringVar()

        self.pause = False

        self.create_widgets()
        self.setup_serial()

    # Éléments dans la page
    def create_widgets(self):
        # Création des frames principales
        self.left_frame = tk.Frame(self.root)
        self.left_frame.grid(row=0, column=0, rowspan=8, sticky="nsew", padx=10, pady=10)

        self.right_frame = tk.Frame(self.root)
        self.right_frame.grid(row=0, column=1, rowspan=8, sticky="nsew", padx=10, pady=10)

        # Ajustement de la pondération pour une bonne répartition
        self.root.columnconfigure(0, weight=1)  # Tout sauf les graphiques
        self.root.columnconfigure(1, weight=3)  # Graphiques
        self.root.rowconfigure(2, weight=4)  # Plus de place aux graphiques

        # ---- COMMANDES ----
        self.command_label = tk.Label(self.left_frame, text="Commande : ")
        self.command_label.grid(row=0, column=0)
        ToolTip(self.command_label,
                msg="Liste de commandes : \n- set_mode {0 pour manuel, 1 pour auto}\n- set_voltage {-1 à 1}\n- set_temp {20 à 30}\n- get_mode\n get_temp_cible\n get_temp_piece")

        self.command_entry = tk.Entry(self.left_frame, width=30)
        self.command_entry.grid(row=0, column=1, padx=10)
        self.command_entry.bind("<Return>", lambda event: self.send_command())

        self.send_button = tk.Button(self.left_frame, text="Envoyer", command=self.send_command)
        self.send_button.grid(row=0, column=2, padx=5)

        self.pause_bouton = tk.Button(self.left_frame, text="\u23F8", command=self.toggle_pause)
        self.pause_bouton.grid(row=0, column=3, padx=(0,50))
        ToolTip(self.pause_bouton, msg="Mettre en pause ou reprendre l'asservissement.")

        self.stop_bouton = tk.Button(self.left_frame, text="Reset", command=self.stop)
        self.stop_bouton.grid(row=0, column=3, padx=(50,0))
        ToolTip(self.stop_bouton, msg="Met la plaque à la température ambiante.")

        # ---- TEXTE SCROLLABLE (Affichage des données) ----
        self.output_text = scrolledtext.ScrolledText(self.left_frame, width=80, height=8)
        self.output_text.grid(row=1, column=0, columnspan=4, pady=10, padx=10)

        # ---- CHAMPS DE TEMPÉRATURES ----
        self.temp_piece_label = tk.Label(self.left_frame, text="Pièce (°C)")
        self.temp_piece_label.grid(row=2, column=0, pady=5,  sticky="e")
        self.temp_piece_entry = tk.Entry(self.left_frame, textvariable=self.temp_piece, state='readonly',
                                         justify="center")
        self.temp_piece_entry.grid(row=2, column=1, pady=5)

        self.temp_actu_label = tk.Label(self.left_frame, text="Actuateur (°C)")
        self.temp_actu_label.grid(row=2, column=2, pady=5, sticky="e")
        self.temp_actu_entry = tk.Entry(self.left_frame, textvariable=self.t_actu, state='readonly', justify="center")
        self.temp_actu_entry.grid(row=2, column=3, pady=5)

        self.temp_milieu_label = tk.Label(self.left_frame, text="Milieu (°C)")
        self.temp_milieu_label.grid(row=3, column=0, pady=5, sticky="e")
        self.temp_milieu_entry = tk.Entry(self.left_frame, textvariable=self.t_milieu, state='readonly',
                                          justify="center")
        self.temp_milieu_entry.grid(row=3, column=1)

        self.temp_laser_label = tk.Label(self.left_frame, text="Estimation laser (°C)")
        self.temp_laser_label.grid(row=3, column=2, pady=5, sticky="e")
        self.temp_laser_entry = tk.Entry(self.left_frame, textvariable=self.t_laser_estime, state='readonly',
                                         justify="center")
        self.temp_laser_entry.grid(row=3, column=3, pady=10)

        # ---- VOYANT DE STABILITÉ ----
        self.stabilite_label = tk.Label(self.left_frame, text="Non stable à partir de 0s")
        self.stabilite_label.grid(row=4, column=1, pady=10)
        self.red_light_canvas = tk.Canvas(self.left_frame, width=20, height=20, highlightthickness=0)
        self.red_light_canvas.grid(row=4, column=0, pady=10, sticky="e")
        ToolTip(self.red_light_canvas, msg="Vert : stable\nJaune : semi-stable\nRouge : non stable")
        self.red_light = self.red_light_canvas.create_oval(2, 2, 18, 18, fill="red")

        # ---- MODE (Automatique / Manuel) ----
        self.mode_label = tk.Label(self.left_frame, text="Mode : ")
        self.mode_label.grid(row=5, column=0, pady=10, sticky="e")
        self.mode_var = tk.StringVar(self.left_frame)
        self.mode_var.set("Manuel")
        self.mode_button = tk.Button(self.left_frame, textvariable=self.mode_var, command=self.show_mode_menu)
        self.mode_button.grid(row=5, column=1, pady=10)
        self.mode_menu = tk.Menu(self.left_frame, tearoff=0)
        self.mode_menu.add_command(label="Manuel", command=lambda: self.set_mode("Manuel"))
        self.mode_menu.add_command(label="Automatique", command=lambda: self.set_mode("Automatique"))

        # ---- CHOIX DU VOLTAGE ----
        self.voltage_label = tk.Label(self.left_frame, text="Voltage : ")
        self.voltage_label.grid(row=6, column=0, pady=10, sticky="e")
        self.voltage_entry = tk.Entry(self.left_frame)
        self.voltage_entry.grid(row=6, column=1, pady=10)
        self.voltage_entry.bind("<Return>", lambda event: self.set_voltage())
        self.set_voltage_button = tk.Button(self.left_frame, text="Fixer la tension", command=self.set_voltage)
        self.set_voltage_button.grid(row=6, column=3, pady=10)

        # ---- CHOIX DE LA TEMPÉRATURE ----
        self.temp_label = tk.Label(self.left_frame, text="Température cible: ")
        self.temp_label.grid(row=7, column=0, pady=10, sticky="e")
        self.temp_entry = tk.Entry(self.left_frame)
        self.temp_entry.grid(row=7, column=1, pady=10)
        self.temp_entry.bind("<Return>", lambda event: self.set_temperature())
        self.temp_cible_mtn = tk.Entry(self.left_frame, width=10, textvariable=self.temp_cible, state='readonly',
                                       justify="center")
        self.temp_cible_mtn.grid(row=7, column=2, pady=10)
        self.set_temp_button = tk.Button(self.left_frame, text="Fixer la température", command=self.set_temperature)
        self.set_temp_button.grid(row=7, column=3, pady=10)


        # ---- CHOIX DU PIDF ----
        self.pidf_info = tk.Label(self.left_frame, text="PIDF de la forme parallèle : u(t)=Kp*e(t)+Ti∫e(t)dt+Td*(Tf/(1+Tf))*de(t)/dt")
        self.pidf_info.grid(row=8, column=0, columnspan=4, pady=(10,5))

        self.kp_label = tk.Label(self.left_frame, text="Kp : ")
        self.kp_label.grid(row=9, column=0, pady=5, sticky="e")
        self.kp_entry = tk.Entry(self.left_frame)
        self.kp_entry.grid(row=9, column=1, pady=5)
        self.kp_entry.bind("<Return>", lambda event: self.set_pidf(kp=True))
        self.kp_mtn = tk.Entry(self.left_frame, width=10, textvariable=self.kp, state='readonly',
                                       justify="center")
        self.kp_mtn.grid(row=9, column=2, pady=5)
        self.set_kp_button = tk.Button(self.left_frame, text="Fixer Kp", command=lambda: self.set_pidf(kp=True))
        self.set_kp_button.grid(row=9, column=3, pady=5)

        self.ti_label = tk.Label(self.left_frame, text="Ti : ")
        self.ti_label.grid(row=10, column=0, pady=5, sticky="e")
        self.ti_entry = tk.Entry(self.left_frame)
        self.ti_entry.grid(row=10, column=1, pady=5)
        self.ti_entry.bind("<Return>", lambda event: self.set_pidf(ti=True))
        self.ti_mtn = tk.Entry(self.left_frame, width=10, textvariable=self.ti, state='readonly',
                               justify="center")
        self.ti_mtn.grid(row=10, column=2, pady=5)
        self.set_ti_button = tk.Button(self.left_frame, text="Fixer Ti", command=lambda: self.set_pidf(ti=True))
        self.set_ti_button.grid(row=10, column=3, pady=5)

        self.td_label = tk.Label(self.left_frame, text="Td : ")
        self.td_label.grid(row=11, column=0, pady=5, sticky="e")
        self.td_entry = tk.Entry(self.left_frame)
        self.td_entry.grid(row=11, column=1, pady=5)
        self.td_entry.bind("<Return>", lambda event: self.set_pidf(td=True))
        self.td_mtn = tk.Entry(self.left_frame, width=10, textvariable=self.td, state='readonly',
                               justify="center")
        self.td_mtn.grid(row=11, column=2, pady=5)
        self.set_td_button = tk.Button(self.left_frame, text="Fixer Td", command=lambda: self.set_pidf(td=True))
        self.set_td_button.grid(row=11, column=3, pady=5)

        self.tf_label = tk.Label(self.left_frame, text="Tf : ")
        self.tf_label.grid(row=12, column=0, pady=5, sticky="e")
        self.tf_entry = tk.Entry(self.left_frame)
        self.tf_entry.grid(row=12, column=1, pady=5)
        self.tf_entry.bind("<Return>", lambda event: self.set_pidf(tf=True))
        self.tf_mtn = tk.Entry(self.left_frame, width=10, textvariable=self.tf, state='readonly',
                               justify="center")
        self.tf_mtn.grid(row=12, column=2, pady=5)
        self.set_tf_button = tk.Button(self.left_frame, text="Fixer Tf", command=lambda: self.set_pidf(tf=True))
        self.set_tf_button.grid(row=12, column=3, pady=5)

        self.temp_piece_label = tk.Label(self.left_frame, text="Température pièce: ")
        self.temp_piece_label.grid(row=13, column=0, pady=10, sticky="e")
        self.temp_piece_entry = tk.Entry(self.left_frame)
        self.temp_piece_entry.grid(row=13, column=1, pady=10)
        self.temp_piece_entry.bind("<Return>", lambda event: self.set_temp_piece())
        self.set_temp_button = tk.Button(self.left_frame, text="Fixer la température", command=self.set_temp_piece)
        self.set_temp_button.grid(row=13, column=3, pady=10)

        # ---- GRAPHIQUE (Seul à droite) ----
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=8, sticky="nsew")

        # Ajustement de la disposition des frames
        self.left_frame.columnconfigure(0, weight=1)
        self.left_frame.columnconfigure(1, weight=2)
        self.left_frame.columnconfigure(2, weight=1)
        self.right_frame.columnconfigure(0, weight=1)  # Graphique bien centré
        self.right_frame.rowconfigure(0, weight=1)  # Remplir l’espace verticalement

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
            rep = envoyer_commande("get_pidf", self.ser)
            kp, ti, td, tf = rep.split(",")
            self.kp.set(kp)
            self.ti.set(ti)
            self.td.set(td)
            self.tf.set(tf)


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

    # Changer la température piece
    def set_temp_piece(self):
        temperature = self.temp_piece_entry.get()
        if temperature and self.ser:
            command = f"set_temp_piece {temperature}"
            reponse = envoyer_commande(command, self.ser)
            self.output_text.insert(tk.END, f"Envoyé : {command}\nRéponse : {reponse}\n")
            self.output_text.see(tk.END)
            self.temp_piece_entry.delete(0, tk.END)
            if reponse != "Aucune réponse, veuillez réessayer." and reponse != "La température n'est pas entre 20°C et 30°C.":
                self.temp_piece.set(temperature)

    def set_pidf(self, kp=False, ti=False, td=False, tf=False):
        if self.ser:
            kp_val = self.kp_entry.get() if kp else self.kp.get()
            ti_val = self.ti_entry.get() if ti else self.ti.get()
            td_val = self.td_entry.get() if td else self.td.get()
            tf_val = self.tf_entry.get() if tf else self.tf.get()
            commande = f"set_pidf {kp_val},{ti_val},{td_val},{tf_val}"
            reponse = envoyer_commande(commande, self.ser)
            self.output_text.insert(tk.END, f"Envoyé : {commande}\nRéponse : {reponse}\n")
            self.output_text.see(tk.END)
            self.kp_entry.delete(0, tk.END)
            self.ti_entry.delete(0, tk.END)
            self.td_entry.delete(0, tk.END)
            self.tf_entry.delete(0, tk.END)
            if reponse != "Aucune réponse, veuillez réessayer.":
                if kp:
                    self.kp.set(kp_val)
                elif ti:
                    self.ti.set(ti_val)
                elif td:
                    self.td.set(td_val)
                elif tf:
                    self.tf.set(tf_val)

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
                    #self.writer.writerow([temps, ocr1a, t_actu, t_milieu, t_laser, t_laser_estime, stable])

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