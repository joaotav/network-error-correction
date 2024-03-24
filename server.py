#!usr/bin/env python3
import socket, argparse, sys, os
from select import select
from uuid import getnode
from protocol_utils import *
from math import ceil
from time import sleep

'''
    Implemented by João Otávio Chervinski - 2018

    The format of the frames used is as follows:
    | Destination MAC (12 bytes) | Source MAC (12 bytes)| Frame number (1 byte)|
    Data (1 - 8128 bytes) | CRC-32 (10 bytes) |
'''

def check_arguments(parser):
    if len(sys.argv) < 8: # If not enough arguments are passed
        parser.print_help() # Display argument help
        raise SystemExit

    args = parser.parse_args()

    if args.buffer_size < 1 or args.buffer_size > 65536000000:
        print("Please choose a buffer size between 1 and 65536 (inclusive).")
        raise SystemExit

    if args.error_rate < 0 or args.error_rate > 100:
        print("Please choose an error probability between 0 and 100 (inclusive).")
        raise SystemExit

    return args

class Server(object):
    def __init__(self, host, port, filename, buffer_size, error_rate):
        self.host = host # IP address
        self.port = port # Service port
        self.filename = filename # Name of the file to be shared
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Creates the UDP socket
        self.message = ''
        self.data = ''
        self.address = hex(getnode())[2:] # Server's physical address
        self.buffer_size = 35 + buffer_size # Header size plus payload
        self.payload_size = buffer_size # The size of the useful content of the frame
        self.error_rate = error_rate
        self.setup()
        self.load_file()

    def setup(self):
        ''' Initializes the socket '''
        self.socket.bind((self.host, self.port)) # Binds the server to listen on this address and port

    def load_file(self):
        '''Loads the PPM file data into memory as binary data.'''
        with open(self.filename, 'rb') as f:  # Note the 'rb' mode for binary read
            self.data = f.read()  # Directly reads the binary data into the variable

    # def load_file(self):
    #     ''' Loads the file data to be sent into memory '''
    #     with open(self.filename) as f:
    #         self.data = f.read().encode() # Loads the file data into the variable

    def handle_requests(self):
        ''' This function handles requests received by the server '''
        print("[*] Waiting for incoming requests...")
        while True:
            try:
                message, client = self.socket.recvfrom(512) # Receives requests
                message = message.decode() # Decodes the message

                if check_integrity(message): # If the message arrived without errors
                    if extract_payload(message) == 'request_data': # If it's a data request
                        client_address = message[:12] # Client's MAC address
                        print("[*] Received request from: %s:%d" % (client[0], client[1]))
                        self.client_handler(client, client_address)
                        print("[*] Waiting for incoming requests...")
                else:
                    # If the request arrived corrupted
                    print("[-] Failed to start transmission.")

            except (KeyboardInterrupt, SystemExit):
                print('[-] Exiting server...')
                self.socket.close()
                raise SystemExit

    def configure_connection(self, client_socket, client_address):
        # Creates and sends the connection acceptance frame
        acceptance_frame = build_frame(client_address, self.address, '/', 'request_accepted')
        self.socket.sendto(acceptance_frame, client_socket)

        # Creates and sends a frame informing the buffer size
        buffer_info = build_frame(client_address, self.address, '/', self.buffer_size)
        self.socket.sendto(buffer_info, client_socket)

        # Checks if the client received the data
        message = recv_message(self.socket, self.buffer_size)
        if check_integrity(message):
            if extract_payload(message) == 'OK': # Client received buffer information
                return
        else:
            print("[-] Failed to start transmission.")
            raise SystemExit

    def send_file_info(self, client_socket, client_address):
        ''' Sends information about the file to be sent '''
        parts = ceil(len(self.data) / self.payload_size) # Number of frames to be sent
        size_info = build_frame(client_address, self.address, '/', parts)
        self.socket.sendto(size_info, client_socket)
        filename_info = build_frame(client_address, self.address, '/', self.filename) # File name
        self.socket.sendto(filename_info, client_socket)

    def display_progress(self, sent, total, client_socket):
        ''' Displays the amount of data already sent '''
        os.system('clear')
        print("[+] Sending file '{}' to {}.".format(self.filename, client_socket[0]))
        print("[+] Sent: {0:.2f}%".format(sent * 100 / total))


    def send_file(self, client_socket, client_address):
        ''' Envia o arquivo para o cliente e gerencia a conexão '''
        total_frames = ceil(len(self.data) / self.payload_size) # Number of frames to be sent
        sent_frames = 0
        frame_no = 0
        index = 0 # Indexes up to where the data has been sent

        while sent_frames < total_frames: # While the server has not sent all the file data
            self.display_progress(sent_frames, total_frames, client_socket)
            retry = 0
            if index + self.payload_size < len(self.data):
                # If the remaining data is larger than the payload size
                payload = self.data[index:(index + self.payload_size)]
                frame = build_frame(client_address, self.address, frame_no, payload)
            else:
                # If the remaining data fits within the payload size
                payload = self.data[index:]
                frame = build_frame(client_address, self.address, frame_no, payload)

            while True: # While the acknowledgement has not been received
                try:
                    # If the connection is lost, retry until a threshold is reached
                    self.socket.sendto(induce_errors(frame, self.error_rate), client_socket)
                    retry += 1
                    if retry > 10:
                        raise OSError

                except OSError:
                    # Se o máximo de tentativas foi atingido, gera um timeout e aguarda novas conexões
                    if retry > 10:
                        print("[-] Connection with client {} timed out.".format(client_socket[0]))
                        return

                    print("[*] Connection lost. Attempting to reestablish.")
                    retry += 1

                received = select([self.socket], [], [], 3) # Waits 3 seconds for a reply
                if received[0]: # If new data is received on the socket
                    retry = 0 # Reset the number of failed attempts
                    response = recv_message(self.socket, self.buffer_size) # Retrieve the message
                    if check_integrity(response): # If the message's contents were not corrupted
                        response = extract_payload(response) # Extract payload
                        if response[:3] == "ACK": # If an acknowledgement was received
                            ack_frame = int(response[3]) # Check which frame was received
                            if ack_frame == frame_no:
                                frame_no = next_frame(frame_no) 
                                index += self.payload_size # Advance the index on the remaining data
                                sent_frames += 1 # Increases the number of sent frames
                                break 

                            elif is_previous_frame(frame_no, ack_frame):
                                # If the received ACK corresponds to the previous frame, the current 
                                # frame didn't reach the receiver, the client suffered a timeout and
                                # sent the previous ACK again, so it's expecting the current frame
                                self.socket.sendto(frame, client_socket) # Resends the current frame


                else: # If a timeout occurred, return to the beginning and resend the frame
                    continue

        os.system('clear')
        self.display_progress(sent_frames, total_frames, client_socket) # Show transmission progress
        print("[+] Transmission completed.\n")


    def client_handler(self, client_socket, client_address):
        ''' Essa função gerencia a conexão com os clientes '''
        self.configure_connection(client_socket, client_address) # Configure the connection (buffer and addresses)
        self.send_file_info(client_socket, client_address) # Send file data (name, extension, size)
        message = recv_message(self.socket, self.buffer_size)
        if check_integrity(message):
            if extract_payload(message) == 'ready': # If the client is ready to receive the data
                print("[+] Starting transmission...")
                self.send_file(client_socket, client_address) # Begin file transmission


def main(args):
    HOST_ADDR = '0.0.0.0' # Server address
    UDP_PORT = args.server_port # Server port
    BUFFER = args.buffer_size
    error_rate = args.error_rate # Probability of introducing errors in transmission
    filename = args.filename # File to be transmitted by the server
    server = Server(HOST_ADDR, UDP_PORT, filename, BUFFER, error_rate) # Creates a server instance
    server.handle_requests() # Wait for and manage requests


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Server details.')
    parser.add_argument('-p', type=int, dest='server_port', help='The port used by the server to accept incoming connections.',
    required=True)
    parser.add_argument('-f', dest='filename', help='The file which will be sent to clients who connect to the server.',
    required=True)
    parser.add_argument('-b', type=int, dest='buffer_size', help='Size of the message buffer.',
    required=True)
    parser.add_argument('-e', type=int, dest='error_rate', help="The probability to induce an error in each frame (0-99)",
    required=True)

    args = check_arguments(parser)
    main(args)
