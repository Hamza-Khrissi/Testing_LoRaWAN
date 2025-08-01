#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_rpi.py - Script pour Raspberry Pi 4 avec transceiver SX1262
Traitement complet des EPCs RFID via LoRaWAN avec transmission réelle.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import signal
import threading

# Import de la classe principale
try:
    from MainController import MainController
except ImportError:
    print("❌ Erreur: Impossible d'importer MainController")
    sys.exit(1)

# Imports pour Raspberry Pi et SX1262
try:
    import spidev
    import RPi.GPIO as GPIO
    SPI_AVAILABLE = True
    print("✅ Modules SPI/GPIO disponibles")
except ImportError:
    SPI_AVAILABLE = False
    print("⚠️ Modules SPI/GPIO non disponibles (mode simulation)")

# Configuration GPIO pour SX1262
class SX1262Config:
    """Configuration des pins GPIO pour le SX1262."""
    
    # Pins GPIO (BCM numbering)
    NSS_PIN = 8      # Chip Select (CE0)
    RESET_PIN = 22   # Reset
    BUSY_PIN = 23    # Busy
    DIO1_PIN = 24    # Digital I/O 1 (IRQ)
    
    # Configuration SPI
    SPI_BUS = 0      # SPI bus number
    SPI_DEVICE = 0   # SPI device number
    SPI_SPEED = 1000000  # 1MHz
    
    # Configuration LoRa
    FREQUENCY = 868100000  # 868.1 MHz (EU868)
    OUTPUT_POWER = 14      # dBm
    PREAMBLE_LENGTH = 8    # symbols


class SX1262Controller:
    """Contrôleur pour le transceiver SX1262."""
    
    def __init__(self):
        self.config = SX1262Config()
        self.spi = None
        self.initialized = False
        
        if SPI_AVAILABLE:
            self.setup_gpio()
            self.setup_spi()
        else:
            print("⚠️ Mode simulation - pas de communication SPI réelle")
    
    def setup_gpio(self):
        """Configure les pins GPIO."""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Configuration des pins
            GPIO.setup(self.config.NSS_PIN, GPIO.OUT)
            GPIO.setup(self.config.RESET_PIN, GPIO.OUT)
            GPIO.setup(self.config.BUSY_PIN, GPIO.IN)
            GPIO.setup(self.config.DIO1_PIN, GPIO.IN)
            
            # État initial
            GPIO.output(self.config.NSS_PIN, GPIO.HIGH)
            GPIO.output(self.config.RESET_PIN, GPIO.HIGH)
            
            print("✅ GPIO configuré")
            
        except Exception as e:
            print(f"❌ Erreur configuration GPIO: {e}")
            raise
    
    def setup_spi(self):
        """Configure la communication SPI."""
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(self.config.SPI_BUS, self.config.SPI_DEVICE)
            self.spi.max_speed_hz = self.config.SPI_SPEED
            self.spi.mode = 0
            
            print("✅ SPI configuré")
            
        except Exception as e:
            print(f"❌ Erreur configuration SPI: {e}")
            raise
    
    def reset_sx1262(self):
        """Reset du SX1262."""
        if not SPI_AVAILABLE:
            print("🔄 [SIMULATION] Reset SX1262")
            time.sleep(0.1)
            return
        
        try:
            GPIO.output(self.config.RESET_PIN, GPIO.LOW)
            time.sleep(0.001)  # 1ms
            GPIO.output(self.config.RESET_PIN, GPIO.HIGH)
            time.sleep(0.01)   # 10ms
            
            # Attendre que BUSY soit à LOW
            timeout = 100
            while GPIO.input(self.config.BUSY_PIN) and timeout > 0:
                time.sleep(0.001)
                timeout -= 1
            
            if timeout == 0:
                raise TimeoutError("SX1262 reste occupé après reset")
            
            print("✅ SX1262 reset effectué")
            
        except Exception as e:
            print(f"❌ Erreur reset SX1262: {e}")
            raise
    
    def send_command(self, command: int, params: list = None) -> list:
        """Envoie une commande au SX1262."""
        if not SPI_AVAILABLE:
            print(f"📡 [SIMULATION] Commande SX1262: 0x{command:02X}")
            return [0x00] * (len(params) if params else 1)
        
        try:
            # Attendre que BUSY soit à LOW
            while GPIO.input(self.config.BUSY_PIN):
                time.sleep(0.001)
            
            # Préparation des données
            data = [command]
            if params:
                data.extend(params)
            
            # Transmission SPI
            GPIO.output(self.config.NSS_PIN, GPIO.LOW)
            response = self.spi.xfer2(data)
            GPIO.output(self.config.NSS_PIN, GPIO.HIGH)
            
            return response
            
        except Exception as e:
            print(f"❌ Erreur commande SX1262: {e}")
            raise
    
    def initialize_lora(self, sf: int, bw: int, cr: int):
        """Initialise le SX1262 en mode LoRa."""
        try:
            print("🔧 Initialisation SX1262...")
            
            # Reset du module
            self.reset_sx1262()
            
            # Commandes d'initialisation (simplifiées)
            commands = [
                (0x80, [0x00]),  # SetStandby
                (0x8A, [0x01]),  # SetPacketType (LoRa)
                (0x8B, [sf, bw, cr, 0]),  # SetModulationParams
                (0x8C, [8, 0, 12, 1, 0, 0]),  # SetPacketParams
                (0x86, [self.config.FREQUENCY >> 24, 
                       (self.config.FREQUENCY >> 16) & 0xFF,
                       (self.config.FREQUENCY >> 8) & 0xFF,
                       self.config.FREQUENCY & 0xFF]),  # SetRfFrequency
                (0x8E, [self.config.OUTPUT_POWER, 0x04]),  # SetTxParams
            ]
            
            for cmd, params in commands:
                self.send_command(cmd, params)
                time.sleep(0.01)
            
            self.initialized = True
            print("✅ SX1262 initialisé")
            
        except Exception as e:
            print(f"❌ Erreur initialisation SX1262: {e}")
            raise
    
    def transmit_payload(self, payload: bytes) -> bool:
        """Transmet un payload via LoRaWAN."""
        if not self.initialized:
            print("⚠️ SX1262 non initialisé")
            return False
        
        try:
            if not SPI_AVAILABLE:
                print(f"📡 [SIMULATION] Transmission: {payload.hex().upper()} ({len(payload)} octets)")
                time.sleep(0.5)  # Simule le temps de transmission
                return True
            
            # Écriture du payload dans le buffer
            self.send_command(0x0E, [0x00])  # WriteBuffer
            self.send_command(0x0E, list(payload))
            
            # Configuration du packet
            self.send_command(0x8C, [self.config.PREAMBLE_LENGTH, 0, len(payload), 1, 0, 0])
            
            # Transmission
            self.send_command(0x83, [0x40, 0x00, 0x00])  # SetTx
            
            # Attente de fin de transmission (simplifiée)
            time.sleep(1.0)  # Timeout approximatif basé sur le SF
            
            print(f"📡 Payload transmis: {payload.hex().upper()} ({len(payload)} octets)")
            return True
            
        except Exception as e:
            print(f"❌ Erreur transmission: {e}")
            return False
    
    def cleanup(self):
        """Nettoyage des ressources."""
        try:
            if self.spi:
                self.spi.close()
            
            if SPI_AVAILABLE:
                GPIO.cleanup()
            
            print("✅ Nettoyage SX1262 terminé")
            
        except Exception as e:
            print(f"⚠️ Erreur nettoyage: {e}")


class RPiMainController:
    """Contrôleur principal pour Raspberry Pi avec transmission LoRa."""
    
    def __init__(self, sf: int = 12, bw: int = 125, cr: int = 1):
        self.main_controller = MainController(sf, bw, cr, "rpi_processing.log")
        self.sx1262 = SX1262Controller()
        self.transmission_active = False
        self.stop_event = threading.Event()
        
        # Configuration du signal handler pour arrêt propre
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Gestionnaire pour arrêt propre."""
        print(f"\n⚠️ Signal {signum} reçu - Arrêt en cours...")
        self.stop_event.set()
        self.transmission_active = False
    
    def initialize_hardware(self):
        """Initialise le matériel LoRa."""
        try:
            print("🔧 Initialisation du matériel LoRa...")
            self.sx1262.initialize_lora(
                sf=self.main_controller.sf,
                bw=self.main_controller.bw,
                cr=self.main_controller.cr
            )
            print("✅ Matériel LoRa prêt")
            
        except Exception as e:
            print(f"❌ Erreur initialisation matériel: {e}")
            raise
    
    def transmit_payloads(self, delay_between_frames: float = 1.0):
        """Transmet tous les payloads générés."""
        try:
            if not self.main_controller.final_results:
                print("⚠️ Aucun payload à transmettre")
                return False
            
            print(f"📡 Début transmission de {len(self.main_controller.final_results)} payloads")
            print(f"⏱️ Délai entre trames: {delay_between_frames:.1f}s")
            
            self.transmission_active = True
            transmitted_count = 0
            failed_count = 0
            
            for i, result in enumerate(self.main_controller.final_results):
                if self.stop_event.is_set():
                    print("\n⚠️ Transmission interrompue")
                    break
                
                print(f"\n📤 Transmission {i+1}/{len(self.main_controller.final_results)}")
                print(f"   Groupe {result['Group_ID']}: {result['Suffix_Count']} EPCs")
                
                # Reconstruction du payload
                payload = bytes.fromhex(result['Payload_Hex'])
                
                # Transmission
                success = self.sx1262.transmit_payload(payload)
                
                if success:
                    transmitted_count += 1
                    print(f"   ✅ Transmis ({result['T_frame_ms']:.2f}ms théorique)")
                else:
                    failed_count += 1
                    print(f"   ❌ Échec transmission")
                
                # Délai entre les transmissions
                if i < len(self.main_controller.final_results) - 1:
                    for remaining in range(int(delay_between_frames * 10), 0, -1):
                        if self.stop_event.is_set():
                            break
                        if remaining % 10 == 0:
                            print(f"   ⏳ Attente {remaining//10}s...", end='\r')
                        time.sleep(0.1)
                    print(" " * 20, end='\r')  # Efface le compteur
            
            self.transmission_active = False
            
            print(f"\n📊 Résumé transmission:")
            print(f"   • Réussies: {transmitted_count}")
            print(f"   • Échecs: {failed_count}")
            print(f"   • Total: {len(self.main_controller.final_results)}")
            
            return transmitted_count > 0
            
        except Exception as e:
            print(f"❌ Erreur durant la transmission: {e}")
            return False
    
    def run_complete_process_with_transmission(self, input_file: str = None, 
                                             transmit: bool = True, 
                                             delay_between_frames: float = 1.0):
        """Exécute le processus complet avec transmission LoRa."""
        try:
            print("🚀 PROCESSUS COMPLET RASPBERRY PI")
            print("=" * 80)
            print(f"📅 Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Étape 1: Traitement des EPCs
            print("\n🔄 Phase 1: Traitement des EPCs")
            result_file = self.main_controller.run_complete_process(input_file)
            
            if transmit:
                # Étape 2: Initialisation du matériel
                print("\n🔄 Phase 2: Initialisation du matériel LoRa")
                self.initialize_hardware()
                
                # Étape 3: Transmission
                print("\n🔄 Phase 3: Transmission LoRa")
                success = self.transmit_payloads(delay_between_frames)
                
                if success:
                    print("\n🎉 TRANSMISSION TERMINÉE AVEC SUCCÈS")
                else:
                    print("\n⚠️ TRANSMISSION TERMINÉE AVEC ERREURS")
            else:
                print("\n⏭️ Transmission désactivée")
            
            print(f"\n📁 Fichiers générés:")
            print(f"   • Log: rpi_processing.log")
            print(f"   • Optimisation: {self.main_controller.optimized_file}")
            print(f"   • Résultats finaux: {result_file}")
            
            return result_file
            
        except Exception as e:
            print(f"💥 Erreur processus complet: {e}")
            raise
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Nettoyage final."""
        print("\n🧹 Nettoyage en cours...")
        self.sx1262.cleanup()


def check_raspberry_pi():
    """Vérifie si on est sur un Raspberry Pi."""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            return 'Raspberry Pi' in model
    except:
        return False


def display_system_info():
    """Affiche les informations système."""
    print("🖥️ INFORMATIONS SYSTÈME")
    print("-" * 50)
    
    # Vérification Raspberry Pi
    is_rpi = check_raspberry_pi()
    print(f"Raspberry Pi détecté: {'✅ Oui' if is_rpi else '❌ Non'}")
    
    # Modules disponibles
    print(f"Modules SPI/GPIO: {'✅ Disponibles' if SPI_AVAILABLE else '❌ Manquants'}")
    
    # Informations système
    try:
        import platform
        print(f"Système: {platform.system()} {platform.release()}")
        print(f"Architecture: {platform.machine()}")
    except:
        pass
    
    print()


def interactive_config():
    """Configuration interactive."""
    print("🎛️ CONFIGURATION INTERACTIVE")
    print("-" * 50)
    
    # Configuration LoRaWAN
    try:
        sf = int(input("Spreading Factor (7-12) [12]: ") or "12")
        if sf not in range(7, 13):
            raise ValueError
    except ValueError:
        print("⚠️ SF invalide, utilisation de SF=12")
        sf = 12
    
    try:
        bw = int(input("Bandwidth kHz (125/250/500) [125]: ") or "125")
        if bw not in [125, 250, 500]:
            raise ValueError
    except ValueError:
        print("⚠️ BW invalide, utilisation de BW=125")
        bw = 125
    
    try:
        cr = int(input("Coding Rate (1-4) [1]: ") or "1")
        if cr not in range(1, 5):
            raise ValueError
    except ValueError:
        print("⚠️ CR invalide, utilisation de CR=1")
        cr = 1
    
    # Options de transmission
    transmit = input("Transmettre via LoRa ? (Y/n): ").lower().strip() not in ['n', 'no', 'non']
    
    delay = 1.0
    if transmit:
        try:
            delay = float(input("Délai entre trames (s) [1.0]: ") or "1.0")
        except ValueError:
            print("⚠️ Délai invalide, utilisation de 1.0s")
            delay = 1.0
    
    return sf, bw, cr, transmit, delay


def main():
    """Fonction principale."""
    print("🍓 RFID LoRaWAN Processing - Raspberry Pi Mode")
    print("=" * 80)
    
    # Informations système
    display_system_info()
    
    # Vérification des fichiers
    if not Path("EPCS.xlsx").exists():
        print("❌ Fichier EPCS.xlsx manquant")
        print("📋 Créez ce fichier avec vos EPCs RFID (24 caractères hex par ligne)")
        return
    
    try:
        # Configuration
        mode = input("Mode interactif ? (y/N): ").lower().strip()
        if mode in ['y', 'yes', 'o', 'oui']:
            sf, bw, cr, transmit, delay = interactive_config()
        else:
            sf, bw, cr, transmit, delay = 12, 125, 1, True, 1.0
            print(f"🔧 Configuration par défaut: SF={sf}, BW={bw}kHz, CR=4/{cr+4}")
            print(f"📡 Transmission: {'Activée' if transmit else 'Désactivée'}")
        
        print()
        
        # Initialisation du contrôleur
        controller = RPiMainController(sf, bw, cr)
        
        # Exécution du processus complet
        result_file = controller.run_complete_process_with_transmission(
            transmit=transmit,
            delay_between_frames=delay
        )
        
        print(f"\n🎉 PROCESSUS TERMINÉ")
        print(f"📁 Résultats dans: {result_file}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Processus interrompu par l'utilisateur")
        
    except Exception as e:
        print(f"\n💥 Erreur: {e}")
        print("📋 Consultez rpi_processing.log pour plus de détails")
        
    finally:
        print(f"\n📅 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("👋 Au revoir !")


if __name__ == "__main__":
    main()