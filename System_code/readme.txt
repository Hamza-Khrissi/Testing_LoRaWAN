# 🔧 RFID LoRaWAN Processing System

## 📋 Description

Système complet de traitement et transmission d'EPCs RFID via LoRaWAN, optimisé pour la compression de données et la transmission efficace.

### 🎯 Fonctionnalités principales

- **Optimisation des EPCs** : Regroupement par préfixes communs pour réduire la taille des payloads
- **Encapsulation LoRaWAN** : Génération de trames LoRaWAN avec calculs précis des paramètres
- **Support multi-plateforme** : Version PC (test) et Raspberry Pi (transmission réelle)
- **Interface SX1262** : Communication SPI avec transceiver LoRa
- **Logging complet** : Traçabilité de tous les traitements

## 📁 Structure du projet

```
LORAWAN-CODE/
├── EPC_OPT.py              # Classe d'optimisation des EPCs
├── Encapsulation.py        # Classe d'encapsulation LoRaWAN
├── MainController.py       # Contrôleur principal
├── main_test.py           # Script pour PC (Visual Studio Code)
├── main_rpi.py            # Script pour Raspberry Pi 4
├── EPCS.xlsx              # Fichier d'entrée (EPCs RFID)
├── EPCSOPT.xlsx           # Résultats d'optimisation
├── FinalOutput.xlsx       # Résultats finaux
└── README.md              # Ce fichier
```

## ⚙️ Installation

### Prérequis communs

```bash
pip install pandas openpyxl pathlib
```

### Pour Raspberry Pi uniquement

```bash
pip install spidev RPi.GPIO
# ou
pip install pySX126x  # Alternative pour SX1262
```

## 🚀 Utilisation

### 1. Préparation des données

Créez un fichier `EPCS.xlsx` contenant vos EPCs RFID :
- Une colonne avec des EPCs de 24 caractères hexadécimaux
- Un EPC par ligne
- Exemple : `E28011606000020000003039`

### 2. Exécution sur PC (Test)

```bash
python main_test.py
```

**Fonctionnalités :**
- ✅ Traitement complet des EPCs
- ✅ Génération des payloads LoRaWAN
- ✅ Export Excel des résultats
- ✅ Mode interactif pour configuration
- ✅ Simulation des paramètres LoRa
- ❌ Pas de transmission réelle

**Fichiers générés :**
- `EPCSOPT.xlsx` : Résultats d'optimisation
- `FinalOutput.xlsx` : Payloads LoRaWAN générés
- `test_processing.log` : Journal détaillé

### 3. Exécution sur Raspberry Pi (Production)

```bash
sudo python main_rpi.py
```

**Fonctionnalités :**
- ✅ Traitement complet des EPCs
- ✅ Génération des payloads LoRaWAN
- ✅ Export Excel des résultats
- ✅ Transmission LoRa via SX1262
- ✅ Communication SPI
- ✅ Gestion GPIO
- ✅ Arrêt propre (Ctrl+C)

**Configuration GPIO (SX1262) :**
```
NSS (CS)  : GPIO 8  (CE0)
RESET     : GPIO 22
BUSY      : GPIO 23
DIO1 (IRQ): GPIO 24
SPI       : Bus 0, Device 0
```

## 🔧 Configuration LoRaWAN

### Paramètres supportés

| Paramètre | Valeurs possibles | Défaut |
|-----------|-------------------|--------|
| Spreading Factor (SF) | 7-12 | 12 |
| Bandwidth (BW) | 125, 250, 500 kHz | 125 |
| Coding Rate (CR) | 1-4 (4/5 à 4/8) | 1 |
| Fréquence | 868.1 MHz (EU868) | Fixe |
| Puissance | 14 dBm | Fixe |

### Calculs automatiques

Le système calcule automatiquement :
- Taille maximale du payload selon le SF
- Nombre d'EPCs par trame
- Durée des symboles (T_sym)
- Durée des trames (T_frame)
- Temps de transmission total
- Respect du duty cycle (1% max/jour)

## 📊 Format des résultats

### Fichier `EPCSOPT.xlsx`

| Colonne | Description |
|---------|-------------|
| Group_ID | Identifiant du groupe |
| Prefix | Préfixe commun (hex) |
| Prefix_Bytes | Taille du préfixe en octets |
| Suffix_Bytes | Taille des suffixes en octets |
| Suffix_Count | Nombre d'EPCs dans le groupe |
| Total_Payload_Bytes | Taille totale compressée |
| EPCs_SF7_51B | EPCs max avec SF7 (51 octets) |
| EPCs_SF12_11B | EPCs max avec SF12 (11 octets) |
| Compression_% | Taux de compression |

### Fichier `FinalOutput.xlsx`

| Colonne | Description |
|---------|-------------|
| Group_ID | Identifiant du groupe |
| Prefix | Préfixe commun |
| Suffix_Count | Nombre d'EPCs |
| Original_EPCs | EPCs d'origine |
| Payload_Hex | Payload LoRaWAN (hex) |
| Payload_Bytes | Taille du payload |
| T_frame_ms | Durée de trame (ms) |
| T_sym_ms | Durée symbole (ms) |
| N_payload | Nombre de symboles payload |
| Decoded_EPCs | EPCs décodés (vérification) |
| Verification_OK | Vérification réussie |

## 🔍 Classes principales

### MainController

Contrôleur principal qui orchestre le processus complet :

```python
controller = MainController(sf=12, bw=125, cr=1)
result_file = controller.run_complete_process()
```

### EPCAnalyzer (EPC_OPT.py)

Analyse et optimise les EPCs par regroupement :
- Lecture fichiers Excel/CSV/TXT
- Regroupement par préfixes communs
- Calcul des compressions
- Export des résultats

### EPCLoRaWANCalculator (Encapsulation.py)

Encapsulation LoRaWAN et calculs :
- Création d'en-têtes LoRaWAN
- Encapsulation des EPCs
- Calculs des paramètres radio
- Décodage et vérification

## 🛠️ Utilisation avancée

### Mode interactif

Les deux scripts supportent un mode interactif :

```bash
python main_test.py
# ou
python main_rpi.py
```

Puis répondre `y` à "Mode interactif ?"

### Configuration programmatique

```python
from MainController import MainController

# Configuration personnalisée
controller = MainController(
    sf=10,           # SF10 pour plus de débit
    bw=250,          # 250 kHz bandwidth
    cr=2,            # CR 4/6
    log_file="custom.log"
)

# Traitement
controller.load_input_epcs("mes_epcs.xlsx")
controller.optimize_epcs()
controller.create_lorawan_calculator()
controller.process_groups_to_payloads()
controller.save_final_results("mes_resultats.xlsx")
```

### Transmission Raspberry Pi

```python
from main_rpi import RPiMainController

controller = RPiMainController(sf=12, bw=125, cr=1)
controller.run_complete_process_with_transmission(
    transmit=True,
    delay_between_frames=2.0  # 2s entre trames
)
```

## 🐛 Dépannage

### Erreurs communes

**"File not found: EPCS.xlsx"**
- Créez le fichier avec vos EPCs
- Utilisez le mode interactif pour générer un exemple

**"Invalid EPC format"**
- Vérifiez que les EPCs font exactement 24 caractères
- Utilisez uniquement des caractères hexadécimaux (0-9, A-F)

**"Modules SPI/GPIO non disponibles"**
- Sur PC : Normal, le script fonctionne en mode simulation
- Sur Raspberry Pi : Installez les modules requis

**"Permission denied" sur Raspberry Pi**
- Utilisez `sudo python main_rpi.py`
- Vérifiez les permissions sur `/dev/spidev*`

### Logs de débogage

Tous les traitements sont enregistrés dans les fichiers de log :
- `test_processing.log` (PC)
- `rpi_processing.log` (Raspberry Pi)

## 📈 Optimisations

### Compression des EPCs

Le système optimise automatiquement :
- Regroupement par préfixes communs (minimum 6 caractères)
- Calcul du taux de compression
- Adaptation selon les limites LoRaWAN

### Paramètres LoRa optimaux

| Cas d'usage | SF | BW | Avantages |
|-------------|----|----|-----------|
| Longue portée | 12 | 125 | Maximum de portée |
| Débit moyen | 10 | 125 | Compromis portée/débit |
| Haut débit | 7 | 250 | Maximum de débit |

### Respect du duty cycle

Le système calcule automatiquement :
- Temps d'antenne par lot d'EPCs
- Nombre maximum de lots par jour (1% duty cycle)
- Planification optimale des transmissions

## 🤝 Contribution

Pour contribuer au projet :
1. Respectez la structure des classes existantes
2. Ajoutez des logs détaillés
3. Testez sur PC avant Raspberry Pi
4. Documentez les nouvelles fonctionnalités

## 📄 Licence

Ce projet est sous licence [LICENSE].

## 📞 Support

Pour toute question ou problème :
- Consultez les fichiers de log
- Vérifiez la configuration LoRaWAN
- Testez d'abord en mode PC