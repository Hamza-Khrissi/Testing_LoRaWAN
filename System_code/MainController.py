import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import traceback

# Import des classes existantes
from EPC_OPT import EPCAnalyzer
from Encapsulation import EPCLoRaWANCalculator


class MainController:
    """
    Classe de contrôle principale pour le traitement complet des EPCs RFID :
    1. Lecture du fichier EPCS.xlsx
    2. Optimisation via EPCAnalyzer
    3. Encapsulation LoRaWAN via EPCLoRaWANCalculator
    4. Export des résultats finaux
    """
    
    def __init__(self, sf: int = 12, bw: int = 125, cr: int = 1, log_file: str = "rfid_processing.log"):
        """
        Initialise le contrôleur principal.
        
        Args:
            sf (int): Spreading Factor LoRaWAN (7-12)
            bw (int): Bandwidth en kHz (125, 250, 500)
            cr (int): Coding Rate (1-4)
            log_file (str): Nom du fichier de log
        """
        self.sf = sf
        self.bw = bw
        self.cr = cr
        
        # Configuration des chemins de fichiers
        self.input_file = "EPCS.xlsx"
        self.optimized_file = "EPCSOPT.xlsx"
        self.final_output_file = "FinalOutput.xlsx"
        
        # Configuration du logging
        self.setup_logging(log_file)
        
        # Initialisation des composants
        self.epc_analyzer = EPCAnalyzer()
        self.lorawan_calculator = None
        
        # Stockage des résultats
        self.original_epcs = []
        self.optimized_df = None
        self.final_results = []
        
        self.logger.info(f"MainController initialisé - SF:{sf}, BW:{bw}kHz, CR:4/{cr+4}")
    
    def setup_logging(self, log_file: str):
        """Configure le système de logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_input_epcs(self, file_path: str = None) -> List[str]:
        """
        Charge les EPCs depuis le fichier d'entrée.
        
        Args:
            file_path (str): Chemin du fichier (optionnel, utilise self.input_file par défaut)
            
        Returns:
            List[str]: Liste des EPCs chargés
        """
        if file_path is None:
            file_path = self.input_file
            
        try:
            self.logger.info(f"Chargement des EPCs depuis {file_path}")
            self.original_epcs = self.epc_analyzer.load_epcs(file_path)
            self.logger.info(f"✅ {len(self.original_epcs)} EPCs chargés avec succès")
            return self.original_epcs
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du chargement des EPCs: {e}")
            raise
    
    def optimize_epcs(self) -> pd.DataFrame:
        """
        Optimise les EPCs via l'EPCAnalyzer.
        
        Returns:
            pd.DataFrame: DataFrame des résultats optimisés
        """
        try:
            if not self.original_epcs:
                raise ValueError("Aucun EPC chargé. Utilisez load_input_epcs() d'abord.")
            
            self.logger.info("Début de l'optimisation des EPCs")
            self.optimized_df = self.epc_analyzer.group_and_analyze(self.original_epcs)
            
            # Sauvegarde des résultats optimisés
            saved_path = self.epc_analyzer.save_results(self.optimized_df, self.optimized_file)
            if saved_path:
                self.logger.info(f"✅ Résultats optimisés sauvegardés dans {saved_path}")
            
            # Log du résumé d'optimisation
            total_groups = len(self.optimized_df)
            compressed_groups = len(self.optimized_df[self.optimized_df['Compression_%'] > 0])
            avg_compression = self.optimized_df['Compression_%'].mean()
            
            self.logger.info(f"📊 Optimisation terminée:")
            self.logger.info(f"   • Groupes créés: {total_groups}")
            self.logger.info(f"   • Groupes compressés: {compressed_groups}")
            self.logger.info(f"   • Compression moyenne: {avg_compression:.1f}%")
            
            return self.optimized_df
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'optimisation: {e}")
            raise
    
    def create_lorawan_calculator(self) -> EPCLoRaWANCalculator:
        """
        Crée et configure le calculateur LoRaWAN avec les EPCs optimisés.
        
        Returns:
            EPCLoRaWANCalculator: Instance configurée
        """
        try:
            if self.optimized_df is None:
                raise ValueError("Aucune optimisation disponible. Utilisez optimize_epcs() d'abord.")
            
            self.logger.info("Initialisation du calculateur LoRaWAN")
            
            # Passage des EPCs et du DataFrame optimisé au calculateur
            epc_input = (self.original_epcs, self.optimized_df)
            
            self.lorawan_calculator = EPCLoRaWANCalculator(
                sf=self.sf,
                bw=self.bw,
                cr=self.cr,
                epc_input=epc_input
            )
            
            self.logger.info("✅ Calculateur LoRaWAN initialisé")
            return self.lorawan_calculator
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'initialisation du calculateur: {e}")
            raise
    
    def process_groups_to_payloads(self) -> List[Dict]:
        """
        Traite chaque groupe optimisé pour générer les payloads LoRaWAN.
        
        Returns:
            List[Dict]: Liste des résultats finaux
        """
        try:
            if self.lorawan_calculator is None:
                self.create_lorawan_calculator()
            
            self.logger.info("Génération des payloads LoRaWAN")
            self.final_results = []
            
            for idx, row in self.optimized_df.iterrows():
                group_id = row['Group_ID']
                prefix = row['Prefix']
                suffix_count = row['Suffix_Count']
                
                # Récupération des EPCs du groupe
                if not prefix:  # Groupe non compressé
                    # Prendre les EPCs restants (logique simplifiée)
                    group_epcs = [epc for epc in self.original_epcs 
                                if not any(epc.startswith(other_row['Prefix']) 
                                         for _, other_row in self.optimized_df.iterrows() 
                                         if other_row['Prefix'] and other_row.name != idx)][:suffix_count]
                else:
                    # EPCs avec ce préfixe
                    group_epcs = [epc for epc in self.original_epcs 
                                if epc.startswith(prefix)][:suffix_count]
                
                if len(group_epcs) != suffix_count:
                    self.logger.warning(f"⚠️ Groupe {group_id}: {len(group_epcs)} EPCs trouvés au lieu de {suffix_count}")
                
                # Génération du payload LoRaWAN pour ce groupe
                try:
                    payload = self.lorawan_calculator.create_lorawan_payload(group_epcs, group_id - 1)
                    payload_hex = payload.hex().upper()
                    
                    # Calcul des paramètres LoRaWAN
                    params = self.lorawan_calculator.calculate_airtime_parameters(len(payload))
                    
                    # Décodage pour vérification
                    decoded = self.lorawan_calculator.decode_payload(payload)
                    
                    result = {
                        'Group_ID': group_id,
                        'Prefix': prefix,
                        'Suffix_Count': suffix_count,
                        'EPCs': group_epcs,
                        'Payload_Hex': payload_hex,
                        'Payload_Bytes': len(payload),
                        'T_frame_ms': params['T_frame_ms'],
                        'T_sym_ms': params['T_sym_ms'],
                        'N_payload': params['N_payload'],
                        'Decoded_EPCs': decoded['epcs'],
                        'Verification_OK': decoded['epcs'] == group_epcs
                    }
                    
                    self.final_results.append(result)
                    
                    self.logger.info(f"✅ Groupe {group_id}: Payload généré ({len(payload)} octets, {params['T_frame_ms']:.2f}ms)")
                    
                except Exception as e:
                    self.logger.error(f"❌ Erreur groupe {group_id}: {e}")
                    continue
            
            self.logger.info(f"🎯 {len(self.final_results)} payloads générés avec succès")
            return self.final_results
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la génération des payloads: {e}")
            raise
    
    def save_final_results(self, output_file: str = None) -> str:
        """
        Sauvegarde les résultats finaux dans un fichier Excel.
        
        Args:
            output_file (str): Chemin du fichier de sortie
            
        Returns:
            str: Chemin du fichier sauvegardé
        """
        try:
            if output_file is None:
                output_file = self.final_output_file
            
            if not self.final_results:
                raise ValueError("Aucun résultat à sauvegarder. Utilisez process_groups_to_payloads() d'abord.")
            
            # Préparation des données pour Excel
            excel_data = []
            
            for result in self.final_results:
                # Formatage des EPCs pour l'affichage
                epcs_display = '\n'.join(result['EPCs'])
                decoded_epcs_display = '\n'.join(result['Decoded_EPCs'])
                
                excel_data.append({
                    'Group_ID': result['Group_ID'],
                    'Prefix': result['Prefix'],
                    'Suffix_Count': result['Suffix_Count'],
                    'Original_EPCs': epcs_display,
                    'Payload_Hex': result['Payload_Hex'],
                    'Payload_Bytes': result['Payload_Bytes'],
                    'T_frame_ms': round(result['T_frame_ms'], 2),
                    'T_sym_ms': round(result['T_sym_ms'], 2),
                    'N_payload': result['N_payload'],
                    'Decoded_EPCs': decoded_epcs_display,
                    'Verification_OK': result['Verification_OK']
                })
            
            df_final = pd.DataFrame(excel_data)
            
            # Sauvegarde Excel
            df_final.to_excel(output_file, index=False, engine='openpyxl')
            
            self.logger.info(f"✅ Résultats finaux sauvegardés dans {output_file}")
            
            # Statistiques finales
            total_epcs = sum(result['Suffix_Count'] for result in self.final_results)
            total_payload_bytes = sum(result['Payload_Bytes'] for result in self.final_results)
            avg_frame_time = sum(result['T_frame_ms'] for result in self.final_results) / len(self.final_results)
            
            self.logger.info(f"📈 Statistiques finales:")
            self.logger.info(f"   • Total EPCs traités: {total_epcs}")
            self.logger.info(f"   • Total payload bytes: {total_payload_bytes}")
            self.logger.info(f"   • Temps de trame moyen: {avg_frame_time:.2f}ms")
            self.logger.info(f"   • Groupes générés: {len(self.final_results)}")
            
            return output_file
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la sauvegarde: {e}")
            raise
    
    def run_complete_process(self, input_file: str = None) -> str:
        """
        Exécute le processus complet de traitement des EPCs.
        
        Args:
            input_file (str): Fichier d'entrée (optionnel)
            
        Returns:
            str: Chemin du fichier de résultats finaux
        """
        try:
            start_time = datetime.now()
            self.logger.info("🚀 DÉBUT DU PROCESSUS COMPLET")
            
            # Étape 1: Chargement des EPCs
            self.load_input_epcs(input_file)
            
            # Étape 2: Optimisation
            self.optimize_epcs()
            
            # Étape 3: Création du calculateur LoRaWAN
            self.create_lorawan_calculator()
            
            # Étape 4: Génération des payloads
            self.process_groups_to_payloads()
            
            # Étape 5: Sauvegarde des résultats
            output_file = self.save_final_results()
            
            # Temps de traitement
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            self.logger.info(f"🎉 PROCESSUS TERMINÉ avec succès en {processing_time:.2f}s")
            self.logger.info(f"📁 Fichiers générés:")
            self.logger.info(f"   • Optimisation: {self.optimized_file}")
            self.logger.info(f"   • Résultats finaux: {output_file}")
            
            return output_file
            
        except Exception as e:
            self.logger.error(f"💥 ÉCHEC DU PROCESSUS: {e}")
            self.logger.error(f"Détails de l'erreur:\n{traceback.format_exc()}")
            raise


if __name__ == "__main__":
    # Test de la classe
    try:
        controller = MainController(sf=12, bw=125, cr=1)
        result_file = controller.run_complete_process()
        print(f"✅ Traitement terminé. Résultats dans: {result_file}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")