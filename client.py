#!usr/bin/env python3
import socket, argparse, sys, os
from uuid import getnode
from protocol_utils import *
from select import select

'''
    Implemented by João Otávio Chervinski - 2018

    The format of the frames used is as follows:
    | Destination MAC (12 bytes) | Source MAC (12 bytes)| Frame number (1 byte)|
    Data (1 - 8128 bytes) | CRC-32 (10 bytes) |
'''


def check_arguments(parser):
    if len(sys.argv) < 4: # If not enough arguments are passed
        parser.print_help() # Displays argument help
        raise SystemExit

    args = parser.parse_args()

    return args


class Client(object):
    def __init__(self, server):
        self.server = server # Server socket information
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.message = ''
        self.data = ''
        self.address = hex(getnode())[2:] # Client MAC address
        self.buffer_size = 0 # Header size + payload (0 for now)
        self.server_address = None


    def request_data(self):
        ''' Requests data from the server '''
        # Initial frames (acknowledgement frames) do not know the destination MAC and are not numbered
        # When the transmission starts, both sides will already know the MACs, and the frames will be numbered
        starting_frame = build_frame('000000000000', self.address, '/', 'request_data')
        self.socket.sendto(starting_frame, self.server) # Sends request to the server
        message = recv_message(self.socket, 512)
        if check_integrity(message):
            if extract_payload(message) == 'request_accepted': # If the server accepts the request
                message = recv_message(self.socket, 512) # Retrieve configuration messages
                if check_integrity(message): # If the message is intact
                    self.server_address = message[12:24] # Gets the server MAC
                    self.buffer_size = int(extract_payload(message)) # Gets the buffer size
                    confirmation_frame = build_frame(self.server_address, self.address, '/', 'OK') # Indicates that the data has been received
                    self.socket.sendto(confirmation_frame, self.server)
                    self.receive_file()

        else:
            print('[-] Failed to request data, please try again.')
            raise SystemExit


    def save_file(self, filename, data):
        ''' Saves received data to a file '''
        with open(filename, 'w') as f:
            f.write(self.data)


    def display_progress(self, received, total, filename, server_socket):
        ''' Displays file receiving progress '''
        os.system('clear')
        print("[+] Receiving file '{}' from {}.".format(filename, server_socket[0]))
        print("[+] Received: {0:.2f}%".format(received * 100 / total))


    def receive_file(self):
        ''' Manages file receiving '''
        total_frames = int(extract_payload(recv_message(self.socket, self.buffer_size))) # Receives the total number of parts
        filename = extract_payload(recv_message(self.socket, self.buffer_size)) # Receives the filename
        ready_frame = build_frame(self.server_address, self.address, '/', 'ready') # Notifies the server that it's ready to receive data
        self.socket.sendto(ready_frame, self.server)
        print("[+] Receiving file '{}'.".format(filename))

        timeout = 0
        received_frames = 0
        frame_no = -1
        percentage = 0
        error_count = 0
        while received_frames < total_frames: # While not all frames are received
            self.display_progress(received_frames, total_frames, filename, self.server) # Displays progress on the screen

            while True:
                if timeout > 10:
                    # If the server stopped sending frames
                    print("[-] The server stopped responding. Quitting.")
                    raise SystemExit

                received = select([self.socket], [], [], 3) # Waits for a response for 3 seconds
                if received[0]: # If a new data is received on the socket
                    frame = recv_message(self.socket, self.buffer_size) # Receives the frame
                    if check_integrity(frame): # If the content is intact
                        if get_frame_no(frame) == next_frame(frame_no): # If it's the next frame in sequence
                            received_data = extract_payload(frame) # Extracts data from the frame
                            self.data += received_data
                            frame_no = next_frame(frame_no) # Advances the frame number
                            received_frames += 1 # Increases the number of received frames

                            # Constructs the message with the ACK of the last received frame
                            ack = build_frame(self.server_address, self.address, frame_no, 'ACK' + str(frame_no))
                            timeout = 0
                            self.socket.sendto(ack, self.server)
                            break # Exit loop to wait for another frame


                    else: # If the frame arrived corrupted, request it again
                        error_count += 1
                        ack = build_frame(self.server_address, self.address, frame_no, 'ACK' + str(frame_no))
                        self.socket.sendto(ack, self.server)


                else:
                    # If the server resent the last frame, or the current frame didn't arrive at the client
                    # Sends the ACK of the last frame, requesting the next frame
                    ack = build_frame(self.server_address, self.address, frame_no, 'ACK' + str(frame_no))
                    self.socket.sendto(ack, self.server)
                    timeout += 1 # Increment timeout counter

        os.system('clear')
        self.display_progress(received_frames, total_frames, filename, self.server)
        print("[+] Transmission completed.\n")
        print("[+] Corrupted frames received during transmission: {}".format(error_count))
        self.save_file('received_' + filename, self.data) # Saves the received file
        print("[+] File has been saved as '{}'.".format('received_' + filename))

def main(args):
    SERVER_ADDR = args.server_addr # Server address
    SERVER_PORT = args.server_port # Server port
    client = Client((SERVER_ADDR, SERVER_PORT)) # Creates a client instance
    client.request_data()


if __name__ == '__main__':

    # Handles arguments passed from the command line
    parser = argparse.ArgumentParser(description='Connection details.')
    parser.add_argument('-s', dest='server_addr', help="The server's address.", required=True)
    parser.add_argument('-p', type=int, dest='server_port', help='The port on which the server is listening.',
    required=True)

    if len(sys.argv) < 4: # If not enough arguments are passed
        parser.print_help() # Displays argument help
        raise SystemExit

    args = check_arguments(parser)
    main(args)
