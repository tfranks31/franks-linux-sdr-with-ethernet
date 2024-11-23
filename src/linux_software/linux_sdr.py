import argparse
import socket
import threading
import mmap
import os
import time

RADIO_PERIPH_ADDRESS = 0x43c00000
INPUT_OFFSET = 0x0
TUNE_OFFSET = 0x4
CONTROL_OFFSET = 0x8

RADIO_FIFO_ADDRESS = 0x43c10000
FIFO_RLR_OFFSET = 0x24
FIFO_RDFD_OFFSET = 0x20

devmem = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
ip = ""
send_over_ethernet = False
tune_frequency = 0
adc_frequency = 0




def print_welcome_message():
    print()
    print("Tyler Franks - Linux SDR With Ethernet")
    print("Welcome to Linux SDR With Ethernet")
    print("To use the application, type in the following commands and hit enter:")
    print(f"    T - Set the tune frequency of the radio - Current: {tune_frequency}")
    print(f"    F - Set the frequency piped into the radio - Current: {adc_frequency}")
    print(f"    S - Toggle on/off data streaming over ethernet - Current: {send_over_ethernet}")
    print("    H - Print this message again for help")


def radio_exfill():
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        packet_buf = bytearray()
        packet_num = 0
        packet_buf.extend(packet_num.to_bytes(4, "little"))
        
        memory = mmap.mmap(devmem, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=RADIO_FIFO_ADDRESS)
        while True:
            if (int.from_bytes(memory[FIFO_RLR_OFFSET:FIFO_RLR_OFFSET + 4], "little") & 0xFFF) > 0:
                data_word = memory[FIFO_RDFD_OFFSET:FIFO_RDFD_OFFSET + 4]
                if send_over_ethernet:
                    packet_buf.extend(data_word)
                    if len(packet_buf) == 1028:
                        udp_socket.sendto(packet_buf, (ip, 25344))
                        packet_buf = bytearray()
                        packet_num += 1
                        packet_buf.extend(packet_num.to_bytes(4, "little"))
            else:
                time.sleep(0.000001)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        udp_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure and stream radio data to the specified IP.")
    parser.add_argument("ip", help="Target IP address")

    args = parser.parse_args()

    ip = args.ip
    print(f"You have entered the ip address: {ip}")

    radio_exfill_thread = threading.Thread(target=radio_exfill, daemon=True)
    radio_exfill_thread.start()

    try:
        memory = mmap.mmap(devmem, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=RADIO_PERIPH_ADDRESS)
        memory[CONTROL_OFFSET:CONTROL_OFFSET + 4] = b"\x00\x00\x00\x01"
        time.sleep(0.01)
        memory[CONTROL_OFFSET:CONTROL_OFFSET + 4] = b"\x00\x00\x00\x00"

        tune_frequency = int.from_bytes(memory[TUNE_OFFSET:TUNE_OFFSET + 4], "little")
        adc_frequency = int.from_bytes(memory[INPUT_OFFSET:INPUT_OFFSET + 4], "little")

        print_welcome_message()

        while True:
            print()
            input_str = input("Enter a command: ")
            first_letter = ""
            for char in input_str:
                if char.isalpha():  # Check if the character is a letter
                    first_letter = char
                    break
            first_letter = first_letter.upper()

            if first_letter == "T":
                try:
                    new_frequency = int(input("Enter a tune frequency (0 - 134217727): "))
                    if new_frequency < 0 or new_frequency > 134217727:
                        print("Invalid tune frequency entered: Frequency not in range")
                    else:
                        memory[TUNE_OFFSET:TUNE_OFFSET + 4] = new_frequency.to_bytes(4, "little")
                        tune_frequency = new_frequency
                        print(f"Set tune frequency to: {new_frequency}")
                except Exception:
                    print("Invalid frequency entered")
            elif first_letter == "F":
                try:
                    new_frequency = int(input("Enter an input frequency (0 - 134217727): "))
                    if new_frequency < 0 or new_frequency > 134217727:
                        print("Invalid input frequency entered: Frequency not in range")
                    else:
                        memory[INPUT_OFFSET:INPUT_OFFSET + 4] = new_frequency.to_bytes(4, "little")
                        adc_frequency = new_frequency
                        print(f"Set input frequency to: {new_frequency}")
                except Exception:
                    print("Invalid frequency entered")
            elif first_letter == "S":
                send_over_ethernet = not send_over_ethernet
                print(f"Received Command S - Ethernet Streaming: {send_over_ethernet}")
            elif first_letter == "H":
                print_welcome_message()
            else:
                print("Command Invalid: Please enter a valid command")
                print_welcome_message()
    except Exception as e:
        print(f"Error: {e}")
    
