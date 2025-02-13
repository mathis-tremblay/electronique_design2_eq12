import os
import serial
import csv
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque


def envoyer_commande(commande):
    """Envoie une commande et attend une réponse RESP:"""
    ser.write((commande + "\n").encode())
    while True:
        ligne = ser.readline().decode('utf-8', errors='ignore').strip()
        if ligne.startswith("RESP:"):
            return ligne[5:]  # Retourner la réponse après "RESP:"

# Lire les données capteur en continu
def lire_donnees():
    ligne = ser.readline().decode('utf-8', errors='ignore').strip()
    if ligne.startswith("DATA:"):
        try:
            # Extraire la valeur après "DATA:" et split la ligne en donnees pour csv
            valeurs = ligne[5:].split(",")

            # Vérifier que le format est correct et écrire dans le fichier CSV
            if len(valeurs) == 4:
                writer.writerow(valeurs)
                print("Donnée enregistrée :", valeurs)
            else:
                print("Format invalide :", ligne)

        except Exception as e:
            print("Erreur de lecture :", e)

# Fonction pour update graphique et csv
def update_plot(frame):
    global nb_points
    ligne = ser.readline().decode('utf-8', errors='ignore').strip()
    if ligne:
        try:
            valeurs = ligne.split(",")

            # Vérifier que le format est ok avant d'ajouter les valeurs
            if len(valeurs) == 4:
                temps, actu, milieu, laser = map(float, valeurs)
                print("Donnée enregistrée :", valeurs)

                # Ajouter les nouvelles valeurs aux buffers
                if nb_points % 10 == 0:
                    x_data.append(temps)
                    actu_data.append(actu)
                    milieu_data.append(milieu)
                    laser_data.append(laser)

                    # Mettre à jour graphique
                    line1.set_data(x_data, actu_data)
                    line2.set_data(x_data, milieu_data)
                    line3.set_data(x_data, laser_data)

                    ax.set_xlim(0, max(x_data) if x_data else 1)
                    ax.set_ylim(min(min(actu_data, default=0), min(milieu_data, default=0), min(laser_data, default=0)),
                                max(max(actu_data, default=1), max(milieu_data, default=1), max(laser_data, default=1)))
                    ax.relim()
                    ax.autoscale_view()


                # Écriture dans le fichier CSV
                with open(OUTPUT_FILE, "a", newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([temps, actu, milieu, laser])

        except ValueError:
            print("Erreur de conversion :", ligne)
    if nb_points % 10 == 0: # Afficher un point sur 10
        nb_points += 1
        return line1, line2, line3


# Configuration du port série (ajuste selon ton système)
PORT = "COM4"  # Changer selon le port usb de l'Arduino
BAUDRATE = 115200
OUTPUT_FILE = "data" # Nom du fichier, s'il existe déjà, renommer
i = 0
while(os.path.exists("./"+OUTPUT_FILE+str(i)+".csv")):
    i += 1
OUTPUT_FILE = OUTPUT_FILE + str(i) + ".csv"

# Init buffers données
BUFFER_SIZE = 1000
x_data = deque(maxlen=BUFFER_SIZE)
actu_data = deque(maxlen=BUFFER_SIZE)
milieu_data = deque(maxlen=BUFFER_SIZE)
laser_data = deque(maxlen=BUFFER_SIZE)

# Init graphique
fig, ax = plt.subplots()
ax.set_title("Données en temps réel")
ax.set_xlabel("Temps [ms]")
ax.set_ylabel("Températures [°C]")
line1, = ax.plot([], [], label="ACTU", color="red")
line2, = ax.plot([], [], label="MILIEU", color="green")
line3, = ax.plot([], [], label="LASER", color="blue")
ax.legend()

# Création du fichier CSV et écriture de l'en-tête
with open(OUTPUT_FILE, "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["temps", "ACTU", "MILIEU", "LASER"])  # En-tête du fichier CSV

print(f"Fichier {OUTPUT_FILE} créé avec en-tête.")

# Ouvrir la connexion série
try:
    ser = serial.Serial(port=PORT, baudrate=BAUDRATE, timeout=1)
    time.sleep(1)  # Attendre 1 seconde pour que le port série soit prêt
    print(f"Port série {PORT} ouvert, enregistrement en cours...")
except serial.SerialException:
    print("Erreur d'ouverture du port série")
    exit(1)

try:
    with open(OUTPUT_FILE, "a", newline='') as f:
        writer = csv.writer(f)
        time.sleep(1)
        print(envoyer_commande("set_voltage -1"))
        while True:
            lire_donnees()



#ani = animation.FuncAnimation(fig, update_plot, interval=100)

# Affichage du graphique en temps réel
#plt.show()

# Fermeture propre en cas d'interruption
#try:
#    while plt.get_fignums():
#        plt.pause(0.1)
except KeyboardInterrupt: # Ctrl C pour terminer
    print("\nArrêt du programme")
    ser.close()
