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
const double freq = 1.5; // Freq échantillonnage = freq/3

// Constantes et variables pour PI
const double Kp = 0.00062;
const double Ki = 0.11735;
const double Kd = 0;

// Memoire donnees pour integrale
const int N = 10;
double u[N] = {0}; // files entrees
double y[N] = {0}; // files sortie
int index = 0;
double erreur_integrale = 0;


// Saturation
const int umin = 350;
const int umax = 3500;

bool mode_rep_echelon = true;  // Pour setter si on veut sauvegarder des réponses à l'échelon ou asservir la temperature (si false)

double temp_cible = 27.0;

// Variables lecteurs températures
volatile uint16_t valeur_ADC[3];
volatile uint8_t canal_ADC = 0;   // numero pin en cours de lecture
volatile bool nouvelle_donnee = false;

// Déclarations fonctions
double PID_output(double cible, double mesure);
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
  OCR1A = 1600; // entre 0 et 4000 (max 3700 sinon short... 0-3700 avec milieux environ a 1850)

  // Timer2 pour test sur arduino uno
  /*TCCR2A = (1 << WGM21);   // Mode CTC pour faire interruptions
  TCCR2B = (1 << CS22);    // Prescaler de 64
  OCR2A = 249;             // Calcul pour trouver OCR2A en fonction de la fréquence d'échantillonnage : (16 MHz / (prescaler *  62.5Hz)) - 1 = 249 
  TIMSK2 |= (1 << OCIE2A); // Activer l’interruption du timer
*/
  // Timer 3: code officiel pour arduino mega
  // Configurer Timer3 pour générer interruption
  TCCR3A = 0;                      // Mode normal
  TCCR3B = (1 << WGM32) | (1 << CS32) | (1 << CS30);  // CTC mode, prescaler 1024
  OCR3A = 16000000 / (1024 * freq) - 1;                 
  TIMSK3 |= (1 << OCIE3A);         // Activer l’interruption du timer
  

  // Configurer l’ADC
  ADMUX = (1 << REFS0);    // Référence AVCC, entrée (A0)
  ADCSRA = (1 << ADEN)  |  // Activer l’ADC
           (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0); // Prescaler 128 (16MHz / prescaler = 125kHz ADC)
  // Complète une conversion en 104us (13 cycle d'horloge / fréquence adc = 104us)
}

// Routine interruption echantillonnage TIMER2 SI arduino uno
ISR(TIMER3_COMPA_vect) {
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

    else if (commande.startsWith("get_mode ")){
      if (mode_rep_echelon){
        Serial.println("RESP:1");
      } else {
        Serial.println("RESP:2");
      }
    }

    else if (commande.startsWith("set_voltage ")) {
      if (mode_rep_echelon) {
        String valeur_str = commande.substring(11);
        valeur_str.trim();
        bool estNombre = true;

        // Vérifier si la valeur est bien un nombre
        for (unsigned int i = 0; i < valeur_str.length(); i++) {
            if (!isDigit(valeur_str[i]) && valeur_str[i] != '.' && valeur_str[i] != '-' && valeur_str[i] != '+' && valeur_str[i] != ' ') {
                estNombre = false;
                break;
            }
        }
        float volt = valeur_str.toFloat();
        if (volt > 1. || volt < -1. || !estNombre) {
          Serial.println("RESP:La tension ne respecte pas les bornes de -1V a 1V.");
        }
        else {
          OCR1A = (volt + 1.) * umax/2;
          Serial.print("RESP:Volts en entré: ");
          Serial.println(volt);
        } 
      }
      else {
        Serial.println("RESP:Tu ne peux pas commander une tension en mode automatique.");
      }
    }

    else if (commande.startsWith("set_temp ")){
      double temp = commande.substring(8).toFloat();
      if (temp > 30. || temp < 20.) {
        Serial.println("RESP:La température n'est pas entre 20°C et 30°C.");
      }
      else {
        temp_cible = temp;
        Serial.print("RESP:Température en entré: ");
        Serial.print(temp);
        if (mode_rep_echelon){
          Serial.println(". Cependant, il y n'aura pas d'effet, car vous êtes en mode manuel.");
        }
        else{
          Serial.println();
        }
      }
    }
    
    else {
        Serial.println("RESP:Commande inconnue.");
    }
  }

  // attendre qu'on recupere une nouvelle donnee
  if (nouvelle_donnee) {
    // Conversions ADC (10 bits)
    // Tensions (pour récolte données)
    double t_actu_brut = valeur_ADC[0] * 5 / 1023.0 * 24000/100000 + 1.7929;
    double t_milieu_brut = valeur_ADC[1] * 5 / 1023.0 * 24000/100000 + 1.7929;
    double t_laser_brut = valeur_ADC[2] * 5 / 1023.0 * 24000/100000 + 1.7929;

    // Convertir les tensions en températures
    double t_actu_traite = tension_a_temp(valeur_ADC[0]);
    double t_milieu_traite = tension_a_temp(valeur_ADC[1]);
    double t_laser_traite = tension_a_temp(valeur_ADC[2]);


    // Afficher les donnees sur le serial monitor (pour export)
    Serial.print("DATA:");
    Serial.print(millis()/1000.0);
    Serial.print(",");
    Serial.print(t_actu_traite);
    Serial.print(",");
    Serial.print(t_milieu_traite);
    Serial.print(",");
    Serial.print(t_laser_traite);
    Serial.print(",");
    Serial.print(t_actu_brut);
    Serial.print(",");
    Serial.print(t_milieu_brut);
    Serial.print(",");
    Serial.print(t_milieu_brut);

    if (mode_rep_echelon){
    }
    else { // Mode controleur
      double sortie_pid = PID_output(temp_cible, t_laser_traite); 
      // ici on va vouloir changer la fréquence du pwm en fonction de sorti_PI :
      OCR1A = sortie_pid;
    }
    Serial.print(",");
    Serial.println(OCR1A);
    nouvelle_donnee = false;


  }
  
}

// Calcule la sortie du PID
double PID_output(double cible, double mesure) {
  double erreur = cible - mesure;

  // Mise à jour de l'erreur integrale
  erreur_integrale += erreur; // Accumulation pour le terme intégral

  // Calcul PID
  double derivee = erreur - u[index];
  index = (index + 1) % N; // maj index
  u[index] = erreur; 

  double output = Kp * erreur + Ki * erreur_integrale + Kd * derivee;
  output = map(output, -104., 104., umin, umax); // output avant saturation... TODO: Changer borne depart
  
  // Appliquer saturation et anti-windup
  if (output > umax) {
    output = umax;
    erreur_integrale -= erreur; // Anti-windup
  } 
  else if (output < umin) {
    output = umin;
    erreur_integrale -= erreur; // Anti-windup
  }

  return constrain(output, 0., 3750.);
}


// Calcule temperature avec thermistance NTC (resistance descend si température monte)
double tension_a_temp(double donne_brute) {
  // Transfert en tension et enlever gain et soustraction ampli
  double tension = donne_brute * 5 / 1023.0 * 24000/100000 + 1.7929; // Avec soustracteur
  //double tension = donne_brute * 5 / 1023.0; // Avec juste un diviseur de tension
  double rt = tension * r_diviseur / (5 - tension) ; // diviseur tension
  double log_r = log(rt/r_25deg); // Simplifier calcul
  return 1/(A+B*log_r+C*log_r*log_r+D*log_r*log_r*log_r) - 273.15; // temperature en °C
}

