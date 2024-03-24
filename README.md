# Network Error Correction Simulator

Error correction plays an essential role in computer networking as it ensures the integrity of data when it is transmitted over unreliable networks. This repository contains an implementation of a python client and server that perform data transmission using a stop-and-wait strategy for flow control and CRC-based error detection. 

## Overview

The application is divided into two main components: a server-side script and a client-side script. The server listens for incoming connections, manages client requests, and transmits a file with error correction mechanisms. The client initiates connections with the server, requests the server's file, and verifies the integrity of the received data.

## Prerequisites

This application requires that you have `python3` installed on your system.

## Scripts

- `server.py`: This script implements the server-side functionality. It handles incoming client connections, manages file transmission, and performs error correction using a stop-and-wait strategy and CRC error detection.

- `client.py`: The client-side script is responsible for initiating connections to the server, requesting files, and verifying the integrity of received data.

- `protocol_utils.py`: This module contains utility functions used by both the server and client. It includes functions for building frames, checking integrity, extracting payload data, and inducing errors for simulation purposes.

## Usage

First, clone the repository:

  ```
  git clone https://github.com/joaotav/network-error-correction.git
  ```

Run the server script to start the server:

  ```
  python3 server.py -p <SERVER_PORT> -f <FILENAME> -b <BUFFER_SIZE> -e <ERROR_RATE>
  ```

  Where:
   - `<SERVER_PORT>`: The port on which the server will listen for incoming connections on `127.0.0.1`.
   - `<FILENAME>`: The file to be sent to clients who connect to the server.
   - `<BUFFER_SIZE>`: Size of the message buffer.
   - `<ERROR_RATE>`: The probability to induce an error in each frame (0-99)

Next, run the client script to connect to the server and request the file:

  ```
  python3 client.py -s <SERVER_ADDR> -p <SERVER_PORT>
  ```

  Where:
   - `<SERVER_ADDR>`: The server's network address (`127.0.0.1`).
   - `<SERVER_PORT>`: The port on which the server is listening.

## Usage example:
> [!IMPORTANT]
> The application is limited to the transmission of text based files. However it can still be used to send images and other files if they are converted to a text-based format first (e.g, base64).

Let's transmit an image from the server to a client. Given that the application can only send text-based data, we can convert the example image included in this repository (`image.jpg`) into a text-based format by converting it to base64 before sending it. Use the following command on Linux or macOS:
  
```
base64 image.jpg > encoded_image.txt
```

Then, start server locally on port `5000`, configured to send `encoded_image.txt` with a buffer size of `1024` and an error rate of `5%`:

```
python3 server.py -p 5000 -f encoded_image.txt -b 1024 -e 5
```

Next, open a new window in your terminal application and start the client, specifying the server's address:

```
python3 client.py -s 127.0.0.1 -p 5000
```

The client will connect to the server and save the received file as `received_encoded_image.txt`. You can then convert the text-based data back into an image to verify that it has been correctly received. Use the following command:

```
base64 -d received_encoded_image.txt > received_image.jpg
```

You can now open the image check that it has been correctly received.
