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

const bool MODE_REP_ECHELON = true;  // Pour setter si on veut sauvegarder des réponses à l'échelon ou asservir la temperature (si false)

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
  TCCR1A |= (1 << COM1A1);  // Sortie PWM sur OC1A (D11)
  TCCR1A |= (1 << WGM11);   // Mode fast PWM 
  TCCR1B |= (1 << WGM12) | (1 << WGM13);  // Mode 14 : Fast PWM avec TOP = ICR1
  // Définir la fréquence du PWM
  ICR1 = 4000;
  // Choix du prescaler
  TCCR1B |= (1 << CS10);  // Prescaler = 1 (fréquence maximale)
  OCR1A = 2000; // 50% du cycle car fréquence de 4000Hz, donc 0V de output


  // Configurer Timer2 pour générer une interruption toutes les 1 ms pour lire les températures (F_échantillonnage = 3ms, car boucle sur les 3 pins)
  TCCR2A = (1 << WGM21);   // Mode CTC
  TCCR2B = (1 << CS22);    // Prescaler de 64
  OCR2A = 249;             // Calcul pour trouver OCR2A en fonction de la fréquence d'échantillonnage (16 MHz / (64 * 1000Hz)) - 1 = 249  
  TIMSK2 |= (1 << OCIE2A); // Activer l’interruption du timer

  // Configurer l’ADC
  ADMUX = (1 << REFS0);    // Référence AVCC, entrée ADC0 (A0)
  ADCSRA = (1 << ADEN)  |  // Activer l’ADC
           (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0); // Prescaler 128 (125 kHz ADC)
  // 
}

// Routine interruption echantillonnage
ISR(TIMER2_COMPA_vect) {
    // Sélectionner le canal ADC (A0, A1, A2)
    ADMUX = (ADMUX & 0xF8) | canal_ADC; // Met à jour les bits MUX pour ADC0, ADC1 ou ADC2

    ADCSRA |= (1 << ADSC);  // Lancer une conversion ADC
    while (ADCSRA & (1 << ADSC));  // Attendre la fin de conversion
    valeur_ADC[canal_ADC] = ADC;  // Lire la valeur (10 bits)

    canal_ADC = (canal_ADC + 1) % 3;
    if (canal_ADC == 0) nouvelle_donnee = true; // Après une séquence complète (A0, A1, A2)
  }

void loop() {
  // attendre qu'on recupere une nouvelle donnee
  if (nouvelle_donnee) {
    // Conversions ADC (10 bits)
    // Si on veut plus precis il va falloir un adc externe
    double t_actu_brut = valeur_ADC[0] * 3.3 / 1023.0;
    double t_milieu_brut = valeur_ADC[1] * 3.3 / 1023.0;
    double t_laser_brut = valeur_ADC[2] * 3.3 / 1023.0;

    // Convertir les tensions en températures
    double t_actu_traite = tension_a_temp(t_actu_brut);
    double t_milieu_traite = tension_a_temp(t_milieu_brut);
    double t_laser_traite = tension_a_temp(t_laser_brut);

    if (MODE_REP_ECHELON){
      // Afficher les donnees
      Serial.print("{\"temps\":");
      Serial.print(millis());
      Serial.print(",\"ACTU\":");
      Serial.print(t_actu_traite);
      Serial.print(",\"MILIEU\":");
      Serial.print(t_milieu_traite);
      Serial.print(",\"LASER\":");
      Serial.print(t_laser_traite);
      Serial.println("}");
    }
    else {
      double sortie_pi = PI_output(28.0, t_laser_traite); // 28 pour test
      // ici on va vouloir changer la fréquence du pwm en fonction de sorti_PI :
      // OCR1A = 2000 // 50% du cycle car fréquence de 4000Hz
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
  double rt = tension * r_diviseur / (3.3 - tension) ; // diviseur tension (3.3V à confirmer)
  double log_r = log(rt/r_25deg); // Simplifier calcul
  return 1/(A+B*log_r+C*log_r*log_r+D*log_r*log_r*log_r) - 273.15; // temperature en °C
}