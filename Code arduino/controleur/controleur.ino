// Constantes pour les pins
const int T_ACTU = A0;
const int T_MILIEU = A1;
const int T_LASER = A2;
const int ACTU = 11; // pour avoir timer1 (16 bits)

// Constantes thermistances
const double A = 0.00335401643468053;
const double B = 0.000256523550896126;
const double C = 0.00000260597012072052;
const double D = 0.000000063292612648746;
const int r_25deg = 10000;
const int r_diviseur = 10000;

// Constantes et variables pour PI
const double GAIN = 0.8;
const double TEMPS_INTEGRALE = 0.1;
const double TS = 0.1; // periode echantillonnage (en sec)... à choisir 
double dt = 0.003; // temps echantillonnage de 3ms
double integrale = 0;

bool mode_rep_echelon = true;  // Pour setter si on veut sauvegarder des réponses à l'échelon ou asservir la temperature (si false)

// Variables lecteurs températures
volatile uint16_t valeur_ADC[3];
volatile uint8_t canal_ADC = 0;   // numero pin en cours de lecture
volatile bool nouvelle_donnee = false;

// Déclarations fonctions
double PI_output(double cible, double mesure);
double tension_a_temp(double tension);


void setup() {
  // Pour print
  Serial.begin(115200);

  pinMode(T_ACTU, INPUT);
  pinMode(T_MILIEU, INPUT);
  pinMode(T_LASER, INPUT);
  pinMode(ACTU, OUTPUT);


  // Pour avoir fréquence de 4kHz et 16 bits sur le pwm
  TCCR1A = (1 << COM1A1) | (1 << WGM11); // Mode Fast PWM avec TOP = ICR1
  TCCR1B = (1 << WGM13) | (1 << WGM12) | (1 << CS10); // Mode 14, prescaler = 1

  ICR1 = 4000;  // Définit la période pour obtenir 4 kHz
  OCR1A = 1200; // entre 0 et 4000

  // Configurer Timer2 pour générer une interruption toutes les x ms pour lire les températures (F_échantillonnage = 3x ms, car boucle sur les 3 pins)
  TCCR2A = (1 << WGM21);   // Mode CTC pour faire interruptions
  TCCR2B = (1 << CS22);    // Prescaler de 64
  OCR2A = 249;             // Calcul pour trouver OCR2A en fonction de la fréquence d'échantillonnage : (16 MHz / (prescaler *  62.5Hz)) - 1 = 249 
  TIMSK2 |= (1 << OCIE2A); // Activer l’interruption du timer

  /* Timer 3 (arduino mega seulement)
  // Configurer Timer3 pour générer une interruption toutes les  0.1 s pour lire les températures (F_échantillonnage = 30Hz, car boucle sur les 3 pins)
  TCCR3A = 0;                      // Mode normal
  TCCR3B = (1 << WGM32) | (1 << CS32) | (1 << CS30);  // CTC mode, prescaler 1024
  OCR3A = 15624;                   // (16 MHz / (1024 * 10 Hz)) - 1 = 15624
  TIMSK3 |= (1 << OCIE3A);         // Activer l’interruption du timer
  */

  // Configurer l’ADC
  ADMUX = (1 << REFS0);    // Référence AVCC, entrée (A0)
  ADCSRA = (1 << ADEN)  |  // Activer l’ADC
           (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0); // Prescaler 128 (16MHz / prescaler = 125kHz ADC)
  // Complète une conversion en 104us (13 cycle d'horloge / fréquence adc = 104us)
}

// Routine interruption echantillonnage
ISR(TIMER2_COMPA_vect) {
   //Sélectionner le canal ADC (A0, A1, A2)
    ADMUX = (ADMUX & 0xF8) | canal_ADC; // Met à jour les bits MUX pour ADC0, ADC1 ou ADC2

    ADCSRA |= (1 << ADSC);  // Lancer une conversion ADC
    while (ADCSRA & (1 << ADSC));  // Attendre la fin de conversion
    valeur_ADC[canal_ADC] = ADC;  // Lire la valeur (10 bits)

    canal_ADC = (canal_ADC + 1) % 3;
    if (canal_ADC == 0) nouvelle_donnee = true; // Après une séquence complète (A0, A1, A2)
  }

void loop() {

  // Vérifier si une commande est reçue
  if (Serial.available() > 0) {
    String commande = Serial.readStringUntil('\n');
    commande.trim();
    if (commande.startsWith("set_mode ")) {
      int mode = commande.substring(8).toInt();
      if (mode == 1) {
        mode_rep_echelon = true;
        Serial.println("RESP:Mode manuel activé.");
      }
      else {
        mode_rep_echelon = false;
        Serial.println("RESP:Mode contrôleur activé.");
      }
    }
    else if (commande.startsWith("set_voltage ")) {
      if (mode_rep_echelon) {
        int volt = commande.substring(11).toFloat();
        if (volt > 1. || volt < -1.) {
          Serial.println("RESP:La tension ne respecte pas les bornes de -1V a 1V");
        }
        else {
          OCR1A = (volt + 1.) * 2000;
        Serial.print("RESP:Volts en entré: ");
        Serial.println(volt);
        } 
      }
      else {
        Serial.println("RESP:Tu ne peux pas commander une tension en mode automatique");
      }
    }
    else {
        Serial.println("RESP:Commande inconnue.");
    }
  }

  // attendre qu'on recupere une nouvelle donnee
  if (nouvelle_donnee) {
    // Conversions ADC (10 bits)
    // Si on veut plus precis il va falloir un adc externe
    double t_actu_brut = valeur_ADC[0] * 5 / 1023.0;
    double t_milieu_brut = valeur_ADC[1] * 5 / 1023.0;
    double t_laser_brut = valeur_ADC[2] * 5 / 1023.0;

    // Convertir les tensions en températures
    double t_actu_traite = tension_a_temp(t_actu_brut);
    double t_milieu_traite = tension_a_temp(t_milieu_brut);
    double t_laser_traite = tension_a_temp(t_laser_brut);



    if (mode_rep_echelon){
      // Afficher les donnees sur le serial monitor (pour export)
      Serial.print("DATA:");
      Serial.print(millis());
      Serial.print(",");
      Serial.print(t_actu_traite);
      Serial.print(",");
      Serial.print(t_milieu_traite);
      Serial.print(",");
      Serial.println(t_laser_traite);
      delay(1000);
    }
    else {
      double sortie_pi = PI_output(28.0, 2); // 28 pour test
      // ici on va vouloir changer la fréquence du pwm en fonction de sorti_PI :
      // OCR1A = 2000 // entre 0 et 4000
    }


  }
  
}

// Calcule la sortie du PI
double PI_output(double cible, double mesure){
  // TODO: technique integrale plus precise
  // TODO: anti wind-up et protection contre saturation
  double erreur = cible - mesure;
  integrale += erreur * dt;
  double output = GAIN * erreur + TEMPS_INTEGRALE * integrale;

  return output;
}

// Calcule temperature avec thermistance NTC (resistance descend si température monte)
double tension_a_temp(double tension) {
  // Enlever le gain de l'ampli si nécessaire
  double rt = tension * r_diviseur / (5 - tension) ; // diviseur tension
  //double rt = (r_diviseur*5 - (r_diviseur*2)*tension)*r_diviseur/(r_diviseur*5 - ((r_diviseur*2)*tension)); // Wheatstone
  double log_r = log(rt/r_25deg); // Simplifier calcul
  return 1/(A+B*log_r+C*log_r*log_r+D*log_r*log_r*log_r) - 273.15; // temperature en °C
}


// 1.2 ohm