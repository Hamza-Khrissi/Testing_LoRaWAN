#!/usr/bin/env python3
"""
main_test_pc.py - Clean test script for PC (Visual Studio Code)
Complete RFID EPC processing via LoRaWAN without real transmission.
"""

import os
import sys
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd

def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = ['pandas', 'openpyxl']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing packages: " + ", ".join(missing_packages))
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_main_controller():
    """Check if MainController can be imported."""
    try:
        from MainController import MainController
        return MainController
    except ImportError as e:
        print("Error importing MainController: " + str(e))
        print("Required files:")
        print("- MainController.py")
        print("- EPC_OPT.py") 
        print("- Encapsulation.py")
        return None

def check_input_files():
    """Check if required input files exist."""
    required_files = ["EPCS.xlsx"]
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("Missing files: " + ", ".join(missing_files))
        return False
    
    return True

def create_sample_epcs_file():
    """Create a sample EPCS.xlsx file."""
    try:
        sample_epcs = [
            "E28011606000020000003039",
            "E28011606000020000003040", 
            "E28011606000020000003041",
            "E28011606000020000003042",
            "E28011606000030000004001",
            "E28011606000030000004002",
            "E28011606000030000004003",
            "ABCDEF1234567890ABCDEF12",
            "123456789ABCDEF123456789"
        ]
        
        # Create DataFrame with simple column name
        df = pd.DataFrame(sample_epcs, columns=['EPC'])
        
        # Save with explicit encoding and engine
        df.to_excel("EPCS.xlsx", index=False, header=False, engine='openpyxl')
        print("Sample EPCS.xlsx file created with 9 test EPCs")
        return True
        
    except Exception as e:
        print("Error creating sample file: " + str(e))
        return False

def get_user_input(prompt, default_value, valid_values=None, value_type=str):
    """Get user input with validation."""
    try:
        full_prompt = prompt + " [" + str(default_value) + "]: "
        user_input = input(full_prompt).strip()
        
        if not user_input:
            return default_value
        
        # Convert to appropriate type
        if value_type == int:
            user_input = int(user_input)
        
        # Validate if valid_values provided
        if valid_values and user_input not in valid_values:
            print("Invalid value. Using default: " + str(default_value))
            return default_value
            
        return user_input
        
    except ValueError:
        print("Invalid input. Using default: " + str(default_value))
        return default_value

def interactive_mode():
    """Interactive mode for testing different configurations."""
    print("\nINTERACTIVE MODE")
    print("=" * 50)
    
    print("LoRaWAN Parameters:")
    sf = get_user_input("Spreading Factor (7-12)", 12, range(7, 13), int)
    bw = get_user_input("Bandwidth kHz (125/250/500)", 125, [125, 250, 500], int)
    cr = get_user_input("Coding Rate (1-4 for 4/5-4/8)", 1, range(1, 5), int)
    
    return sf, bw, cr

def display_configuration(controller):
    """Display system configuration."""
    print("\n" + "=" * 80)
    print("SYSTEM CONFIGURATION")
    print("=" * 80)
    print("LoRaWAN Parameters:")
    print("  Spreading Factor (SF): " + str(controller.sf))
    print("  Bandwidth (BW): " + str(controller.bw) + " kHz")
    print("  Coding Rate (CR): 4/" + str(controller.cr + 4))
    print("Files:")
    print("  Input: " + str(controller.input_file))
    print("  Optimization: " + str(controller.optimized_file))
    print("  Final output: " + str(controller.final_output_file))

def display_results_summary(controller):
    """Display results summary."""
    if not hasattr(controller, 'final_results') or not controller.final_results:
        print("No results to display")
        return
    
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    total_epcs = sum(result.get('Suffix_Count', 0) for result in controller.final_results)
    total_payload_bytes = sum(result.get('Payload_Bytes', 0) for result in controller.final_results)
    total_frame_time = sum(result.get('T_frame_ms', 0) for result in controller.final_results)
    
    if len(controller.final_results) > 0:
        avg_frame_time = total_frame_time / len(controller.final_results)
    else:
        avg_frame_time = 0
    
    print("Global Statistics:")
    print("  EPCs processed: " + str(total_epcs))
    print("  Groups generated: " + str(len(controller.final_results)))
    print("  Total payload: " + str(total_payload_bytes) + " bytes")
    print("  Average frame time: " + "{:.2f}".format(avg_frame_time) + " ms")
    print("  Total transmission time: " + "{:.2f}".format(total_frame_time) + " ms")
    
    print("\nDetails by group:")
    for result in controller.final_results:
        verification = "OK" if result.get('Verification_OK', False) else "ERROR"
        group_id = result.get('Group_ID', 'N/A')
        suffix_count = result.get('Suffix_Count', 0)
        payload_bytes = result.get('Payload_Bytes', 0)
        frame_time = result.get('T_frame_ms', 0)
        
        print("  Group " + str(group_id) + ": " + str(suffix_count) + " EPCs, " + 
              str(payload_bytes) + " bytes, " + "{:.2f}".format(frame_time) + "ms " + verification)
    
    # Display compression info if available
    if hasattr(controller, 'optimized_df') and controller.optimized_df is not None:
        try:
            avg_compression = controller.optimized_df['Compression_%'].mean()
            compressed_groups = len(controller.optimized_df[controller.optimized_df['Compression_%'] > 0])
            print("\nCompression:")
            print("  Compressed groups: " + str(compressed_groups) + "/" + str(len(controller.optimized_df)))
            print("  Average rate: " + "{:.1f}".format(avg_compression) + "%")
        except KeyError:
            print("\nCompression info not available")

def main():
    """Main function of the test script."""
    print("RFID LoRaWAN Processing - PC Test Mode")
    print("=" * 80)
    print("Start: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    try:
        # Check environment
        print("\nChecking environment...")
        
        # Check dependencies
        if not check_dependencies():
            return 1
        print("Dependencies OK")
        
        # Check MainController
        MainController = check_main_controller()
        if MainController is None:
            return 1
        print("MainController OK")
        
        # Interactive or automatic mode
        mode = input("\nInteractive mode? (y/N): ").lower().strip()
        if mode in ['y', 'yes', 'o', 'oui']:
            sf, bw, cr = interactive_mode()
        else:
            # Default configuration
            sf, bw, cr = 12, 125, 1
            print("Default configuration: SF=" + str(sf) + ", BW=" + str(bw) + "kHz, CR=4/" + str(cr+4))
        
        # Check input files
        print("\nChecking input files...")
        if not check_input_files():
            create_sample = input("Create sample file? (Y/n): ").lower().strip()
            if create_sample not in ['n', 'no', 'non']:
                if not create_sample_epcs_file():
                    return 1
                print("You can now modify EPCS.xlsx with your own EPCs")
                proceed = input("Continue with sample file? (Y/n): ").lower().strip()
                if proceed in ['n', 'no', 'non']:
                    print("Stopping program")
                    return 0
            else:
                print("Stopping program")
                return 0
        else:
            print("Input files OK")
        
        # Initialize controller
        print("\nInitializing controller...")
        controller = MainController(sf=sf, bw=bw, cr=cr, log_file="test_processing.log")
        
        # Display configuration
        display_configuration(controller)
        
        # Start processing
        print("\nStarting processing...")
        print("This may take a moment...")
        
        start_time = datetime.now()
        result_file = controller.run_complete_process()
        end_time = datetime.now()
        
        # Display results
        display_results_summary(controller)
        
        processing_time = (end_time - start_time).total_seconds()
        print("\n" + "=" * 80)
        print("PROCESSING COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("Processing time: " + "{:.2f}".format(processing_time) + " seconds")
        print("Generated files:")
        print("  Log: test_processing.log")
        if hasattr(controller, 'optimized_file'):
            print("  Optimization: " + str(controller.optimized_file))
        print("  Final results: " + str(result_file))
        
        # Option to display payloads
        show_payloads = input("\nDisplay hex payloads? (y/N): ").lower().strip()
        if show_payloads in ['y', 'yes', 'o', 'oui']:
            print("\nGENERATED LORAWAN PAYLOADS:")
            print("-" * 80)
            for result in controller.final_results:
                group_id = result.get('Group_ID', 'N/A')
                payload_hex = result.get('Payload_Hex', 'N/A')
                payload_bytes = result.get('Payload_Bytes', 0)
                frame_time = result.get('T_frame_ms', 0)
                
                print("Group " + str(group_id) + ": " + str(payload_hex))
                print("         (" + str(payload_bytes) + " bytes, " + "{:.2f}".format(frame_time) + "ms)")
        
        print("\nYou can now open the Excel files to analyze the results")
        return 0
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        return 1
        
    except Exception as e:
        print("\nError during processing: " + str(e))
        print("Check test_processing.log for more details")
        print("Full error traceback:")
        traceback.print_exc()
        return 1
        
    finally:
        print("\nEnd: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("Goodbye!")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)