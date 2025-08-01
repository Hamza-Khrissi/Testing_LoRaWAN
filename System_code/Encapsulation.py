import random
import struct
import math
import pandas as pd
from typing import List, Dict, Optional, Union, Tuple
from datetime import datetime

class EPCLoRaWANCalculator:
    """
    Calculateur LoRaWAN pour encapsuler les EPCs RFID avec calculs de temps d'antenne.
    """
    
    def __init__(self, sf: int = 12, bw: int = 125, cr: int = 1, payload_size: int = None, epc_input: Union[List[str], Tuple[List[str], pd.DataFrame]] = None):
        """
        Initialise le calculateur avec les paramètres LoRaWAN.
        
        Args:
            sf (int): Spreading Factor (7-12)
            bw (int): Bandwidth en kHz (125, 250, 500)
            cr (int): Coding Rate (1-4 pour 4/5, 4/6, 4/7, 4/8)
            payload_size (int): Taille max du payload (calculée auto si None)
            epc_input: Either a list of 24-char hex EPCs or a tuple of (epc_list, optimized_df)
        """
        self.sf = sf
        self.bw = bw
        self.cr = cr
        self.epc_size_bytes = 12  # 24 caractères hex = 12 octets
        self.header_size = 4  # 4 octets pour l'en-tête
        
        # Calcul de la taille max du payload selon le SF
        if payload_size is None:
            self.max_payload_size = self._calculate_max_payload_size()
        else:
            self.max_payload_size = payload_size
            
        self.max_epcs_per_packet = (self.max_payload_size - self.header_size) // self.epc_size_bytes
        
        # Handle EPC input
        if epc_input is None:
            self.epc_list = []
        elif isinstance(epc_input, tuple) and len(epc_input) == 2:
            epc_list, optimized_df = epc_input
            self.epc_list = self._reconstruct_epcs_from_df(epc_list, optimized_df)
        else:
            self.epc_list = epc_input
        
        self._validate_epcs()
        
        print(f"=== CONFIGURATION LoRaWAN ===")
        print(f"SF: {self.sf}, BW: {self.bw} kHz, CR: 4/{self.cr + 4}")
        print(f"Taille max payload: {self.max_payload_size} octets")
        print(f"EPCs max par trame: {self.max_epcs_per_packet}")
        print()
    
    def _calculate_max_payload_size(self) -> int:
        """Calcule la taille max du payload selon le SF."""
        sf_limits = {7: 230, 8: 230, 9: 123, 10: 59, 11: 59, 12: 51}
        return sf_limits.get(self.sf, 51)
    
    def _reconstruct_epcs_from_df(self, epc_list: List[str], optimized_df: pd.DataFrame) -> List[str]:
        """
        Reconstruct full 24-character EPCs from optimized DataFrame and original EPC list.
        
        Args:
            epc_list (List[str]): List of original 24-character EPCs
            optimized_df (pd.DataFrame): DataFrame with 'Prefix' and 'Suffix_Count' columns
            
        Returns:
            List[str]: List of reconstructed 24-character EPCs
        """
        reconstructed_epcs = []
        used_epcs = set()
        
        for _, row in optimized_df.iterrows():
            prefix = row['Prefix']
            suffix_count = row['Suffix_Count']
            
            if not prefix:  # Single EPC group (no compression)
                matching_epcs = [epc for epc in epc_list if epc not in used_epcs][:suffix_count]
            else:
                matching_epcs = [epc for epc in epc_list if epc.startswith(prefix) and epc not in used_epcs][:suffix_count]
            
            if len(matching_epcs) != suffix_count:
                raise ValueError(f"Could not reconstruct {suffix_count} EPCs for prefix '{prefix}'")
            
            reconstructed_epcs.extend(matching_epcs)
            used_epcs.update(matching_epcs)
        
        if len(reconstructed_epcs) != len(epc_list):
            raise ValueError(f"Reconstructed EPC count ({len(reconstructed_epcs)}) does not match original ({len(epc_list)})")
        
        return reconstructed_epcs
    
    def _validate_epcs(self):
        """Validate that all EPCs are 24-character hexadecimal strings."""
        for epc in self.epc_list:
            if len(epc) != 24 or not all(c in '0123456789ABCDEFabcdef' for c in epc):
                raise ValueError(f"Invalid EPC format: {epc}")
    
    def generate_random_epc(self, n: int = 1) -> List[str]:
        """
        Génère n EPCs RFID aléatoires.
        
        Args:
            n (int): Nombre d'EPCs à générer
            
        Returns:
            List[str]: Liste des EPCs
        """
        epcs = []
        for _ in range(n):
            epc = ''.join(random.choices('0123456789ABCDEF', k=24))
            epcs.append(epc)
        return epcs
    
    def calculate_airtime_parameters(self, payload_bytes: int) -> Dict:
        """
        Calcule les paramètres de temps d'antenne selon le tableau fourni.
        
        Args:
            payload_bytes (int): Taille du payload en octets
            
        Returns:
            Dict: Paramètres calculés
        """
        T_sym = (2**self.sf) / (self.bw * 1000)  # Durée d'un symbole en secondes
        T_pream = (8 + 4.25) * T_sym  # Durée du préambule
        
        PL_H = 1 if self.sf >= 11 else 0  # Header présent si SF >= 11
        N_payload = 8 + max(((8 * payload_bytes - 4 * self.sf + 28 + 16 - 20 * PL_H) / (4 * (self.sf - 2))), 0) * (self.cr + 4)
        
        T_payload = N_payload * T_sym  # Durée payload
        T_frame = T_pream + T_payload  # Durée totale de la trame
        
        EPC_frame = math.floor((self.max_payload_size - self.header_size) / self.epc_size_bytes)
        
        return {
            'T_sym_ms': T_sym * 1000,
            'T_pream_ms': T_pream * 1000,
            'N_payload': N_payload,
            'T_payload_ms': T_payload * 1000,
            'T_frame_ms': T_frame * 1000,
            'EPC_frame': EPC_frame
        }
    
    def calculate_transmission_plan(self, total_epcs: int) -> Dict:
        """
        Calcule le plan de transmission pour un nombre d'EPCs donné.
        
        Args:
            total_epcs (int): Nombre total d'EPCs à transmettre
            
        Returns:
            Dict: Plan de transmission
        """
        N_frames = math.ceil(total_epcs / self.max_epcs_per_packet)
        
        params_700 = self.calculate_airtime_parameters(self.max_payload_size)
        T_frame_700 = params_700['T_frame_ms']
        T_batch_700 = math.ceil(700 / self.max_epcs_per_packet) * T_frame_700
        
        params_current = self.calculate_airtime_parameters(self.max_payload_size)
        T_frame_current = params_current['T_frame_ms']
        T_batch_current = N_frames * T_frame_current
        
        T_max_per_day = 864000  # 1% de 24h en ms
        lots_per_day = math.floor(T_max_per_day / T_batch_current)
        
        return {
            'total_epcs': total_epcs,
            'frames_needed': N_frames,
            'epcs_per_frame': self.max_epcs_per_packet,
            'frame_duration_ms': T_frame_current,
            'batch_duration_ms': T_batch_current,
            'batch_duration_s': T_batch_current / 1000,
            'max_batches_per_day': lots_per_day,
            'max_epcs_per_day': lots_per_day * total_epcs,
            'parameters': params_current
        }
    
    def create_packet_header(self, packet_id: int, epc_count: int) -> bytes:
        """Crée l'en-tête du packet LoRaWAN."""
        timestamp = int(datetime.now().timestamp()) & 0xFFFF
        return struct.pack('>BBH', packet_id & 0xFF, epc_count & 0xFF, timestamp)
    
    def create_lorawan_payload(self, epcs: List[str], packet_id: int = 0) -> bytes:
        """Crée un payload LoRaWAN à partir d'une liste d'EPCs."""
        if len(epcs) > self.max_epcs_per_packet:
            raise ValueError(f"Trop d'EPCs pour un seul packet. Max: {self.max_epcs_per_packet}")
        
        header = self.create_packet_header(packet_id, len(epcs))
        epc_bytes = b''.join(bytes.fromhex(epc) for epc in epcs)
        
        return header + epc_bytes
    
    def decode_payload(self, payload: bytes) -> Dict:
        """Décode un payload LoRaWAN pour extraire les informations."""
        if len(payload) < self.header_size:
            raise ValueError("Payload trop court")
        
        packet_id, epc_count, timestamp = struct.unpack('>BBH', payload[:4])
        
        epc_data = payload[4:]
        epcs = []
        
        for i in range(epc_count):
            start_idx = i * self.epc_size_bytes
            end_idx = start_idx + self.epc_size_bytes
            
            if end_idx > len(epc_data):
                break
                
            epc_bytes = epc_data[start_idx:end_idx]
            epc_hex = epc_bytes.hex().upper()
            epcs.append(epc_hex)
        
        return {
            'packet_id': packet_id,
            'epc_count': epc_count,
            'timestamp': timestamp,
            'epcs': epcs
        }
    
    def process_epcs(self, epc_count: int) -> Dict:
        """
        Traite un nombre d'EPCs et retourne les résultats complets.
        
        Args:
            epc_count (int): Nombre d'EPCs à traiter
            
        Returns:
            Dict: Résultats complets
        """
        if len(self.epc_list) < epc_count:
            raise ValueError(f"Not enough EPCs provided. Required: {epc_count}, Available: {len(self.epc_list)}")
        
        epcs = self.epc_list[:epc_count]
        
        print(f"EPCs à traiter: {len(epcs)}")
        for i, epc in enumerate(epcs):
            print(f"  EPC {i+1}: {epc}")
        
        payloads = []
        payload_details = []
        
        for i in range(0, len(epcs), self.max_epcs_per_packet):
            packet_epcs = epcs[i:i + self.max_epcs_per_packet]
            payload = self.create_lorawan_payload(packet_epcs, i // self.max_epcs_per_packet)
            payloads.append(payload)
            
            params = self.calculate_airtime_parameters(len(payload))
            
            payload_details.append({
                'payload': payload,
                'epcs': packet_epcs,
                'params': params
            })
        
        print(f"\nPayloads LoRaWAN créés: {len(payloads)}")
        
        for i, detail in enumerate(payload_details):
            payload = detail['payload']
            packet_epcs = detail['epcs']
            params = detail['params']
            
            print(f"  Payload {i+1}: {payload.hex().upper()} ({len(payload)} octets)")
            
            decoded = self.decode_payload(payload)
            print(f"    Packet ID: {decoded['packet_id']}, EPCs: {decoded['epc_count']}")
            print(f"    EPCs décodés: {decoded['epcs']}")
            
            print(f"    CALCULS LoRaWAN:")
            print(f"      • Durée symbole (T_sym): {params['T_sym_ms']:.2f} ms")
            print(f"      • Durée préambule (T_pream): {params['T_pream_ms']:.2f} ms")
            print(f"      • Nombre symboles payload (N_payload): {params['N_payload']:.0f}")
            print(f"      • Durée payload (T_payload): {params['T_payload_ms']:.2f} ms")
            print(f"      • Durée totale trame (T_frame): {params['T_frame_ms']:.2f} ms")
            print(f"      • EPCs max par trame: {params['EPC_frame']}")
            print()
        
        plan = self.calculate_transmission_plan(epc_count)
        
        print(f"=== RÉSUMÉ TRANSMISSION ===")
        print(f"Total EPCs traités: {epc_count}")
        print(f"Nombre de trames: {plan['frames_needed']}")
        print(f"Durée totale du lot: {plan['batch_duration_s']:.2f} s")
        print(f"Débit max par jour (1% duty): {plan['max_epcs_per_day']:,} EPCs/jour")
        
        return {
            'epcs': epcs,
            'payloads': payloads,
            'plan': plan,
            'payload_details': payload_details
        }