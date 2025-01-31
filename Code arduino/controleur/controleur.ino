// Constantes pour les pins
const int T_ACTU = A0;
const int T_MILIEU = A1;
const int T_LASER = A2;
const int ACTU = 3;

// Constantes thermistances
const double A = 0.00335401643468053;
const double B = 0.000256523550896126;
const double C = 0.00000260597012072052;
const double D = 0.000000063292612648746;
const int r_25deg = 10000;
const int r_diviseur = 10000;

// Constantes pour PI
const double GAIN = 0.8;
const double TEMPS_INTEGRALE = 0.1;
const double TS = 0.1; // periode echantillonnage (en sec)... à choisir 

// Params
bool asservir = true;  // Pour setter si on veut asservir la temperature

double dt;
double last_time;
double integrale;

// Déclarations fonctions
double PI_output(...);
double tension_a_temp(double tension);


void setup() {
  // Pour print
  Serial.begin(9600);

  pinMode(T_ACTU, INPUT);
  pinMode(T_MILIEU, INPUT);
  pinMode(T_LASER, INPUT);
  pinMode(ACTU, OUTPUT);

  integrale = 0;
}

void loop() {
  // Temps entre chaque echantillon
  double now = millis();
  dt = (now - last_time)/1000.0; // en secondes
  last_time = now;
  // Donnes temperature (brut = tension termistance, traite = converti en temperature)
  double t_actu_brut = 1;//analogRead(T_ACTU);
  double t_actu_traite = tension_a_temp(t_actu_brut);
  double t_milieu_brut = 2;//analogRead(T_MILIEU);
  double t_milieu_traite = tension_a_temp(t_milieu_brut);
  double t_laser_brut = 2.5;//analogRead(T_LASER);
  double t_laser_traite = tension_a_temp(t_laser_brut);
  Serial.println(String(t_actu_traite) + " | " + String(t_milieu_traite) + " | " + String(t_laser_traite) + "\n");
  delay(1000); // temporaire

  double sortie_pi = PI_output(28.0, t_laser_traite); // 28 pour test
  //analogWrite(ACTU, constrain(sortie_pi * 255.0 / 5.0, 0, 255)); 
  Serial.println(constrain(sortie_pi * 255.0 / 5.0, 0, 255));
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
  double rt = tension * r_diviseur / (3.3 - tension) ; // diviseur tension (3.3V à confirmer)
  double log_r = log(rt/r_25deg); // Simplifier calcul
  return 1/(A+B*log_r+C*log_r*log_r+D*log_r*log_r*log_r) - 273.15; // temperature en °C
}